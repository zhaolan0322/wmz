# 打包说明

这个项目自带一个打包脚本，用来生成独立的发布版本。

## 使用方式

先执行：

```powershell
./prepare_open_source_release.ps1
```

执行完成后，会在 `open-source-dist/` 目录下生成：

- 一个可直接查看的项目文件夹
- 一个对应的 zip 压缩包

## 发布包内容

发布包默认会包含：

- 源码
- 前端页面与静态资源
- 示例数据 `data/sample_sessions.json`
- 第三方依赖目录 `vendor/Star-Office-UI`

## 许可证说明

- 本仓库新增代码按仓库根目录的 [LICENSE](./LICENSE) 说明发布
- `vendor/Star-Office-UI` 保留其自己的 [LICENSE](./vendor/Star-Office-UI/LICENSE)
- 其中代码部分可复用，但该第三方项目自带美术资源是非商用的
- 如果你要做商用版本，请自行替换相关素材
