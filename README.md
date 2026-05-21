# finagent-research

> 金融深度研究 Agent 系统
> FinAgent 平台的三个子项目之一（core / **research** / kb）

## 这是什么

finagent-research 是**金融深度研究引擎**：用多个专家 Agent 协作，针对一个研究问题
（如"贵州茅台的投资价值"）执行 规划 → 搜索 → 撰写 → 审核 的循环，产出一份
带数据、带引用的研究报告。

被 finagent-core 通过 `research-proxy` 调用——用户在飞书里问深度研究问题，
就会触发本服务。

## 架构（借鉴 industry_information_assistant，自行重写）

基于 **LangGraph 状态机 + 多专家 Agent 协作**：

```
PLANNING（ChiefArchitect 规划：大纲/假设/子问题）
  → RESEARCHING（DeepScout 搜索 + 信源评级）
  → WRITING（LeadWriter 逐章撰写）
  → REVIEWING（CriticMaster 对抗式审核）
  →（不通过则 REVISING 循环）
  → COMPLETED
```

特点：假设驱动研究、对抗式质检、信源可信度评级、SSE 流式输出。

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 编排 | LangGraph 状态机 |
| 大模型 | DeepSeek |
| 搜索 | 博查AI / Tavily |
| 服务 | FastAPI + SSE |
| 存储 | Redis（检查点/取消） |

## 快速开始

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 填 DEEPSEEK_API_KEY + 搜索 API key
# python -m deep_research.api.server   （服务入口，后续步骤完成）
```

## 开发进度

- [x] R1：项目骨架 + ResearchState 状态结构
- [ ] R2：BaseAgent + ChiefArchitect（规划）
- [ ] R3：DeepScout（搜索 + 信源评级）
- [ ] R4：LeadWriter（撰写）+ CriticMaster（审核）
- [ ] R5：LangGraph 状态机编排
- [ ] R6：FastAPI /research/stream SSE 接口
- [ ] R7：接入 finagent-core + 飞书异步体验

## 声明

本项目为独立实现，借鉴公开的多 Agent 研究架构模式。所有 AI 输出仅供研究参考，不构成投资建议。
