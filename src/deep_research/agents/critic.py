"""
毒舌评论家 Agent（CriticMaster）。

研究流程第四棒：对抗式质检——专挑报告的毛病，绝不手软。
重点检查：无来源数据、逻辑漏洞、合规违规（买卖建议=红线）、过时、不完整。
产出审核意见 + 质量分，供状态机决定是否打回重写。
"""

from deep_research.agents.base import BaseAgent
from deep_research.state import ResearchState

CRITIC_PROMPT = """你是毒舌评论家，金融研究报告的质检专家。你的职责是挑出报告的问题，绝不手软。

重点检查以下几类问题：
- **compliance（合规，最高优先级）**：报告里出现"建议买入/卖出"、"必涨/必跌"、
  "保证收益"等违规表述 —— 这是金融红线，一旦发现标 critical
- **missing_source**：关键数据或结论没有来源支撑
- **logic_error**：逻辑漏洞、论证不严密、结论与事实矛盾
- **outdated**：使用了明显过时的数据
- **incomplete**：大纲章节缺失、关键维度没覆盖

对每个问题判断严重程度：critical（严重）/ major（较重）/ minor（轻微）。
给报告一个整体质量分（0-100）。

输出 JSON：
{
  "issues": [
    {"issue_type": "compliance", "severity": "critical", "description": "问题描述", "target_section": "所在章节"}
  ],
  "quality_score": 75
}
如果报告质量很好、没什么问题，issues 可以为空数组，quality_score 给高分。"""


class CriticMaster(BaseAgent):
    """毒舌评论家：对抗式质检。"""

    def __init__(self) -> None:
        super().__init__(name="CriticMaster", role="毒舌评论家")

    async def process(self, state: ResearchState) -> ResearchState:
        self.add_message(state, "phase", "审核报告...")

        facts_text = "\n".join(f"- {f['content']}" for f in state["facts"][:20])
        user_prompt = (
            f"研究问题：{state['query']}\n\n"
            f"【可用事实库】（用于核对报告数据是否有依据）\n{facts_text}\n\n"
            f"【待审核报告】\n{state['final_report']}\n"
        )

        resp = await self.call_llm(CRITIC_PROMPT, user_prompt)
        result = self.parse_json_response(resp)

        state["critic_feedback"] = result.get("issues", [])
        state["quality_score"] = float(result.get("quality_score", 0))

        # 统计严重问题数（供状态机路由）
        critical = sum(1 for c in state["critic_feedback"] if c.get("severity") in ("critical", "major"))
        self.add_message(
            state,
            "review_complete",
            {
                "quality_score": state["quality_score"],
                "issues": len(state["critic_feedback"]),
                "critical_major": critical,
            },
        )
        return state
