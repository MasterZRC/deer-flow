# PR 工作流：分工、命令、以及沙箱做不到的事

> 目标：阶段 3 不出意外。每条命令都实测过或明确标注未实测。
> 环境限制的完整清单见 [env-windows.md](env-windows.md)。

## 1. 硬约束（已实测，2026-10-01）

| 动作 | 沙箱内（agent） | 你的终端（人类） |
| --- | --- | --- |
| 读 GitHub（公开 API） | ✅ Python `urllib` | ✅ |
| 读 GitHub（`gh`） | ❌ 未登录 | ✅ 登录后可用 |
| **`git ls-remote` / `git fetch`（HTTPS）** | ✅ 走 git 自带 openssl | ✅ |
| **`git push`（HTTPS 或 SSH）** | ❌ **`fatal error - couldn't create signal pipe, Win32 error 5`** | ✅ |
| 写工作树、跑测试 | ✅ | ✅ |
| 发 PR / 评论（有 token） | ✅ REST API | ✅ `gh` |

**`git push` 失败的真实原因**：git 需要 spawn `git-remote-https`，而本沙箱禁止 msys 进程建立信号管道
（与 SSH 失败同一个根因）。**不是凭证问题**——所以别指望加 token 就能在沙箱里 push。
`git ls-remote` 能成功是因为它不 spawn 远程 helper。

**结论：分支必须由你在自己的终端推送。** 我的职责是把分支准备到"你只需粘贴一条命令"的状态。

## 2. 分支策略（已执行）

```
upstream/main  ──●─ (5b83cb50, 比本地新 1 个提交)
                 │
main           ──●  4d560722  ← 与 origin/main 同步
                 │
contrib/agent-runtime ──●  我们的学习产物（docs/contributor/、.gitignore 本地忽略项）
```

- `main`：**保持干净**，永远只跟 `origin/main` 同步。这样 PR diff 只含目标改动。
- `contrib/agent-runtime`：**我们的工作台**，放学习产物。**这些不进任何 PR。**
- 真正的修复分支：**从 `upstream/main` 切**，名字用 `fix/<scope>-<short-desc>`（仓库惯例：
  `codex/...`、`fix/...` 都有，Human 提交多用 `fix(...)` 前缀的 commit message）。

## 3. 你在阶段 3 需要执行的命令（模板）

```powershell
# ① 一次性认证（二选一）
gh auth login                                    # 交互式，推荐
# 或：让 git 复用 gh 的凭证
gh auth setup-git

# ② 同步官方最新（我们的修复必须基于最新 main）
git fetch upstream main
git checkout -b fix/<scope>-<desc> upstream/main

# ③ 从工作台把修复搬过来（或直接在 agent 准备好的分支上）
git cherry-pick <sha>            # 或 git checkout contrib/... -- <paths>

# ④ 本地验证（必须与 PR 的 Validation 段逐字一致）
cd backend
$env:UV_CACHE_DIR = "$PWD\..\.uv-cache"
uv run pytest tests/<相关测试> -q
uv run ruff format --check <改动的文件>
uv run ruff check <改动的文件>

# ⑤ 推送（沙箱做不到，必须你来）
git push -u origin fix/<scope>-<desc>
```

## 4. PR 正文的写法（照维护者口径，不要自由发挥）

模板在 `.github/pull_request_template.md`，**每一项都要如实填**，尤其：

- **Why**：触发器（你是怎么撞上这个问题的）+ 被解决的痛点。**不要写"代码不够优雅"。**
- **Surface area**：勾选项决定 reviewer 的审查范围，勾错会被退回。
- **Bug fix verification**（bug 修复必填）：
  - 复现 bug 的测试路径；
  - **在 `main` 上是否变红、在本分支是否变绿**（yes/no）——这一条是我们最大的加分项；
  - 如果红测试不好写，说明为什么、以及你改用了什么替代证据。
- **Validation**：贴**真实跑过的命令与输出**，不是"should pass"。
- **AI assistance**：三段全填，并**保留**"我已读懂每一行并负责"的勾选。
  仓库明确欢迎 AI 参与，但要求人类读懂；**这一栏填得诚实，反而是加分项**。

## 5. 我们提交前的自查清单（agent 会逐条核对）

- [ ] 分支基于 `upstream/main` 的最新提交，不是旧 base
- [ ] 一个 PR 只做一件事，无顺手重构
- [ ] 有在 `main` 上变红的测试，且现在变绿
- [ ] `ruff format --check` 与 `ruff check` 干净
- [ ] 相关测试全绿（按第 2 节验证矩阵选范围）
- [ ] 改了行为的地方，同步更新了对应文档（仓库的 documentation update policy 是硬要求）
- [ ] PR 正文的 Validation 段与真实命令逐字一致
- [ ] **没有夹带** `docs/contributor/`、`.tools/`、`.uv-cache/` 等本地产物
- [ ] AI assistance 三段已填

## 6. 关于 fork 的推送目标

`origin` = `https://github.com/MasterZRC/deer-flow.git`（fork）。远程配置里有一条
`url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:` 的改写规则，
所以 `git remote -v` 显示的是 SSH 形式；但 SSH 在本沙箱不可用。
**推送时显式用 HTTPS 地址**，或先 `git remote set-url --push origin https://github.com/MasterZRC/deer-flow.git`。
