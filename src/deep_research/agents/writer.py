"""
首席撰稿人 Agent（LeadWriter）。

研究流程第三棒：根据大纲、事实库、假设验证结果，撰写金融研究报告。
- 严格按大纲组织
- 用事实库数据支撑论点，引用标来源
- 结合假设验证结果写结论
- 支持"修订模式"：带上一版审核意见重写（R5 审核-修订循环用）
"""

from deep_research.agents.base import BaseAgent
from deep_research.state import ResearchPhase, ResearchState

WRITER_PROMPT = """你是首席撰稿人，撰写专业的金融研究报告。

要求：
- 严格按给定大纲的章节组织
- 用"事实库"里的数据支撑论点，引用时标注来源，如"2024年营收1741亿元（腾讯网）"
- 在结论章节，结合"假设验证结果"逐条回应每个投资假设
- 客观专业，像券商研报；有数字、有逻辑
- **合规红线**：绝不给买卖建议、不预测必涨必跌、不承诺收益
- 报告末尾加风险提示："本报告基于公开信息整理，仅供研究参考，不构成投资建议。"
- 用 Markdown 格式

直接输出报告正文（Markdown），不要输出 JSON 或额外说明。"""


class LeadWriter(BaseAgent):
    """首席撰稿人：撰写研究报告。"""

    def __init__(self) -> None:
        super().__init__(name="LeadWriter", role="首席撰稿人")

    async def process(self, state: ResearchState) -> ResearchState:
        is_revision = state["iteration"] > 0 and bool(state["critic_feedback"])
        self.add_message(
            state, "phase", "修订报告..." if is_revision else "撰写报告..."
        )

        # 格式化输入
        outline_text = "\n".join(
            f"{s.get('id')}. {s.get('title')} —— {s.get('description', '')}"
            for s in state["outline"]
        )
        facts_text = "\n".join(
            f"- {f['content']}（来源：{f.get('source_name', '')}，可信度{f['credibility_score']}）"
            for f in state["facts"]
        )
        hyps_text = "\n".join(
            f"- {h.get('statement')} → 验证：{h.get('verdict', 'unverified')}"
            f"（{h.get('verify_reason', '')}）"
            for h in state["hypotheses"]
        )

        user_prompt = (
            f"研究问题：{state['query']}\n\n"
            f"【报告大纲】\n{outline_text}\n\n"
            f"【假设验证结果】\n{hyps_text}\n\n"
            f"【事实库】\n{facts_text}\n"
        )

        # 修订模式：附上审核意见和上一版报告
        if is_revision:
            feedback_text = "\n".join(
                f"- [{c.get('severity')}] {c.get('issue_type')}: {c.get('description')}"
                for c in state["critic_feedback"]
            )
            user_prompt += (
                f"\n【上一版审核意见，请针对性改进】\n{feedback_text}\n\n"
                f"【上一版报告】\n{state['final_report']}\n"
            )

        report = await self.call_llm(WRITER_PROMPT, user_prompt, json_mode=False)
        state["final_report"] = report

        # 构建参考文献（事实来源去重）
        seen = set()
        refs = []
        for f in state["facts"]:
            url = f.get("source_url", "")
            if url and url not in seen:
                seen.add(url)
                refs.append(
                    {
                        "name": f.get("source_name", ""),
                        "url": url,
                        "type": f.get("source_type", ""),
                    }
                )
        state["references"] = refs

        state["phase"] = ResearchPhase.REVIEWING.value
        self.add_message(state, "writing_complete", {"report_length": len(report), "refs": len(refs)})
        return state
