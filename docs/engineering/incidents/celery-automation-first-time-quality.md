# Celery 自动化任务：为什么第一次会写错、怎样第一次就写对

> 来源：从 `.cursor/celery-automation-first-time-quality.md` 迁移。  
> 用途：工程知识沉淀（长期复用），不属于 agent 运行态文件。

**目标**：不只是记录 bug 现象，而是搞清「第一次生成的程序为什么会有 bug」，把对策写进规则，让以后一次成功。

---

## 两次 Bug 的根因（为什么是「我」第一次写错）

### Bug 1：`sync_printify_products_to_local` 报 `unexpected keyword argument 'ignore_flags'`

- **表面原因**：任务签名没有 `ignore_flags`，而调度/API 会传这个参数。
- **为什么第一次会这样写**：写任务时只按「这个任务需要什么」来设计签名（例如 tenant_id、limit），**没有先看调用方传了哪些参数**。调用方（`automation_scheduler_service.py` 的 task_kwargs、`api/v1/endpoints/automation.py` 的 task_kwargs）固定会传 `tenant_id` 和 `ignore_flags`，任务必须全部接受。
- **对策**：写**任何**新 automation 任务签名之前，**必须先看** `automation_scheduler_service.py` 和 `api/v1/endpoints/automation.py` 里如何构建 kwargs，任务签名要能接受这些参数（可加默认值）。规则里已写成强制步骤。

### Bug 2：`sync_shopify_fulfillment_to_local` 报 `Future attached to a different loop` / `Event loop is closed`

- **表面原因**：在 Celery worker 里用 `asyncio.run()` + 全局 `AsyncSessionLocal`，event loop 与连接绑定错位。
- **为什么第一次会这样写**：按「普通 async 函数」的写法来写任务，没有按「Celery worker 内 async+DB」的约束来写；或者没有先看同文件里**已有正确实现**（如 `sync_printify_orders_to_local`），而是自己写了一套结构，结果用了全局 session。
- **对策**：凡任务内要用 asyncio + 数据库，**禁止从零写**。必须先读同文件中的参考任务（`sync_printify_orders_to_local` 或 shopify_tasks 的 `sync_shopify_orders_1min_task`），**复制**其 `run_in_thread` + 线程内 `create_async_engine` + `ThreadAsyncSessionLocal` 的整体结构，只替换内部业务逻辑。规则里已写成强制步骤。

---

## 已做的规则强化（第一次就写对）

在 **`.cursor/rules/celery-async-database.mdc`** 中：

1. **「为什么第一次会写错」**：明确写了两条根因——(1) 没看调用方就写签名；(2) async+DB 没抄参考任务、自己写导致用错模式。
2. **「第一次就写对的强制步骤」**：
   - 写签名前：看 `automation_scheduler_service.py` 与 `api/v1/endpoints/automation.py` 的 kwargs，任务至少接受 `tenant_id`、`ignore_flags`。
   - 写 async+DB 任务时：先读并复制 `sync_printify_orders_to_local`（或 `sync_shopify_orders_1min_task`）的 run_in_thread + 线程内 engine/session 结构，再改业务逻辑。
3. **自检清单**：按「先看调用方 → 先抄参考任务 → 交付前建议用户手动触发一次」执行。

Rule 的 globs 已包含 `**/automation_scheduler_service.py` 和 `**/api/**/automation.py`，编辑这些文件或 tasks 时都会带上上述约定。

---

## TDD（暂不引入）

当前约定：暂不引入 pytest，不做 TDD；依靠「规则 + 强制步骤 + 自检 + 建议用户手动触发一次」提高首次过关率。若日后要加冒烟测试或 TDD，可再在规则或本项目中补充。
