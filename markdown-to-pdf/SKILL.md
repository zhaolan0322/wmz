---
name: markdown-to-pdf
description: 将任意 Markdown 文件转换为带专业样式的 PDF 文件（支持中文、表格、代码块）。调用本 skill 时只需提供目标 md 文件路径，无需手动配置任何工具。
---

# Markdown → PDF 转换 Skill

## 工具依赖

- **Node.js ≥ 18** + **npm**（运行 `node --version` 确认）
- **md-to-pdf**（通过 `npx` 自动安装，无需手动 install）

---

## 使用方式

用户触发示例：
> "把 xxx.md 转成PDF"
> "将这个markdown导出为PDF"
> "生成可发给客户的PDF版本"

---

## 执行步骤

### Step 1：确认目标文件路径

从用户请求中获取 md 文件的**绝对路径**，例如：
```
C:\Users\19b370\Desktop\test\PPT\课程方案设计_银行AI应用科普内训.md
```
将其拆分为：
- `$DIR`：文件所在目录（`C:\Users\19b370\Desktop\test\PPT`）
- `$FILE`：文件名（`课程方案设计_银行AI应用科普内训.md`）

---

### Step 2：检查配置文件是否存在

检查 `$DIR` 下是否已有以下两个文件：

| 文件 | 作用 |
|------|------|
| `.md-to-pdf.json` | md-to-pdf 转换配置（页面尺寸、边距、CSS引用） |
| `pdf-style.css` | PDF 视觉样式（中文字体、表格、标题层级） |

**如果不存在**，执行 Step 3 创建它们。
**如果已存在**，直接跳到 Step 4。

---

### Step 3：创建配置文件（首次使用时）

#### 3a. 创建 `.md-to-pdf.json`

在 `$DIR` 下创建文件 `.md-to-pdf.json`，内容：

```json
{
  "stylesheet": "pdf-style.css",
  "pdf_options": {
    "format": "A4",
    "margin": {
      "top": "20mm",
      "bottom": "20mm",
      "left": "18mm",
      "right": "18mm"
    },
    "printBackground": true
  },
  "launch_options": {
    "args": ["--no-sandbox", "--disable-setuid-sandbox"]
  }
}
```

#### 3b. 创建 `pdf-style.css`

在 `$DIR` 下创建文件 `pdf-style.css`，内容复制自本 skill 的 `resources/pdf-style.css`。

---

### Step 4：执行转换命令

在 PowerShell 中，`cd` 到 `$DIR`，执行：

```powershell
npx -y md-to-pdf --config-file ".md-to-pdf.json" "$FILE"
```

> 首次运行会自动下载 md-to-pdf 及 Chromium，约需 1-3 分钟，后续运行秒级完成。

---

### Step 5：确认输出

转换成功后，PDF 文件输出在**与 md 文件相同目录**下，文件名与 md 相同，扩展名改为 `.pdf`。

验证命令：
```powershell
Get-Item "$DIR\output.pdf" | Select-Object Name, Length, LastWriteTime
```

---

## 常见报错处理

| 报错信息 | 原因 | 解决方法 |
|---------|------|---------|
| `ENOENT: no such file or directory` | 文件路径不存在或含特殊字符 | 检查路径，用引号包裹文件名 |
| `JSON parse error` | PDF options 参数格式错误 | 使用 `--config-file` 替代命令行内联 JSON |
| `Exit code: 1` 无详细信息 | Chromium 启动失败 | 在 `launch_options.args` 中加入 `--no-sandbox` |
| 中文乱码 | 系统缺少中文字体 | CSS 中已配置微软雅黑作为 fallback，通常无需处理 |
| 转换超时 | 首次下载 Chromium | 等待完成即可，后续不再下载 |

---

## 样式定制说明

如需修改 PDF 视觉风格，编辑 `$DIR/pdf-style.css`：

| 修改目标 | 对应 CSS 选择器 |
|---------|---------------|
| 主标题颜色 | `h1 { color: ... }` |
| 表格头部颜色 | `thead tr { background: ... }` |
| 正文字号 | `body { font-size: ... }` |
| 页面字体 | `body { font-family: ... }` |
| 引用块样式 | `blockquote { ... }` |

修改后重新执行 Step 4 即可生效。

---

## 批量转换（多个 md 文件）

```powershell
# 将目录下所有 .md 文件转为 PDF
Get-ChildItem -Path "$DIR" -Filter "*.md" | ForEach-Object {
    npx md-to-pdf --config-file ".md-to-pdf.json" $_.Name
}
```

---

## 输出质量说明

本 skill 生成的 PDF 特性：
- ✅ A4 标准尺寸，可直接打印或发送
- ✅ 中文字体正常显示（微软雅黑 / Noto Sans SC）
- ✅ Markdown 表格完整渲染，含表头色块
- ✅ 代码块保留等宽字体和背景
- ✅ 标题层级视觉清晰，含颜色区分
- ✅ 引用块蓝色底色，突出显示
