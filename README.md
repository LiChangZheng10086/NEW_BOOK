# AI 小说创作助手

基于多 Agent 协作的 AI 小说创作工具：从编剧设定、章节大纲到正文写作与审阅，支持分步编辑与本地持久化。

## 功能特点

- **三步创作流程**：编剧设定 → 章节大纲 → 写作与审阅，每步可编辑后再确认存入
- **多 Agent 协作**：
  - **编剧 Agent**：根据标题、类型、大纲等完善整体设定（含角色、世界、伏笔、剧情段落），可选联网搜索补充
  - **大纲 Agent**：按设定为指定章节生成详细大纲（关键事件、涉及角色、伏笔提示）
  - **章节 Agent**：按大纲撰写正文，支持根据评论家反馈修订
  - **评论家 Agent**：审阅逻辑、风格、角色、连贯性等，输出结构化意见与是否通过
- **本地持久化**：设定、大纲、章节内容存入 Chroma 向量库，支持按小说与章节精确查询
- **会话隔离**：前端使用 Gradio 会话级状态，多用户/多标签互不干扰

## 技术栈

| 类别     | 技术 |
|----------|------|
| LLM 调用 | LangChain + OpenAI 兼容接口（默认 DeepSeek） |
| 工作流   | LangGraph（可选，当前前端为分步手动流程） |
| 向量库   | Chroma + 本地中文嵌入 BAAI/bge-small-zh-v1.5 |
| 前端     | Gradio |
| 配置     | python-dotenv + 项目内 `config` |

## 项目结构

```
new_book_agnet/
├── main.py              # 入口，启动 Gradio
├── requirements.txt
├── .env.example         # 环境变量示例
├── config/
│   ├── settings.py      # 配置（API、模型、Chroma 路径等）
│   └── prompts.py       # 各 Agent 提示词模板
├── core/
│   ├── models.py        # Pydantic 数据模型
│   ├── database.py      # Chroma 封装（设定/大纲/章节存储）
│   ├── workflow.py      # LangGraph 工作流（自动编排整书）
│   └── logger.py        # 统一日志（项目根 logs/）
├── agents/
│   ├── planner.py       # 编剧 Agent
│   ├── outline_writer.py # 大纲 Agent
│   ├── chapter_writer.py # 章节写作 Agent
│   └── critic.py        # 评论家 Agent
└── frontend/
    └── app.py           # Gradio 界面（三步 Tab + 会话状态）
```

## 环境要求

- Python 3.10+
- 已配置 DeepSeek API Key（或其它 OpenAI 兼容 API）
- 可选：Tavily API Key（编剧阶段联网搜索世界设定参考）

## 安装与运行

### 1. 克隆并进入项目目录

```bash
cd new_book_agnet
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例并填写密钥：

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

在 `.env` 中设置：

- `DEEPSEEK_API_KEY`：必填，用于所有 LLM 调用
- `TAVILY_API_KEY`：可选，用于编剧阶段的联网搜索

### 4. 启动应用

```bash
python main.py
```

浏览器访问终端中显示的地址（默认 `http://127.0.0.1:7860`）。若未配置 `DEEPSEEK_API_KEY`，页面顶部会提示先配置再使用。

## 使用说明

1. **第一步：编剧设定**  
   填写标题、类型、故事大纲、角色、世界设定、伏笔线索、写作风格、目标章节数 → 点击「生成完善设定」→ 在右侧编辑 JSON → 点击「确认并存入数据库」。

2. **第二步：章节大纲**  
   输入章节编号 → 点击「生成章节大纲」→ 编辑 JSON → 点击「确认大纲并存入数据库」。

3. **第三步：写作与审阅**  
   点击「生成章节正文」→ 可编辑正文 → 点击「评论家审阅」查看意见 → 需要时点击「根据建议修改」→ 满意后点击「确认章节并存入数据库」。

数据保存在项目目录下的 `chroma_db/`，日志在 `logs/novel_agent.log`。

## 配置说明

- `config/settings.py`：可修改默认模型（如 `deepseek-reasoner`）、`chroma_db_dir`、`max_critic_iterations` 等。
- 使用其它 OpenAI 兼容服务时，可修改 `deepseek_base_url` 与对应 API Key 的读取方式。

## 许可证

按项目仓库约定使用。
