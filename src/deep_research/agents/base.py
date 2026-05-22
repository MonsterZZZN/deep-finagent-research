"""
专家 Agent 基类。

所有专家 Agent（架构师/侦探/撰写/审核等）继承此类，共用：
- call_llm：统一的大模型调用（异步）
- parse_json_response：健壮的 JSON 解析（处理 markdown 代码块、多余文本）
- add_message：把进度消息推进 state（供 SSE 流式输出）

约定：每个 Agent 实现 process(state) -> state，读写共享的 ResearchState。
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from deep_research import config
from deep_research.state import ResearchState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class BaseAgent(ABC):
    """专家 Agent 基类。"""

    def __init__(self, name: str, role: str) -> None:
        self.name = name
        self.role = role
        self.model = config.get_model()
        self.logger = logging.getLogger(f"Agent.{name}")

    @abstractmethod
    async def process(self, state: ResearchState) -> ResearchState:
        """处理状态并返回更新后的状态（子类实现）。"""
        ...

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> str:
        """
        调用大模型。

        json_mode=True 时，会在 system prompt 末尾强调输出 JSON
        （配合 parse_json_response 健壮解析）。
        """
        if json_mode:
            system_prompt += "\n\n严格只输出合法的 JSON，不要任何额外解释或 markdown 标记。"
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        resp = await self.model.ainvoke(messages)
        return resp.content if isinstance(resp.content, str) else str(resp.content)

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """健壮地从 LLM 输出里提取 JSON。"""
        s = text.strip()
        # 1. 直接解析
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        # 2. markdown 代码块
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # 3. 最外层花括号
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        self.logger.warning(f"JSON 解析失败，原文前 300 字: {text[:300]}")
        return {}

    def add_message(self, state: ResearchState, event_type: str, content: Any) -> None:
        """把进度消息追加到 state（SSE 流式输出会消费它）。"""
        state["messages"].append(
            {
                "type": event_type,
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "content": content,
            }
        )
        self.logger.info(f"[{event_type}] {self.name}")
