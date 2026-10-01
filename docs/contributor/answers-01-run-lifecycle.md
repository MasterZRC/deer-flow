# 答案卷 01：一次 run 的生命周期（**先自己答题，再看这里**）

> 来源：独立子代理在 HEAD `4d560722` 上做的只读考古，**所有行号已二次核验**；其中
> Unknowns 里的"孤儿状态"一项由我另行验证（见 §5）。
> 用法：你答完 [assignment-01-run-lifecycle.md](assignment-01-run-lifecycle.md) 之后再对照本卷。
> **提前看会损失最大的那部分价值——被自己的错误纠正过的记忆，才是最牢的。**

---

## 1. 一次 run 的调用链（从 nginx 到最后一帧）

nginx 把 `/api/langgraph/*` 重写为 `/api/*`（`docker/nginx/nginx.conf:80-81`），所以
线上路径是 `POST /api/langgraph/threads/{tid}/runs/stream` → Gateway 的 `POST /api/threads/{tid}/runs/stream`。

| # | 位置 | 符号 / 作用 |
| --- | --- | --- |
| 1 | `app/gateway/routers/thread_runs.py:963` | `stream_run`（SSE 版）；同族 `create_run:945`、`wait_run:1018`；无状态版 `routers/runs.py:33` |
| 2 | `app/gateway/routers/thread_runs.py:91` | `_scope_http_run_idempotency_key` → `http-run:{sha256(owner\0tid\0key)}` |
| 3 | `app/gateway/services.py:1684` | **`start_run` —— 唯一的准入咽喉**（HTTP / 定时 / MCP 通知都走它） |
| 4 | `services.py:1713` | `require_cancel_permission_if`：`interrupt`/`rollback` 需要 `runs:cancel` 而非 `runs:create` |
| 5 | `services.py:1723` | `validate_run_metadata_secrets`（body.metadata 与 body.config.metadata） |
| 6 | `services.py:1728` | `normalize_stream_modes` + 模型白名单校验 |
| 7 | `services.py:1766` | `thread_access_allowed`（run 行还不存在时就先做属主校验） |
| 8 | `services.py:1795` | `normalize_input`（拒绝外部传入的 system/developer 角色）、`Command(resume=…)` 优先 |
| 9 | `services.py:1810` | **trace id 重新盖章** `ensure_trace_id()`（调用方传的 `deerflow_trace_id` 一律不认） |
| 10 | `services.py:1813` | `build_run_config`（默认 `recursion_limit` 热重载；剥掉调用方的 `__` 前缀 context key） |
| 11 | `services.py:1814` | `apply_checkpoint_to_run_config`（校验 checkpoint 属于本 thread） |
| 12 | `services.py:1820-1824` | `merge_run_context_overrides(internal=)` + `strip_internal_context_keys`（**信任边界**） |
| 13 | `services.py:1888` | `inject_authenticated_user_context`（清空并重盖服务端拥有的一切身份/生命周期 key） |
| 14 | `services.py:2062` | `goal_thread_lock(thread_id)` → `runtime/goal.py:71`（进程内串行化） |
| 15 | `services.py:2063` | `ensure_checkpoint_history_seeded`（老 checkpoint → 事件流的回填垫片） |
| 16 | `services.py:2076` | **`run_mgr.create_or_reject(...)` → 持久化准入**；记录初始状态 `pending` |
| 17 | `runtime/runs/manager.py:1570` | `_admit_thread_operation`：幂等索引 + 本地 in-flight 检查 + `create_thread_operation_atomic` |
| 18 | `services.py:2126` | `record.task = asyncio.create_task(run_after_metadata(record))`（持久化准入与挂任务之间**没有 await**） |
| 19 | `services.py:1946` | `run_after_metadata` → `_ensure_thread_metadata` → `run_agent(...)` |
| 20 | `runtime/runs/worker.py:868` | **`run_agent`**：建 journal(`:1004`)、等前一个 finalizing run(`:1035`)、`try_start`(`:1041`) → **pending→running** |
| 21 | `worker.py:1073/1085/1126` | 线程状态置 `running`、模式门 `aensure_checkpoint_mode_compatible`、发布 `metadata` 帧 |
| 22 | `worker.py:1143-1180` | `_build_runtime_context` → `_pin_admission_project_context` → `_bind_trace_id` → `_install_runtime_context` |
| 23 | `worker.py:1214` | `run_assembly(agent_factory=…)` 在 loop 外装配；工厂是 `deerflow.agents:make_lead_agent` |
| 24 | `agents/lead_agent/agent.py:832→952→1326→1357` | `make_lead_agent` → `assemble_lead_agent`（冻结模式）→ `build_middlewares` → **`create_agent` 编译图** |
| 25 | `worker.py:1231-1278` | `CheckpointStateAccessor.bind(...)` + `_capture_rollback_point` + `_linearize_delta_checkpoint_resume`（都在 `_checkpoint_thread_lock` 内） |
| 26 | `worker.py:1326-1446` | `_stream_once`：`astream(..., stream_mode=lg_modes, subgraphs=…)`；每块 → `_unpack_stream_item` → `_publish_stream_item` → `bridge.publish` |
| 27 | `worker.py:1447-1469` | 隐藏的 goal 续跑循环（cap 8） |
| 28 | `worker.py:1471-1524` | 终态判定：abort → `_finish_cancellation`；LLM fallback → `error`；否则 delivery 检查 → `success`/`error` |
| 29 | `worker.py:1606-1693` | `journal.flush()` → `_persist_delivery_receipt` → duration checkpoint → `persist_current_status` → `update_run_completion` |
| 30 | `worker.py:1797-1800` | `set_finalizing(False)` → `bridge.publish_end(run_id)` |
| 31 | `worker.py:1829-1860` | `_release_run_scoped_references` → `bridge.cleanup(delay=60)` → `run_manager.cleanup` |
| 32 | `services.py:997` | `StreamingResponse(sse_consumer(...), media_type="text/event-stream")` |
| 33 | `services.py:2358-2391` | `sse_consumer`：`bridge.subscribe(run_id, last_event_id=Last-Event-ID)` → `format_sse`；`END_SENTINEL` → 终结 `event: end` |

## 2. Q1 —— 准入

- **入口**：`POST /api/threads/{tid}/runs/stream` → `stream_run`（`thread_runs.py:963`）。同族 `create_run:945`、`wait_run:1018`、无状态 `routers/runs.py:33`。**只有 `start_run` 一条准入路径**。
- **两把互斥锁**（必须分清）：
  - 进程内：`async with self._lock`，覆盖"in-flight 检查 + 落库 + 本地注册"（`manager.py:1630-1772`，锁序约定见 `:1590-1596`）；
  - 跨进程/持久：`create_thread_operation_atomic` + 局部唯一索引 `(thread_id) WHERE status IN ('pending','running')`（`manager.py:1697`、`:1734`），由所有 `ThreadOperationKind` 共享（`runs/schemas.py:6-14`）。
- **幂等**：调用方 `Idempotency-Key` → 作用域化后进 `RunManager` 的进程级索引。本地命中返回同一条记录（`idempotency_reused=True`，`manager.py:1631`）；**对端/持久命中返回 `store_only` 句柄且故意不本地注册**（`manager.py:1640`，不变式见 `runtime/AGENTS.md:133`）。
- **状态机**：`pending`（`manager.py:1615`）→ `running`（`manager.py:928`）→ 终态 `success` / `error` / `interrupted`（`runs/schemas.py:17-25`）。线程侧投影：`running`（`worker.py:1073`）→ `success` 则 `idle`，否则等于 run 状态（`worker.py:1737`）。
- **客户端能/不能影响**：能影响白名单内的 `context` key；**不能**影响服务端拥有的身份与生命周期 key。四处闸门：`merge_run_context_overrides`（`services.py:702`，`internal=` 门在 `:729`）、`strip_internal_context_keys`（`:687`）、`inject_authenticated_user_context`（`:762`）、worker 侧 `_SERVER_OWNED_RUNTIME_CONTEXT_KEYS` 拒绝（`worker.py:535-556`、`:587`）。`non_interactive` / `disable_clarification` / `github_token` / `channel_name` **仅内部调用方可得**（`services.py:669-684`）。

## 3. Q2 —— 执行

- **`run_agent()`（`worker.py:868`）= 生命周期所有者**：journal、pending→running 屏障、线程状态、模式门、`metadata` 帧、runtime context、回调注册、图工厂调用、accessor + 回滚点捕获、`astream` 循环、goal 续跑、终态判定、整个 finalization `finally`（`:1551-1863`）。**它不构造 agent。**
- **`make_lead_agent()`（`agents/__init__.py:20` → `agent.py:832`）= LangGraph Server ABI**：返回 `assemble_lead_agent(config).graph`。
- **`assemble_lead_agent`（`agent.py:837-875`）**：**冻结** checkpoint 模式（`:869`）与 delta 快照频率（`:873`），注入模式（`:874`）；`_assemble_lead_agent:952` 解析工具、skills、prompt、middleware。
- **`build_middlewares()`（`agent.py:481）= 链装配器**：委托基础链给 `_build_runtime_middlewares`（`tool_error_handling_middleware.py:346`），再追加 lead 专属项，**最后**才合并扩展 `compose_with_extensions`（`agent.py:787/793`）。
- **图在哪编译**：`create_agent(...)`（`agent.py:1357-1364`），`state_schema=get_thread_state_schema(mode)`（`thread_state.py:492`），`context_schema=dict`。
- **顺序语义的坑**：列表顺序 = 组合顺序，但 `after_model` 钩子是**反向**派发的，这就是 `SafetyFinishReasonMiddleware` 要排在 `LoopDetection`/`TokenBudget` 之后（`agent.py:766-770`）、`ToolReceiptMiddleware` 成为最外层 `wrap_tool_call` 的原因（`tool_error_handling_middleware.py:418-425`）。
- middleware 全链（43 项，每个的 `file:line` 见 §6 附录 A）关键起点：`InputSanitizationMiddleware` → `KnowledgeScopeMiddleware` → `ToolOutputBudgetMiddleware` → `ToolResultSanitizationMiddleware` → `ThreadDataMiddleware` → `UploadsMiddleware` → `SandboxMiddleware` → … → `ClarificationMiddleware`（**必须最后**，`agent.py:776`）。

## 4. Q3 —— 流式

- **谁序列化、谁传输**：harness **序列化**（`runtime/serialization.py:134` `serialize()`；`:126` `messages`、`:112` `values`，剥掉 `__pregel_*` 与 base64 图片块）；app **传输**（`services.py:2304` `sse_consumer` → `services.py:176` `format_sse`）。bridge **从不检查载荷**。
- **帧类型**：`messages-tuple`（内部名 `messages`，载荷 `[message_dump, metadata]`，`serialization.py:126`）、`values`（每步完整状态快照 + `deerflow_seq` 戳，`worker.py:3103`）、`custom`（`StreamWriter`，内建事件经 `deerflow.utils.custom_events` 双发）；另有 `metadata`（worker 首先发布，`worker.py:1126`）、`updates`、`tasks`、`error`、`end`、以及无 id 的 `gap` 控制帧。
- **`values|<ns>` 的由来**（`worker.py:3080-3090`）：被委派的子智能体**继承父 checkpoint 命名空间**，若把它的 `values` 当裸 `values` 发布，会**整体替换 SDK 客户端的线程视图**（#4399）。LangGraph SDK 正是按 `event.split("|").slice(1)` 解析。根命名空间消费者（文件工具分块批处理、子智能体事件持久化、LLM 错误兜底检测）都要求 `not namespace`（`worker.py:1392-1398`）。
- **`StreamBridge` vs `RunJournal` 的分工**：bridge 只承载**易失**帧，容量受 `stream_bridge.queue_maxsize` 限制、进程死则丢；journal 是 LangChain `BaseCallbackHandler`（`journal.py:222`，挂在 `worker.py:1185`），把回调写成**持久、有序、可查询**的 `RunEvent` 行。**journal 独有**：`run.start`、`llm.human.input`、`llm.ai.response`、`llm.tool.result`、`llm.error`、`subagent.start/step/end`、`middleware:{tag}`、`workspace_changes`、`run.end`/`run.error`、**`run.delivery` 交付收据**（幂等 `put_if_absent`，**故意早于终态状态写**，`worker.py:1601`）、token 用量汇总（`journal.get_completion_data()`）、线程全局单调 `seq`。

## 5. Q4 —— 终止

所有路径共用同一个 `finally`（`worker.py:1551-1863`），**只有状态判定不同**：

| 路径 | 谁决定 | 关键位置 |
| --- | --- | --- |
| **成功** | delivery 检查通过 → `set_status_if_not_cancelled(success, stop_reason=…)` | `worker.py:1505-1522`；`stop_reason` 由守卫中间件盖（`loop_capped`/`token_capped`/`safety_capped`…） |
| **错误** | ①LLM 兜底（仅根命名空间）②delivery 不完整 ③未捕获异常（额外发 `error` 帧）④cancel-with-rollback | `worker.py:1474` / `:1516` / `:1529` / `:958` |
| **取消** | `RunManager.cancel` 决定：置 `abort_action`、`task.cancel()`、**状态 `interrupted`** | `manager.py:1374-1385`；worker 侧 `_finish_cancellation`（`worker.py:987`） |
| **取消+回滚** | `_finish_cancellation` 记 `error="Rolled back by user"`，再 `_rollback_to_pre_run_checkpoint` | `worker.py:958-964` → `:2506` |
| **中断（未启动）** | 启动屏障处 `try_start` 返回 `cancelled` → `_finish_cancellation(..., restore_checkpoint=False)` | `worker.py:1041-1048` |
| **超时** | **不存在生产者**（见 §5.1） | —— |

**full vs delta 的唯一判据**：`accessor.mode == "delta"`。
`_linearize_delta_checkpoint_resume` 在 `accessor.mode != "delta"` 时直接返回（`worker.py:2456`）；
`_rollback_to_pre_run_checkpoint` 用 `if accessor.mode == "delta":` 分叉（`worker.py:2553` delta 线性整状态 `Overwrite` / `:2570` full 分叉 + 只 `Overwrite` messages）。
**原因**：delta 分叉会重放被丢弃兄弟节点的 `pending_writes`（#4458），所以 delta **永不 fork**；full 的 checkpoint 带完整 `channel_values`，保留 LangGraph 原生分叉语义。
`accessor.mode` 来自启动期冻结的 `app.state.checkpoint_channel_mode`（`app/gateway/deps.py:451`、`:767`）。

**清理**：`close_agent_stream`（`runs/stream_cleanup.py:19`）在两个 `_stream_once` 的 `finally` 里调用（`worker.py:1356`、`:1412`）；shield 到完成、延迟宿主取消、把关闭取消映射为 `AgentStreamCloseCancelledError`、**永不超时**。`_release_run_scoped_references`（`worker.py:211`）从每个 runnable config 与 runtime context 里摘掉 journal、`__pregel_runtime`、会话读取器、扩展快照、task store，随后把大对象置 `None` 并触发 `_schedule_terminal_cycle_collection()`。

### 5.1 我另行验证的发现：`RunStatus.timeout` 是**孤儿状态**

- 定义：`runs/schemas.py:24`。**仅 3 处消费**，全是把它当终态集合成员：
  `app/gateway/services.py:135`、`app/mcp_tasks/service.py:902`、`runtime/runs/manager.py:850`。
- **零处生产**：`run_agent`、`RunManager`、各 router 都不写这个值（`channels/wechat.py:833` 的 `status="timeout"` 是扫码登录状态，与此无关）。
- 引入来源：`34e835bc`（#1403，Gateway 实现 LangGraph Platform API），为**对齐上游词表**而声明。
- 判断：**不是 bug，是词表冗余**——消费者把它当终态是安全的（永不发生）。这属于"可提但优先级低"的清理项；若将来要提，应连同"是否要真正实现 run 级超时"一起讨论，而不是单独删枚举值。

## 6. 附录 A：middleware 链（43 项，顺序即组合顺序）

基础链 `tool_error_handling_middleware.py:378-528`：
1 `InputSanitizationMiddleware`:379 · 2 `KnowledgeScopeMiddleware`:380 · 3 `ToolOutputBudgetMiddleware`:381 ·
4 `ToolResultSanitizationMiddleware`:382 · 5 `PiiRedactionMiddleware`:392(opt) · 6 `ThreadDataMiddleware`:396 ·
7 `UploadsMiddleware`:401(lead) · 8 `SandboxMiddleware`:403 · 9 `DanglingToolCallMiddleware`:415 ·
10 `LLMErrorHandlingMiddleware`:416 · 11 `ToolReceiptMiddleware`:430(opt) · 12 `ArtifactResolutionMiddleware`:437(opt) ·
13/14 `GuardrailMiddleware`:455/:486(opt) · 15 `SandboxAuditMiddleware`:490 · 16 `ReadBeforeWriteMiddleware`:502(opt) ·
17 `ToolProgressMiddleware`:512(opt) · 18 `ToolErrorHandlingMiddleware`:514 · 19 `ArtifactCaptureMiddleware`:526(opt)

lead 专属 `agent.py`：
20 `DynamicContextMiddleware`:569 · 21 `SkillActivationMiddleware`:583 · 22 `DeferredToolPromotionAuditMiddleware`:599(opt) ·
23 `SkillToolPolicyMiddleware`:605 · 24 `DurableContextMiddleware`:623 · 25 `SummarizationMiddleware`:646(opt) ·
26 `TodoMiddleware`:653(plan) · 27 `TokenUsageMiddleware`:657(opt) · 28 `TitleMiddleware`:660 ·
29 `MemoryMiddleware`:674/:684(opt) · 30 `ViewImageMiddleware`:696(vision) · 31 `McpRoutingMiddleware`:701(opt) ·
32 `DeferredToolFilterMiddleware`:710(opt，不变式断言在 :713) · 33 `SystemMessageCoalescingMiddleware`:720 ·
34 `SubagentLimitMiddleware`:733(opt) · 35 `LoopDetectionMiddleware`:738(opt) · 36 `TokenBudgetMiddleware`:745(opt) ·
37 caller `custom_middlewares`:749 · 38 `extensions.middlewares`:753 · 39 `TerminalResponseMiddleware`:758 ·
40 `ModelLengthFinishReasonMiddleware`:764 · 41 `SafetyFinishReasonMiddleware`:773(opt) ·
42 `ClarificationMiddleware`:776(**必须最后**) · 43 `compose_with_extensions`:787/:793

## 7. 附录 B：先读这 10 个文件

1. `runtime/runs/worker.py`（3230）— 整个 run 生命周期，从它开始
2. `app/gateway/services.py`（2487）— `start_run:1684`、信任边界 `:687-957`、`sse_consumer:2304`
3. `runtime/runs/manager.py`（2424）— 准入/幂等/持久唯一性/取消结果/租约/孤儿回收
4. `app/gateway/routers/thread_runs.py`（1873）— HTTP 面（create/stream/wait/cancel/join）
5. `agents/lead_agent/agent.py`（1398）— 装配与 `create_agent` 编译
6. `agents/middlewares/tool_error_handling_middleware.py`（842）— 基础链的权威顺序
7. `runtime/journal.py`（1386）— 持久化了什么 vs 流式发了什么
8. `runtime/stream_bridge/{base,memory,redis}.py`（115/192/384）— pub/sub 契约、`StreamGap`、心跳
9. `runtime/{stream_modes,serialization}.py`（47/148）— 模式名翻译表与线上序列化规则
10. `runtime/runs/schemas.py` + `runtime/events/catalog.py`（32/119）— 两个被到处引用的小词表

## 8. 附录 C：尚未证实的问题（子代理如实标注）

1. `store_only` + Redis 下 `RunManager.cancel` 的端到端时序（代码路径在 `manager.py:1221-1305`、`:2128-2240`，未执行）。验证入口：`backend/tests/test_multi_worker_run_ownership.py`。
2. `run.end` 载荷在 JSONL 与 DB 两种 store 下的一致性（未对比真实行）。读 `events/store/jsonl.py`、`db.py` 或 `backend/docs/RUN_EVENT_STREAM.md`。
3. 只请求 `updates`（不含 `values`）时，客户端排序如何保证——seq 戳只在请求了 `values` 时才构建（`worker.py:1324`）。看 `frontend/tests/unit/core/threads/` 的排序用例。
4. `error` 帧（`worker.py:1542`）在 Python `langgraph-sdk` 里映射到哪个回调（`onError`？）——已确认发布端，未确认解码端。
