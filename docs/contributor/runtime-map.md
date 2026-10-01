# 运行时内核：学习索引（阶段 A）

> 本文件是**索引**，不存放答案。答案两处：
> - 结构导航 → [runtime-symbol-map.md](runtime-symbol-map.md)（runtime 包 398 行全量符号表）
> - 已核验答案 → [answers-01-run-lifecycle.md](answers-01-run-lifecycle.md)（作业答案卷，先答题再看）
>
> 作业题目 → [assignment-01-run-lifecycle.md](assignment-01-run-lifecycle.md)

## 阅读顺序（别跳）

1. [docs/ARCHITECTURE.md](../ARCHITECTURE.md) —— 全局拓扑与分层
2. [runtime/AGENTS.md](../../backend/packages/harness/deerflow/runtime/AGENTS.md) —— **维护者写的雷区清单**，
   先读它再读代码，否则会低估复杂度（checkpoint 模式、rollback、journal 批次都在这里）
3. [runtime-symbol-map.md](runtime-symbol-map.md) —— 决定"读哪个文件"
4. 然后**从 HTTP 入口往下读**，不要从工具函数往上读

## 体量预告（避免迷路）

| 文件 | 行数 |
| --- | --- |
| `runtime/runs/worker.py` | 3230（`run_agent` 从 868 行写到 1872 行） |
| `app/gateway/services.py` | 2487（`start_run` 在 1684） |
| `runtime/runs/manager.py` | 2424 |
| `runtime/journal.py` | 1386 |
| `agents/lead_agent/agent.py` | 1398 |
