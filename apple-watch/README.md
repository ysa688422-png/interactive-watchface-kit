# Apple Watch 照片表盘导出

把本地、有使用权的图片排成 Apple Watch 系统“照片”表盘可用的 PNG。保留比例、不裁掉可见图像内容，预留系统时间区。所有操作在本地完成，无联网、设备控制或后台服务。

这是照片简化版，不是 `.bin` 转换器，也不生成 `.watchface`。自动眨眼、心率触发变身、原 Lua 点击状态机和独立白花息屏不能由这些 PNG 携带。黑底图也是普通照片；常亮显示由设备与系统表盘控制。

## 使用

需要 Python 3.10+ 和 Pillow：

```sh
python3 -m pip install -r apple-watch/requirements.txt
python3 apple-watch/export_photos.py \
  --input ./my-art/portrait.png ./my-art/flower.png \
  --output ./exports/apple-photos
```

从本模块目录运行时，也可以用 `python3 export_photos.py ...`。脚本按自身位置找到默认配置，不依赖启动目录。

默认配置 `profiles/apple-watch-photo-generic.json` 是 **4:5、1000×1250 的通用导出画布**，不是某款 Apple Watch 的原生分辨率，也不是苹果规定的安全区。未指定机型时先用它，再在 Watch App 的实际预览中校准。

调整机型、系统记录和布局：

```sh
python3 apple-watch/export_photos.py \
  --input ./my-art/portrait.png --output ./exports/custom-size \
  --profile apple-watch/profiles/apple-watch-photo-generic.json \
  --width 1080 --height 1320 \
  --top-safe-fraction 0.30 --bottom-safe-fraction 0.07 \
  --padding-fraction 0.09 \
  --background-top '#ECE4F3' --background-bottom '#A68EBB' \
  --watch-model 'your actual model and size' --watchos-version 'your actual version'
```

`width` / `height` 可设任意合理矩形尺寸；`top_safe_fraction`、`bottom_safe_fraction` 留出上下区；`padding_fraction` 是左右留白比例。背景支持两个 RGB 颜色的竖向渐变。`trim_transparent` 默认仅移除完全透明的外围空白，可用 `--no-trim-transparent` 保留完整图像画布。透明像素的叠合使用 alpha compositing，不会叠乘透明度造成边缘变黑。

机型和 watchOS 字段只用于记录，不会自动推断原生尺寸或改变平台能力。调整配置不等于已在该设备上验证。程序不负责抠图，原图已有的裁切也无法补回。

## 多图层清单

输入完整图片时使用 `source`；重建有透明裁边的素材时使用 `canvas` 和 `layers`，坐标以原画布为单位。文件路径相对清单文件；导出工具拒绝 URL。

```json
{
  "photos": [
    {"name": "portrait", "source": "art/portrait.png"},
    {
      "name": "layered",
      "canvas": [400, 500],
      "layers": [
        {"file": "art/decor.png", "x": 0, "y": 0, "opacity": 0.5},
        {"file": "art/person.png", "x": 35, "y": 30}
      ],
      "background_top": "#171320",
      "background_bottom": "#292032"
    }
  ]
}
```

```sh
python3 apple-watch/export_photos.py \
  --manifest ./my-project/photos.json --output ./exports/layered
```

每张照片还可覆盖安全区、留白、背景和透明边处理设置。所有图层必须完整处于输入画布内，否则程序报错，避免静默裁切。现有输出默认不覆盖；明确要替换时加 `--overwrite`。一次最多导出 24 张，与官方手动选图上限一致。

输出包含 PNG、`使用说明.txt` 以及 `export-report.json`（导出尺寸与保留区域，不记录输入绝对路径）。不会复制原图 EXIF，也不添加时间和数据。请输入没有旧表盘文字的原画：工具不会自动识别或清除源图已有的时间或数据。

## 手机上导入

1. 将 PNG 保存到已配对 iPhone 的“照片”。
2. Watch App → 表盘图库 → 照片 → 选取照片 → 添加。
3. 在预览中调整时间布局与缩放，尽量保留上方留白。系统自动构图和表壳圆角仍可能影响可见区域。
4. 多图由系统处理点按／抬腕换图；若只要固定图片，就只选一张。

不要把多图误认为确定顺序的状态机；不能保证“每点一次严格在两个状态间往返”。本工具导出的白花图片不能指定为不同于亮屏图的独立 AOD。

官方依据（2026-10-20 核验）：[在 Apple Watch 上自定义“照片”表盘](https://support.apple.com/zh-cn/guide/watch/apd501eb33b3/watchos)介绍最多 24 张手选照片与抬腕／点按换图；[Apple 表盘共享](https://developer.apple.com/documentation/clockkit/sharing-an-apple-watch-face)介绍系统表盘配置的 `.watchface` 共享，不能把任意图片或程序改扩展名冒充该格式。具体界面随系统版本变化。

## 原创示例与测试

公开目录不携带动漫图片、用户图片或本机路径。以下示例是代码绘制的原创几何图形：

```sh
python3 apple-watch/examples/make_example.py
python3 apple-watch/export_photos.py \
  --manifest apple-watch/examples/generated/photos.json \
  --output ./exports/example-photos
python3 -m unittest discover -s apple-watch/tests -v
```

测试覆盖边缘完整保留、尺寸和时钟留白、透明叠合、图层越界拒绝、配置覆盖与报告不泄漏本机路径。代码许可不授予任何导入图像的版权；发布自己的导出成果前，应有相应使用与分发权。
