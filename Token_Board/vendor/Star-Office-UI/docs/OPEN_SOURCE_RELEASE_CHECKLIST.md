# Star Office UI — 项目整理清单

## 1. 目录检查

建议保留：
- `backend/`
- `frontend/`
- `docs/`
- `office-agent-push.py`
- `set_state.py`
- `state.sample.json`
- `join-keys.sample.json`
- `README.md`
- `LICENSE`
- `SKILL.md`

建议清理：
- `*.log`
- `*.out`
- `*.pid`
- `state.json`
- `agents-state.json`
- `join-keys.json`
- `*.backup*`
- `*.original`
- `.venv/`
- `venv/`
- `__pycache__/`

## 2. 配置检查

- 把本地运行路径改成环境变量或占位路径
- 保留 `.env.example`、`state.sample.json` 这类模板文件
- 不把运行时状态文件放进项目目录说明中

## 3. 文档检查

- README 只保留正常使用说明
- 许可协议里写清楚代码与素材的使用边界
- 示例域名、示例 key、示例路径统一使用占位内容
- 更新记录和说明文档避免写入本机环境信息

## 4. 美术与素材

- 保留已经允许分发的素材文件
- 对第三方素材继续附带原始许可说明
- 如果用于商用版本，需自行替换对应素材

## 5. 建议目录结构

```text
star-office-ui/
  backend/
    app.py
    requirements.txt
    run.sh
  frontend/
    index.html
    layout.js
    assets/
  office-agent-push.py
  set_state.py
  state.sample.json
  README.md
  LICENSE
  SKILL.md
  docs/
```
