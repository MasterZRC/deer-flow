# 选题侦察：候选池与"如何真正拿到贡献位"（阶段 2 弹药）

> 数据：`issue_survey.py`（同目录，只读公共 API）2026-10-01 快照；原始 JSON 在 `.scratch/issue-survey.json`。
> **本文档在 2026-10-01 做过一次事实更正**，更正记录见 §5。

## 1. 先接受的事实（决定了整个策略）

| 指标 | 数值 |
| --- | --- |
| 近 45 天新开 issue | 69 |
| 其中已被 open PR 认领 | **45（65%）** |
| 真正未被认领 | 24（其中 11 个是 RFC） |
| 近 45 天 open PR | **104** |

**关键更正案例**：issue **#6050**（Checkpoint retention 有实现但从未被触发）在我们第一版快照里
显示"未认领"，实际查证后发现：**issue 与 PR #6051 的创建时间戳是同一秒（2026-09-29T13:23:1x）**，
PR 正文完整包含 root cause、5 段执行顺序、安全边界、测试矩阵、reviewer focus 5 问。
这不是巧合，而是这个仓库的常态：**作者在贴 issue 的同时就把 PR 推上去了。**

**结论（必须内化）**：
1. **不要指望"捡一个没人做的官方 issue"**——窗口是分钟级，甚至是同一秒。
2. 官方 issue 的正确用法是 **①验证它的判断是否成立；②作为学习路线图**，
   而不是"任务清单"。把 issue 当"作业本"的人，永远在别人后面交卷。
3. 真正的入场券是 **信息优势 + 更硬的证据**。维护者自己的流程
   （`.agent/skills/deerflow-maintainer-orchestrator/SKILL.md`）里专门有
   **"Competing PR Comparison"** 一节：他们**经常要比较同一个 issue 的多个 PR**，
   评判维度就是"是否真正解决 ask / 正确性与边界覆盖 / 测试质量 / 影响面与兼容性 / 可维护性"。
   我们的目标应该是**成为那个"更对"的一方**，或在已开的 PR 上贡献**被采纳的深度评审**。

## 2. 候选池（**已由对抗性验证修正，2026-10-01 第二轮**）

> ⚠️ 本节第一版的两条判断**都被证伪**。保留原文会误导后续决策，故直接改写为验证后的版本。
> 验证方法：GitHub API 查 timeline / 同日 PR / **`git merge-base --is-ancestor` 判断修复是否已在本地 HEAD**。

| # | 标题 | 验证后判读 |
| --- | --- | --- |
| **6119** | MCP task cancellation misses older targets and accepts ambiguous names | **NO-GO（维护者不认为该修，见 §2.1）**。缺陷在 HEAD 上真实存在：`app/mcp_tasks/service.py:731-744` 的 `cancel_matching_task()` 调用 `list_tasks(..., active_only=True)` 用**默认 `limit=50`**（`service.py:703`），只在**这一页**里匹配（`:745-747`）；`persistence/mcp_tasks/sql.py:291` 按 `created_at DESC` + `.limit(limit)`。**但维护者已明确表示 50 条上限是合理设计。** |
| ~~5953~~ | Parallel task_note calls can silently evict existing notes after reporting success | **NO-GO（已修复）**。PR **#5954**（作者 ZJPex）在 issue 提交后 **24 秒**创建、**已于 2026-09-30 合并**（merge commit `8e282c4c`）；`git merge-base --is-ancestor 8e282c4c HEAD` → 0，**修复已在本地 HEAD 里**，且新增了 `backend/tests/test_task_note_capacity.py`（366 行）。**issue 本身仍是 OPEN 且 0 评论**——只看 issue 页面会误判为"空闲"。 |
| 5552 | Codex CLI credential loader raises AttributeError when credentials file is not JSON | 未验证；面窄但边界清晰。 |
| 6037 | Propose shadow-measuring duplicate paid web calls across parallel subagents | 不是 bug，是要先做**测量实验**再谈优化；对方带自己的开源项目，有利益关联。谨慎。 |
| 5378 | 上下文管理与任务连续性：现状与实测（中文报告） | 报告/讨论类，不是待修 bug；**当读物而非任务**。 |

### 2.1 #6119 的真实风险：**维护者不认为该修**（比"有人做过"严重得多）

PR **#6120**「fix(mcp): resolve cancellation targets independently of task list limits」
（issue 后 **79 秒**创建）状态 **closed / merged=false**，`size/L` + `risk:medium`。

**我拉到了关闭原因（这是关键证据，非推测）**：一位 COLLABORATOR 的留言只有一句 ——

> *"Thanks for your contribution, as current 50 task list is reasonable, we don't need to change it."*

而**评审反馈其实是被认真处理过的**：
- 一位贡献者指出 `find_active_matches()` 已把结果限制为 2 行，`matches[:5]` 是过期边界，且错误文案说"specify a task ID"却列出 **name**，可能诱导模型把 name 当 ID 回传；
- 作者回复已修（commit `98f1c8b7`），并报告 Fork CI 全绿（四个后端分片 + blocking-IO + 前端 + Replay E2E 全部通过）。

**也就是说：作者照着评审改完了、CI 全绿了，PR 仍然被关。** 理由不是技术缺陷，而是
**维护者认为「50 条任务列表的容量」是合理设计，不需要改**。

**这推翻了我上一版写在这节里的结论。** 真实教训是三条，一条比一条重要：

1. **"未被认领 + 缺陷真实"是必要条件，不是充分条件。** 第三个必须验证的维度是
   **维护者是否认为它值得修**（`wanted?`）。
2. **改动"被有意设计的行为"会被拒。** #6119 的表现（取消不到前 50 之外的任务）在维护者眼里
   是**刻意的容量边界**。我们可以论证它有害，但那需要**用户影响证据**，而不是代码推理。
3. **CI 全绿 ≠ 会被合并。** 作者把评审意见全部改完、CI 全过，依然被关。
   **决定权在"这个改动该不该存在"的判断上，那一步发生在写代码之前。**

> **#6119 降级为 NO-GO（除非出现新的用户影响证据）。**
> 我们的阶段 2 因此需要重新选靶——这次要把「维护者意愿」作为**第一优先级过滤器**，
> 而不是等写完代码才发现方向错了。

## 2.2 「维护者想要」信号扫描的结果（`wanted_survey.py`，2026-10-01）

**方法**：`/collaborators` 需要认证（401），所以改用**从数据推断维护者集合** —— 谁在合并 PR。
结果毫不含糊：**`WillemJiang` 权重 75，其余人 0**（他是唯一的实际合并者）。
另有一位以 review 身份出现的关键人 `willem-bd`（见 §2.1 的评审意见）。

然后扫描近 60 天 open issue 的评论，只保留 `COLLABORATOR`/`MEMBER`/`OWNER` 或推断出的维护者，
并用"肯定语"正则（`pr welcome` / `please submit a PR` / `confirmed` / `we should fix` …）
与"否定语"正则（`we don't need` / `by design` / `out of scope` / `not a bug` …）分类。

**结果：78 个 open issue 里，只有 3 个带"想要"信号，而且全都是 RFC：**

| # | 标题 | 为什么不能做 |
| --- | --- | --- |
| 5510 | RFC: Frontend Dynamic Plugin System | **RFC**；维护者的 agent 流程对 RFC 是硬跳过（不评论、不当任务）；且已有实现型 PR #5645 |
| 5398 | [RFC] Cross-session conversation references and retrieval | **RFC**；作者自己说"三点已在 #5421 处理" |
| 5391 | RFC: 内置本地知识库（Harness RAG） | **RFC** |

**并且："维护者说过 NO"的列表在本次扫描中是空的** —— 因为我们先前的 NO（#6119）来自**已关闭 PR** 的评论，
而不在 issue 评论里。**这说明"看 issue 评论"会漏掉最关键的一类负面信号，必须同时查已关闭的同主题 PR。**

> **结论（重要）**：在这个仓库里，**"维护者公开表示想要、且没人做"的 issue 基本不存在**。
> 不是我们没找对关键字，是这类机会被"issue 后数十秒内自提 PR"的模式系统性吃掉了。
> **阶段 2 的可行路径必须换一种，见 §4。**

## 3. 已被占领、不要重复投入的方向

- **配置字段校验类**（bool/负数/`.inf` 被静默强转）：#6016→PR6017、#6033→PR6035、
  #5865→PR5867、#6144→PR6145、#6146→PR6147…… 已成"PR 工厂"流水线，
  且 #6033 正文点名"该字段不在 #6025 的十个字段列表里"——说明有人在系统性扫这类问题。
  **跟进只剩边角料，且极易撞车。**
- **Windows/POSIX 兼容类**：#5922 / #5932 → 都由 PR#6079 统一处理；#5904→PR5905；
  #6141→PR6142（同一秒）。这个方向曾经是好机会，现在也满了。

## 4. 路线（**经三轮证伪后重写**）

三轮侦察的净结果：**"找 issue → 写 PR"这条路的期望收益接近零。** 数据是：

| 事实 | 数字 |
| --- | --- |
| 近 45 天新 issue | 69 |
| 已被 PR 认领 | 45（65%） |
| 同期 open PR | **104** |
| 维护者公开"想要且没人做"的 issue | **≈0**（§2.2） |
| 唯一实际合并者 | `WillemJiang`（权重 75，其余全 0） |

**瓶颈在评审侧，不在发现侧。** 于是路线改为：

1. **阶段 A 继续**（不变）。无论走哪条路，checkpoint / journal / lifecycle 都是硬通货。
2. **主力：对已开的高风险 PR 做深度评审，并持续做。** 这是这个仓库**唯一可以重复的**贡献动作：
   - 供给无限（104 个 open PR，还在涨）；
   - 需求真实（一个合并者 review 不过来）；
   - **门槛是理解深度，而理解深度正是我们在积累的东西**；
   - 维护者自己的流程给了明确口径：公开只发"**高置信 且 ≥P2 且是本 diff 引入或加重**"的问题。
   - 首个靶子：**PR #6051**（checkpoint retention，`risk:high` + `needs-validation` + `size/L`，9 条评审），
     它正好在阶段 A 的学习范围内。
3. **机会型：只在"信息优势"出现时提 PR** —— 即发现 issue 没写、PR 也没解决的真问题。
   依然要求：复现命令 + 红转绿测试 + **事先确认维护者想要**。
4. **一手痛点优先**：如果人类自己在使用 DeerFlow 时撞到问题，那条路径天然满足 `wanted?`
   （因为用户影响证据是你亲身拿到的），**优先级高于任何"扫列表"的结果**。

> 一句话：**在这个仓库，"能读懂别人 PR 的问题"比"能自己写 PR"更稀缺，也更值钱。**

### 4.1 评审靶子已锁定：PR #6051（预审已开始）

diff 已落到本地：`.scratch/pr6051.diff`（10 文件，+443 / −61）。
**第一个发现：PR 描述与实现已经不一致** ——

| | 说的 | 做的 |
| --- | --- | --- |
| 触发时机 | PR 正文写"run 完成之后、**finalizing 屏障释放前**"跑 retention | `checkpoint_retention.py` 的新 docstring 写"**下次 run 赢得同线程持久准入之后、该 worker 读取 checkpoint 之前**"；`deps.py::_run_admission_hook` 是 **admission hook**，不是 completion hook |

即作者把方案从"完成后剪"改成了"**下次准入时剪**"（理由是保住 history 快路径缓存叶）。
**这属于"描述未同步"的评审发现（P2 级，低风险但真实）。**

**下一步深审必须回答的安全问题**（已定位到证据文件）：
1. **安全谓词的可信度**：`app/gateway/checkpoint_lineage.py:43` 的 `is_duration_only_checkpoint`
   仅判断 `metadata["writes"]` 是否含 `runtime_run_duration` 键。要确认 duration checkpoint
   **确实不写任何 channel**，否则删除即丢状态。
2. **保护集合是否完整**：`deps.py::_selected_checkpoint_ids` 只保护**客户端显式选择**的 checkpoint。
   若本次 run 隐式从"当前 head"恢复，而该 head 恰是 duration-only 叶，是否会被误删？
   （契约声称"duration-only 叶不携带状态变化"，若成立则安全——但必须自己验证，不能信注释。）
3. **`_ensure_supported_saver` 的收紧**：原来用 `isinstance(..., AsyncPostgresSaver)` 白名单，
   改成 `callable(getattr(storage, "_cursor", None))` 鸭子类型探测。**私有属性探测取代类型白名单**
   是否是可接受的契约？这是我认为最值得问维护者的一点。

#### 4.1.1 已核实：钩子的真实插入点（描述不符已确认，升级为可提交的发现）

用 `worker.py` 现有代码对照 diff 的 hunk 头 `@@ -1048,6 +1051,12 @@` 反推：插入点正是
`start_outcome = await run_manager.try_start(run_id)`（`worker.py:1041`）成功之后的 `started = True`
（`worker.py:1049`）与 `task_id = lead_task_id(run_id)`（`worker.py:1051`）之间 —— 即
**pending→running 之后、扩张任务通知 / 线程状态 / checkpoint 模式门 / agent 装配之前**。

| | 位置 | 与 `await run_manager.wait_for_prior_finalizing(...)`（`:1035`）的关系 |
| --- | --- | --- |
| **PR 正文说** | "after duration persistence and **before clearing the finalizing barrier**" | —— |
| **代码实际** | try_start 成功之后立刻（`:1049` 与 `:1051` 之间） | **在等前一个 run 完成 finalizing 之后**，与"清除自己的 finalizing 屏障"无关 |

**所以"描述不符"成立且可被 review 验证**：正文把钩子描述成"完成路径上、清除 finalizing 之前"，
代码是"**准入路径上、agent 还没构造时**"。二者对并发语义的含义不同。

**顺带核实的两点（都对，值得在评审里确认而非质疑）**：
- `except Exception` **不吞** `asyncio.CancelledError`（它是 `BaseException` 子类），
  所以准入期被取消时取消仍会传播——这是**正确**的写法。
- 但该钩子**无超时**，它内部做的是 checkpoint 列表 + 分类 + 删除。若存储变慢/挂起，
  **run 会在"已置 running、尚未开始"的窗口里卡住**。风险等级取决于存储超时配置，属 P2 级观察。

## 5. 更正记录（保持可追溯）

- 2026-10-01 第一版把 **#6050 列为"首选候选（未认领）"**，依据是 survey 的 PR 文本匹配。
  经查 `GET /repos/bytedance/deer-flow/pulls/6051`：PR #6051 标题
  `fix(checkpoints): run conservative retention after completion`，**state=open，`Closes #6050`**，
  443 增加 / 61 删除 / 10 文件，`risk:high`、`needs-validation`、`size/L`，9 条评审评论、0 issue 评论。
  → **#6050 不可做。** 教训已写入 §1。

## 6. 复现与更新方式

```powershell
$env:PYTHONIOENCODING='utf-8'
python docs/contributor/.scratch/issue_survey.py --days 45      # 刷新候选池
```

> 注意：该脚本的"是否被认领"用的是**PR 正文里的 `#nnnn` 文本匹配**，
> 会**漏掉同秒提交、正文未引用 issue 号的情况**。看到"未认领"时必须再查一次
> `GET /repos/bytedance/deer-flow/issues/<n>/timeline` 与相邻 PR 号，别重蹈 §5 的错。
