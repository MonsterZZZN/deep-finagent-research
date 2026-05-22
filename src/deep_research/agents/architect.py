"""
总架构师 Agent（ChiefArchitect）。

研究流程第一棒：接到研究问题，产出研究规划——
关键实体、投资假设（假设驱动研究）、待研究子问题、报告大纲。

把产出写进 ResearchState，供 DeepScout 带着假设去搜证。
"""

from deep_research.agents.base import BaseAgent
from deep_research.state import ResearchPhase, ResearchState

ARCHITECT_PROMPT = """你是金融研究的总架构师。给定一个研究问题，你要做研究规划：

1. **关键实体**：识别问题涉及的公司、行业、概念
2. **投资假设**（假设驱动研究的核心）：提出 2-4 个可被验证或证伪的假设。
   好的假设是具体、可查证的，例如：
   - "贵州茅台当前 PE 处于历史高位，估值偏贵"
   - "白酒行业需求受人口结构变化承压"
   不要写"茅台是好公司"这种无法证伪的空话。
3. **待研究子问题**：拆出 3-5 个需要搜集资料回答的具体问题
4. **报告大纲**：设计研究报告的章节结构

输出 JSON：
{
  "key_entities": ["实体1", "实体2"],
  "hypotheses": [
    {"statement": "假设内容", "rationale": "提出该假设的理由"}
  ],
  "research_questions": ["子问题1", "子问题2"],
  "outline": [
    {"id": "1", "title": "章节标题", "description": "本章要点"}
  ]
}
"""


class ChiefArchitect(BaseAgent):
    """总架构师：研究规划。"""

    def __init__(self) -> None:
        super().__init__(name="ChiefArchitect", role="总架构师")

    async def process(self, state: ResearchState) -> ResearchState:
        query = state["query"]
        self.add_message(state, "phase", "开始规划研究方案...")

        user_prompt = f"研究问题：{query}\n\n请生成完整的研究规划。"
        resp = await self.call_llm(ARCHITECT_PROMPT, user_prompt)
        result = self.parse_json_response(resp)

        if not result:
            state["errors"].append("ChiefArchitect: 规划解析失败")
            return state

        state["key_entities"] = result.get("key_entities", [])
        state["hypotheses"] = result.get("hypotheses", [])
        state["research_questions"] = result.get("research_questions", [])
        state["outline"] = result.get("outline", [])

        # 待搜索查询 = 子问题（DeepScout 会用）
        state["pending_queries"] = list(state["research_questions"])

        state["phase"] = ResearchPhase.RESEARCHING.value
        self.add_message(
            state,
            "planning_complete",
            {
                "entities": state["key_entities"],
                "hypotheses_count": len(state["hypotheses"]),
                "questions_count": len(state["research_questions"]),
                "sections_count": len(state["outline"]),
            },
        )
        return state
