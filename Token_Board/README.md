# Token_Board

这是一个给多 bot 场景做可视化展示的小项目，包含两部分：

1. `Token Dashboard`：查看会话 token 消耗、活跃情况和排行
2. `Star Office`：用像素办公室视图展示 bot 当前状态，并支持多 bot 切换

项目主要面向 OpenClaw 风格的会话数据，但整体结构也适合改造成你自己的 bot 看板。

## 功能

- 展示多 bot 的 token 消耗和会话统计
- 支持 `today / 7d / 30d / all` 时间窗口
- 集成像素风办公室视图
- 支持在办公室视图中切换不同 bot
- 根据会话内容推断 bot 当前状态
- 提供项目打包脚本，便于整理发布版本

## 目录结构

- `app.py`：轻量级 token 看板服务
- `src/`：会话解析、聚合、快照导出
- `templates/` `static/`：看板前端
- `sync_mishu_star_office.py`：把 bot 会话状态映射到办公室视图
- `vendor/Star-Office-UI/`：集成进来的第三方办公室 UI

## 快速开始

启动 token 看板：

```bash
python app.py
```

启动办公室视图：

```bat
start_star_office.example.cmd
```

默认访问地址：

- `http://127.0.0.1:8787`
- `http://127.0.0.1:19000`

## 环境变量

Token 看板：

- `TOKEN_BOARD_SESSIONS_PATH`
- `TOKEN_BOARD_HOST`
- `TOKEN_BOARD_PORT`
- `TOKEN_BOARD_CACHE_SECONDS`
- `TOKEN_BOARD_AGENTS_ROOT`

Star Office：

- `OPENCLAW_WORKSPACE`
- `STAR_BACKEND_PORT`
- `FLASK_SECRET_KEY`
- `ASSET_DRAWER_PASS`
- `STAR_OFFICE_STATE_FILE`

## 打包发布

如果你想整理一个单独的发布版本，可以先执行：

```powershell
./prepare_open_source_release.ps1
```

它会生成一个独立的项目副本，并自动打包到 `open-source-dist/` 目录。

补充说明：

- [打包说明](./OPEN_SOURCE_RELEASE.md)
- [data/README.md](./data/README.md)
- [vendor/Star-Office-UI/LICENSE](./vendor/Star-Office-UI/LICENSE)

## 许可证说明

- 本仓库新增代码按仓库根目录的 [LICENSE](./LICENSE) 说明发布
- `vendor/Star-Office-UI` 保留其自己的 [LICENSE](./vendor/Star-Office-UI/LICENSE)
- 其中代码部分可复用，但该第三方项目自带美术资源是非商用的
- 如果你要做商用版本，请自行替换相关素材
