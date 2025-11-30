# CHANGELOG.md

## [v3.0.0-alpha] - 2025-11-30 (当前版本)
> **核心里程碑：引入 LangGraph 多智能体协作与人机协同 (Human-in-the-loop)**
> 本次更新彻底重构了后端核心逻辑，从线性的工作流升级为具备自我反思和纠错能力的自主智能体集群。

### 🚀 新特性 (New Features)
- **多智能体架构 (Multi-Agent Swarm)**: 引入 `LangGraph`，拆分为 Parser, Researcher, TechLead, HR, Reviewer 五个独立智能体。
- **自我反思与纠错 (Self-Correction)**: 新增 `Reviewer` (质检员) 节点，自动审核题目质量，不合格则打回 `TechLead` 重写，形成质量闭环。
- **人机协同 (Human-in-the-loop)**: 利用 LangGraph `MemorySaver` 实现状态持久化。当 AI 拿捏不准或质量评分较低时，自动挂起任务，等待人类（用户）介入决策。
- **状态路由 (Conditional Routing)**: 实现了基于质量评分的动态路由逻辑，防止死循环生成。

### 🏗 架构升级 (Architecture)
- **Graph State**: 定义了全局 `AgentState`，实现多 Agent 间的上下文共享与数据流转。
- **Checkpointing**: 引入内存检查点机制，支持任务的暂停、恢复与状态回滚。

---

## [v2.1.0] - 2025-11-29
> **核心里程碑：全双工语音交互与沉浸式模拟面试**
> 重点打磨交互体验，实现了“听得见、说得出”的实时面试官。

### 🚀 新特性 (New Features)
- **语音交互闭环 (Voice Interaction)**:
    - 集成 **ASR (Whisper)**: 支持前端录音并调用 SiliconFlow/OpenAI 接口转录。
    - 集成 **TTS (Text-to-Speech)**: 支持将 AI 回复实时转化为语音朗读。
- **音频队列系统 (Audio Queue)**: 前端实现分句缓冲与串行播放逻辑，解决流式生成导致的语音重叠问题，体验更自然。
- **模拟面试模式 (Mock Interview)**: 新增独立的面试模式，AI 动态切换为“严厉面试官”人设，支持连续追问。

### 🛠 修复与优化 (Fixes & Improvements)
- **Next.js SSR 兼容性修复**: 解决 `react-media-recorder` 导致的 `Worker is not defined` 报错，采用 Dynamic Import 隔离服务端渲染。
- **UI 布局重构**: 使用 Flexbox 重写聊天界面布局，修复输入框遮挡最新消息的问题。
- **双模型配置策略**: 解耦 LLM (DeepSeek) 与 Audio (SiliconFlow) 配置，以最低成本实现多模态能力。

---

## [v2.0.0] - 2025-11-28
> **核心里程碑：全栈化重构与长期记忆系统**
> 从脚本工具转型为带有用户系统和数据库的 SaaS 级应用。

### 🚀 新特性 (New Features)
- **用户鉴权系统**: 基于 `SQLModel` + `JWT` 实现完整的注册、登录、Token 验证流程。
- **长期记忆 (Long-Term Memory)**:
    - 支持上传 PDF/Word 简历。
    - 自动提取简历画像并存入数据库 (`UserProfile`)。
    - 生成面试题时自动注入用户背景信息。
- **会话历史管理**: 侧边栏实时显示历史会话，支持点击切换与上下文回溯。
- **现代化 UI**: 复刻 DeepSeek 风格界面，支持 Markdown 实时渲染与流式打字机效果。

### 🏗 性能优化 (Performance)
- **异步并发 (Asyncio)**: 将 JD 解析、技术出题、公司背调从串行改为 `asyncio.gather` 并行，响应速度提升 300%。
- **流式响应 (SSE)**: 全面支持 Server-Sent Events，显著降低首字等待时间 (TTFT)。

---

## [v1.0.0] - 2025-11-25
> **核心里程碑：MVP (最小可行性产品) 发布**
> 实现了基于 JD 生成面试指南的核心业务逻辑。

### ✨ 核心功能
- **JD 深度解析**: 使用 LangChain 提取技术栈、职级要求与软技能。
- **智能出题**: 基于 JD 生成技术面试题与 HR 行为面试题。
- **RAG 检索增强**: 集成 FAISS 向量数据库，基于本地博客知识库增强回答准确性。
- **公司背景调查**: 集成 Tavily Search API，自动联网搜索公司近期新闻与业务动态。
- **结构化输出**: 使用 Pydantic Parser 强制大模型输出标准 JSON 格式。

---

### 🔮 未来规划 (Roadmap)
- [ ] **多模态简历分析**: 支持图片格式简历 (OCR)。
- [ ] **WebRTC 实时通话**: 进一步降低语音延迟，实现打断式对话。
- [ ] **真实面经库接入**: 爬取牛客/脉脉真实面经作为 RAG 数据源。
