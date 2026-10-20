# Apple Watch 系统照片表盘素材

## 平台能力与交付物

本路径把合法素材导出成照片，交给 Apple Watch 系统“照片”表盘显示。素材工具不拥有系统时钟、传感器触发或息屏生命周期控制权。

- 时钟由系统绘制。导出图不要烘焙时间、日期、心率或假实时电量；用户自带图片中已有数字时，先识别它们是否为需要去除的表盘示例数据。
- 多张图片可表达不同形态；以目标 watchOS 的照片切换方式为准。不要承诺规定的播放顺序、逐帧变身、自动眨眼、心率驱动动画或独立自定义 AOD。
- 不伪造 `.watchface` 文件。Watch 应用是独立应用，不能把应用安装称为第三方原生表盘安装。
- 特定型号是否支持常亮、照片界面如何摆放时间和可选复杂功能，需要查该型号与 watchOS 的官方说明。照片导出 profile 中记录系统版本，不会因此获得新的系统能力。

官方入口：[Apple Watch 照片表盘](https://support.apple.com/zh-cn/guide/watch/apd501eb33b3/watchos)。按目标版本阅读；本路径据此支持照片选择和切换，不据此扩展为自定义脚本表盘。

## 使用仓库导出工具

读取：

- `apple-watch/profiles/apple-watch-photo-generic.json`
- `apple-watch/export_photos.py --help`

示例：

```bash
python3 "<仓库>/apple-watch/export_photos.py" \
  --profile "<仓库>/apple-watch/profiles/apple-watch-photo-generic.json" \
  --input "<图片一.png>" "<图片二.png>" \
  --output "<输出目录>"
```

也可用 `--manifest "<JSON文件>"`：`photos` 数组中的每项可以引用 `source`，或以 `canvas` 与 `layers` 组合；以工具当前 schema 为准。优先读取已有项目清单，不再平行维护相同素材配置。

默认通用照片画布是 4:5、1000 × 1250，它是导出模板尺寸，并非所有 Apple Watch 的屏幕分辨率。按图片构图与目标设备实测调整 `--width`、`--height`、上下安全区、留白及背景渐变。记录 `--watch-model`、`--watchos-version` 便于复测，不声称这些参数会自动完成原生分辨率适配。

安全区用于给系统时钟留位置，人物整体等比缩放，避免通过 `cover` 裁掉头发、手、裙摆或腿。系统可能再次自动裁切，因此本地 PNG 检查之后，还需在 iPhone/Apple Watch 的表盘预览中核对人物与系统时间。

## 交付与使用

确认输出 PNG、中文说明和 `export-report.json` 成功生成。报告应列出实际画布、使用素材及尚待实机确认的部分；不要混入私人路径到对外发布示例。

把照片保存到用户 iPhone 可访问的照片库，再按对应系统版本通过 Watch App 或照片的表盘创建入口选择“照片”、选图和设置系统时间位置。提供当前官方路径，避免把某个旧版本菜单写成所有版本通用。

需要原生 Lua 级别的点击互动、心率联动或自定义 AOD 时，明确此照片路径的边界，然后讨论设备支持的替代交付；不要静默把动画降级为静态图片后称全部完成。
