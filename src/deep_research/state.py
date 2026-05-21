"""
研究状态 —— 全局工作记忆。

借鉴 industry_information_assistant 的 ResearchState 模式（自行重写、金融化）：
所有 Agent 读写同一份 TypedDict 状态，通过它通信。

研究流程是一个状态机：
INIT → PLANNING → RESEARCHING → WRITING → REVIEWING →（REVISING 循环）→ COMPLETED
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional, TypedDict


class ResearchPhase(str, Enum):
    """研究阶段状态机。"""
    INIT = "init"
    PLANNING = "planning"          # 规划：出大纲、假设、子问题
    RESEARCHING = "researching"    # 搜索：搜集事实、信源评级
    WRITING = "writing"            # 撰写：逐章写报告
    REVIEWING = "reviewing"        # 审核：对抗式质检
    REVISING = "revising"          # 修订：按审核意见改
    COMPLETED = "completed"


@dataclass
class Hypothesis:
    """研究假设（假设驱动研究）。"""
    statement: str                 # 假设内容，如"贵州茅台当前估值偏高"
    rationale: str = ""            # 提出该假设的理由
    verdict: Literal["unverified", "support", "refute", "neutral"] = "unverified"


@dataclass
class Fact:
    """结构化事实（带可信度）。"""
    content: str
    source_url: str = ""
    source_name: str = ""
    # 来源类型决定可信度：官方/研报 高，自媒体 低
    source_type: Literal["official", "report", "news", "self_media"] = "news"
    credibility_score: float = 0.5  # 0-1


@dataclass
class CriticFeedback:
    """审核反馈。"""
    issue_type: Literal[
        "missing_source", "logic_error", "compliance", "outdated", "incomplete"
    ]
    severity: Literal["critical", "major", "minor"]
    description: str
    target_section: str = ""


# 来源类型 → 可信度参考
SOURCE_CREDIBILITY = {
    "official": 0.95,   # 政府/交易所/公司公告
    "report": 0.85,     # 券商研报
    "news": 0.65,       # 主流财经媒体
    "self_media": 0.35,  # 自媒体/论坛
}


class ResearchState(TypedDict):
    """LangGraph 全局状态：所有 Agent 共享读写。"""
    # 基础
    query: str                          # 用户研究问题
    session_id: str
    phase: str                          # 当前阶段
    iteration: int                      # 当前迭代轮次
    max_iterations: int

    # 规划产出（ChiefArchitect）
    outline: List[dict]                 # 报告大纲（章节序列）
    hypotheses: List[dict]              # 研究假设
    research_questions: List[str]       # 待研究子问题
    key_entities: List[str]             # 关键实体（公司/行业）

    # 搜索产出（DeepScout）
    facts: List[dict]                   # 结构化事实库（带可信度）
    pending_queries: List[str]          # 待执行搜索

    # 撰写产出（LeadWriter）
    draft_sections: dict                # {section_id: content}
    final_report: str
    references: List[dict]              # 引用来源

    # 审核产出（CriticMaster）
    critic_feedback: List[dict]
    quality_score: float

    # 流式输出
    messages: List[dict]                # Agent 间消息（SSE 推送用）

    # 错误
    errors: List[str]


def create_initial_state(
    query: str,
    session_id: str,
    max_iterations: int = 2,
) -> ResearchState:
    """创建初始研究状态。"""
    return ResearchState(
        query=query,
        session_id=session_id,
        phase=ResearchPhase.INIT.value,
        iteration=0,
        max_iterations=max_iterations,
        outline=[],
        hypotheses=[],
        research_questions=[],
        key_entities=[],
        facts=[],
        pending_queries=[],
        draft_sections={},
        final_report="",
        references=[],
        critic_feedback=[],
        quality_score=0.0,
        messages=[],
        errors=[],
    )
