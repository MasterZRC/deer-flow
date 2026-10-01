# 贡献者作战手册（人机共同记忆）

> 本文件是 **agent 与人类贡献者的共享记忆与工作契约**。每次会话开始时先读它；
> 每次形成新的结论、踩坑、决策或进度，都在此更新。它不替代 `AGENTS.md`（代码规范）
> 和 `CONTRIBUTING.md`（流程），而是记录"我们两人的位置、目标、计划与已有认知"。

---

## 1. 双方定位（Who we are）

| 角色 | 定位 | 职责 |
| --- | --- | --- |
| **人类（你）** | deer-flow 的**准贡献者 / 决策者 / 最终署名者** | 定方向、拍板、review 每一行改动、对 PR 内容负责、与维护者沟通 |
| **Agent（我）** | **结对研究员 + 实现工程师 + 复核者** | 读码与考古、拆解 issue、复现与定位、写补丁与测试、跑验证、整理 PR 证据 |
| **共同目标** | **成为 agent 领域专家，并把能力沉淀为被合并的 PR** | 认识 → 细节 → 技术深挖 → 上游认可 |

上游仓库：`bytedance/deer-flow`。本地 `origin` = `MasterZRC/deer-flow`（个人 fork，待确认）。

**最终目标（North Star）**：在 `bytedance/deer-flow` 上有**被合并的 PR**，成为 Contributors 之一，
并且对"super-agent harness"的架构有可对外表达、可被追问的深度理解。

## 2. 达成路径（三阶段，每阶段有硬门槛）

### 阶段 0/1 — 项目地形（Repomap）：完成度 ███░░░░░░░
- 目标：能脱离文档口述「一次 run 从 HTTP 到 SSE 的完整链路」「harness/app 边界为什么重要」
  「状态、沙箱、子智能体、记忆分别由谁拥有」。
- 手段：`docs/ARCHITECTURE.md` → `backend/AGENTS.md` → 模块级 `AGENTS.md`（每个包都有一份）
  → 真实读代码。**注意：本仓库的 `AGENTS.md` 是"每层都有"的分层文档体系，这是最高杠杆的入口。**
- 硬门槛：能独立画出 run 生命周期 + middleware 链，并指出每条链路上的契约面。

### 阶段 2 — 单点纵深（Issue → Root cause）：完成度 ░░░░░░░░░░
- 目标：锁定 **1 个** 官方 issue，产出：可复现的最小用例、精确到 file:line 的根因、
  与维护者习惯一致的修复方案（含 blast radius 与兼容性判断）。
- 硬门槛：**测试先红后绿**（本仓库 TDD 是强制的：根目录 `CONTRIBUTING.md`、`backend/AGENTS.md`），
  且能说清"为什么这样修，而不是那样修"。

### 阶段 3 — PR 与上游对话：完成度 ░░░░░░░░░░
- 目标：1 个 PR 通过 CI、通过 review、被合并。
- 硬门槛：PR 模板每一项都如实填写（含 **AI assistance 披露**，本仓库明确欢迎 AI 参与但要求
  人类读完并负责），验证命令与输出真实可复现，不夹带无关改动。

## 3. 工作契约（Working agreement）

1. **一切以代码与可复现命令为准**：任何结论都要能落到 file:line 或一条可跑的命令输出。
   文档与代码冲突时，**代码是真相**，并把冲突记录到本文件。
2. **TDD 优先**：先写/找到失败的测试，再改实现；提交前跑对应模块的 lint/format/test。
3. **小步、可回滚**：一个 PR 只做一件事；不顺手重构无关代码。
4. **人类负责制**：AI 可以写代码，但**每一行都要人类读懂**才提交。做不到就不提交。
5. **验证矩阵**（沿用维护者自己的标准，见 `.agent/skills/deerflow-maintainer-orchestrator/SKILL.md`）：

   | 改动面 | 验证命令 |
   | --- | --- |
   | backend / harness / agents / MCP / skills | `cd backend && make lint && make test` |
   | 阻塞 IO、async 文件/网络 | `cd backend && make test-blocking-io` |
   | harness ↔ app 边界 | `cd backend && uv run pytest tests/test_harness_boundary.py` |
   | frontend UI/core | `cd frontend && pnpm format && pnpm lint && pnpm typecheck && BETTER_AUTH_SECRET=local-dev-secret pnpm build && make test` |
   | 前后端 thread/SSE 契约 | backend replay golden + full-stack replay |
   | 用户可见流程 | Playwright E2E 或带截图/DOM 断言的浏览器证据 |

6. **本文件持续更新**：每完成一个阶段或改变方向，更新第 2 节完成度与第 6 节日志。

## 4. 上游的"隐规则"（读维护者自己的 agent 技能得到，价值极高）

仓库里 `.agent/skills/` 是**维护者/内部 Agent 的工作手册**（已 tracked），等于公开的评审口径：

- `deerflow-maintainer-orchestrator`：issue 分类（`ready-to-fix` / `needs-more-evidence` /
  `defer-or-close` / RFC 不评论）、**PR 发现的分级 P0/P1/P2**、放行门槛
  （"高置信 且 ≥P2，且必须是本 diff 引入或加重的问题"）、`Missing info` 与 `Risk` 的写法。
- `engineer-system-change`、`smoke-test`、`blocking-io-guard`：内部改代码/冒烟/阻塞 IO 规范。

**对我们的直接含义**：
- 提 issue/PR 时用**证据说话**：复现命令、红/绿测试、受影响文件与行号、兼容性影响。
- 平台类修复（Windows/POSIX 差异）在本仓库是**被认可的正经贡献方向**（有历史先例与测试约定）。
- 不要提交"高置信但低价值"的 P2 式改动；也不要漏掉测试。

## 5. 已验证的环境事实（2026-10-01）

- 分支 `dsh`，HEAD = `4d560722`，与本地 `main` / `origin/main` 同一提交 → **当前 = 上游 main 的位点**
  （fork 未做任何领先提交）。仓库 3683 个提交，历史跨度 2025-04 → 2026-10。
- 工作树**已清空**：此前 18 个已跟踪文件（`frontend/*.js` 配置、`.ico`、demo 脚本等）在工作树中缺失
  （疑似被外部清理工具删除），已用 `git restore -- .` 恢复。
- **不可用工具：`gh` CLI 不在 PATH**（已下载到 `.tools/gh/gh.exe`，v2.83.2，**未登录**）；本机沙箱禁止
  msys/ssh 建信号管道 → `git ls-remote` 走 SSH 失败；Windows 原生 TLS（`curl.exe`/`Invoke-WebRequest`）
  因取不到凭证而失败 → **所有下载必须走 Python `urllib`**。详见 [env-windows.md](env-windows.md)。
- **远程已配置**：`origin` = 个人 fork（`MasterZRC/deer-flow`，SSH 改写为 ssh.github.com:443）；
  `upstream` = `https://github.com/bytedance/deer-flow.git`（已 fetch，`upstream/main` = `5b83cb50`，
  比本地 HEAD 新 —— 选题时以 `upstream/main` 为准）。
- **工作分支**：`contrib/agent-runtime`（从 `main` 切出），当前 = 本地产物（docs/contributor 等）都在此分支。
- **验证基线已跑通**：`$env:UV_CACHE_DIR="$PWD\.uv-cache"; cd backend; uv run pytest tests/test_harness_boundary.py -q` → **1 passed**。
- 本机工具链：`uv` ✅、`node` ✅（nvm4w）、`python` = Anaconda ✅、`pnpm` 未在 PATH（用 `scripts/pnpm.py` 包装）。

## 6. 地图可信度（抽检记录）

**结论：`answers-01-run-lifecycle.md` 的行号与断言可信，可直接作为参考。**
2026-10-01 由主 agent 亲自抽检三条"最关键且最不可能碰巧对"的断言，**三中三**：

| 抽检项 | 断言 | 实测 |
| --- | --- | --- |
| `values\|<ns>` 命名空间规则 | 根帧保持裸名，子图帧变 `mode\|ns1\|ns2`，SDK 按 `split("\|").slice(1)` 解析 | ✅ `worker.py:3080-3090` 逐字吻合，docstring 明写该 SDK 行为 |
| full / delta 判据 | rollback 用 `if accessor.mode == "delta"` 分叉 | ✅ `worker.py:2553`（delta 线性恢复）/ `:2570`（full 分叉），且注释解释了 delta fork 的写归属问题 |
| delivery receipt 先于终态 | 交付收据**故意**写在终态状态之前以关闭崩溃窗口 | ✅ `worker.py:1601-1633`，注释原文：*"then the staged terminal status is persisted. This ordering closes the crash window where a terminal run could otherwise outlive its receipt."* |

> **方法论（会一直沿用）**：别人给的结论必须抽检；抽检要挑"最不可能碰巧对"的那几条。
> 三中三之后，其余行号的信任成本才降得下来。这条习惯在阶段 2/3 直接决定评审质量。

## 8. 运行成本与节奏（自我约束）

**这条是写给 agent 自己的，防止"agent 一直往前跑、人类变成旁观者"。**

### 8.1 触发暂停的条件（满足任一即应停下，不再开启新的侦察）

1. **下一个动作需要人类已验证的能力**。例：评审 PR #6051 的增量点依赖 checkpoint 语义
   （阶段 A 的 Q4），而人类尚未作答。此时继续产出的是"未经人类复核的结论"——
   在评审里无法对它负责，等于没有价值。
2. **人类侧存在未完成的、路径上更靠前的待办**。例：阶段 A 作业未交、`GH_TOKEN` 未设。
3. **同一方向已连续 2 轮以上没有新的可验证产出**（说明进入边际收益递减区）。

### 8.2 暂停时的正确动作（不是"什么都不做"）

- 把已完成结论**固化**（文档 + 证据 + 复现命令）；
- 把**未完成项与阻塞原因**写清楚，让人类接手零成本；
- 清理工作区（未跟踪文件、临时产物）；
- **明确告诉人类"现在需要你做什么"**，而不是继续汇报进展。

### 8.3 已记录的运行成本教训

- **API 限流是预算**：未认证 60 次/小时，我们实测撞到过（见 [env-windows.md](env-windows.md) §4.1），
  导致最后取不到 PR CI 状态。**零散调用最贵。**
- **一次假发现的代价 > 三条没发出去的评论**：发到公开 PR 上的错误结论会消耗信誉，
  而信誉是我们在本仓库唯一能积累的资产。
- **重发别人的话是最坏的一种发言**：它不增加信息，却稀释了真正有价值的意见（第 10 轮实测）。

## 9. 进度日志（倒序，最新在上）

- **2026-10-01（第十轮 · 评审前必须先读现有评审——差点重发别人的话）**：
  子代理回报了 PR #6051 的**全部 9 条现有评审**，结果**否掉了我一半的准备**：
  - **F1（钩子插入点与描述不符）作废**：已被 `discussion_r4141724644`（30 小时前）覆盖，
    且对方**点名了 commit `6c54a190`**，写得比我们更精确。我们的版本是更窄的复述。
    → **教训（已内化）：发评审前必须先把现有评审全部读完。重发别人的话不仅无用，
    还会让后来真正有价值的意见被低估。**
  - **F2（准入钩子无超时）保留**：9 条评审无一提超时/挂起语义；最接近的一条讲的是**性能**
    （每次准入全线程 `alist(limit=None)`、持每线程锁扫描）。我们的角度是增量，**但必须在评论里显式区分**。
  - **局面判断**：PR 仍 open，`comments: 0` —— **维护者从头到尾没说过一句话**；9 条评审全部来自
    同一位**非维护者**贡献者。→ 这个 PR 缺的不是"更多发现"，而是**收敛**。
    我们的价值在「判断 9 条里哪几条是真问题 + 给出可验证的收敛方案」，而不是再找一条新缺陷。
  - **唯一候选增量**：`protect_checkpoint_ids` 的保护集合完备性（对应 `r4142320883`），
    待人类验证后定稿。全部重写见 `.scratch/pr6051-review-prep.md` §9。
- **2026-10-01（第九轮 · #6119 缺陷获得实测红证据 + 工作区清理）**：
  - **实测确认缺陷为真**：`evidence-6119-repro.py`（子代理产出，我已亲自复跑）在 HEAD 上
    **2 failed in 2.64s**。断言信息直接点名机制：
    *"ambiguous name ' strasse ' silently requested cancellation of 'task-050' instead of reporting
    ambiguity; 'task-000' shares the same casefolded name and is also active, but sits outside the
    newest 50 rows"*。复现命令与完整输出见 `.scratch/evidence-6119.md`。
  - **同时证明"红测试 ≠ 该修"**：维护者已明确关闭该方向的 PR #6120。留档价值在于演示这条判据。
  - **工作区清理**：子代理把 `CANDS.json` / `PENDING_CANDS.json` 留在了**仓库根目录**（未跟踪），
    已移入 `.scratch/`；`backend/tests/test_scratch_6119_repro.py` 也已移出仓库树为
    `.scratch/evidence-6119-repro.py`。**当前未跟踪项只剩 `docs/contributor/`。**
- **2026-10-01（第八轮 · PR #6051 预审定稿）**：产出 `.scratch/pr6051-review-prep.md`。
  - **2 条已核实可提交的 P2 发现**：F1 钩子插入点与 PR 描述不符（`worker.py:1049/1051` 之间，
    正文却说是"完成路径、清除 finalizing 之前"）；F2 准入钩子无超时，可阻塞 run 启动
    （同时核实 `except Exception` **不吞** `CancelledError`，这点是对的，不该当缺陷提）。
  - **2 条自我证伪的假发现（重要方法论产出）**：X1「`_storage_saver` 找不到 `source_saver`」
    ——本 PR 正好新增了该属性，且 `CachedHistorySaver.__getattr__`（`cached_saver.py:63-70`）
    会把未知属性委托给 `_inner`；X2「`_cursor` 是臆造契约」——实测 `AsyncSqliteSaver`/`InMemorySaver`
    都没有 `_cursor`，但它们由 `isinstance` 白名单先行处理，`_cursor` 只用于识别 `AsyncPostgresSaver`。
    → **教训：怀疑必须落到代码上验证。假发现发给维护者，代价大于三条没发出去的评论。**
  - **1 条 P0 级待人类独立验证**：安全谓词 `is_duration_only_checkpoint`
    （`app/gateway/checkpoint_lineage.py:43`）只检查 metadata `writes` 是否含 `runtime_run_duration`。
    它是整个 PR 的安全基础；不验证就不能提交 U1/U2 相关结论。
- **2026-10-01（第七轮 · 选靶穷尽，路线转向评审侧）**：新增 `wanted_survey.py`（推断维护者集合 +
  扫"想要"信号）。关键数据：
  - **唯一的实际合并者是 `WillemJiang`**（合并权重 75，其余所有人 0）；`/collaborators` 接口需认证（401）。
  - 近 60 天 **78 个 open issue 里只有 3 个带"维护者想要"信号，且全是 RFC**（而维护者流程对 RFC 是硬跳过）。
  - **"维护者说 NO"的 issue 评论列表为空** —— 因为我们的 NO（#6119）来自**已关闭 PR** 的评论。
    → **教训：判断"是否被拒"必须同时查已关闭的同主题 PR，光看 issue 评论会漏掉最关键的一类信号。**
  - **结论：本仓库"维护者公开想要 + 无人认领"的 issue ≈ 0。** 不是搜索方法问题，是结构性的。
- **2026-10-01（第六轮 · 选靶标准被重建）**：拉到了 PR #6120 的**关闭原话**（COLLABORATOR）：
  *"as current 50 task list is reasonable, we don't need to change it."*
  **而作者已按评审改完、CI 全绿，PR 仍被关闭。** → **#6119 也出局**（不是技术原因，是维护者意愿）。
  **由此确立"三过滤器"选靶标准（按顺序，缺一不可）**：
  1. **`wanted?` 维护者是否认为该修**（最便宜的信号：issue 下有维护者留言 / 被接受的 RFC / 明确邀请修复）
  2. **`unclaimed?` 是否真的没人做**（必须查 timeline + 同日 PR，**不能只看 issue 页面**）
  3. **`verifiable?` 能否离线验证**（单测可复现，不依赖 API key / 运行中的 Gateway / 外部服务）
  → **顺序不能颠倒。** 我们两次都是先满足 2+3、最后才碰 1，两次都白跑。
  **"CI 全绿 ≠ 会被合并"：决定权在"这个改动该不该存在"，而那一步发生在写代码之前。**
- **2026-10-01（第五轮 · 候选池被证伪 + PR 工作流就位）**：对抗性验证的第一批结论**推翻了两条判断**：
  - **#5953 → NO-GO**：PR #5954 在 issue 后 **24 秒**创建，**已合并**（`8e282c4c` 已在本地 HEAD），
    修复与测试（`tests/test_task_note_capacity.py`）都在。**而 issue 仍是 OPEN + 0 评论** ——
    "看 issue 页面判断是否空闲"这个做法本身是错的。
  - **#6119 → 唯一 GO 候选，但风险变了**：缺陷在 HEAD 上仍存在（`app/mcp_tasks/service.py:731-744`
    用默认 `limit=50` 分页后只在该页匹配），但 PR **#6120 曾试图修它并被关闭未合并**（含 Alembic 迁移
    `0027_mcp_task_name_key`，被标记为默认行为变更）。→ **决策门槛：必须给出"无 schema 变更"的方案**。
  - 产出 [pr-workflow.md](pr-workflow.md)：分工、分支策略、命令模板、PR 正文口径、自查清单。
  - **新增实测约束**：`git push` 在沙箱内**物理不可行**（git 要 spawn `git-remote-https`，
    沙箱禁止 msys 建信号管道；与 SSH 失败同根因，**不是凭证问题**）。分支推送必须由人类完成。
- **2026-10-01（第四轮 · 运行时地图交付）**：独立子代理完成只读考古，产出**已核验行号**的答案卷
  [answers-01-run-lifecycle.md](answers-01-run-lifecycle.md)：33 步调用链、43 项 middleware 全序、
  5 个问题的代码级答案、词表与 4 项未证实问题。
  **顺带发现**：`RunStatus.timeout`（`runtime/runs/schemas.py:24`）是**孤儿状态** —— 全仓库 3 处消费
  （`app/gateway/services.py:135`、`app/mcp_tasks/service.py:902`、`runtime/runs/manager.py:850`）、
  **零处生产**，源自 #1403 的词表对齐。判断为"词表冗余而非 bug"，优先级低，记录备查。
- **2026-10-01（第三轮 · 选题侦察）**：产出 [issue-scouting.md](issue-scouting.md)。
  **关键发现（影响策略）**：近 45 天 69 个新 issue 里 65% 已被 PR 认领，104 个 PR 在抢；
  且存在"issue 与 PR 同秒提交"的极端案例（#6050 / PR#6051）。
  → **"捡官方 issue"这条路基本被堵死**；路线修正为「信息优势 + 深度评审 + 只在发现真缺口时提 PR」。
  已在文档里记录一次事实更正（我最初误判 #6050 未被认领）。
- **2026-10-01（第二轮 · 工具链）**：配好 `upstream`、切出 `contrib/agent-runtime`、就位 `gh` v2.83.2、
  跑通后端验证基线；摸清沙箱三条限制（uv 缓存 / Windows TLS / 用户目录不可写）并写入
  [env-windows.md](env-windows.md)。产出 [runtime-symbol-map.md](runtime-symbol-map.md)（398 行符号表）。
- **2026-10-01（第一轮 · 定位）**：建立本文件；修复工作树 18 个缺失文件；确认 HEAD 位点；
  确立三阶段路径与验证矩阵。
