"""
网络搜索工具。

支持两个搜索提供商，由 config.SEARCH_PROVIDER 切换：
- bochaai：博查AI（中文搜索好，推荐）
- tavily：Tavily（备选）

统一返回格式：[{"title", "url", "snippet", "site"}]
"""

import httpx

from deep_research import config

BOCHAAI_URL = "https://api.bochaai.com/v1/web-search"
TAVILY_URL = "https://api.tavily.com/search"


async def web_search(query: str, count: int = 5) -> list[dict]:
    """执行网络搜索，返回统一格式的结果列表。"""
    provider = (config.SEARCH_PROVIDER or "bochaai").lower()
    try:
        if provider == "tavily":
            return await _tavily_search(query, count)
        return await _bochaai_search(query, count)
    except Exception as e:  # noqa: BLE001
        print(f"[web_search] 搜索失败 query={query!r}: {e}")
        return []


async def _bochaai_search(query: str, count: int) -> list[dict]:
    if not config.BOCHAAI_API_KEY:
        print("[web_search] 未配置 BOCHAAI_API_KEY")
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BOCHAAI_URL,
            headers={"Authorization": f"Bearer {config.BOCHAAI_API_KEY}"},
            json={"query": query, "count": count, "summary": True},
        )
        resp.raise_for_status()
        data = resp.json()
    pages = (
        data.get("data", {}).get("webPages", {}).get("value", [])
        if isinstance(data.get("data"), dict)
        else []
    )
    results = []
    for p in pages:
        results.append(
            {
                "title": p.get("name", ""),
                "url": p.get("url", ""),
                "snippet": p.get("summary") or p.get("snippet", ""),
                "site": p.get("siteName", ""),
            }
        )
    return results


async def _tavily_search(query: str, count: int) -> list[dict]:
    if not config.TAVILY_API_KEY:
        print("[web_search] 未配置 TAVILY_API_KEY")
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TAVILY_URL,
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "max_results": count,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for r in data.get("results", []):
        results.append(
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "site": "",
            }
        )
    return results
