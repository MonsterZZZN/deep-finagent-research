"""
完整研究流程测试（LangGraph 状态机）。

一条命令跑完整流程：规划→搜索→撰写→审核→（不过则修订循环）→完成。
重点观察：如果初稿有合规问题，系统会自动打回重写并修正。

会调用多次 DeepSeek + 搜索，可能跑 2-4 分钟（含修订循环）。

用法（服务器上，激活 venv）：
    python test_graph.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deep_research.graph import run_research  # noqa: E402


async def main():
    print("=" * 60)
    print("运行完整深度研究流程（含审核-修订循环）...")
    print("问题：分析贵州茅台的投资价值")
    print("（2-4 分钟，含可能的修订循环）")
    print("=" * 60)

    state = await run_research("分析贵州茅台的投资价值", session_id="test-graph-001")

    print("\n" + "=" * 60)
    print("【最终研究报告】")
    print("=" * 60)
    print(state["final_report"])

    print("\n" + "=" * 60)
    print(f"迭代轮次: {state['iteration']}（0=初稿通过，≥1=经过修订）")
    print(f"最终质量分: {state['quality_score']}")
    print(f"剩余审核问题: {len(state['critic_feedback'])}")
    print(f"引用来源: {len(state['references'])} 条")
    print("=" * 60)

    # 检查最终报告是否还有合规违规词
    bad_words = ["建议买入", "建议卖出", "买入", "卖出", "增持", "减持"]
    found = [w for w in bad_words if w in state["final_report"]]
    if found:
        print(f"⚠️  最终报告仍含疑似违规词: {found}")
    else:
        print("✅ 最终报告未见买卖建议违规词，合规循环生效")
    print("\n✅ R5 状态机测试完成")


if __name__ == "__main__":
    asyncio.run(main())
