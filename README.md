# 智语桥（ZhiYuQiao）

面向国际中文教师与学习者的海派文化 AI 学习平台：本地知识库检索（RAG-lite）+ DeepSeek(OpenAI-compatible) 对话生成 + FastAPI 双角色网页工作台。

## 目录结构

- `app.py`：启动入口，默认运行 FastAPI 网站（端口默认 `7860`）
- `main.py`：网站与 API 主应用，包含登录、注册、设置、会话和助手页面
- `templates/`：登录 / 注册 / 设置 / 学生学习空间 / 教师教学工作台模板
- `static/`：网站样式与前端交互脚本
- `core/db.py`：数据库连接与会话工厂
- `core/account_profiles.py`：账号、密码哈希、学生/教师画像、服务端会话、学习任务和教案草稿
- `core/assistant_service.py`：网页工作台的统一 skill 调度入口
- `core/ai_agent.py`：顾问对话（检索 + 生成）
- `core/retriever.py`：知识库检索与路由（HSK/策略/软件/文献/纠错等）
- `core/skills/specs.py`：Skill Spec 注册表
- `core/skills/runtime.py`：Skill Spec 运行时（调模型 / JSON 解析 / 后处理）
- `core/skills/translation.py`：翻译 skill 封装
- `core/skills/correction.py`：批改 skill 封装
- `database/haipai_culture/`：可追溯海派文化知识记录与官方来源
- `database/`：其他结构化知识库数据（CSV/JSONL）

## 配置（.env）

在项目根目录创建 `.env`（不要提交到 Git）：

```
DEEPSEEK_API_KEY=你的key
# 可选：默认 deepseek-chat
DEEPSEEK_MODEL=deepseek-chat
# 可选：自定义 OpenAI-compatible base_url
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 生产环境建议使用 PostgreSQL
# 例如：
# DATABASE_URL=postgresql+psycopg://zhiyuqiao:password@127.0.0.1:5432/zhiyuqiao
#
# 本地如果不配置 DATABASE_URL，会回退到项目内置 sqlite 文件，便于开发调试
```

## 本地运行（网页工作台）

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
python3 app.py
```

浏览器访问：`http://127.0.0.1:7860`

首次启动后：

- 如果系统里还没有任何账号，会先进入注册页
- 注册时可选择“学生”或“教师”，登录后系统自动进入对应空间
- 学生端按 HSK 水平和学习目标提供海派文化探索、中文学习与情景口语功能
- 教师端提供海派文化课程实验室、教学设计、批改、翻译与标准政策工具
- AI 回答支持流式显示与停止生成，海派文化回答附带可点击的核验来源
- 学生可保存任务、记录反思并形成真实进度；教师可保存、编辑、审核并导出教案
- 身份、首选讲解语种、学习/教学画像和主题色都可以在 `/settings` 中修改
- 用户可在设置中自助注销并删除账号、任务、反思、草稿和登录会话

## 运行主应用（uvicorn 方式）

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 主要页面

- `/register`：注册页
- `/login`：登录页
- `/student`：学生学习空间（仅学生身份）
- `/teacher`：教师教学工作台（仅教师身份）
- `/assistant`：兼容入口，按当前身份自动跳转
- `/settings`：账号设置页
- `/privacy`：隐私与 AI 使用说明
- `/teacher/artifacts/{id}`：教师草稿编辑、审核与打印导出页

## 主要 API

### 当前登录用户

```
GET /api/me
```

### 获取 skill 列表

```
GET /api/skills
```

### 发送一条助手消息

前端默认使用 `POST /api/message/stream` 获取 NDJSON 流式回答；`POST /api/message` 保留为非流式兼容接口。两者都需要登录 Cookie 和与 `zhiyuqiao_csrf` Cookie 相同的 `X-CSRF-Token` 请求头。

```
curl -X POST http://127.0.0.1:8000/api/message \
  -H 'Content-Type: application/json' \
  -H 'Cookie: zhiyuqiao_session=你的session; zhiyuqiao_csrf=你的csrf' \
  -H 'X-CSRF-Token: 你的csrf' \
  -d '{
    "skill_key": "teacher_advisor",
    "text": "请帮我设计一节葡语背景零基础学习者的中文导入课",
    "history": []
  }'
```

### 学习任务与教案草稿

- `GET/POST /api/student/tasks`：获取或保存当前学习者的任务
- `POST /api/student/tasks/{id}/complete`：记录完成情况与学习反思
- `GET/POST /api/teacher/artifacts`：获取或保存当前教师的教案草稿
- `GET /teacher/artifacts/{id}/download`：导出本人草稿为 Markdown

### 健康检查

- `GET /health`：进程存活
- `GET /health/ready`：数据库与知识目录就绪，可用于部署验收

## Skill Spec

当前项目新增了轻量级 Skill Spec 机制，模仿 OpenClaw 的“声明式能力定义 + 统一运行时”思路：

- `跨语种翻译`：跨语种教学翻译，输出结构化结果，中文输出时自动补拼音和核心词汇解释
- `中文批改`：中文学习文本批改，输出纠错结果、错误分析和教学建议
- `教学设计咨询`、`HSK 备考指导`、`数字化工具推荐`、`政策法规解读`：统一通过 Skill Spec 运行时调度

网页端的“快捷功能”已经统一并入 skill 列表，不再区分额外模块。

## Ubuntu 部署

如果你想直接在 Ubuntu 服务器上重建网站，仓库里已经提供了可复用模板：

- `deploy/ubuntu/README.md`：完整部署步骤
- `deploy/ubuntu/zhiyuqiao.service`：`systemd` 服务模板
- `deploy/ubuntu/nginx-ip.conf`：公网 IP 访问模板
- `deploy/ubuntu/nginx-domain.conf`：域名访问模板
- `deploy/ubuntu/server.env.example`：服务器 `.env` 示例

建议先用公网 IP 方案上线，确认服务可用后，再切换域名和 HTTPS。

## 测试与质量门

```bash
ruff check main.py core test_role_security.py test_learning_workflow.py test_retriever_regressions.py test_minimal_launch.py
python test_role_security.py
python test_learning_workflow.py
python test_retriever_regressions.py
python test_minimal_launch.py
```

GitHub Actions 会在 `main` 推送和 Pull Request 上自动执行同一组静态检查与关键回归。完整的向量库构建、数据分析和文档生成工具仍保留在 `requirements.txt`；仅部署网站时使用更小的 `requirements-web.txt`。
