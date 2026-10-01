# Windows 开发环境注意事项（本机实测）

> 记录本机（Windows + DSH 沙箱 workspace-write）跑通验证命令所需的**额外环境变量**。
> 目的：阶段 3 里每条验证命令都能一次跑通、可复制进 PR 的 Validation 段。

## 1. `uv` 必须重定向缓存目录

沙箱禁止写入 `%LOCALAPPDATA%`，`uv` 默认缓存就在那里，会直接失败：

```text
uv : error: Failed to initialize cache at `C:\Users\ROG\AppData\Local\uv\cache`
  Caused by: failed to open file `...\sdists-v9\.git`: 拒绝访问。 (os error 5)
```

解决（每次会话设置一次）：

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
```

已在 `.gitignore` 之外，注意别把 `.uv-cache/` 提交上去（见下）。

## 2. `pytest` 缓存告警（可忽略，但会污染输出）

```text
PytestCacheWarning: could not create cache path ...\backend\.pytest_cache\v\cache\nodeids: [WinError 5]
```

测试仍然全部通过（实测 `tests/test_harness_boundary.py` → `1 passed`）。要消除噪声：

```powershell
uv run pytest tests/... -q -p no:cacheprovider
```

## 3. 已验证的基线命令

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
cd backend
uv run pytest tests/test_harness_boundary.py -q     # 1 passed（harness/app 边界）
```

## 4. 网络与凭证：**只有 Python 的 TLS 可用**

沙箱下三条下载路径实测结果：

| 方式 | 结果 |
| --- | --- |
| `Invoke-WebRequest`（PS 5.1） | ❌ 基础连接已关闭 |
| `curl.exe`（Windows schannel） | ❌ `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` |
| `winget install` | ❌ 退出码 `-1978335231`（写用户目录被拒 + 源不可达） |
| `python -c "urllib.request.urlopen(...)"` | ✅ HTTP 200 |
| `git fetch https://...` | ✅ 可用（走 OpenSSL） |
| `web_fetch`（harness 内置） | ✅ 可用（**与 Python 走不同出口**，见 §4.1） |

### 4.1 GitHub 未认证限流：**60 次/小时，实测撞到过**

`collaborators` 接口需要认证（401），未认证的 API 调用上限是 **60 次/小时**。
我们在连续扫描候选池时**实测触发**：`HTTPError: HTTP Error 403: rate limit exceeded`。

**应对方式（已实测有效）**：

| 需求 | 手段 |
| --- | --- |
| 读 GitHub 数据 | **优先 `web_fetch`**（harness 内置，配额与 Python 出口独立）；Python `urllib` 留给需要循环/分页/解析的场景 |
| 需要高配额或写操作 | **`GH_TOKEN`**（仍未设置）—— 认证后 5000 次/小时，且可发评论/建 PR |
| 一次调用拿多个事实 | 合并成一个脚本，别用十几个零散调用（限流是按请求数算的） |

**代价教训**：为验证"某 issue 是否真被认领"，我们用零散调用烧掉了整小时配额，
导致最后**没能取到 PR #6051 的 CI 状态**。**限流预算要像钱一样花。**

**结论：需要下载东西时，用 Python 的 `urllib`/`requests`，不要用 Windows 原生 TLS 栈。**
安装 `gh` 就是这么做的：

```powershell
python -c "import urllib.request;urllib.request.urlretrieve('https://github.com/cli/cli/releases/download/v2.83.2/gh_2.83.2_windows_amd64.zip', r'$env:TEMP\gh.zip')"
```

## 5. `gh` CLI 的可用形态（已就绪）

- 位置：`.tools/gh/gh.exe`（已从 zip 的 `bin/` 解出；`.tools/` 已 gitignore），版本 2.83.2，可正常执行。
- **未登录**：`gh auth status` → not logged into any GitHub hosts。且 `%APPDATA%\GitHub CLI\hosts.yml` 不存在。
- 沙箱禁止写用户目录，所以登录前需指定配置目录：

```powershell
$env:GH_CONFIG_DIR = "$PWD\.tools\gh-config"
gh auth login --hostname github.com --git-protocol https --web    # 浏览器 / device code 流程
```

（本机 fork 的 remote 是 SSH；提 PR 用 `gh` 的 API 通道即可，不依赖 SSH。若要让 `git push` 也走 HTTPS，
改用 `https://github.com/MasterZRC/deer-flow.git`，并注意本机存在
`url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:` 的改写规则。）

## 6. `git push` 在沙箱内**物理上不可行**（已实测）

```text
git push --dry-run https://github.com/MasterZRC/deer-flow.git HEAD:refs/heads/probe
→ fatal error - couldn't create signal pipe, Win32 error 5   (exit 128)
```

与 SSH 失败**同一根因**：git 需要 spawn `git-remote-https`，而沙箱禁止 msys 建信号管道。
**这不是凭证问题**——加 token 也没用。对比：`git ls-remote` 成功，因为它不 spawn 远程 helper。

**因此分工固定**：agent 把分支与测试准备到"可粘贴"状态，**分支推送由人类在自己的终端执行**。
完整命令模板见 [pr-workflow.md](pr-workflow.md)。

## 7. 需要加入 `.gitignore` 的本地产物

`.uv-cache/`、`.tools/`、`docs/contributor/.scratch/`（已加入）
（提交前用 `git status` 复核；这些目录不应进入任何 PR。）
