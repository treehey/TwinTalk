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

短信验证码相关字段：

- `SMS_PROVIDER=mock`（本地开发默认，仅打印到后端日志）
- `SMS_PROVIDER=twilio`（生产推荐，启用真实短信发送）
- `TWILIO_ACCOUNT_SID=...`
- `TWILIO_AUTH_TOKEN=...`
- `TWILIO_FROM_NUMBER=...`
- `SMS_BODY_TEMPLATE=[TwinTalk] Your verification code is {code}. It expires in 5 minutes.`

### 前端代理（`twintalk/frontend/vite.config.js`）

前端将 `/api` 请求代理到：

- `http://127.0.0.1:5000`（默认）
- 或由 `VITE_API_PROXY_TARGET` 指定

## 短信验证码实施要求（交接必读）

本节用于给后续开发/维护同学，明确“手机号登录/注册验证码”能力的现状、接口约定与上线要求。

### 1) 功能目标

- 登录与注册都必须先通过短信验证码校验。
- 验证码为 6 位数字，服务端校验。
- 同一手机号+用途有发送冷却，避免频繁轰炸。
- 验证码有有效期，并限制错误重试次数。

### 2) 当前实现范围（已落地）

- 后端接口：`POST /api/auth/send-sms-code`
  - 用途：发送短信验证码。
  - 请求体：`{ phone_number, purpose }`
  - `purpose` 仅允许：`login`、`register`
- 后端接口：`POST /api/auth/register`
  - 请求体新增：`sms_code`、`sms_purpose=register`
- 后端接口：`POST /api/auth/login`
  - 请求体新增：`sms_code`、`sms_purpose=login`
- 前端登录/注册页：
  - 增加“发送验证码”按钮
  - 增加 60 秒倒计时
  - 增加短信码输入框

### 3) 接口契约（必须保持兼容）

#### 3.1 发送验证码

- 路径：`POST /api/auth/send-sms-code`
- 请求示例：

```json
{
  "phone_number": "13800138000",
  "purpose": "login"
}
```

- 成功响应示例：

```json
{
  "success": true,
  "ttl_seconds": 300,
  "retry_after": 60
}
```

- 失败响应约定：
  - `400`：参数不合法（手机号为空、purpose 无效）
  - `429`：发送过于频繁，返回 `retry_after`
  - `503`：短信供应商调用失败

#### 3.2 登录

- 路径：`POST /api/auth/login`
- 请求示例：

```json
{
  "phone_number": "13800138000",
  "password": "******",
  "sms_code": "123456",
  "sms_purpose": "login"
}
```

#### 3.3 注册

- 路径：`POST /api/auth/register`
- 请求示例：

```json
{
  "phone_number": "13800138000",
  "password": "******",
  "sms_code": "123456",
  "sms_purpose": "register"
}
```

### 4) 关键策略参数（当前默认）

- 验证码有效期：`300` 秒
- 单次发送冷却：`60` 秒
- 校验最大错误次数：`5` 次
- 验证成功后立即失效（防重放）

### 5) 短信供应商配置说明

- 开发环境：`SMS_PROVIDER=mock`
  - 不实际发短信，只在后端日志输出验证码（便于联调）
- 生产环境：`SMS_PROVIDER=twilio`
  - 必填：`TWILIO_ACCOUNT_SID`、`TWILIO_AUTH_TOKEN`、`TWILIO_FROM_NUMBER`

### 6) 安全与合规要求

- 严禁在前端、日志、响应体长期暴露真实验证码。
- `debug_code` 仅允许在开发环境临时返回，生产必须关闭。
- 短信文案不得包含敏感业务信息。
- 必须启用 HTTPS 传输，避免验证码在链路中明文泄露。
- 验证码存储应有过期和删除机制，防止内存堆积。

### 7) 生产化改造建议（后续必须排期）

当前验证码状态使用进程内内存保存，适合单机开发。若要正式上线，建议按优先级完成：

- 使用 Redis 存储验证码状态（支持多实例共享）。
- 增加按手机号、IP、设备指纹的更细粒度限流。
- 增加手机号格式校验（E.164）与风控黑名单。
- 接入短信发送回执与失败重试告警。
- 增加审计日志（发送次数、失败原因、风控拦截）。

### 8) 联调与验收清单

- 能发送登录验证码，并在 60 秒内重复发送被正确拦截。
- 验证码错误时返回明确提示，且累计超过阈值后需重新发送。
- 验证码过期后不可使用。
- 登录/注册必须依赖验证码，缺失验证码时请求应失败。
- 切换到 `twilio` 配置后可真实下发短信。

### 9) 变更影响范围

- 后端：`twintalk/backend/api/auth.py`
- 后端：`twintalk/backend/services/sms_service.py`
- 后端：`twintalk/backend/config.py`
- 前端：`twintalk/frontend/src/services/api.js`
- 前端：`twintalk/frontend/src/pages/Onboarding.jsx`

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
