# 角色设定
你是一个资深的 Python 高并发后端架构师。目前我们的项目中有一个调用大语言模型（LLM）的服务，我们手头拥有多个 API Key。为了极致化利用这些 Key，防止并发冲突和超频，我需要你基于“连接池（Connection Pool）”的理念，实现一套线程/协程安全的 API Key 管理器。

# 核心机制要求：闲置队列与动态冷却
请在 `backend/services/llm_client.py` 中编写一个 `APIKeyPool` 类，并遵循以下机制：

## 1. 闲置池管理 (Idle Queue)
* 系统启动时，将 15 个 API Key 全部放入一个线程安全的队列中（如 Python 原生的 `queue.Queue` 或 `asyncio.Queue`，请根据代码的同步/异步环境选择）。
* **借出（Borrow）**：每次发起 LLM 请求前，必须使用 `queue.get()` 阻塞或等待获取一个处于“空闲”状态的 Key。
* **归还（Return）**：无论请求成功还是遇到普通异常，请求结束后必须在 `finally` 块中通过 `queue.put(key)` 将 Key 归还给空闲池，供其他并发线程使用。

## 2. 限流冷却机制 (Cooldown / Circuit Breaker)
* 如果在使用某个 Key 请求时遇到了 `429 Too Many Requests`（限流/超频），该 Key **不能立刻归还**到空闲池。
* 请实现一个异步任务或后台定时器机制：将触发 429 的 Key 扣留在一个“冷却区”，等待 N 秒（例如 20 秒）后，再自动将其 `put` 回空闲池。

## 3. 自动重试逻辑 (Retry Strategy)
* 封装一个调用函数 `call_llm_with_pool(prompt, max_retries=3)`。
* 内部逻辑：从池中借出一个 Key -> 发起 HTTP 请求 -> 
  * 如果成功：归还 Key，返回结果。
  * 如果报 429：扣留该 Key 进入冷却，立刻执行 `continue` 进入下一次循环（自动从池中借用**下一个空闲的 Key** 并重试）。
  * 如果报其他网络错误：归还 Key，并记录日志重试。

## 4. 工程规范
* 代码必须是线程安全的（考虑我们在业务中使用了 `ThreadPoolExecutor` 并发请求）。
* 支持从环境变量读取这 15 个 Key（逗号分隔的字符串）。
* 提供详细的日志打印，例如：“[APIKeyPool] 成功借出 Key(xxx)”，“Key(xxx) 触发限流，进入冷却 20s”，“等待空闲 Key 超时”等。
* 提供健壮的容错处理：如果池子里的 Key 全部在冷却中，`queue.get(timeout=X)` 应该能优雅捕获 `Empty` 异常并告知调用方当前系统繁忙。

## 5. 限额解除
* 取消安全限制，允许无限次调用。
请直接输出可运行的 Python 代码结构，包含类定义和实际调用的封装函数。