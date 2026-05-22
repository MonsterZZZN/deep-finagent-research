"""
DeepScout 测试。

流程：架构师规划 → 侦探搜索 → 看搜到的事实 + 假设验证结果。
会调用 DeepSeek + 搜索 API（需要 .env 配 DEEPSEEK_API_KEY 和搜索 key）。

用法（服务器上，激活 venv）：
    python test_scout.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deep_research.agents.architect import ChiefArchitect  # noqa: E402
from deep_research.agents.scout import DeepScout  # noqa: E402
from deep_research.state import create_initial_state  # noqa: E402


async def main():
    state = create_initial_state("分析贵州茅台的投资价值", session_id="test-002")

    print("=" * 60)
    print("【1】架构师规划...")
    print("=" * 60)
    state = await ChiefArchitect().process(state)
    print(f"  子问题 {len(state['research_questions'])} 个，假设 {len(state['hypotheses'])} 个")

    print("\n" + "=" * 60)
    print("【2】侦探搜索（搜索 + 抽取事实 + 验证假设，约 30-60 秒）...")
    print("=" * 60)
    state = await DeepScout().process(state)

    print(f"\n共搜集到 {len(state['facts'])} 条事实，按可信度展示前 8 条：")
    facts = sorted(state["facts"], key=lambda f: -f["credibility_score"])
    for f in facts[:8]:
        print(f"  [{f['source_type']} {f['credibility_score']}] {f['content'][:80]}")
        print(f"      来源: {f['source_name']} {f['source_url'][:60]}")

    print("\n【假设验证结果】")
    for h in state["hypotheses"]:
        verdict = h.get("verdict", "unverified")
        mark = {"support": "✅支持", "refute": "❌反驳", "neutral": "➖中立"}.get(verdict, "❔未验证")
        print(f"  {mark}  {h.get('statement')}")
        if h.get("verify_reason"):
            print(f"        依据: {h['verify_reason'][:80]}")

    print("\n" + "=" * 60)
    if state["facts"]:
        print("✅ DeepScout 测试通过（R3 验证通过）")
    else:
        print("⚠️  没搜到事实，检查搜索 API key 是否配置正确")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
