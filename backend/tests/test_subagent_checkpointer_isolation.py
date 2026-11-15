"""A default native child must never inherit its parent's synchronous saver."""

import importlib.util
import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from deerflow.agents.middlewares import tool_error_handling_middleware
from deerflow.config.app_config import AppConfig
from deerflow.subagents.config import SubagentConfig


@pytest.mark.asyncio
async def test_default_child_disables_inherited_checkpointer(monkeypatch):
    # conftest installs a stub at the production import path. A private module
    # name leaves the real packages and the stub used by other tests intact.
    path = Path(__file__).parents[1] / "packages/harness/deerflow/subagents/executor.py"
    spec = importlib.util.spec_from_file_location("_checkpoint_isolation_executor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)

    model = FakeListChatModel(responses=["done"])
    monkeypatch.setattr(module, "create_chat_model", lambda **kwargs: model)
    monkeypatch.setattr(tool_error_handling_middleware, "build_subagent_runtime_middlewares", lambda **kwargs: [])
    config = AppConfig.model_validate({"sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"}})
    executor = module.SubagentExecutor(
        config=SubagentConfig(name="probe", description="Check native child isolation", model="offline"),
        tools=[],
        app_config=config,
    )

    agent = await executor._create_agent()

    assert agent.checkpointer is False
