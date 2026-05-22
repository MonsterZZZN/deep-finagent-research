"""
研究流程状态机编排（LangGraph）。

把 4 个专家 Agent 编排成自动流程：
  规划(architect) → 搜索(scout) → 撰写(writer) → 审核(critic)
                                        │
                          ┌─────────────┴─────────────┐
                  有critical/major问题            通过/达迭代上限
                  且未达迭代上限                       │
                          │                            ▼
                       修订(iteration+1)              END
                          │
                          └──→ 回到撰写

这是"多 Agent 状态机 + 对抗审核循环"的核心：审核不过自动打回重写，
直到合格或用尽迭代次数。
"""

from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from deep_research.agents.architect import ChiefArchitect
from deep_research.agents.critic import CriticMaster
from deep_research.agents.scout import DeepScout
from deep_research.agents.writer import LeadWriter
from deep_research.observability.handler import ObservabilityHandler
from deep_research.state import ResearchState, create_initial_state


def _should_revise(state: ResearchState) -> str:
    """审核后的路由决策：是否需要修订。"""
    critical_major = sum(
        1 for c in state["critic_feedback"] if c.get("severity") in ("critical", "major")
    )
    if critical_major > 0 and state["iteration"] < state["max_iterations"]:
        return "revise"
    return "done"


def _revise_node(state: ResearchState) -> ResearchState:
    """修订节点：迭代计数 +1，然后回到撰写。"""
    state["iteration"] += 1
    return state


def build_graph():
    """构建并编译研究流程状态机。"""
    # Agent 实例化一次，复用
    architect = ChiefArchitect()
    scout = DeepScout()
    writer = LeadWriter()
    critic = CriticMaster()

    g = StateGraph(ResearchState)

    g.add_node("planning", architect.process)
    g.add_node("researching", scout.process)
    g.add_node("writing", writer.process)
    g.add_node("reviewing", critic.process)
    g.add_node("revise", _revise_node)

    g.add_edge(START, "planning")
    g.add_edge("planning", "researching")
    g.add_edge("researching", "writing")
    g.add_edge("writing", "reviewing")
    # 审核后条件路由
    g.add_conditional_edges(
        "reviewing",
        _should_revise,
        {"revise": "revise", "done": END},
    )
    g.add_edge("revise", "writing")  # 修订 → 回到撰写

    return g.compile()


# 全局编译一次
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_research(
    query: str, session_id: str, max_iterations: int = 2, trace_id: str | None = None
) -> ResearchState:
    """运行一次完整的深度研究，返回最终状态（含报告）。"""
    state = create_initial_state(query, session_id, max_iterations)
    graph = get_graph()
    # 挂可观测性 handler：callback 沿 graph 节点传播，捕获 4 个 Agent 的 LLM 调用
    handler = ObservabilityHandler(
        trace_id=trace_id or uuid4().hex, session_id=session_id, service="finagent-research"
    )
    final_state = await graph.ainvoke(
        state, config={"recursion_limit": 50, "callbacks": [handler]}
    )
    return final_state
