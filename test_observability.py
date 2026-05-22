"""
finagent-research 可观测性埋点测试。

跑一次完整研究（含 4 个 Agent 节点），然后从 MongoDB 查出捕获的 span，
验证 LangGraph 节点里的 LLM 调用都被埋点捕获。

用法（finagent-research 目录，激活 venv，.env 配了 DEEPSEEK_API_KEY + 搜索 key + MONGODB_URI）：
    python test_observability.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deep_research.graph import run_research  # noqa: E402
from deep_research.observability.store import trace_store  # noqa: E402

SESSION = "research-obs-001"


async def main():
    print("=" * 60)
    print("跑一次完整研究（含4个Agent节点，max_iterations=1，约1-2分钟）...")
    print("=" * 60)
    await run_research(
        "分析贵州茅台的投资价值", session_id=SESSION, max_iterations=1
    )

    spans = list(trace_store.col.find({"session_id": SESSION}).sort("ts", 1))
    print(f"\n捕获 {len(spans)} 条 span：")
    print("=" * 60)
    total_tokens = 0
    for s in spans:
        line = f"  [{s['type']:4}] {s['name']:18} {s['latency_ms']:>6}ms  {s['status']}"
        if s.get("total_tokens"):
            line += f"  tokens={s['total_tokens']}"
            total_tokens += s["total_tokens"]
        print(line)

    print("\n" + "=" * 60)
    print(f"本次总 token: {total_tokens}")
    # research 一次研究至少有 规划+搜索抽取+假设验证+撰写+审核 多次 LLM 调用
    llm_spans = [s for s in spans if s["type"] == "llm"]
    if len(llm_spans) >= 4:
        print(f"✅ 捕获 {len(llm_spans)} 次 LLM 调用，LangGraph 节点埋点生效（O1b 验证通过）")
    elif spans:
        print(f"⚠️  只捕获 {len(llm_spans)} 次 LLM 调用，可能 callback 未完全传播到节点，发我看")
    else:
        print("⚠️  没捕获到 span，检查 MONGODB_URI 配置")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
