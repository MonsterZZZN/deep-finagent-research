"""
finagent-research FastAPI 服务。

暴露 POST /research/stream（SSE 流式）：
- 研究过程中实时推送进度事件（规划/搜索/撰写/审核）
- 最后推送 complete 事件，带完整研究报告

被 finagent-core 的 research-proxy 调用。

启动（在 src 目录下）：
    python -m deep_research.api.server
"""

import json
import uuid

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from deep_research import config
from deep_research.graph import get_graph
from deep_research.observability.handler import ObservabilityHandler
from deep_research.state import create_initial_state

app = FastAPI(title="finagent-research", version="1.0.0")


class ResearchRequest(BaseModel):
    query: str
    session_id: str | None = None
    max_iterations: int = 2
    trace_id: str | None = None  # 由 finagent-core 传入，实现跨服务全链路追踪


@app.get("/health")
async def health():
    return {"status": "ok", "service": "finagent-research"}


@app.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """深度研究，SSE 流式返回进度 + 最终报告。"""
    session_id = req.session_id or uuid.uuid4().hex[:16]

    async def event_generator():
        state = create_initial_state(req.query, session_id, req.max_iterations)
        graph = get_graph()
        final_state = state
        sent = 0  # 已推送的消息数

        # 可观测性 handler：trace_id 优先用调用方传入的（跨服务全链路追踪）
        handler = ObservabilityHandler(
            trace_id=req.trace_id or session_id,
            session_id=session_id,
            service="finagent-research",
        )

        try:
            # stream_mode="values"：每个超步后产出完整状态
            async for s in graph.astream(
                state,
                stream_mode="values",
                config={"recursion_limit": 50, "callbacks": [handler]},
            ):
                final_state = s
                msgs = s.get("messages", [])
                # 推送新增的进度消息
                for m in msgs[sent:]:
                    yield {
                        "event": "progress",
                        "data": json.dumps(
                            {
                                "phase": s.get("phase"),
                                "type": m.get("type"),
                                "agent": m.get("agent"),
                                "content": m.get("content"),
                            },
                            ensure_ascii=False,
                        ),
                    }
                sent = len(msgs)

            # 完成：推送最终报告
            yield {
                "event": "complete",
                "data": json.dumps(
                    {
                        "report": final_state.get("final_report", ""),
                        "quality_score": final_state.get("quality_score", 0),
                        "references": final_state.get("references", []),
                        "iteration": final_state.get("iteration", 0),
                        "session_id": session_id,
                    },
                    ensure_ascii=False,
                ),
            }
        except Exception as e:  # noqa: BLE001
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


def main():
    print(f"[finagent-research] 启动于 http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)


if __name__ == "__main__":
    main()
