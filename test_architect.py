"""
ChiefArchitect 测试。

给一个研究问题，看总架构师输出研究规划（实体/假设/子问题/大纲）。
会调用 DeepSeek（消耗少量额度）。

用法（服务器上，激活 venv，.env 配了 DEEPSEEK_API_KEY）：
    python test_architect.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deep_research.agents.architect import ChiefArchitect  # noqa: E402
from deep_research.state import create_initial_state  # noqa: E402


async def main():
    state = create_initial_state("分析贵州茅台的投资价值", session_id="test-001")

    print("=" * 60)
    print("研究问题：分析贵州茅台的投资价值")
    print("总架构师规划中（调 DeepSeek，约 10-20 秒）...")
    print("=" * 60)

    architect = ChiefArchitect()
    state = await architect.process(state)

    print("\n【关键实体】")
    print("  ", state["key_entities"])

    print("\n【投资假设】")
    for h in state["hypotheses"]:
        print(f"  - {h.get('statement')}")
        print(f"    理由: {h.get('rationale')}")

    print("\n【待研究子问题】")
    for q in state["research_questions"]:
        print(f"  - {q}")

    print("\n【报告大纲】")
    for s in state["outline"]:
        print(f"  {s.get('id')}. {s.get('title')} —— {s.get('description')}")

    print("\n" + "=" * 60)
    if state["key_entities"] and state["outline"]:
        print("✅ ChiefArchitect 测试通过（R2 验证通过）")
    else:
        print("⚠️  规划产出不完整，可能解析失败，检查输出")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
