"""Offline model boundary for parallel native task execution in a real Gateway."""

from threading import Barrier

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

CHILDREN = ("alpha", "bravo")
_both_running = Barrier(2)


@tool
def lookup_marker(key: str) -> str:
    """Look up a marker for the test assignment."""
    return f"child-only evidence for {key}"


class HistoryModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "offline-subagent-history"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        prompt = str(next(message.content for message in reversed(messages) if isinstance(message, HumanMessage)))
        if "record a follow-up" in prompt:
            answer = AIMessage(content="follow-up complete")
        elif "delegate both assignments" in prompt:
            if any(isinstance(message, ToolMessage) and message.name == "task" for message in messages):
                answer = AIMessage(content="parent finished")
            else:
                calls = [{"name": "task", "args": {"prompt": f"investigate {key}", "subagent_type": "general-purpose"}, "id": f"delegate-{key}"} for key in CHILDREN]
                answer = AIMessage(content="", tool_calls=calls)
        else:
            key = next(key for key in CHILDREN if f"investigate {key}" in prompt)
            if any(isinstance(message, ToolMessage) and message.name == "lookup_marker" for message in messages):
                answer = AIMessage(content=f"report for {key}")
            else:
                # Both child graphs must actually reach the model concurrently.
                _both_running.wait(timeout=20)
                answer = AIMessage(content="", tool_calls=[{"name": "lookup_marker", "args": {"key": key}, "id": f"lookup-{key}"}])
        return ChatResult(generations=[ChatGeneration(message=answer)])
