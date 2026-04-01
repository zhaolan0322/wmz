# 个人分层 AI 记忆系统运行时

这是基于设计稿与实现规格书落地的本地 MVP。

当前版本目标：

- 单机运行
- 本地 SQLite 存储
- 分层记忆
- 触发门控
- 作用域隔离
- 候选排序
- 污染抑制
- 成本感知交付
- 决策 trace
- benchmark 回归
- cleanup 瘦身
- protected memory 完整性校验

## 快速开始

1. 初始化数据库和样例数据

```powershell
python scripts/init_db.py
```

2. 运行演示

```powershell
python scripts/demo_run.py
```

3. 运行 benchmark

```powershell
python scripts/run_benchmark.py
```

4. 运行 cleanup

```powershell
python scripts/run_cleanup.py
```

5. 检查绝密记忆完整性

```powershell
python scripts/check_integrity.py
```

6. 导入真实 Codex 会话日志

```powershell
python scripts/import_codex_session.py --session-id YOUR_SESSION_ID --project-id your-project-id --project-path "C:\path\to\your-project"
```

7. 导入项目文档为项目记忆

```powershell
python scripts/import_project_docs.py --project-id your-project-id --project-name "Your Project" --project-path "C:\path\to\your-project"
```

## 推荐使用方式：统一 CLI

后续日常使用建议优先走这一个入口：

```powershell
python scripts/memory_cli.py <command>
```

常用命令：

```powershell
python scripts/memory_cli.py init
python scripts/memory_cli.py status
python scripts/memory_cli.py find-sessions --keyword "slide"
python scripts/memory_cli.py sync
python scripts/memory_cli.py ask --query "PPT skill项目 默认是可编辑PPT路线还是全AI视觉路线？" --explicit-recall
python scripts/memory_cli.py review --limit 8
python scripts/memory_cli.py cleanup
python scripts/memory_cli.py benchmark
python scripts/memory_cli.py integrity
python scripts/memory_cli.py scan-openclaw --sync
python scripts/memory_cli.py validate-openclaw
python scripts/memory_cli.py report-openclaw
```

基准案例文件位于：

- [data/benchmark_cases](C:/Users/19b370/Desktop/记忆论文/memory_system_runtime/data/benchmark_cases)

如果需要重建 20 个标准回归用例：

```powershell
python scripts/generate_benchmark_cases.py
```

项目注册文件：

- `config/source-registry.yaml`
- 示例文件：`config/source-registry.example.yaml`

这份配置用于保存：

- 默认项目
- 项目路径
- 项目对应的真实会话 `session_id`

建议流程：

1. 先 `init`
2. 再 `sync`
3. 后续直接用 `ask / status / review / cleanup`
4. 如果要接入新的真实会话，先用 `find-sessions` 找 `session_id`，再 `import-session` 或直接更新 `source-registry.yaml`

## openclaw 真实项目验证

如果你把真实项目创建在：

- `memory_system_runtime/openclaw/<project-name>`

建议用下面这条链路：

```powershell
python scripts/memory_cli.py scan-openclaw --sync
python scripts/memory_cli.py validate-openclaw
python scripts/memory_cli.py report-openclaw
```

作用分别是：

- `scan-openclaw --sync`
  自动发现新项目、登记到 registry、导入项目记忆；如果某个 openclaw 项目目录被删除，也会自动清理对应项目记忆，防止污染。
- `validate-openclaw`
  针对每个 openclaw 真实项目自动生成项目级问题，统计项目命中率、污染抑制率、交付匹配率、平均同 scope 精度。
- `report-openclaw`
  输出一份 Markdown 观察报告：
  [openclaw_memory_observation_report.md](C:/Users/19b370/Desktop/记忆论文/memory_system_runtime/openclaw_memory_observation_report.md)

如果你希望持续监听新项目创建，可以单独开一个终端运行：

```powershell
python scripts/memory_cli.py start-watch-openclaw --interval 10
```

它会在检测到**新项目目录或新的 openclaw 对话历史**后自动执行：

1. `scan-openclaw --sync`
2. `replay-openclaw-history`
3. `report-openclaw`
4. `dashboard`

监听状态与停止方式：

```powershell
python scripts/memory_cli.py watch-status
python scripts/memory_cli.py stop-watch-openclaw
```

如果你只想立即看一次真实对话历史命中率：

```powershell
python scripts/memory_cli.py replay-openclaw-history
python scripts/memory_cli.py dashboard
```

说明：

- `replay-openclaw-history` 会先自动导入 `~/.codex/sessions` 中 `cwd` 位于 `openclaw` 下的真实会话，再进行历史回放。
- 也就是说，这里测的是**真实对话历史命中率**，不是文档命中率。
- 上面这套 `openclaw` 相关命令是**观测与诊断链路**，用于验证真实对话历史命中率，不应被当作 memory 核心能力的“项目特化规则”。
- 也就是说，`openclaw` 只是当前用于观测的真实工作区，不应该被写死到记忆系统主逻辑里。

真实项目阶段优先观察这几个指标：

- `project_hit_rate`
- `pollution_free_rate`
- `delivery_fit_rate`
- `avg_scope_precision`
- `avg_used_memory_count`
- `history_hit_rate`
- `same_scope_hit_rate`

## 固定入口文件

系统现在有两个轻量入口：

- 全局固定入口：
  [data/runtime_data/protected/entry.md](C:/Users/19b370/Desktop/记忆论文/memory_system_runtime/data/runtime_data/protected/entry.md)
- 项目固定入口：
  `data/runtime_data/memory/archive/projects/<project-id>/project_entry.md`

读取原则：

- 每次查询先登记并读取全局 `entry.md`
- 如果当前有 `project_id`，再读取该项目的 `project_entry.md`
- 之后才进入渐进式读取：`task -> project -> global -> raw`
- 对项目问题，当前项目的 `core/project_profile`、`procedural`、`dynamic` 记忆会优先前台放行；全局相似经验默认降为后台候选

## 记忆分类判定规则

后续写入记忆时，不要只选一个标签，而要按三维一起判断：

1. 作用域
- `global`：离开项目仍成立
- `project`：只在项目内成立
- `task`：只对当前一次任务有效
- `session`：只对当前窗口临时有效

2. 稳定性
- `immutable`：不允许自动修改
- `stable`：长期稳定
- `dynamic`：中期有效、可能演化
- `temporary`：临时有效

3. 内容类型
- `fact`
- `preference`
- `decision`
- `experience`
- `procedure`
- `episode`

主规则：

- 先判作用域，再判稳定性，再判类型
- 一条记忆可以有多个辅助标签，但主归属只能有一个
- 连续两次以上复用且仍成立的 task 记忆，才考虑升级为 project 或 global
- 固定参数、身份、硬约束默认标记为 `exact_recall_required`

## 发布到 GitHub

如果要把仓库公开发布并交给别的环境安装，建议保持下面这些约束：

- 不提交 `data/runtime_data/`，里面包含本地数据库、trace、会话归档和运行日志。
- 不提交真实的 `config/source-registry.yaml`，它通常带有本地绝对路径和真实 `session_id`。
- 只提交源码、脚本、benchmark 用例、配置模板和文档。

一个最小发布流程可以是：

```powershell
git init
git add .
git commit -m "Initial public version"
git branch -M main
git remote add origin https://github.com/<your-account>/memory_system_runtime.git
git push -u origin main
```

在新环境安装后，先执行：

```powershell
python scripts/memory_cli.py init
python scripts/memory_cli.py status
python scripts/memory_cli.py benchmark
```

如果要在 openclaw 真实环境里观察效果，再执行：

```powershell
python scripts/memory_cli.py scan-openclaw --sync
python scripts/memory_cli.py validate-openclaw
python scripts/memory_cli.py replay-openclaw-history
python scripts/memory_cli.py dashboard
```
