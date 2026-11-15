import asyncio
import threading
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_history_shutdown_drains_owner_loop_close_and_fences_new_children(monkeypatch):
    from deerflow.subagents import checkpoint_history

    gateway_loop = asyncio.get_running_loop()
    opened = asyncio.Event()
    closing = asyncio.Event()
    allow_close = threading.Event()
    closed = threading.Event()
    loops = []

    @asynccontextmanager
    async def saver(_config):
        loops.append(asyncio.get_running_loop())
        gateway_loop.call_soon_threadsafe(opened.set)
        try:
            yield object()
        finally:
            gateway_loop.call_soon_threadsafe(closing.set)
            assert await asyncio.to_thread(allow_close.wait, 5)
            loops.append(asyncio.get_running_loop())
            closed.set()

    monkeypatch.setattr(checkpoint_history, "make_checkpointer", saver)
    history = checkpoint_history.SubagentCheckpointHistory(object())

    async def child():
        async with history.open("thread", threading.Event()):
            await asyncio.Event().wait()

    worker = asyncio.create_task(asyncio.to_thread(asyncio.run, child()))
    try:
        await asyncio.wait_for(opened.wait(), 5)
        assert history.has_writer_for_thread("thread")
        assert not history.has_writer_for_thread("other-thread")
        shutdown = asyncio.create_task(history.aclose())
        await asyncio.wait_for(closing.wait(), 5)
        with pytest.raises(RuntimeError, match="shutting down"):
            async with history.open("thread", threading.Event()):
                pytest.fail("shutdown must fence new history writers")
        assert not shutdown.done()
        assert history.has_writer_for_thread("thread")
        allow_close.set()
        await asyncio.wait_for(shutdown, 5)
        assert closed.is_set()
        assert not history.has_writer_for_thread("thread")
        assert len(loops) == 2 and loops[0] is loops[1]
        assert loops[0] is not asyncio.get_running_loop()
    finally:
        allow_close.set()
        await history.aclose()
        with suppress(asyncio.CancelledError):
            await worker


@pytest.mark.asyncio
async def test_late_cancelled_dispatch_cannot_reopen_deleted_thread(tmp_path):
    from deerflow.config.app_config import AppConfig
    from deerflow.subagents.checkpoint_history import SubagentCheckpointHistory

    config = AppConfig.model_validate({"sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"}, "database": {"backend": "sqlite", "sqlite_dir": str(tmp_path)}})
    history = SubagentCheckpointHistory(config)
    cancelled = threading.Event()
    cancelled.set()
    assert not history.has_writer_for_thread("thread")
    with pytest.raises(asyncio.CancelledError):
        async with history.open("thread", cancelled):
            pytest.fail("an expired dispatch acquired a writer after the deletion guard")
    assert not list(tmp_path.iterdir())
    async with history.open("thread", threading.Event()):
        assert history.has_writer_for_thread("thread")
    assert not history.has_writer_for_thread("thread")
    await history.aclose()


def test_gateway_close_during_loop_drain_only_cancels_writer_once(tmp_path):
    from deerflow.config.app_config import AppConfig
    from deerflow.subagents.checkpoint_history import SubagentCheckpointHistory, drain_checkpoint_writers_before_loop_exit

    config = AppConfig.model_validate({"sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"}, "database": {"backend": "sqlite", "sqlite_dir": str(tmp_path)}})
    history = SubagentCheckpointHistory(config)
    closing, release, cleanup_finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    loop = asyncio.new_event_loop()
    started = loop.create_future()

    async def writer():
        async with history.open("thread", threading.Event()):
            try:
                started.set_result(None)
                await asyncio.Event().wait()
            finally:
                closing.set()
                await release.wait()
                cleanup_finished.set()

    async def close_gateway():
        await closing.wait()
        loop.call_soon(release.set)
        await history.aclose()

    child = loop.create_task(writer())
    gateway = loop.create_task(close_gateway())
    try:
        loop.run_until_complete(asyncio.wait({started, child}, return_when=asyncio.FIRST_COMPLETED))
        assert started.done()
        drain_checkpoint_writers_before_loop_exit(loop)
        loop.run_until_complete(gateway)
        assert child.cancelled()
        assert cleanup_finished.is_set()
        assert child.cancelling() == 1
        assert not history.has_writer_for_thread("thread")
    finally:
        release.set()
        child.cancel()
        gateway.cancel()
        loop.run_until_complete(asyncio.gather(child, gateway, return_exceptions=True))
        loop.close()


@pytest.mark.asyncio
async def test_delta_child_history_materializes_after_reopening_sqlite(tmp_path):
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.runnables.config import var_child_runnable_config
    from langgraph.graph import StateGraph

    from deerflow.agents.thread_state import get_thread_state_schema
    from deerflow.config.app_config import AppConfig
    from deerflow.runtime.checkpoint_mode import CHECKPOINT_MODE_METADATA_KEY
    from deerflow.runtime.checkpoint_state import CheckpointStateAccessor
    from deerflow.runtime.checkpointer.async_provider import make_checkpointer
    from deerflow.subagents.checkpoint_history import SubagentCheckpointHistory

    config = AppConfig.model_validate({"sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"}, "database": {"backend": "sqlite", "sqlite_dir": str(tmp_path), "checkpoint_channel_mode": "delta"}})
    history = SubagentCheckpointHistory(config)
    graph = StateGraph(get_thread_state_schema(history.channel_mode))
    graph.add_node("answer", lambda state: {"messages": [AIMessage(content=state["messages"][-1].content + " done")]})
    graph.set_entry_point("answer")
    graph.set_finish_point("answer")

    owner = {"configurable": {"thread_id": "parent-thread"}}
    parent_checkpoint = str(uuid4())
    inherited = {"configurable": {**owner["configurable"], "checkpoint_ns": "tools:parent", "checkpoint_map": {"": parent_checkpoint}, "checkpoint_id": parent_checkpoint}}
    token = var_child_runnable_config.set(inherited)
    runs = ["parent-run-a", "parent-run-b"]
    try:
        for run in runs:
            chunks = [
                value
                async for value in history.stream(
                    graph.compile(),
                    {"messages": [HumanMessage(content=run)]},
                    {},
                    {"thread_id": "parent-thread", "run_id": run},
                    execution_id=str(uuid4()),
                    tool_call_id="reused-provider-id",
                    cancel_event=threading.Event(),
                )
            ]
            assert chunks[-1]["messages"][-1].content == run + " done"
    finally:
        var_child_runnable_config.reset(token)
        await history.aclose()

    async with make_checkpointer(config) as reopened:
        reader = CheckpointStateAccessor.bind(graph.compile(), reopened, mode="delta", direct_namespace=True)
        namespaces = set()
        for run in runs:
            rows = [row async for row in reopened.alist(owner, filter={"subagent_parent_run_id": run})]
            assert rows and rows[0].metadata["parents"] == {"": parent_checkpoint}
            assert rows[0].metadata[CHECKPOINT_MODE_METADATA_KEY] == "delta"
            namespaces.add(rows[0].config["configurable"]["checkpoint_ns"])
            snapshot = await reader.aget(rows[0].config)
            assert [message.content for message in snapshot.values["messages"]] == [run, run + " done"]
        assert len(namespaces) == 2
        assert await reopened.aget_tuple(owner) is None
