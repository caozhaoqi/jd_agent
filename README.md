# 🚀 JD Agent: 全栈 AI 模拟面试官 (L5 Autonomous Agent)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![Next.js](https://img.shields.io/badge/Frontend-Next.js-black)
![LangGraph](https://img.shields.io/badge/AI-LangGraph-orange)

> **JD Agent** 是一个基于 **多智能体协同 (Multi-Agent Swarm)** 的全栈 AI 应用。它不仅能深度解析岗位描述 (JD) 生成突击指南，还能化身为**全双工语音交互**的面试官，进行实时的模拟面试。

---

## ✨ 核心特性 (Key Features)

### 🧠 1. L5 级多智能体协同 (LangGraph)
摒弃了传统的线性工作流，构建了一个具备**自我反思与纠错能力**的虚拟团队：
- **🕵️ Researcher**: 自动联网 (Tavily) 搜索公司背景、财报与业务动态。
- **💻 Tech Lead**: 基于 JD 技术栈构建硬核面试题。
- **⚖️ Reviewer (质检员)**: 审核题目质量，评分低于 85 分自动打回重写 (Self-Correction)。
- **👨‍💼 Human Approval Node**: 支持人工介入审核流程，提供交互式反馈和状态跟踪。
- **🧠 Brain Dashboard**: 前端实时可视化 Agent 的思维路径、当前步骤与长期记忆。

### 🔊 2. 全双工语音交互 (Real-time Voice)
打造“听得见、说得出”的沉浸式体验：
- **👂 ASR (听)**: 集成 **SiliconFlow / Whisper**，实现秒级语音转文字。
- **🗣️ TTS (说)**: 
    - **macOS**: 调用原生 `say` 命令，零延迟、零成本。
    - **Windows/Linux**: 使用 `pyttsx3` 并通过 `asyncio.to_thread()` 实现异步处理，避免主线程阻塞。
    - **📱 跨平台兼容**: 自动将平台特定格式 (.m4a/.wav) 转换为统一 MP3 格式。
- **⚡️ 增强型音频队列 (Audio Queue)**: 
    - 分句缓冲与串行播放，解决流式生成导致的语音重叠问题。
    - 支持加载状态、错误处理、暂停/恢复功能。
    - 实时队列状态反馈（播放中、队列长度等）。

### 🎨 3. DeepSeek 风格交互 UI
- **深度思考模式**: 实时展示 AI 的思考过程（Thinking Stream），缓解长推理时间的等待焦虑。
- **流式打字机**: 基于 SSE (Server-Sent Events) 实现极速首字响应。
- **Markdown 渲染**: 完美渲染结构化报告、代码块与表格。

### 💾 4. 长期记忆系统 (Memory)
- **简历解析**: 上传 PDF/Word 简历，自动提取画像存入 SQLModel 数据库。
- **会话回溯**: 侧边栏管理历史会话，AI 永远记得你的技术栈偏好。

---

## 🏗️ 技术架构 (Architecture)

```mermaid
graph TD
    User((🙍‍♂️ 用户)) <-->|Web Audio / SSE| Frontend[🖥️ Next.js 前端]
    Frontend <-->|HTTP / Stream| Backend[⚙️ FastAPI 后端]

    subgraph "🧠 智能体大脑 (LangGraph)"
        Start(开始) --> Parser[🔍 职位解析员]
        Parser --> Researcher[🕵️ 商业情报员]
        Parser --> TechLead[💻 技术面试官]
        
        Researcher --> Context{信息汇总}
        TechLead --> Reviewer[⚖️ 质量检察员]
        
        Reviewer -->|评分 < 85| TechLead
        Reviewer -->|评分 >= 85| End(✅ 输出报告)
    end

    subgraph "🔊 语音交互层"
        ASR[👂 Whisper API]
        TTS[🗣️ Native / Edge TTS]
    end

    Backend --> ASR
    Backend --> TTS
    Backend --> Start
```

---

## 🛠️ 快速开始 (Getting Started)

### 前置要求
- Python 3.10+
- Node.js 18+
- OpenAI / DeepSeek / SiliconFlow API Key

### 1. 后端设置 (Backend)

```bash
# 1. 进入项目目录
cd jd_agent

# 2. 创建虚拟环境并激活
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key (推荐使用 DeepSeek + SiliconFlow 组合)

# 5. 启动服务
uvicorn src.app.main:app --reload
```

**`.env` 配置示例：**
```ini
# LLM (大脑)
OPENAI_API_KEY=sk-deepseek-xxx
OPENAI_API_BASE=https://api.deepseek.com
MODEL_NAME=deepseek-ai/DeepSeek-V3

# Audio (感官 - 推荐 SiliconFlow 免费版)
AUDIO_API_KEY=sk-siliconflow-xxx
AUDIO_API_BASE=https://api.siliconflow.cn/v1
ASR_MODEL=FunAudioLLM/SenseVoiceSmall

# Search (联网)
TAVILY_API_KEY=tvly-xxx
```

### 2. 前端设置 (Frontend)

```bash
# 1. 进入前端目录 (假设你在根目录下创建了 jd-chat-ui)
cd jd-chat-ui

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

打开浏览器访问 [http://localhost:3000](http://localhost:3000) 即可开始使用。

---

## 🖥️ 使用指南

### 模式一：JD 深度分析
1.  在输入框粘贴 **岗位描述 (JD)**。
2.  观察右侧 **Brain Dashboard**，查看 Agent 如何拆解任务、搜集情报。
3.  获取一份包含 **公司背景、技术必考题、HR 陷阱题** 的结构化报告。

### 模式二：模拟面试 (Mock Interview)
1.  分析完 JD 后，点击 **“🎤 开始模拟面试”** 按钮。
2.  AI 将切换为 **“严厉面试官”** 人设。
3.  **按住麦克风** 回答问题，AI 会识别语音并进行追问。
4.  开启右上角的 **语音开关**，体验全语音对话。

---

## 📂 项目结构

```text
jd_agent/
├── src/
│   ├── app/
│   │   ├── api/             # FastAPI 路由接口 (Stream, Auth, Audio)
│   │   ├── chains/          # LangChain 原子能力 (Generator, Parser)
│   │   ├── core/            # 核心配置 (Config, DB, LLM Factory) & 统一错误处理
│   │   ├── graph/           # LangGraph 多智能体编排 (Nodes, Workflow) - 含人工介入节点
│   │   └── services/        # 业务逻辑层
│   ├── components/          # Next.js UI 组件 (ChatInput, Dashboard, AudioQueue)
│   └── prompts/             # Prompt YAML 模板管理
├── tests/                   # 测试用例
└── requirements.txt         # 依赖列表
```

---

## 🚧 开发计划 (Roadmap)

- [x] **v1.0**: JD 解析与题库生成 (RAG)
- [x] **v2.0**: 长期记忆 (User Profile) 与 鉴权系统
- [x] **v3.0**: L5 多智能体协同 & 全双工语音交互
- [x] **v3.1**: 低优先级优化
  - [x] TTS 异步处理 pyttsx3 调用，避免阻塞主线程
  - [x] 完善多智能体工作流人工介入机制
  - [x] 优化前端音频队列用户体验
  - [x] 统一系统全局错误处理机制
- [ ] **v4.0**: WebRTC 超低延迟通话 (打断式交互)
- [ ] **v5.0**: 多模态简历分析 (支持图片/PDF 图表读取)

---

## 🤝 贡献 (Contribution)

欢迎提交 Issue 或 Pull Request！
如果你喜欢这个项目，请给一个 ⭐️ Star！

## 📄 开源协议 (License)

MIT License © 2025 CaoZhaoQi