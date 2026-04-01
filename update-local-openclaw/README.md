# update-local-openclaw

一个面向 **OpenClaw 本地环境** 的安全更新 skill，目标不是“把升级命令跑完”，而是：

> **尽量确保更新前先识别风险，更新中尽量不中断，更新后能自动验收，失败时能停在安全态。**

这是一个“偏生产级”的更新编排器，适合用于：

- 本地 / 云端 OpenClaw 节点升级
- 需要在聊天不中断或尽量少中断前提下更新
- 希望有明确门禁、日志、回滚快照、结果摘要
- 不想再靠纯手工拍脑袋升级

---

# 一、它解决的核心问题

传统更新最大的问题，不是“命令不会写”，而是下面这些坑：

- 机器上有多套 OpenClaw 安装，升级命令打错目标
- Telegram 还能用，但 Web UI / WebChat 已经坏了
- `openclaw doctor` 已经在报警，但流程仍继续升级
- 重启看起来成功，实际用户入口不可用
- 出问题后只能手工救火，没有明确快照和结果报告

这个仓库就是为了解决这些问题。

它把更新流程拆成：

1. **更新前预检**：先判断这台机器能不能安全升级
2. **干跑（dry-run）**：先看升级计划是否正常
3. **先应用不重启**：先把包装上，避免一步切断
4. **中途健康检查**：确认 Telegram / Web 都还活着
5. **受控重启**：必要时走 fallback
6. **更新后验收**：确认不是“脚本成功、入口已坏”
7. **结果归档**：输出 run summary，便于复盘和排障

---

# 二、这版已经补上的关键加固

相比早期版本，这版已经新增以下能力：

## 1）安装方式安全门禁
更新前会识别安装来源，例如：

- `app-dir-package`
- `npm-global`
- `pnpm-app-dir`

如果识别结果是：

- `unknown`
- 或同时存在多种安装方式（混装）

则会直接阻断升级，不继续执行 apply。

**原因：** 混装环境是最容易导致“升级了 A，实际运行的是 B”的高风险场景。

---

## 2）doctor 硬阻断门禁
更新前会跑 `openclaw doctor`，并对高风险异常做阻断。

当前已纳入硬阻断的典型关键词包括：

- `token missing`
- `entrypoint missing`
- `service config mismatch`
- `multiple gateways`
- `state dir migration skipped`
- `target already exists`
- `config mismatch`

命中后直接返回 `BLOCKED`，不执行升级。

**原因：** 有些 warning 不是“提醒”，而是“升级前必须处理的硬问题”。

---

## 3）双通道健康检查
现在不再只看 Telegram。

更新流程会检查：

### Telegram 健康
要求下列账号都在线：

- `baozi`
- `fugui`
- `rescue`

### Web 健康
会探测 OpenClaw dashboard / gateway 的 Web 可达性。

检查时机：

- 更新前（pre）
- 更新中（mid）
- 更新后（postcheck / restart）

**意义：** 防止出现“Telegram 正常，但 Web 入口已经挂了”的假成功。

---

## 4）更严格的重启成功定义
这版不再把“进程起来了”当成“恢复成功”。

重启后的成功标准变成：

- Telegram 正常
- Web 正常
- `openclaw status` / `openclaw health` 正常
- 观察期内没有明显异常

否则不会给出 `SUCCESS`。

---

## 5）更清晰的结果状态
最终结果不再只说成功/失败，而是细分为：

- `SUCCESS`：通过全部门禁和验收
- `PARTIAL`：流程跑了一部分，但未满足完整成功标准
- `BLOCKED`：更新前门禁拦截，不允许继续
- `ROLLED_BACK`：升级/重启失败，但已回到可恢复状态

这比“脚本执行完了”更接近真实业务结果。

---

# 三、适用范围与边界

## 适用
适合这类场景：

- 你知道自己在升级 OpenClaw 本地安装
- 你愿意让流程在风险不明时 **主动阻断**
- 你接受“宁可先停住，也不要带病继续升级”
- 你需要留痕与可复盘结果

## 不适合
暂时 **不建议** 直接用于以下环境：

- 完全未知、历史遗留非常重的混乱安装现场
- 你要求“无论环境多脏都必须自动升级成功”
- 你需要真正的“二进制/依赖版本级完整回滚”
- 你有复杂的多 gateway / 多实例 / 多容器并存拓扑

当前版本已经解决很多问题，但还没有做到“所有复杂环境都可无脑一键成功”。

它当前更准确的定位是：

> **带强门禁的安全更新器**，而不是“任何环境下都绝对成功的魔法按钮”。

---

# 四、目录结构

```text
update-local-openclaw/
├─ README.md
├─ SKILL.md
└─ scripts/
   ├─ assert_baseline_safe.sh
   ├─ check_bot_comms.sh
   ├─ check_doctor_gate.sh
   ├─ check_install_method.sh
   ├─ check_web_health.sh
   ├─ cleanup.sh
   ├─ fetch_releases.py
   ├─ full_auto.sh
   ├─ full_auto_bg.sh
   ├─ postcheck.sh
   ├─ restart_with_fallback.sh
   ├─ rollback.sh
   ├─ run_summary.sh
   ├─ run_update.sh
   └─ snapshot.sh
```

---

# 五、使用前提

请先确认以下前提：

## 1）系统里已安装 `openclaw`
需要能正常执行：

```bash
openclaw --version
openclaw status
openclaw health
```

## 2）具备必要工具
通常需要：

- `bash`
- `python3`
- `curl`
- `npm` 或 `pnpm`（视你的安装方式而定）
- `ss`（用于端口检查）

## 3）当前节点本身是“可诊断”的
也就是说：

- `openclaw status` 至少能返回
- dashboard / gateway 端口不是完全失联
- `openclaw doctor` 能跑出结果

如果节点已经彻底坏死，这个 skill 不是第一救援工具，应该先做故障恢复。

---

# 六、最推荐的使用方式

## 方式 A：前台执行

```bash
scripts/full_auto.sh --restart
```

适合：

- 手动值守
- 希望看到完整过程
- 当前升级动作较短

---

## 方式 B：后台执行（推荐）

```bash
scripts/full_auto_bg.sh --restart
```

然后查看进度：

```bash
tail -f <run_dir>/progress.log
```

适合：

- 你还想保持聊天不中断
- 升级时间可能较长
- 希望日志自动落盘

---

## 方式 C：只分析，不实际升级

```bash
RUN_DIR="$HOME/.openclaw/update-local-openclaw/runs/analyze-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
scripts/check_install_method.sh "$RUN_DIR"
scripts/assert_baseline_safe.sh "$RUN_DIR"
scripts/check_doctor_gate.sh "$RUN_DIR"
scripts/check_web_health.sh "$RUN_DIR" pre
python3 scripts/fetch_releases.py "$RUN_DIR"
scripts/run_update.sh --mode dry-run --run-dir "$RUN_DIR"
```

适合：

- 先排风险
- 先看这台机器有没有资格升级
- 先看目标版本是否合理

---

# 七、完整流程说明

`full_auto.sh` 的执行顺序大致如下：

1. 收集 baseline
2. 检查安装方式是否安全
3. 检查 doctor 是否命中硬阻断
4. 检查 Telegram 通道
5. 检查 Web 通道
6. 拉取 release 信息
7. 创建回滚快照
8. 先跑 dry-run
9. 真正 apply，但先 `--no-restart`
10. 再做 mid 阶段健康检查
11. 做预重启 postcheck
12. 如有需要，执行 restart + fallback
13. 重启后再次验收
14. 生成 run summary

这个顺序的核心原则是：

> **先确认风险，再动生产；先确认不中断，再考虑重启。**

---

# 八、会产出哪些文件

每次执行都会在如下目录生成产物：

```bash
~/.openclaw/update-local-openclaw/runs/<timestamp>/
```

常见文件包括：

- `baseline.json`：当前机器的安装基线
- `doctor-gate.json`：doctor 门禁结果
- `release-info.json`：release 源信息
- `dryrun.log`：dry-run 输出
- `update.log`：apply 输出
- `comms-pre.json` / `comms-mid.json` / `comms-post.json`
- `web-pre.json` / `web-mid.json` / `web-postcheck.json`
- `restart-state.json`
- `postcheck.json`
- `rollback-manifest.json`
- `run-summary.md`
- `progress.log`
- `progress.jsonl`

这些文件的作用，不只是“记录跑过了”，而是为了让你在出问题时能快速判断：

- 卡在哪一步
- 是 Telegram 坏了还是 Web 坏了
- 是环境问题、升级问题，还是重启问题
- 是否已经回滚

---

# 九、如何判断这次升级算真正成功

不是脚本退出 0 就算成功。

必须同时满足：

- 目标版本达到
- `openclaw status` 正常
- `openclaw health` 正常
- 基本 smoke check 正常
- Web 健康检查通过
- Telegram 健康检查通过
- 重启后观察期通过
- doctor 预检未命中硬阻断

只有这样，最终结果才应该是：

```text
SUCCESS
```

---

# 十、常见结果怎么理解

## `SUCCESS`
表示：

- 升级完成
- Telegram 正常
- Web 正常
- 验收通过

这是理想结果。

---

## `PARTIAL`
表示：

- 流程跑通了一部分
- 但并未满足全部成功标准

常见原因：

- 版本到了，但某个健康检查没过
- 未重启或重启后观察不足
- 某个入口存在异常

这类结果 **不要当成功**。

---

## `BLOCKED`
表示：

- 更新前就发现风险
- 为了安全，流程主动终止

常见原因：

- 混合安装方式
- doctor 命中高风险 blocker
- release 信息不一致

这不是失败，而是**正确的风控行为**。

---

## `ROLLED_BACK`
表示：

- 升级或重启阶段出问题
- 已尝试回到更安全的状态

这类结果说明：

- 系统经历过异常
- 但流程没有放任它停在半残状态

后续仍建议人工复核。

---

# 十一、当前最常见的阻断原因

## 1）混合安装方式
例如同时检测到：

- `app-dir-package`
- `npm-global`
- `pnpm-app-dir`

这说明机器上可能存在多套运行来源。

### 建议处理
先统一安装方式，再升级。

---

## 2）doctor 报高风险异常
例如：

- token 丢失
- 配置不一致
- entrypoint 缺失
- gateway 冲突

### 建议处理
先修 doctor 问题，再重新跑更新。

---

## 3）Web 通道不可达
如果 Telegram 正常但 Web 探测失败，流程不会给 `SUCCESS`。

### 建议处理
检查：

- gateway 端口
- dashboard URL
- 反向代理 / 防火墙 / 本机回环
- Web 鉴权或来源校验

---

# 十二、故障排查建议

如果升级没过，建议按这个顺序看：

## 第一步：看 `run-summary.md`
先看结果总览，不要一上来翻大日志。

## 第二步：看 `progress.log`
确认卡在哪个阶段。

## 第三步：看这几类 JSON
- `baseline.json`
- `doctor-gate.json`
- `comms-*.json`
- `web-*.json`
- `postcheck.json`
- `restart-state.json`

## 第四步：必要时单独运行子脚本
比如：

```bash
scripts/check_install_method.sh <run_dir>
scripts/check_doctor_gate.sh <run_dir>
scripts/check_web_health.sh <run_dir> pre
scripts/check_bot_comms.sh <run_dir> pre
```

这样可以快速判断到底是：

- 环境门禁
- 通道门禁
- 更新 apply
- 重启恢复
- 还是 postcheck 验收

---

# 十三、当前版本仍然存在的限制

为了避免误导，下面这些限制要明确说清楚：

## 1）还不是完整版本级回滚
当前回滚更偏向：

- 配置恢复
- 凭证恢复
- 运行恢复尝试

还没有做到“完整应用版本回退”。

## 2）混乱现场不会自动帮你全部修干净
当前策略是：

- 先识别
- 先阻断
- 不带病升级

而不是自动把所有复杂历史包袱都清理完再升级。

## 3）Web 检查当前偏可达性检查
这版已比以前强很多，但目前主要还是：

- dashboard/gateway 可达
- HTTP 返回码合理

如果你需要更深的业务级 Web 验证，后续可以继续补。

---

# 十四、推荐的使用原则

如果你想让它长期稳定服务别人，建议坚持三条：

## 原则 1：先分析，再 apply
不要把任何环境都当成“直接一键升级”。

## 原则 2：遇到 `BLOCKED` 不要硬冲
`BLOCKED` 不是脚本保守，而是在保护现场。

## 原则 3：成功标准必须以用户入口为准
不是命令没报错就算成功，而是：

- 人还能继续聊天
- Web 还能访问
- 节点没有进入半残状态

---

# 十五、推荐命令速查

## 只分析

```bash
RUN_DIR="$HOME/.openclaw/update-local-openclaw/runs/analyze-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
scripts/check_install_method.sh "$RUN_DIR"
scripts/assert_baseline_safe.sh "$RUN_DIR"
scripts/check_doctor_gate.sh "$RUN_DIR"
scripts/check_web_health.sh "$RUN_DIR" pre
python3 scripts/fetch_releases.py "$RUN_DIR"
scripts/run_update.sh --mode dry-run --run-dir "$RUN_DIR"
```

## 前台全流程

```bash
scripts/full_auto.sh --restart
```

## 后台全流程

```bash
scripts/full_auto_bg.sh --restart
```

## 查看进度

```bash
tail -f <run_dir>/progress.log
```

## 查看结果摘要

```bash
cat <run_dir>/run-summary.md
```

---

# 十六、给二次开发者的建议

如果你准备把这个 skill 集成到自己的 OpenClaw 环境里，建议下一步继续增强：

- 真正版本级回滚
- 混合安装自动收敛
- 更深的 WebSocket / 鉴权检查
- 容器 / systemd / 多实例场景模板化
- CI 自测样例

---

# 十七、结论

这不是一个“盲目一键升级器”。

它的设计理念是：

> **先识别风险，再决定是否升级；先确保关键入口存活，再判断是否真的成功。**

如果你要的是“拿来就能在规范环境里稳定更新”，这版已经比传统手工升级稳很多。

如果你要的是“任何脏环境都无脑一键成功”，那还需要继续往第二阶段演进：

- 自动标准化安装
- 真版本回滚
- 更深业务级验收

但从工程安全性角度，这版已经迈过了最关键的一步：

**不再把“能跑完脚本”误当成“升级成功”。**
