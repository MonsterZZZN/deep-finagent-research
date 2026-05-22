"""
追踪记录存储（与 finagent-core 共用同一 MongoDB agent_traces 集合）。

观测不能拖垮业务：保存失败只打日志，不抛异常。
"""

from pymongo import MongoClient

from deep_research import config


class TraceStore:
    def __init__(self) -> None:
        self._col = None

    @property
    def col(self):
        if self._col is None:
            client = MongoClient(config.MONGODB_URI)
            self._col = client[config.MONGODB_DB_NAME]["agent_traces"]
        return self._col

    def save(self, doc: dict) -> None:
        try:
            self.col.insert_one(doc)
        except Exception as e:  # noqa: BLE001
            print(f"[observability] 保存追踪记录失败: {e}")


trace_store = TraceStore()
