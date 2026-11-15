"""Gateway-owned checkpoint history for ordinary native task executions."""

import asyncio
import threading
from collections.abc import AsyncIterator
from concurrent.futures import Future
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import var_child_runnable_config
from langgraph._internal._constants import (
    CONFIG_KEY_CHECKPOINT_MAP,
    CONFIG_KEY_CHECKPOINTER,
    CONFIG_KEY_RUNTIME,
    CONFIG_KEY_STREAM,
    CONFIG_KEY_STREAM_MESSAGES_V2,
    CONFIG_KEY_TASK_ID,
    NS_SEP,
)
from langgraph.types import Checkpointer

from deerflow.config.app_config import AppConfig
from deerflow.config.database_config import CheckpointChannelMode
from deerflow.runtime.checkpoint_mode import inject_checkpoint_mode
from deerflow.runtime.checkpointer.async_provider import make_checkpointer
from deerflow.runtime.context_keys import NATIVE_TASK_CHECKPOINT_NS_PREFIX
from deerflow.runtime.runs.stream_cleanup import close_agent_stream
from deerflow.utils.file_io import await_drained

# The process owns the isolated loop, while each Gateway owns its own admission
# fence. Either shutdown may start first; they share the same close receipts.
_writers_lock = threading.Lock()
_writers: dict[Future[None], tuple["SubagentCheckpointHistory", str, asyncio.Task]] = {}
_stopping_loops: set[asyncio.AbstractEventLoop] = set()


async def _wait_for_closes(receipts: list[Future[None]]) -> None:
    await asyncio.gather(*(asyncio.wrap_future(receipt) for receipt in receipts))


def _cancel_writer(writer: asyncio.Task) -> None:
    # Both shutdown paths make this decision on the writer's event loop.
    # A second cancel could interrupt the first cancellation's cleanup.
    if not writer.cancelling():
        writer.cancel()


def drain_checkpoint_writers_before_loop_exit(loop: asyncio.AbstractEventLoop) -> None:
    """Called on the owning thread after run_forever returns, before loop.close."""
    with _writers_lock:
        active = {writer for _, _, writer in _writers.values() if writer.get_loop() is loop}
        if not active:
            return
        _stopping_loops.add(loop)
    try:
        for writer in active:
            _cancel_writer(writer)
        loop.run_until_complete(asyncio.gather(*active, return_exceptions=True))
    finally:
        with _writers_lock:
            _stopping_loops.discard(loop)


class SubagentCheckpointHistory:
    def __init__(self, startup_config: AppConfig):
        self._startup_config = startup_config
        self._closed = False

    @property
    def channel_mode(self) -> CheckpointChannelMode:
        return self._startup_config.database.checkpoint_channel_mode

    @asynccontextmanager
    async def open(self, thread_id: str, cancel_event: threading.Event) -> AsyncIterator[Checkpointer]:
        """Open, use and close one saver on the execution's own event loop."""
        writer = asyncio.current_task()
        assert writer is not None
        done: Future[None] = Future()
        with _writers_lock:
            if self._closed or writer.get_loop() in _stopping_loops:
                raise RuntimeError("Native subagent checkpoint history is shutting down")
            # Timeout can publish to the parent before the child has entered
            # its stream. After deletion or rollback observes zero writers,
            # that cancelled dispatch must not open the old thread again.
            if cancel_event.is_set():
                raise asyncio.CancelledError
            _writers[done] = self, thread_id, writer
        try:
            async with make_checkpointer(self._startup_config) as saver:
                yield saver
        finally:
            with _writers_lock:
                _writers.pop(done)
                done.set_result(None)

    def has_writer_for_thread(self, thread_id: str) -> bool:
        with _writers_lock:
            return any(owner is self and thread == thread_id for owner, thread, _ in _writers.values())

    async def wait_for_thread(self, thread_id: str) -> None:
        with _writers_lock:
            receipts = [receipt for receipt, (owner, thread, _) in _writers.items() if owner is self and thread == thread_id]
        if receipts:
            await await_drained(_wait_for_closes(receipts))

    async def aclose(self) -> None:
        """Fence admission, then wait for remaining streams and their SQLite writes."""
        with _writers_lock:
            first_close = not self._closed
            self._closed = True
            writers = {receipt: writer for receipt, (owner, _, writer) in _writers.items() if owner is self}
            if first_close:
                for writer in set(writers.values()):
                    writer.get_loop().call_soon_threadsafe(_cancel_writer, writer)
        if writers:
            await await_drained(_wait_for_closes(list(writers)))

    async def stream(
        self,
        agent: Any,
        state: dict,
        config: RunnableConfig,
        context: dict,
        *,
        execution_id: str,
        tool_call_id: str | None,
        cancel_event: threading.Event,
    ) -> AsyncIterator[dict]:
        async with self.open(context["thread_id"], cancel_event) as saver:
            # Explicit checkpoint coordinates discard the ambient configurable
            # in LangGraph. Keep the stream and the parent's checkpoint map,
            # but never inherit its saver, replay cursor or mutable scratchpad.
            parent = (var_child_runnable_config.get() or {}).get("configurable", {})
            child = {key: parent[key] for key in (CONFIG_KEY_STREAM, CONFIG_KEY_STREAM_MESSAGES_V2, CONFIG_KEY_RUNTIME, CONFIG_KEY_CHECKPOINT_MAP) if key in parent}
            namespace = f"{NATIVE_TASK_CHECKPOINT_NS_PREFIX}{execution_id}"
            if parent_ns := parent.get("checkpoint_ns"):
                namespace = f"{parent_ns}{NS_SEP}{namespace}"
            child.update(
                thread_id=context["thread_id"],
                checkpoint_ns=namespace,
            )
            # LangGraph resets a non-empty namespace to root for a standalone
            # invocation. Mark this graph as the dispatched child task.
            child[CONFIG_KEY_TASK_ID] = execution_id
            child[CONFIG_KEY_CHECKPOINTER] = saver
            metadata = {
                **(config.get("metadata") or {}),
                "subagent_parent_run_id": context["run_id"],
                "subagent_execution_id": execution_id,
                "subagent_tool_call_id": tool_call_id,
            }
            config = {**config, "configurable": child, "metadata": metadata}
            inject_checkpoint_mode(config, self.channel_mode)
            stream = agent.astream(state, config=config, context=context, stream_mode="values")
            try:
                async for chunk in stream:
                    yield chunk
            finally:
                await close_agent_stream(stream)
