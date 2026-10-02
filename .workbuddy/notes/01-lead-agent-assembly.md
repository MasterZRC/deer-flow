# 架构笔记 01 — Lead Agent 装配链路与 Middleware 链

> 归档日期：2026-10-01 ｜ 阶段一·第一轮精读  
> 精读范围：`backend/packages/harness/deerflow/agents/lead_agent/agent.py`（约 1400 行）、  
> `agents/middlewares/AGENTS.md`、`agents/thread_state.py`、`tools/tools.py`、  
> `agents/lead_agent/prompt.py`、`agents/middlewares/tool_error_handling_middleware.py`  
> 证据等级：**已抽查复核**（本人复核）／**转述自源码精读**（行号来自实际读取，未逐条复核）

---

## 0. 一句话调用链

`langgraph.json:lead_agent` → `make_lead_agent`（agent.py:832）→ `assemble_lead_agent`（:837，冻结 checkpoint 模式）→ `_assemble_lead_agent`（:952，授权／模型／工具／middleware／prompt 全流程）→ `create_agent`（:1357）→ `_complete_assembly`（:888，产出 `LeadAgentAssembly`）→ 消费方经 `unwrap_agent_graph`（:106）取 `.graph`。

---

## 1. 入口契约

**`make_lead_agent` 为什么必须"轻"**（agent.py:832-834，已复核）

```python
def make_lead_agent(config: RunnableConfig):
    """LangGraph graph factory; keep the signature compatible with LangGraph Server."""
    return assemble_lead_agent(config).graph
```

它是 LangGraph Server 的 ABI 入口：Server 只能以 `(config) -> CompiledGraph` 形式调用图工厂，签名多一个参数、或返回非 graph 对象都会破坏加载（docstring 明说，:833、:844-847）。`langgraph.json:8-10` 声明 `"lead_agent": "deerflow.agents:make_lead_agent"`。

**`LeadAgentAssembly` 三字段**（agent.py:92-103，已复核结构）

| 字段                | 含义                                             | 消费方                                                                                                                                       |
| ----------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `graph`           | 编译后的 LangGraph 图                               | `make_lead_agent`（:834）、Gateway `app/gateway/services.py:1167`、run worker `runtime/runs/worker.py:701` —— 统一经 `unwrap_agent_graph`（:106）取 |
| `descriptor`      | `AgentAssemblyDescriptor`（契约在 extension-api 包） | `_complete_assembly` → `notify_agent_assembled`（:948）；**无 observer 时为 `None`**                                                            |
| `effective_model` | 授权后的最终模型名                                      | `runtime/runs/worker.py:712-720`                                                                                                          |

设计细节：`descriptor` 的类型故意放宽为 `Any`（:96-99），避免 LangGraph Server 的启动导入链把 extension-api 契约包拉进来。

---

## 2. 装配流水线（`_assemble_lead_agent`，agent.py:952-1398）

按执行顺序（行号转述自精读）：

| #   | 步骤                                              | 关键点                                                                                 |
| --- | ----------------------------------------------- | ----------------------------------------------------------------------------------- |
| 0   | 惰性导入（:953-957）                                  | 避免循环依赖                                                                              |
| 1   | 合并运行时配置（:959）                                   | `_get_runtime_config`（:216-222）：`configurable` 与 `context` 合并，**后者覆盖前者**            |
| 2   | checkpoint 模式（:960-964）                         | 真正的冻结在 `assemble_lead_agent`（:853-874），fail-closed                                  |
| 3   | 解析权威 user_id（:966-971）                          | Agent Server 保留的 auth 字段优先于 client context                                          |
| 4   | 读取运行时开关（:973-986）                               | 模型/plan/subagent/bootstrap/interaction_policy                                       |
| 5   | 加载 custom AgentConfig（:988）                     | `is_bootstrap` 时**不加载**                                                             |
| 6   | 派生 memory/subagent 策略（:989-998）                 | `subagent_enabled` = 请求 ∧ `allowed_subagents != []`（空列表是硬拒绝）；并**回写 config**         |
| 7   | skill 白名单初值（:999）                               | `None`（无 agent 级白名单）与空集（无 skill 可激活）语义不同                                            |
| 8   | **skill 授权过滤 Layer 1**（:1001-1039）              | 被拒 skill 不进 `<skill_index>`、不能 describe、不能 slash 激活                                 |
| 9   | 模型解析与 reasoning 契约（:1040-1095）                  | 见下                                                                                  |
| 10  | 日志/元数据/tracing（:1085-1128）                      | tracing callbacks 挂在图调用根，故所有 in-graph `create_chat_model` 必须 `attach_tracing=False` |
| 11  | enabled skills + skill search setup（:1130-1137） | `deferred_discovery` 开关                                                             |
| 12A | bootstrap 分支（:1139-1261）                        | 见 §6                                                                                |
| 12B | 主分支（:1263-1398）                                 | 工具 → 授权 → 延迟装配 → middleware → prompt → `create_agent`                               |
| 13  | `_complete_assembly`（:888-949）                  | 无 observer 走快速路径，跳过 hash/探测开销                                                       |

**第 9 步的模型契约（重点）**

- thinking/reasoning 优先级：`request > custom agent default > runtime default`，用 `key in cfg` 区分"未提供"与"显式 false"（`_resolve_runtime_option`，:164-177）。
- 模型授权 `_authorize_model_name`（:240-332）：拒绝时回退到第一个"list 可见且 `authorize("model","use")` 通过"的模型——因为自定义 provider 可能允许 list 却拒绝 use；`fail_closed` 下直接抛错。
- **reasoning 契约归一化**（:1067-1083，语义在 `models/reasoning.py:67-187`）：`thinking` 取 `unsupported`（回退关）/`required`（强制开，`on_disable_request=="reject"` 时抛 `ReasoningPolicyError`）/`optional`；`effort` 分 strict 校验与透传两档。
- **vision** 不在这里决定，而是 `get_available_tools` 按 `supports_vision` 决定是否给 `view_image_tool`（tools.py:197-201）。

---

## 3. 工具组装

**`get_available_tools` 的合并源**（tools.py:104-336，转述）

1. config 声明的工具（:142-157，按 `groups` 过滤，可剔除 conversation reader / knowledge 组 / host bash）
2. builtin：`present_file` / `ask_clarification` / `review_skill_package`（:175-184），按运行时能力追加后台任务工具、`list_uploaded_files`、`skill_manage`
3. subagent：`subagent_enabled` 时 `task_tool`（:187-191），batch 可用时再加 `batch_task/batch_status/cancel_batch`
4. vision：`view_image_tool`（:197-201）
5. MCP（:227-293）：合并 ExtensionsConfig + 缓存工具 + 用户级工具，处理部署名冲突与 `mcp_plugins` 过滤，逐个 `tag_mcp_tool`
6. ACP 工具（:295-310）
7. plugin 工具（:317-324）

最后 `ordinary_tools + plugin_tools` 按 name 去重，**ordinary 优先**（:314-336）。细节：`write_file` 会按模型有效 max_tokens 克隆并追加 per-response budget 提示（:203-225）。

**延迟工具（deferred tools）机制**（`tools/builtins/tool_search.py`，转述）

解决的问题：MCP 目录可能很大，把每个 MCP 工具的完整 JSON schema 都绑给模型会持续烧 token，且默认不可见更安全。

- 模型只看到**工具名清单**（`<available-deferred-tools>`），需要时用 `tool_search` 拉取 schema，命中后以 `Command(update={"promoted": ...})` 把工具"晋升"为可调用（:142-172）。
- **fail-closed**：`enabled` 且有 MCP 候选却恢复不出 deferred 集合 → 抛 `RuntimeError`，绝不静默全量绑定（:213-214）。
- `DeferredToolFilterMiddleware` 在模型调用前隐藏未晋升的 schema；`promoted` 按 `catalog_hash` 分域，防 catalog 漂移后用旧名暴露不同工具（thread_state.py:145-163）。
- 不变量：`tool_search_tool is None ⟺ deferred_names 空 ⟺ catalog_hash is None`（:120-139）。

---

## 4. Middleware 链（工程精华，务必吃透）

装配分两段：**共享基座**（`tool_error_handling_middleware.py::build_lead_runtime_middlewares` → `_build_runtime_middlewares`）+ **lead-only 追加**（`agent.py::build_middlewares`，:481-807）。列表首元素 = 最外层。

### 4.1 共享基座（subagent 复用大部分）

**A. Layer-1 wrap_model_call（安全门）**

1. `InputSanitizationMiddleware` — 最外层，保证所有内层（含 LLM 重试）看到已净化消息
2. `KnowledgeScopeMiddleware` — 只暴露 Gateway 准入的执行范围
3. `ToolOutputBudgetMiddleware` — 超大工具输出外置到 `.tool-results`，留 synopsis + `read_file` 引用
4. `ToolResultSanitizationMiddleware` — 中和**远端内容**工具结果里的注入标签（防抓取页面伪造框架上下文）；本地工具输出不动
5. `PiiRedactionMiddleware`（可选，默认关）

**B. Thread / 沙箱钩子**  
6\. `ThreadDataMiddleware` — 建 per-thread 目录树  
7\. `UploadsMiddleware` — 注入上传（**lead only**）  
8\. `SandboxMiddleware` — 获取沙箱，存 `sandbox_id`

**C. tail（工具执行包裹 / 审计 / 终止保护）**  
9\. `DanglingToolCallMiddleware` — 给缺失响应的 tool_calls 补占位 ToolMessage  
10\. `LLMErrorHandlingMiddleware` — provider 失败转可恢复错误（circuit-generation ownership）  
11\. `ToolReceiptMiddleware`（可选，默认开）— **最外层 wrap_tool_call**  
12\. `ArtifactResolutionMiddleware`（可选）  
13\. `GuardrailMiddleware(AuthorizationAdapter)`（可选，复用 Layer-1 provider）  
14\. `GuardrailMiddleware(显式 provider)`（可选）  
15\. `SandboxAuditMiddleware`  
16\. `ReadBeforeWriteMiddleware`（可选，默认开）  
17\. `ToolProgressMiddleware`（可选）  
18\. `ToolErrorHandlingMiddleware`  
19\. `ArtifactCaptureMiddleware`（可选）

### 4.2 lead-only 追加（agent.py:481-807）

1. `DynamicContextMiddleware`（日期/记忆注入）→ 21. `SkillActivationMiddleware` → 22. `DeferredToolPromotionAuditMiddleware` → 23. `SkillToolPolicyMiddleware` → 24. `DurableContextMiddleware` → 25. `SummarizationMiddleware`（可选）→ 26. `TodoMiddleware`（plan mode）→ 27. `TokenUsageMiddleware` → 28. `TitleMiddleware` → 29. `MemoryMiddleware` → 30. `ViewImageMiddleware`（vision）→ 31. `McpRoutingMiddleware` → 32. `DeferredToolFilterMiddleware` → 33. `SystemMessageCoalescingMiddleware` → 34. `SubagentLimitMiddleware` → 35. `LoopDetectionMiddleware` → 36. `TokenBudgetMiddleware` → 37. custom → 38. 配置的扩展 → 39. `TerminalResponseMiddleware` → 40. `ModelLengthFinishReasonMiddleware` → 41. `SafetyFinishReasonMiddleware` → 42. `ClarificationMiddleware`（**恒为最后**）→ 43. `compose_with_extensions`

### 4.3 顺序约束最硬的三个（面试必问点）

- **Clarification 必须最后**（agent.py:775-776）：它拦截 `ask_clarification` 并以 `Command(goto=END)` 中断图，且 `after_model` 丢弃同回合 sibling tool calls（防止用户回答前先执行别的工具）。扩展锚点 `TOOL_RAW` / `MODEL_PHYSICAL` 都用 `outer_of_last(ClarificationMiddleware)`（stack.py:47-71）。
- **McpRouting 必须在 DeferredToolFilter 之前**（agent.py:698-713）：路由先晋升，filter 再据此隐藏未晋升者。源码有显式断言 `assert_mcp_routing_before_deferred_filter`（:711-713）。
- **ToolProgress 必须在 ToolErrorHandling 之外**：ToolProgress 的 wrap_tool_call 依赖 ToolErrorHandling 先盖上 `deerflow_tool_meta` 再读取。同理 **ToolReceipt 必须是最外层 wrap_tool_call**（:418-425）：Guardrail / SandboxAudit / ReadBeforeWrite / ToolProgress 都可能用自己的 ToolMessage 短路调用，receipt 放内侧会**静默产生台账缺口**。

---

## 5. ThreadState（thread_state.py:352-369）

在 `AgentState` 基础上新增：`sandbox`、`thread_data`、`title`、`artifacts`、`todos`、`goal`、`uploaded_files`、`viewed_images`、`promoted`、`delegations`、`skill_context`、`tool_artifacts`、`tool_artifact_processed`、`task_notes`、`task_history`、`summary_text`、`background_tasks`。

关键 reducer 语义：

- `merge_artifacts`（:93-100）：`existing + new` 后去重保序。
- `merge_delegations`（:192-226）：按 `(run_id, id)` 追加/替换保序；**终态 status 不被非终态覆盖**；legacy 无 run_id 回退到最近同名条目；上限 50 条保留尾部。
- `merge_skill_context`（:252-283）：按 `path` 去重、后读刷新 recency；**只存 name/path/description（截断 500 字符），绝不存正文**；上限 8 条。
- `merge_promoted`（:145-163）：按 `catalog_hash` 分域。
- `merge_tool_artifacts`（:313-349）：支持 `trim_to` 滑窗，上限 1000。
- `get_thread_state_schema(mode)`（:492-495）：`mode != "delta"` 返回 `ThreadState`，否则 delta schema。

---

## 6. Bootstrap 分支（agent.py:1139-1261）

用途：自定义 agent **首次创建**的引导流程，此时 agent 尚不存在，需要确定性。

差异：不加载 custom agent（`agent_config=None`）；skill 集极窄（`_BOOTSTRAP_SKILL_NAMES = {"bootstrap"}`，:81）；工具集注入 `setup_agent` 而非 `update_agent`；`owns_agent_skill_projection=False`（不成为线程 skill 投影 owner）；模型构造**不传** `reasoning_effort` / `model_overrides`（:1150 vs 主分支 :1291）；描述符硬编码 `reasoning_effort=None`（:1238）。

---

## 7. 运行时开关的影响面

| 开关                         | 影响                                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| `thinking_enabled`         | 经 reasoning 契约归一化后传给 `create_chat_model`；不直接增删 middleware                                             |
| `is_plan_mode`             | 决定是否追加 `TodoMiddleware`；进 metadata 与 effective_policies                                               |
| `subagent_enabled`         | 被 `allowed_subagents != []` 收紧后回写 config；影响 `task_tool`、`SubagentLimitMiddleware`、prompt 的 subagent 段 |
| `max_concurrent_subagents` | 经 `effective_subagent_concurrency`（含 startup `max_running` 与 1-64 范围）传给 `SubagentLimitMiddleware`     |
| `max_total_subagents`      | 经 `effective_total_subagents_per_run`（默认 6，1-50）传入；上限按**当前 run** 记账，防同一 run 反复规划无限委派                  |

---

## 8. Prompt 组装（prompt.py:1030-1165）

注入项：thinking/clarification 策略段、agent_name、`<soul>`、self-update 段（仅自定义 agent）、skills 段（deferred 走 `<skill_index>`）、deferred tools 段、mcp routing hints、subagent 段、memory tool 段、subagent/skill 提醒、acp 段、workspace scripts 指引，最后叠加 `lead_prompt_overlay`。

**关键设计**：memory 与当前日期**不**进 system prompt，而是每轮由 `DynamicContextMiddleware` 以 system-reminder 形式注入首条 HumanMessage —— 让 system prompt 保持静态以**复用 prefix cache**（prompt.py:1138-1141）。

---

## 9. 扩展点


`compose_with_extensions`（extensions/stack.py:134-169）在 `build_middlewares` **最末尾**调用（agent.py:778-807），按 `Placement` 锚点把扩展 middleware 注入到已装配完的栈，随后统一 `assert_ordering` 复校验。

为什么必须在最外层 builder 末尾：栈分两段构建，`MODEL_PHYSICAL` 落在 lead-only 段；若在基座内部注入，会让观察点落在约 18 个 lead-specific middleware 之上，改变"最终请求"的语义（agent.py:778-781、stack.py:1-11）。

---

## 10. 文档与源码不一致（已发现，复核确认 1 处）

1. **【已复核】AGENTS.md 的 middleware 编号与源码追加顺序不符**：`middlewares/AGENTS.md:69-81` 把 `ArtifactResolution`(10) / `Authorization`(11) / `SandboxAudit`(12) / `ReadBeforeWrite`(13) / `ToolProgress`(14) 排在 `ToolReceipt`(15) 之前；但源码中 `ToolReceiptMiddleware` 在 **:430** 追加，早于 `ArtifactResolutionMiddleware`（**:437**）与 `GuardrailMiddleware`（**:454**）。文档正文其实自己承认 receipts 是最外层 wrap_tool_call（:81），与其编号自相矛盾。
2. `middlewares/AGENTS.md:88` 说 `_authorize_model_name` "called from `_make_lead_agent`"，当前实际调用点是 `_assemble_lead_agent`（agent.py:1061）——表述滞后。
3. `agent.py:226` docstring 说无模型配置时返回 None，实际是 `raise ValueError`（:229-230），类型标注也是 `str`。
4. `agent.py:474` 注释称 Summarization "early"，实际在 DynamicContext/SkillActivation/SkillToolPolicy/DurableContext 之后追加（:645）。

> 这几条是很好的"贡献切入点"备选（文档修正类 PR），但按我们的策略，**不以文档 typo 类 PR 作为首个贡献**，价值有限。

---

## 11. 设计亮点与潜在坑

**亮点**

- prefix-cache 友好：system prompt 静态化，动态内容逐轮注入。
- 授权分层：Layer 1 装配期过滤（skill/model）＋ Layer 2 执行期 GuardrailMiddleware 复用同一 provider —— 身份与执行分离，"Gateway 剥离客户端身份覆盖，只有服务端 auth 源能设 `is_internal`"。
- 延迟工具 fail-closed；checkpoint 模式冻结 fail-closed。
- tracing invariant 在模块头集中声明（agent.py:1-23）。

**坑**

- `descriptor` 可为 `None`，消费方不判空会 NPE。
- bootstrap 与主分支的模型构造不对称（不传 reasoning_effort）。
- `config` 被**原地 mutate**（`:996-998` 回写 subagent_enabled、`:1101-1115` 写 metadata、`:1128` 写 callbacks）——对共享 config 对象有副作用。
- `available_skills` 的 **None vs 空集**语义不可互换。
- skill 授权与 runtime 激活是两层：装配期只管可见性，激活期由 `SkillActivationMiddleware` / `SkillToolPolicyMiddleware` 再校验。
- `_ensure_sync_invocable_tool` 原地修改进程级单例（tools.py:60-73），是共享可变状态——并发点。
- webhook 渠道门控按 `_WEBHOOK_CHANNELS = {"github"}` 硬编码（agent.py:89），新增渠道需同步。

---

## 12. 待下钻（下一轮）

1. `create_agent` 的 middleware 组装语义：`normalize_middleware_state_schemas` 与 state schema 合并规则。
2. `DeerFlowClient` 复用路径与 Gateway 路径的差异（`_ensure_agent`）。
3. `build_assembly_descriptor` 的指纹算法与 observer 机制。
4. runtime 层：`RunManager` 准入 + `stream_bridge` SSE 契约。
5. subagents：隔离事件循环、checkpoint 命名空间隔离、双身份。
