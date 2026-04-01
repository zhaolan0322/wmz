# gstack for OpenClaw

`gstack` 在这个 fork 里只保留 `OpenClaw` 使用路径。目标不是兼容多个宿主，而是提供一套可迁移、可安装、可验证的 `OpenClaw` 多 agent Web 应用交付工作流。

核心能力：
- 保留 `gstack` 的主流程技能：`/office-hours -> /plan-ceo-review -> /plan-eng-review -> /review -> /qa -> /ship -> /land-and-deploy`
- 增加 `OpenClaw` 的 `/build` 包装 skill，用来先出方案、确认后再派工
- 安装到 `~/.openclaw/skills`
- 提供 `leader / builder / reviewer / qa / deploy` 角色模板
- 保留 `browse` 二进制和浏览器自动化能力

## 要求

- `bun`
- `bash`
- `openclaw`
- `git`
- Windows 上还需要 `node`

## 安装

```bash
git clone https://github.com/garrytan/gstack.git ~/gstack
cd ~/gstack
./setup --host openclaw
```

安装完成后会：
- 生成 OpenClaw 专用技能到 `.openclaw/skills`
- 创建运行时根目录 `~/.openclaw/skills/gstack`
- 链接所有 `gstack-*` skills 到 `~/.openclaw/skills`
- 链接 `openclaw/skills/build` 到 `~/.openclaw/skills/build`

## OpenClaw 配置

1. 将 `openclaw/config/openclaw.example.json` 的内容合并到你的 OpenClaw 配置。
2. 创建这些 agents：
   - `leader`
   - `builder`
   - `reviewer`
   - `qa`
   - `deploy`
3. 把 `openclaw/agents/*/AGENTS.md` 复制到对应 agent 的 workspace。
4. 重启 OpenClaw，让它重新扫描 `~/.openclaw/skills`。

## 使用

在 OpenClaw 中执行：

```text
/build 做一个公网可访问的 Web 应用，需求是……
```

执行规则：
- `leader` 先跑 `office-hours + plan-ceo-review + plan-eng-review`
- 先输出方案给你确认
- 你确认后，才允许 `builder -> reviewer -> qa -> deploy`
- 最终由 `leader` 汇总，返回公网链接

第一阶段目标是 `Cloudflare` 上的真实公网 Web 应用交付，不是 demo 页面。

## 验证

本仓库当前保留的验证入口：

```bash
bun run gen:skill-docs
bun run skill:check
bun test browse/test/ test/gen-skill-docs.test.ts test/skill-validation.test.ts test/global-discover.test.ts
./setup --host openclaw
```

## 目录

- `openclaw/skills/build/`: OpenClaw 的 `/build` 入口
- `openclaw/agents/`: `leader / builder / reviewer / qa / deploy` 模板
- `browse/`: 持久化浏览器 CLI
- `.openclaw/skills/`: 生成出的 OpenClaw skills
- `review/`: 审查检查单和辅助资料

## 当前边界

这个 fork 现在只支持：
- `OpenClaw`
- `Web 应用` 交付路径

它还没有在仓库内置真实的 Cloudflare 凭证或你的域名环境。  
所以“安装链、技能生成、技能校验”可以本地完整验证，但“真实公网部署到 `*.wangmz.dpdns.org`”仍然需要你在目标环境补齐 Cloudflare 账号、Token 和 OpenClaw 运行配置。
