"""
research API 测试客户端。

调用运行中的 /research/stream 接口，打印流式进度 + 最终报告。

用法（需要先在另一个终端启动服务）：
    # 终端1：启动服务
    cd /root/finagent-research && source venv/bin/activate
    bash dev.sh serve            # 或 cd src && python -m deep_research.api.server

    # 终端2：跑测试
    cd /root/finagent-research && source venv/bin/activate
    python test_api.py
"""

import asyncio
import json

import httpx

URL = "http://127.0.0.1:8001/research/stream"


async def main():
    payload = {"query": "分析贵州茅台的投资价值", "max_iterations": 1}
    print("调用 /research/stream，流式接收...\n")

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("POST", URL, json=payload) as resp:
            event = None
            async for line in resp.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    if not data:
                        continue
                    obj = json.loads(data)
                    if event == "progress":
                        print(f"  [进度] {obj.get('agent')} - {obj.get('type')} - {obj.get('phase')}")
                    elif event == "complete":
                        print("\n" + "=" * 60)
                        print(f"【完成】迭代轮次 {obj['iteration']}，质量分 {obj['quality_score']}，引用 {len(obj['references'])} 条")
                        print("=" * 60)
                        print(obj["report"][:1500])
                        print("...(报告略)")
                    elif event == "error":
                        print(f"  [错误] {obj.get('message')}")

    print("\n✅ R6 API 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
