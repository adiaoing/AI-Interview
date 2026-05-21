# AI Interview - AI 模拟面试教练

Friday 是一个全栈 AI 模拟面试项目，支持行为面试、角色定制面试和技术编程面试。项目包含 Next.js 前端、FastAPI 后端、Supabase 数据库、RAG 检索和本地代码执行能力。

当前版本已经针对中国大陆开发环境做了适配：后端大模型与向量模型使用阿里云百炼 DashScope 的 OpenAI 兼容接口，不再默认依赖 Claude 或 OpenAI 官方接口。

## 功能概览

- 行为面试：按 STAR 方法生成问题，并根据回答给出评分和建议。
- 角色面试：可填写目标岗位，生成更贴近岗位要求的问题。
- 技术面试：从内置题库中抽取算法题，提供编辑器、运行和提交入口。
- 面试报告：汇总回答记录、分数、能力项和教练建议。
- 本地代码执行：技术题运行通过后端本地执行 Python/JavaScript，不再依赖外部 Piston 服务。

## 本次新增功能

### 1. 会话级短期记忆

- 新增基于 LangGraph 共享 `state` 的短期工作记忆，面试官、评分器、追问器、教练 Agent 在同一场 session 中共享当前问题、候选人回答、能力分数、追问状态和教练建议。
- 短期记忆不再只依赖后端内存，新增 `session_state_snapshots` 表，在 session 创建、首题生成、每轮回答结束、面试完成时都会保存会话快照。
- 当后端进程重启或 `_session_states` 内存态丢失时，可以从最新快照恢复当前 session，避免同一场面试中断后完全丢失上下文。
- `POST /sessions/{session_id}/start` 现在支持“已生成过首题则直接恢复返回”，不会重复生成新的开场题。

### 2. 当前 session 内历史弱点检索

- 新增基于 `message_embeddings` 的会话级语义检索，每轮回答结束后会把“问题 + 回答”写入向量库。
- 检索时采用“回答优先、题目辅助”的 embedding 策略，更关注候选人的表达方式、细节缺失和回答深度，而不是只按题目表面相似度匹配。
- `followup` 节点会在当前 session 内检索相似历史回答，用于判断候选人是否在同一场面试中反复暴露相似弱点。
- 报告页和面试页新增了历史相似弱点展示区，可以直接看到命中的历史片段、能力项、分数和相似度。

### 3. 用户级长期记忆

- 新增 `user_memories` 表，用于保存跨 session 的用户级长期记忆。
- 长期记忆支持以下类型：
  - `profile`：长期技能栈、经验方向、背景标签
  - `project`：项目背景、职责范围、核心技术栈
  - `strength`：稳定出现的优势
  - `weakness`：反复暴露的问题或表达缺陷
  - `preference`：偏好的岗位方向、技术方向、工作重心
- 每条长期记忆都包含 `content`、`embedding`、`confidence`、`source_session_id`、`last_used_at` 等字段，便于后续检索和更新。
- 新增 `match_user_memories()` pgvector 检索函数，支持按用户维度和记忆类型进行跨 session 召回。

### 4. 长期记忆写入策略

- 不是所有对话内容都会写入长期记忆，只抽取“稳定信息”。
- 简历上传后，会从简历中抽取长期技能栈、核心项目背景、显著优势和目标岗位方向，写入 `user_memories`。
- 每轮面试回答结束后，也会从候选人的回答、评分反馈、优点、缺口中抽取少量稳定信息写入长期记忆。
- 写入时会对相同 `user_id + memory_type + content` 做去重；如果已存在相同记忆，会更新 `confidence` 和 `last_used_at`，避免重复堆积。

### 5. 跨 session 记忆注入

- 新 session 出题前，系统会先检索用户级长期记忆，而不是只依赖当前 session 的消息历史。
- 检索时会综合以下信息构造查询：
  - 当前目标岗位 `role`
  - 当前面试类型
  - 当前轮次的问题方向
  - 当前 session 中上传的简历和岗位信息片段
- `interviewer` 节点在生成问题时，会把召回的长期记忆作为内部上下文注入 prompt，从而让问题更贴近候选人的真实背景和历史表现。
- 这样同一个用户下一次再来面试时，系统可以记住他过去的技能栈、项目经历、偏好方向和长期薄弱点，而不是每次从零开始。

### 6. 简历上传与简历检索增强

- 新增简历文本上传接口：`POST /sessions/{session_id}/resume`
- 新增简历文件上传接口：`POST /sessions/{session_id}/resume/file`
- 支持两种简历输入方式：
  - 直接粘贴文本
  - 上传 `PDF / DOCX` 文件
- 后端会对简历内容做标准化清洗、切块、向量化，并写入：
  - `session_resumes`：保存原始简历文本和处理状态
  - `document_chunks`：保存切块后的向量化片段
- 面试官生成问题时，会优先检索和当前岗位、当前问题方向相关的简历片段，让开场问题和项目深挖问题更贴近候选人的真实项目经历。
- 同时，简历中的稳定信息还会进入用户级长期记忆，供跨 session 复用。

### 7. 岗位信息 / JD 上传与检索增强

- 新增岗位描述文本上传接口：`POST /sessions/{session_id}/job-description`
- 新增岗位描述文件上传接口：`POST /sessions/{session_id}/job-description/file`
- 支持两种岗位信息输入方式：
  - 直接粘贴 JD 文本
  - 上传 `PDF / DOCX` 文件
- 后端会对岗位描述做标准化清洗、切块、向量化，并写入：
  - `session_job_descriptions`：保存原始岗位文本和处理状态
  - `document_chunks`：保存 JD 切块后的向量化片段
- 面试官在出题时会结合 JD 检索结果，动态切换提问重点：
  - 项目轮次更偏向简历片段
  - 基础知识、岗位场景、职责判断更偏向 JD 片段
- 这样生成的问题会更贴近目标岗位要求，而不是只根据通用模板随机提问。

### 8. 报告与前端可视化增强

- 面试页新增“历史相似弱点”展示区域，用于实时显示当前 session 内命中的历史弱点片段。
- 面试页新增“Cross-session memory”展示区域，用于显示当前轮次召回到的用户长期记忆。
- 报告页新增 `rag_insights` 展示，用于汇总本场面试中命中的历史相似弱点。
- 报告页新增 `user_memory_matches` 展示，用于显示当前 session 中召回到的跨 session 长期记忆。
- 前后端类型定义同步扩展，新增了 `RagMatch`、`RagInsight`、`UserMemoryMatch` 等结构，便于后续继续扩展 memory 功能。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 16、React 19、Tailwind CSS、Monaco Editor |
| 后端 | FastAPI、Uvicorn、Pydantic |
| 大模型 | 阿里云百炼 DashScope OpenAI 兼容接口 |
| 向量模型 | DashScope `text-embedding-v4`，默认 1536 维 |
| 数据库 | Supabase PostgreSQL + pgvector |
| 认证 | Supabase Auth |
| 语音 | ElevenLabs TTS，可选 |
| 代码执行 | 后端本地 Python / Node.js 子进程 |

## 项目结构

```text
.
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── requirements.txt         # 后端依赖
│   ├── api/
│   │   ├── sessions.py          # 面试 session 接口
│   │   ├── technical.py         # 技术题与本地代码执行接口
│   │   └── tts.py               # TTS 接口
│   ├── agents/
│   │   ├── llm.py               # 百炼模型调用封装
│   │   ├── interviewer.py       # 面试官节点
│   │   ├── grader.py            # 评分节点
│   │   ├── followup.py          # 追问节点
│   │   ├── coach.py             # 教练建议节点
│   │   └── state.py             # 面试状态类型
│   ├── rag/
│   │   ├── embeddings.py        # 百炼 embedding 调用
│   │   ├── retriever.py         # 当前 session 相似回答检索
│   │   └── user_memories.py     # 用户级长期记忆抽取与检索
│   ├── db/
│   │   ├── schema.sql           # Supabase 建表 SQL
│   │   ├── client.py            # Supabase client
│   │   └── queries.py           # 数据库查询封装
│   └── data/
│       └── problems.json        # 技术题题库
├── frontend/
│   ├── app/                     # Next.js App Router 页面
│   ├── components/              # UI 与面试组件
│   ├── lib/                     # 前端 API、Supabase、代码执行调用封装
│   ├── types/                   # TypeScript 类型
│   └── package.json
├── setup.sh                     # 初始化脚本
├── dev.sh                       # 本地开发启动脚本
├── deploy.sh                    # 部署脚本
└── kill.sh                      # 停止本地进程脚本
```

## 环境要求

- Python 3.11+
- Node.js 18+
- npm
- Supabase 项目
- 阿里云百炼 API Key
- Node.js 运行时，用于本地执行 JavaScript 技术题

## 环境变量

### 后端：`backend/.env`

```env
# 阿里云百炼 / DashScope
DASHSCOPE_API_KEY=你的百炼APIKey
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_CHAT_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSIONS=1536

# 可选：语音合成。不填则禁用 TTS，不影响文本面试。
ELEVENLABS_API_KEY=

# Supabase
SUPABASE_URL=https://你的项目id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=你的service_role_key

# 本地前端地址
CORS_ORIGINS=http://localhost:3000

# 普通面试最大轮数
MAX_TURNS=8

# 可选：本地代码执行超时时间，单位秒
CODE_RUN_TIMEOUT_SECONDS=5
```

说明：

- `DASHSCOPE_API_KEY`：阿里云百炼 API Key，用于问题生成、评分、追问、教练建议和 embedding。
- `DASHSCOPE_CHAT_MODEL`：聊天模型，默认 `qwen-plus`。
- `DASHSCOPE_EMBEDDING_MODEL`：向量模型，默认 `text-embedding-v4`。
- `DASHSCOPE_EMBEDDING_DIMENSIONS`：向量维度，默认 `1536`，需要和 `backend/db/schema.sql` 里的 `vector(1536)` 保持一致。
- `SUPABASE_SERVICE_ROLE_KEY`：后端服务端密钥，不要放到前端，也不要提交到 GitHub。

### 前端：`frontend/.env.local`

```env
NEXT_PUBLIC_SUPABASE_URL=https://你的项目id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=你的anon_public_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

说明：

- `NEXT_PUBLIC_SUPABASE_URL` 和后端 `SUPABASE_URL` 通常相同。
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` 是 Supabase 的公开 anon key，可以放在前端。
- `NEXT_PUBLIC_API_URL` 指向 FastAPI 后端。

## 初始化数据库

在 Supabase Dashboard 中打开 `SQL Editor`，执行：

```text
backend/db/schema.sql
```

该脚本会创建：

- `sessions`：面试会话
- `messages`：面试问答与评分
- `message_embeddings`：回答向量，用于当前 session 内弱点检索
- `competency_scores`：能力项分数
- `session_state_snapshots`：会话状态快照，用于短期记忆恢复
- `user_memories`：用户级长期记忆，用于跨 session 检索
- `match_session_embeddings()`：pgvector 相似度检索函数
- `match_user_memories()`：用户级长期记忆相似度检索函数

如果建表后接口仍提示找不到表，可以在 Supabase SQL Editor 中执行：

```sql
NOTIFY pgrst, 'reload schema';
```

## 安装依赖

### 后端

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

如果在国内网络环境下安装依赖，建议使用可访问的 PyPI 镜像。

### 前端

```powershell
cd frontend
npm install
```

## 本地启动

### 启动后端

PowerShell：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

访问健康检查：

```text
http://localhost:8000/health
```

正常返回：

```json
{"status":"ok"}
```

注意：当前 Windows 环境下 `uvicorn --reload` 可能遇到 named pipe 权限问题，建议先不使用 `--reload`。

### 启动前端

```powershell
cd frontend
npm run dev
```

访问：

```text
http://localhost:3000
```

## 常见问题

### 点击 Start interview 后提示 Failed to fetch

优先检查：

- 后端是否运行在 `http://localhost:8000`
- `frontend/.env.local` 中 `NEXT_PUBLIC_API_URL` 是否为 `http://localhost:8000`
- `backend/.env` 中 `CORS_ORIGINS` 是否包含 `http://localhost:3000`
- Supabase 是否已经执行 `backend/db/schema.sql`

### 后端提示找不到 `public.sessions`

说明 Supabase 还没有创建表，或 PostgREST schema cache 没刷新。

处理方式：

1. 在 Supabase SQL Editor 执行 `backend/db/schema.sql`
2. 再执行：

```sql
NOTIFY pgrst, 'reload schema';
```

### 技术题加载失败，出现 GBK / UnicodeDecodeError

后端读取题库时必须使用 UTF-8。当前代码已在 `backend/api/technical.py` 中显式使用：

```python
open(data_path, encoding="utf-8")
```

### 点击 Run 或 Submit 出现 Code execution failed (401)

旧版本前端使用外部 Piston 代码执行服务，国内网络环境下可能返回 401。当前版本已改为本地后端执行：

```text
POST /sessions/run-code
```

当前支持：

- Python
- JavaScript

注意：本地代码执行只适合个人开发环境，不建议在公网生产环境直接执行不受信任代码。

### 页面出现不属于本项目的浮层或残影

如果页面里出现其他网站内容，比如不属于 Friday 的列表、广告、赛车页面等，通常是浏览器扩展、缓存或 GPU 合成层问题。

建议：

- 使用 `Ctrl + Shift + R` 强制刷新
- 使用无痕窗口打开
- 临时关闭浏览器扩展
- 尝试换一个浏览器

## API 概览

### 面试 session

```text
POST /sessions
POST /sessions/{session_id}/start
POST /sessions/{session_id}/turn
GET  /sessions/{session_id}/report
GET  /sessions/{session_id}/history
```

### 技术面试

```text
GET  /sessions/{session_id}/technical-problems
POST /sessions/run-code
```

### TTS

```text
POST /tts
POST /tts/interrupt
```

## 当前限制

- 面试状态暂存在后端内存中，多实例部署时需要改为 Redis 或数据库状态存储。
- 本地代码执行没有沙箱隔离，只适合本地开发。
- 技术题当前主要支持 Python 和 JavaScript。
- ElevenLabs TTS 在国内网络环境下可能不可用，可留空禁用。
- README 与部分脚本中历史遗留的乱码注释不影响核心运行，但后续可以继续清理。

## 许可证

MIT License。
