"""
可观测性 callback handler（finagent-research）。

与 finagent-core 的 handler 同款，区别：
- 多一个 service 字段（标记 finagent-research），便于在统一 MongoDB 里区分两个项目
- 挂在 LangGraph StateGraph 的 ainvoke/astream 上

原理相同：LangGraph 节点里的 LLM 调用是 LangChain Runnable，
callback 沿调用树（contextvar）传播，所以 4 个 Agent 节点的 LLM 调用都会被捕获。
"""

import time
from datetime import datetime
from typing import Any, Optional

from langchain_core.callbacks.base import BaseCallbackHandler

from deep_research.observability.store import trace_store


class ObservabilityHandler(BaseCallbackHandler):
    def __init__(
        self,
        trace_id: str,
        session_id: str = "",
        service: str = "finagent-research",
    ) -> None:
        self.trace_id = trace_id
        self.session_id = session_id
        self.service = service
        self._starts: dict[str, dict] = {}

    # ---------- LLM ----------
    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kwargs):
        self._starts[str(run_id)] = {
            "t": time.time(), "type": "llm",
            "name": self._model_name(serialized, kwargs), "parent": parent_run_id,
        }

    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id=None, **kwargs):
        self._starts[str(run_id)] = {
            "t": time.time(), "type": "llm",
            "name": self._model_name(serialized, kwargs), "parent": parent_run_id,
        }

    def on_llm_end(self, response, *, run_id, **kwargs):
        info = self._starts.pop(str(run_id), None)
        if info:
            self._record(info, run_id, "success", self._extract_usage(response))

    def on_llm_error(self, error, *, run_id, **kwargs):
        info = self._starts.pop(str(run_id), None)
        if info:
            self._record(info, run_id, "error", {
                "error_type": type(error).__name__, "error_message": str(error)[:500]})

    # ---------- 工具 ----------
    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs):
        self._starts[str(run_id)] = {
            "t": time.time(), "type": "tool",
            "name": (serialized or {}).get("name", "unknown"), "parent": parent_run_id,
        }

    def on_tool_end(self, output, *, run_id, **kwargs):
        info = self._starts.pop(str(run_id), None)
        if info:
            self._record(info, run_id, "success", {})

    def on_tool_error(self, error, *, run_id, **kwargs):
        info = self._starts.pop(str(run_id), None)
        if info:
            self._record(info, run_id, "error", {
                "error_type": type(error).__name__, "error_message": str(error)[:500]})

    # ---------- 辅助 ----------
    def _model_name(self, serialized: Optional[dict], kwargs: dict) -> str:
        if serialized and isinstance(serialized.get("kwargs"), dict):
            m = serialized["kwargs"].get("model") or serialized["kwargs"].get("model_name")
            if m:
                return m
        inv = kwargs.get("invocation_params") or {}
        return inv.get("model") or inv.get("model_name") or "unknown"

    def _extract_usage(self, response: Any) -> dict:
        usage = {}
        try:
            out = getattr(response, "llm_output", None) or {}
            tu = out.get("token_usage") or out.get("usage") or {}
            if tu:
                usage = {
                    "prompt_tokens": tu.get("prompt_tokens", 0),
                    "completion_tokens": tu.get("completion_tokens", 0),
                    "total_tokens": tu.get("total_tokens", 0),
                }
            else:
                msg = response.generations[0][0].message
                um = getattr(msg, "usage_metadata", None) or {}
                if um:
                    usage = {
                        "prompt_tokens": um.get("input_tokens", 0),
                        "completion_tokens": um.get("output_tokens", 0),
                        "total_tokens": um.get("total_tokens", 0),
                    }
        except Exception:  # noqa: BLE001
            pass
        return usage

    def _record(self, info: dict, run_id, status: str, extra: dict) -> None:
        doc = {
            "trace_id": self.trace_id,
            "span_id": str(run_id),
            "parent_span_id": str(info["parent"]) if info.get("parent") else None,
            "type": info["type"],
            "name": info["name"],
            "session_id": self.session_id,
            "service": self.service,          # 区分项目
            "latency_ms": int((time.time() - info["t"]) * 1000),
            "status": status,
            "ts": datetime.utcnow(),
        }
        doc.update(extra or {})
        trace_store.save(doc)
