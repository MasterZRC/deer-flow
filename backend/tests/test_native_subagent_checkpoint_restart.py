"""Run two native tasks, restart the Gateway, then inspect their SQLite history."""

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from support.subagent_history_model import CHILDREN

BACKEND = Path(__file__).resolve().parents[1]


@contextmanager
def _gateway(home, generation):
    env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG") if key in os.environ}
    env.update(
        DEER_FLOW_HOME=str(home),
        DEER_FLOW_PROJECT_ROOT=str(home),
        DEER_FLOW_CONFIG_PATH=str(home / "config.yaml"),
        DEER_FLOW_EXTENSIONS_CONFIG_PATH=str(home / "extensions.json"),
        DEER_FLOW_ENV_FILE=str(home / "empty.env"),
        DEER_FLOW_AUTH_DISABLED="1",
        PYTHONIOENCODING="utf-8",
        PYTHONPATH=os.pathsep.join(str(path) for path in (BACKEND, BACKEND / "tests", BACKEND / "packages/harness", BACKEND / "packages/extension-api")),
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log_path = home / f"gateway-{generation}.log"
    with log_path.open("w", encoding="utf-8") as log, httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=60) as client:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.gateway.app:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"], cwd=home, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                assert process.poll() is None, log_path.read_text(encoding="utf-8")
                try:
                    if client.get("/health").is_success:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(0.05)
            else:
                raise AssertionError(log_path.read_text(encoding="utf-8"))
            yield client
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=15)


def test_parallel_task_histories_remain_isolated_after_gateway_restart(tmp_path):
    model = "support.subagent_history_model"
    config = {
        "models": [{"name": "offline", "use": model + ":HistoryModel", "model": "offline", "supports_tool_calling": True}],
        "sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"},
        "skills": {"path": str(tmp_path / "skills")},
        "tool_groups": [{"name": "lookup"}],
        "tools": [{"name": "lookup_marker", "group": "lookup", "use": model + ":lookup_marker"}],
        "title": {"enabled": False},
        "memory": {"enabled": False},
        "summarization": {"enabled": False},
        "tool_search": {"enabled": False},
        "database": {"backend": "sqlite", "sqlite_dir": str(tmp_path / "db")},
        "run_events": {"backend": "memory"},
        "subagent_runtime": {"checkpoint_history": True},
    }
    (tmp_path / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    (tmp_path / "extensions.json").write_text("{}", encoding="utf-8")
    (tmp_path / "empty.env").touch()
    with _gateway(tmp_path, 1) as client:
        thread_id = client.post("/api/threads", json={}).raise_for_status().json()["thread_id"]
        path = f"/api/threads/{thread_id}"
        body = {"assistant_id": "lead_agent", "input": {"messages": [{"role": "user", "content": "delegate both assignments"}]}, "context": {"subagent_enabled": True}}
        state = client.post(path + "/runs/wait", json=body).raise_for_status().json()
        reports = {m["tool_call_id"]: m["content"] for m in state["messages"] if m.get("name") == "task"}
        assert set(reports) == {f"delegate-{key}" for key in CHILDREN}, state
        for key in CHILDREN:
            assert f"report for {key}" in reports[f"delegate-{key}"], reports
        (run,) = client.get(path + "/runs").raise_for_status().json()
        run_id = run["run_id"]
        events_url = f"{path}/runs/{run_id}/events"
        assert client.get(events_url).raise_for_status().json()
        # A client annotating a follow-up can use the same metadata names.
        # Only the persisted namespace identifies a native child trajectory.
        follow_up = {
            "assistant_id": "lead_agent",
            "input": {"messages": [{"role": "user", "content": "record a follow-up"}]},
            "metadata": {"subagent_parent_run_id": run_id, "subagent_execution_id": str(uuid4()), "subagent_tool_call_id": "parent-annotation"},
        }
        result = client.post(path + "/runs/wait", json=follow_up).raise_for_status().json()
        assert result["messages"][-1]["content"] == "follow-up complete"

    with _gateway(tmp_path, 2) as client:
        assert client.get(events_url).raise_for_status().json() == []
        head = client.post(path + "/history", json={"limit": 1}).raise_for_status().json()[0]
        assert head["values"]["messages"][-1]["content"] == "follow-up complete"
        assert all(m.get("name") != "lookup_marker" for m in head["values"]["messages"])

        with SqliteSaver.from_conn_string(str(tmp_path / "db" / "deerflow.db")) as saver:
            root = {"configurable": {"thread_id": thread_id}}
            candidates = list(saver.list(root, filter={"subagent_parent_run_id": run_id}))
            assert any(row.config["configurable"]["checkpoint_ns"] == "" for row in candidates)
            rows = [row for row in candidates if row.config["configurable"]["checkpoint_ns"].split("|")[-1] == f"deerflow_native_task:{row.metadata.get('subagent_execution_id')}"]
            calls = {row.metadata["subagent_tool_call_id"] for row in rows}
            assert calls == {f"delegate-{key}" for key in CHILDREN}
            namespaces, executions = set(), set()
            for key in CHILDREN:
                child = [row for row in rows if row.metadata["subagent_tool_call_id"] == f"delegate-{key}"]
                (namespace,) = {row.config["configurable"]["checkpoint_ns"] for row in child}
                (execution,) = {row.metadata["subagent_execution_id"] for row in child}
                assert str(UUID(execution)) == execution
                assert namespace and namespace not in namespaces
                assert execution and execution not in executions
                namespaces.add(namespace)
                executions.add(execution)
                # A pre-tool snapshot and a completed one distinguish a trajectory
                # from a saved copy of the report returned to the parent.
                earlier = [row.checkpoint["channel_values"].get("messages", []) for row in child[1:]]
                pending = [snapshot[-1] for snapshot in earlier if snapshot and isinstance(snapshot[-1], AIMessage)]
                assert any(call["id"] == f"lookup-{key}" for message in pending for call in message.tool_calls)
                messages = child[0].checkpoint["channel_values"]["messages"]
                assert {m.content for m in messages if isinstance(m, ToolMessage)} == {f"child-only evidence for {key}"}
                assert isinstance(messages[-1], AIMessage)
                assert messages[-1].content == f"report for {key}"
