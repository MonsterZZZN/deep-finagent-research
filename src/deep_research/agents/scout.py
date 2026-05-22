"""
深度侦探 Agent（DeepScout）。

研究流程第二棒：带着架构师提的假设和子问题，去网络搜证。
- 对每个子问题做网络搜索
- 用 LLM 从搜索结果中提取关键事实，并判断信源类型 → 打可信度分
- 搜完后回头验证每个假设（支持/反驳/中立）—— 假设驱动研究的闭环
"""

import asyncio

from deep_research import config
from deep_research.agents.base import BaseAgent
from deep_research.state import SOURCE_CREDIBILITY, ResearchPhase, ResearchState
from deep_research.tools.web_search import web_search

EXTRACT_PROMPT = """你是金融研究侦探。给定一个研究问题和若干网络搜索结果，
提取与问题相关、有信息量的关键事实（最多 5 条）。

对每条事实，判断来源类型：
- official：政府/交易所/公司公告/年报
- report：券商研报/专业机构报告
- news：主流财经媒体（新浪财经/财联社/证券时报/第一财经等）
- self_media：自媒体/论坛/个人（雪球个人帖/知乎/贴吧等）

输出 JSON：
{
  "facts": [
    {"content": "事实内容（含具体数字更好）", "source_url": "结果的URL", "source_name": "来源名", "source_type": "news"}
  ]
}
只提取真实出现在搜索结果中的信息，不要编造。"""

VERIFY_PROMPT = """你是金融研究侦探。根据已搜集的事实，判断每个研究假设的验证结果。

对每个假设，给出 verdict：
- support：事实支持该假设
- refute：事实反驳该假设
- neutral：证据不足或中性

输出 JSON：
{"verdicts": [{"statement": "假设原文", "verdict": "support", "reason": "依据"}]}"""


class DeepScout(BaseAgent):
    """深度侦探：搜索 + 信源评级 + 假设验证。"""

    def __init__(self) -> None:
        super().__init__(name="DeepScout", role="深度侦探")

    async def process(self, state: ResearchState) -> ResearchState:
        queries = state["pending_queries"][: config.MAX_SEARCH_QUERIES]
        self.add_message(state, "phase", f"开始搜索 {len(queries)} 个子问题...")

        # 并发搜索所有子问题
        all_results = await asyncio.gather(*[web_search(q) for q in queries])

        # 逐个问题用 LLM 抽取事实
        for query, results in zip(queries, all_results):
            if not results:
                self.add_message(state, "search_result", {"query": query, "facts_found": 0, "note": "无结果"})
                continue
            facts = await self._extract_facts(query, results)
            state["facts"].extend(facts)
            self.add_message(state, "search_result", {"query": query, "facts_found": len(facts)})

        # 验证假设（假设驱动研究闭环）
        await self._verify_hypotheses(state)

        state["pending_queries"] = []
        state["phase"] = ResearchPhase.WRITING.value
        self.add_message(state, "research_complete", {"total_facts": len(state["facts"])})
        return state

    async def _extract_facts(self, query: str, results: list[dict]) -> list[dict]:
        """用 LLM 从搜索结果中提取事实并评级。"""
        # 把搜索结果格式化给 LLM
        results_text = "\n\n".join(
            f"[{i + 1}] 标题: {r['title']}\n来源: {r.get('site', '')}\nURL: {r['url']}\n摘要: {r['snippet']}"
            for i, r in enumerate(results)
        )
        user_prompt = f"研究问题：{query}\n\n搜索结果：\n{results_text}"
        resp = await self.call_llm(EXTRACT_PROMPT, user_prompt)
        parsed = self.parse_json_response(resp)

        facts = []
        for f in parsed.get("facts", []):
            source_type = f.get("source_type", "news")
            facts.append(
                {
                    "content": f.get("content", ""),
                    "source_url": f.get("source_url", ""),
                    "source_name": f.get("source_name", ""),
                    "source_type": source_type,
                    "credibility_score": SOURCE_CREDIBILITY.get(source_type, 0.5),
                }
            )
        return facts

    async def _verify_hypotheses(self, state: ResearchState) -> None:
        """根据搜集的事实，更新每个假设的验证结果。"""
        if not state["hypotheses"] or not state["facts"]:
            return
        facts_summary = "\n".join(f"- {f['content']}" for f in state["facts"][:20])
        hyps = "\n".join(f"- {h.get('statement')}" for h in state["hypotheses"])
        user_prompt = f"假设：\n{hyps}\n\n已搜集事实：\n{facts_summary}"
        resp = await self.call_llm(VERIFY_PROMPT, user_prompt)
        parsed = self.parse_json_response(resp)

        verdicts = {v.get("statement", ""): v for v in parsed.get("verdicts", [])}
        for h in state["hypotheses"]:
            v = verdicts.get(h.get("statement", ""))
            if v:
                h["verdict"] = v.get("verdict", "neutral")
                h["verify_reason"] = v.get("reason", "")
