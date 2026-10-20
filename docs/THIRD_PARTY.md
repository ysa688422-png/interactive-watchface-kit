# Third-party components and artwork

The repository's MIT license applies to its original code and documentation. It
does not relicense third-party software, fonts, characters, or imported images.
Asset ownership and redistribution permission must be checked separately.

## External Xiaomi packer

`scripts/pack_xiaomi.py` is an adapter. The user must explicitly supply
`--packer PATH` to a compatible executable or wrapper accepting:

```text
packer pack PROJECT_DIRECTORY OUTPUT.bin n67
```

It does not download a tool, select one from PATH, or implement a new binary
encoder. It validates the project before invoking that executable, writes into a
temporary directory, and independently checks the resulting package before
publishing the output. It supports the kit's limited n67 profile: one ordinary
Lua face and one static native AOD face with hour/minute digit widgets.
Validation is not proof of installation, firmware compatibility or power use.
The wrapper must run its compiler in the foreground and must not start a daemon.

The development environment used
[zhy8388608/Mi8WfBinTool](https://github.com/zhy8388608/Mi8WfBinTool), at revision
`5e4195ce91b9d8810a7a2233c96b4cba44184adc`, with local compatibility changes.
That checked revision contained no license file or README license grant; the
repository API also reported no detected license when checked on 2026-10-20.
Its Java source, compiled classes, JDK, and upstream-code-containing patches are
therefore **not distributed by this kit**. A public GitHub repository is not,
by itself, an MIT permission grant. See
[GitHub's licensing explanation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

A compatible packer must write native AOD flag `0x04` at header offset `0x1E`
and native left-aligned clock digits (`align=1`). This kit rejects packages
with the earlier incorrect flag or alignment. The format rule was cross-checked
against the original
[DefaultPacker source](https://github.com/RedKage/Xiaomi_Band_Tools/blob/f413b3453093d68a34155c54cf14092bd84f23f9/Compiler/MiWatchCompiler.Packers/DefaultPacker.cs).
That reference source is not included or relicensed here.

## Public runtime and test dependencies

- [Lua](https://www.lua.org/license.html) uses the MIT license, with the Lua.org
  and PUC-Rio copyright notice. Install a Lua interpreter separately; this kit
  does not vendor the local development interpreter. Lua is needed for the
  optional host-side runtime tests.
- [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) has its own
  license notices. It is the public Python tools' declared image-processing
  dependency, not code relicensed by this project.

The public generator draws its own geometric heart, footprint, flower, avatar,
and seven-segment clock examples in `scripts/create_project.py`. Those generated
examples are original project code-drawn artwork under MIT. It does not copy
Lucide paths or embed system font files.

The independent host-side Lua test double is project code, not a bundled LVGL
or Xiaomi firmware implementation. It can exercise logic but cannot establish
actual rendering, Bluetooth behavior, sensor behavior, or device compatibility.

## Private development tools not bundled

The earlier private artwork workflow used
[Lucide](https://github.com/lucide-icons/lucide/blob/main/LICENSE) icons (ISC,
with additional notices for Feather-derived icons),
[Playwright](https://github.com/microsoft/playwright/blob/main/LICENSE)
(Apache-2.0), and
[sharp](https://github.com/lovell/sharp/blob/main/LICENSE) (Apache-2.0).
Their packages, icons, browser binaries, and private rendered outputs are not
included in this public kit and are not required by its published generator.
These historical dependencies do not change the public code-drawn examples'
license. If adding third-party icons or font files later, retain their own
applicable permission and attribution notices.

## Reference projects not redistributed

- [LeeKLong/Lua_MiBand9Pro](https://github.com/LeeKLong/Lua_MiBand9Pro/blob/81d4ae38b46e70a766baebff2324acab19bcddcc/LICENSE):
  AGPL-3.0.
- [AstroBox Core](https://github.com/AstralSightStudios/AstroBox-NG-Module-Core/blob/2fcea036f2f7fa2e594782ddf9970b995ff233f8/LICENSE):
  AGPL-3.0.
- [m0tral/MiWatchLuaWatchfaces](https://github.com/m0tral/MiWatchLuaWatchfaces):
  no license found at the reference revision
  `5af6e14ea92830a394c88dc04f76ceef697a6ded`.
- [sf-yuzifu/daymatter](https://github.com/sf-yuzifu/daymatter): its default
  quickapp branch declares GPL-3.0, while the consulted watchface revision
  `daa731e335380dad4cc13b99f2b2af3a0acb99b8` did not carry a license file.

Their source trees, firmware extracts, and example watchface packages are not
part of this kit.

## Character art and personal builds

The original private project used user-supplied anime references and derived
character illustrations. No transferable open-source permission for those
illustrations or underlying characters was established. The code's MIT license
does not cover them. Do not assume that AI editing, noncommercial use, or a
personal-use source image creates redistribution permission.

Public examples should use the included generic placeholders or images you
are authorized to redistribute. Keep imported personal art and resulting
private packages outside the public repository. A self-contained HTML preview,
an exported PNG, and a compiled watchface package can all embed that art even
when the source-art folder itself is excluded.
