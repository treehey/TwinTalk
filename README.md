# Twin Talk（数字孪生 Demo）

Twin Talk 是一个前后端分离的数字孪生应用 Demo。

- 后端：Flask + SQLAlchemy + SQLite
- 前端：React + Vite
- 核心交互：世界（圈子/私信） + 本我（拟合度校准）

## 项目结构

```text
twin_talk/
├─ demo开发.md
├─ README.md
└─ twintalk/
   ├─ backend/
   │  ├─ api/
   │  ├─ database/
   │  ├─ models/
   │  ├─ prompts/
   │  ├─ services/
   │  ├─ app.py
   │  ├─ config.py
   │  └─ requirements.txt
   └─ frontend/
      ├─ src/
      ├─ index.html
      ├─ package.json
      └─ vite.config.js
```

## 主要功能

- 双核导航
  - 世界（World）：圈子浏览、会话入口、私信聊天
  - 本我（Ego）：拟合度展示、记忆同步、对齐问答、镜像测试
- 私信系统
  - 会话列表、未读标记、会话删除、置顶（本地）
- 画像能力
  - 问卷构建画像、记忆管理、对齐问题生成与提交

## 环境要求

- Python 3.11+（当前环境可使用 3.13）
- Node.js 20+
- npm 10+

## 快速开始

### 1) 启动后端

```powershell
cd twintalk/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

或在根目录直接执行：

```powershell
.\start-backend.ps1
```

后端默认地址：

- `http://127.0.0.1:5000`
- 健康检查：`http://127.0.0.1:5000/api/health`

### 2) 启动前端

```powershell
cd twintalk/frontend
npm install
npm run dev
```

或在根目录直接执行：

```powershell
.\start-frontend.ps1
```

前端默认会尝试使用 `3000` 端口；如果被占用，Vite 会自动切换到 `3001` 或其他端口。

## 配置说明

### 后端环境变量（`twintalk/backend/.env`）

关键字段：

- `FLASK_ENV=development`
- `FLASK_DEBUG=true`
- `PORT=5000`
- `DATABASE_URL=sqlite:///digital_twin.db`
- `OPENAI_API_KEY=...`
- `OPENAI_BASE_URL=...`
- `OPENAI_MODEL=...`

### 前端代理（`twintalk/frontend/vite.config.js`）

前端将 `/api` 请求代理到：

- `http://127.0.0.1:5000`（默认）
- 或由 `VITE_API_PROXY_TARGET` 指定

## 常见问题

### 1. 页面空白/看不到 UI

请确认：

- 你打开的是前端地址（Vite 输出的 Local URL），不是后端根地址
- 前端是否因端口占用从 `3000` 自动切换到 `3001`
- 后端是否已启动并能访问 `/api/health`

### 2. `npm ERR! enoent ... package.json`

通常是当前目录不对。请先进入 `twintalk/frontend` 再执行 `npm` 命令。

### 3. `ModuleNotFoundError: No module named 'flask_cors'`

说明后端依赖未安装完整。请在 `twintalk/backend` 目录执行：

```powershell
pip install -r requirements.txt
```

## 开发命令

前端：

```powershell
cd twintalk/frontend
npm run dev
npm run build
npm run preview
```

根目录快捷命令：

```powershell
.\start-frontend.ps1
```

后端：

```powershell
cd twintalk/backend
python app.py
```

根目录快捷命令：

```powershell
.\start-backend.ps1
```

## 安全建议

- 不要把真实密钥写进仓库（`.env` 仅本地保存）
- 如果密钥已泄露，请立刻在服务商控制台轮换
- 生产环境请关闭 `FLASK_DEBUG`

## Roadmap（Demo）

- [ ] 私信体验细节优化（输入态、加载态、错误提示）
- [ ] 画像校准流程可观测性（进度和结果追踪）
- [ ] Docker 化一键启动
- [ ] 自动化测试覆盖核心流程
