# Interactive Watchface Kit · 互动表盘技能包

把有使用权的图片制作成可维护的手环表盘，或适配成 Apple Watch 照片表盘。包含可安装的 AI Skill、设备配置、原创几何示例、导出脚本和独立校验。

这份项目提炼自一套实际制作的 n67 互动表盘。公开仓库提供通用代码与原创示例，个人动漫图片、成品包、私人设备资料和没有明确分发许可的第三方编译器均不包含在内。

## 支持到什么程度

| 目标 | 已实现 | 使用边界 |
| --- | --- | --- |
| 小米手环 9 Pro / n67 | Lua 模板、自动表情、点击切换、心率阈值触发、静态 AOD、工程生成与独立包检查 | 336×480；需要单独准备兼容的外部打包器。主机测试通过不等于所有固件实机通过。 |
| Apple Watch / iPhone | 通用照片导出，按画布尺寸、留白、背景、型号和 watchOS 记录配置 | 输出 PNG。系统“照片”表盘负责时间和换图；图片不能携带自动眨眼、心率变身或独立 AOD。 |
| 其他型号 | 能力核验与适配流程、可复用素材组织 | 尚未实现对应原生导出器。修改型号字段或文件扩展名不会自动获得兼容性。 |

Apple Watch 的详细操作和限制见 [照片表盘适配](apple-watch/README.md)。本项目不会伪造 `.watchface` 文件，也不会把网页预览或普通手表 App 当成系统表盘。

## 安装 Skill

先下载或克隆**完整仓库**，保留在固定位置。把
[`skills/interactive-watchface`](skills/interactive-watchface)
复制到你的 AI 工具支持的技能目录。Codex 通常使用 `~/.codex/skills/`；其他工具按其技能安装说明操作。

仓库地址：[ysa688422-png/interactive-watchface-kit](https://github.com/ysa688422-png/interactive-watchface-kit)。可在仓库的 Code 菜单选择 Download ZIP，解压后保留完整目录。

技能会寻找完整仓库。若技能复制后不在仓库内，可在任务中直接给出仓库位置，或设置 `WATCHFACE_KIT_ROOT`。只读定位检查：

```sh
python3 skills/interactive-watchface/scripts/locate_kit.py --root .
```

可以这样发起任务：

> 使用 $interactive-watchface。完整仓库在我指定的目录。把这些有使用权的图片做成小米手环 9 Pro 的互动表盘：轻点换图、自然眨眼、心率大于 120 切换形态，息屏只留白花和时间。先检查设备能力和预览，再生成包。

> 使用 $interactive-watchface。制作 Apple Watch 通用照片版，顶部留出系统时间位置。后续按具体型号、屏幕尺寸和 watchOS 调整配置。不要把静态换图当成心率变身。

## 快速体验

需要 Python 3.10+ 和 Pillow。建议使用虚拟环境：

```sh
python3 -m venv .venv
# macOS / Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Apple Watch 照片

```sh
python apple-watch/export_photos.py \
  --input ./my-art/portrait.png ./my-art/flower.png \
  --output ./build/apple-photos
```

把导出的 PNG 保存到配对 iPhone 的“照片”，然后打开 Watch App → 表盘图库 → 照片 → 选择图片 → 添加。默认 1000×1250 是通用制作画布，不是某款 Apple Watch 的原生分辨率；仍需在 Watch App 预览里确认取景和时间位置。

```sh
python apple-watch/export_photos.py \
  --input ./my-art/portrait.png --output ./build/apple-custom \
  --width 1080 --height 1320 --top-safe-fraction 0.30 \
  --watch-model "实际机型和尺寸" --watchos-version "实际版本"
```

没有自己的图片也可以试用原创几何示例：

```sh
python apple-watch/examples/make_example.py
python apple-watch/export_photos.py \
  --manifest apple-watch/examples/generated/photos.json \
  --output ./build/apple-example
```

### 小米 n67 互动工程

```sh
python scripts/create_project.py \
  --output ./build/demo --name "Interactive Bloom" \
  --id 100000002 --threshold 120
python scripts/validate_project.py --project ./build/demo
```

生成器自带原创几何人物、表情、变换帧和花形图案，可自由替换。默认读取 [`profiles/xiaomi-band-9-pro.json`](profiles/xiaomi-band-9-pro.json)。不传 `--id` 时生成新的九位 ID；同一成品更新时应继续使用原 ID。

后续制作请同时维护 `asset-geometry.json` 与 `main.lua` 的坐标。保留 PNG 透明通道，完整对齐人物手臂、头部和动作轨迹。外部素材不应带旧表盘时间或数据。

**打包器是额外依赖。** 仓库不分发未经许可的 Mi8WfBinTool 源码、二进制或 JDK。准备好兼容的本地工具后，显式提供其可执行包装脚本：

```sh
python scripts/pack_xiaomi.py \
  --project ./build/demo \
  --output ./build/interactive-bloom.bin \
  --packer /absolute/path/to/wf-tool
```

包装脚本接收 `pack PROJECT OUTPUT n67` 参数。它需要支持 Lua 资源、正确的 AOD 标志和原生数字对齐。独立检查通过后才交付输出，避免把不含有效 AOD 的包误报成成功。安装使用你设备上已验证可用的工具，项目不执行蓝牙写入或固件操作。

## 型号与系统适配

- **Apple 照片版**：复制 `apple-watch/profiles/apple-watch-photo-generic.json` 调整尺寸、留白和背景。型号与系统版本用于记录；它们不改变系统提供的表盘能力。
- **n67**：现有布局和原生格式限定为 336×480。心率阈值可以修改，其他分辨率应新增布局和设备适配器并测试。
- **新平台**：先核实系统是否允许第三方原生表盘、支持什么安装格式、动画、交互、数据源和 AOD，再决定实现范围。参见 [设备适配参考](skills/interactive-watchface/references/device-adaptation.md)。

## 验证

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s apple-watch/tests -v
# Lua 5.4；在已生成 build/demo 后运行
lua tests/lua/test_runtime.lua build/demo/images/_lua/watchface/main.lua
```

Lua 主机测试覆盖心率 120/121 边界、未知数据、点击状态、睡眠/唤醒和资源销毁等 13 个场景、871 个断言。它们执行真实 Lua 逻辑与独立替身，不模拟固件、传感器、蓝牙或实际屏幕。

AOD 使用 `headerFlags=4`；小时、分钟原生数字元素左对齐使用 `align=1`。打包器与解包器可能共享同一错误，所以不能只凭往返相同证明兼容。检查代码会核对实际字节和图片数据。

## 许可

本项目自写代码、技能说明和代码生成的原创几何示例采用 [MIT](LICENSE)。使用者导入的图片不随代码获得授权。外部工具与参考资料各自适用其原有许可，见 [第三方说明](docs/THIRD_PARTY.md)。

项目不隶属于 Apple、小米或 Google。请在实际设备上验证显示、数据更新、耗电和安装行为后，再声明某个机型/固件已兼容。
