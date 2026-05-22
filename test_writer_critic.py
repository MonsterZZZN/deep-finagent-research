"""
LeadWriter + CriticMaster 测试（完整研究链路一次跑通）。

流程：架构师规划 → 侦探搜索 → 撰稿人写报告 → 评论家审核。
会调用多次 DeepSeek + 搜索（需要 .env 配 DEEPSEEK_API_KEY 和搜索 key）。

用法（服务器上，激活 venv）：
    python test_writer_critic.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deep_research.agents.architect import ChiefArchitect  # noqa: E402
from deep_research.agents.critic import CriticMaster  # noqa: E402
from deep_research.agents.scout import DeepScout  # noqa: E402
from deep_research.agents.writer import LeadWriter  # noqa: E402
from deep_research.state import create_initial_state  # noqa: E402


async def main():
    state = create_initial_state("分析贵州茅台的投资价值", session_id="test-003")

    print("【1】规划...")
    state = await ChiefArchitect().process(state)
    print(f"   大纲 {len(state['outline'])} 章")

    print("【2】搜索...（约 30-60 秒）")
    state = await DeepScout().process(state)
    print(f"   搜集 {len(state['facts'])} 条事实")

    print("【3】撰写...（约 30-60 秒）")
    state = await LeadWriter().process(state)
    print(f"   报告 {len(state['final_report'])} 字，引用 {len(state['references'])} 条")

    print("【4】审核...（约 20-40 秒）")
    state = await CriticMaster().process(state)

    print("\n" + "=" * 60)
    print("【研究报告】")
    print("=" * 60)
    print(state["final_report"])

    print("\n" + "=" * 60)
    print(f"【审核结果】质量分: {state['quality_score']}")
    print("=" * 60)
    if state["critic_feedback"]:
        for c in state["critic_feedback"]:
            print(f"  [{c.get('severity')}] {c.get('issue_type')}: {c.get('description')}")
    else:
        print("  无明显问题")

    print("\n" + "=" * 60)
    if state["final_report"] and state["quality_score"] > 0:
        print("✅ LeadWriter + CriticMaster 测试通过（R4 验证通过）")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
