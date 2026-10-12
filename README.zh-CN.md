# DayMirth Journey Forge

[English](README.md) | [简体中文](README.zh-CN.md)

**只需一次 Codex 对话，把确认好的行程制作成精致、可安装的手机旅行助手。**

DayMirth Journey Forge 是一个开源 Codex Skill，可将每日路线、地图导航、门票、打卡、备注、提醒和离线记录整合为 Android App 或可添加到 iPhone 主屏幕的 PWA。

> 本 Skill 在电脑端 Codex/Agent 中执行。手机使用的是最终生成的 App，而不是在手机上运行 Skill。

<p align="center">
  <img src="assets/readme/showcase-final.png" alt="DayMirth 成品旅行 App 脱敏展示，无遮挡显示已完成打卡、门票入口、日期、路线、导航和备注等双语功能说明" width="100%">
</p>

<p align="center"><em>展示图来自成品 App；日期、时间和同行信息均已移除或替换，不展示门票文件、二维码或预约凭证。</em></p>

## 可以制作什么

- 每日时间线、按访问顺序显示的地图和一键外部导航。
- PDF/JPG/PNG 票据；人数、文件和页数均为动态列表，不设固定槽位。
- 可持久保存的打卡、文字备注、每个事件最多六张备注图片及 JSON 备份恢复。
- 预约与注意事项提醒、缺失数据降级布局、相互隔离的离线记录。
- 主动搜索带许可记录的景点实景图；使用者明确提供的图片始终优先。
- 先完成完整交互预览并确认，再打包 Android/PWA，同时生成对应手机使用说明。

地图连线表示游览顺序，不代表实时路况或最短路线。地图瓦片和外部导航需要网络。

## 60 秒安装

电脑需要安装 Codex、Git 和 Python 3.9 或更高版本。

### Windows PowerShell

```powershell
$skillDir = Join-Path $env:USERPROFILE ".codex\skills\daymirth-journey-forge"
git clone https://github.com/kskbl-0714/daymirth-journey-forge.git $skillDir
python -m pip install -r (Join-Path $skillDir "requirements.txt")
```

### macOS / Linux

```bash
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills/daymirth-journey-forge"
git clone https://github.com/kskbl-0714/daymirth-journey-forge.git "$skill_dir"
python3 -m pip install -r "$skill_dir/requirements.txt"
```

也可以下载仓库 ZIP，将其中的 `daymirth-journey-forge` 文件夹直接放进 Codex 的 `skills` 目录。安装后重新启动或刷新 Codex。

## 如何调用

使用 `$daymirth-journey-forge` 明确调用；同时也支持 Codex 自动发现。

```text
使用 $daymirth-journey-forge，把我已经确认的行程制作成 Android 旅行 App。
使用我在当前对话中提供的门票和图片，打包前先展示完整预览。
```

最好先确认每日行程、景点顺序、交通方式及已购票的预约时间。Skill 会复用当前对话，先汇总已知信息，再一次性询问真正影响成品的缺项；可选信息不提供时也有替代方案。

```text
行程和门票 -> 确认关键选择 -> 搜索/匹配图片
-> 完整初版预览 -> 集中反馈一次 -> 验证 -> 打包
```

## 需要提供什么

| 项目 | 最好提供 | 不提供时的方案 |
|---|---|---|
| 行程 | 目的地、日期、景点顺序、固定预约时间 | 至少提供目的地或旅行意图；未定日期按 Day 1/2，未定时间按时段/顺序 |
| 手机平台 | Android、iPhone 或两者 | 交付经过验证的 PWA，并在工具链可用时尝试 Android 版本 |
| 地图/导航 | 内嵌地图和外部导航偏好 | OpenStreetMap 加手机系统选择 |
| App 名称 | 中文或英文名称 | `TripPocket` |
| 门票 | PDF/JPG/PNG 及旅客/事件关联 | 隐藏对应票据入口，或在生成的 App 中本地导入 |
| 封面/景点图 | 使用者指定图片优先 | 先搜索可复用实景图；找不到时说明，并使用补图、明确标注的情境插画或无图布局 |
| 每日趣味图 | 图片池或明确映射 | 询问使用 AI 生成还是移除该区域 |

主题色和副标题自动生成，不会作为额外问题；预览确认阶段明确提出的修改仍然优先。

## 不同手机的产物

| 平台 | 默认产物 | 条件与边界 |
|---|---|---|
| Android | 源码、签名 APK、SHA-256 和验证报告 | APK 打包需要 JDK 17、Android SDK 35 与 build-tools 35.0.0 |
| iPhone | 可添加到主屏幕的 HTTPS PWA | 需要 Safari 和 HTTPS 托管；它不是 IPA |
| 原生 iOS | 有条件的 IPA/原生工程 | 需要 macOS、Xcode、描述文件和 Apple 签名；不会承诺在 Windows 直接生成 |

如果本机缺少原生工具链，Skill 仍会交付验证过的 PWA、原生源码、诊断信息和准确续建命令，不会把尚未生成的 APK/IPA 标为完成。

## 运行虚构演示

```powershell
python scripts/create_demo_assets.py
python scripts/validate_trip.py examples/fictional-trip/trip.json --assets-root examples/fictional-trip
python scripts/build_app.py examples/fictional-trip/trip.json --input-root examples/fictional-trip --output ../daymirth-demo --embed-private-tickets
python scripts/verify_output.py ../daymirth-demo/web
python -m http.server 8000 --directory ../daymirth-demo/web
```

打开 `http://localhost:8000`。演示行程和旅客均为虚构，图片为原创可再分发素材，演示票据明确标为无效。

Android 打包依赖、无需 Gradle 的直接 SDK 方案和正式签名方式见 [references/platforms.md](references/platforms.md)。

## 验证与隐私

```powershell
python scripts/self_test.py
python scripts/public_release_check.py .
```

测试覆盖任意人数/票据数量、私人票据排除、文件路径与 HTML 边界、最简输入、稳定 ID 和生成结果完整性。GitHub Actions 会在每次 push 和 pull request 时运行可移植校验。

不要提交真实门票、二维码、旅客资料、私人照片、签名密钥或私人构建结果。APK 资源可以被提取，公开托管的 PWA 也不是私人存储。私人输入和输出必须放在仓库外，并在发布前人工检查。

Leaflet、PDF.js、OpenStreetMap 数据及搜索所得旅行图片各自保留原许可证和署名要求。原创代码、模板和虚构演示图片使用 MIT 许可证。

## 仓库结构

```text
SKILL.md                 Skill 入口与决策规则
agents/openai.yaml       Codex 展示信息和调用策略
assets/                  Web/Android 模板与 README 截图
examples/fictional-trip  可公开再分发的虚构演示
references/              工作流、数据结构、媒体隐私和平台说明
scripts/                 校验、生成、APK 构建和发布打包工具
```

## 打包公开版本

```powershell
python scripts/public_release_check.py .
python scripts/package_skill.py ../outputs/daymirth-journey-forge-github.zip
```

ZIP 会排除缓存、私人输出、APK 和签名材料，检查自身完整性并生成 SHA-256 文件。脚本不会创建或推送远程 GitHub 仓库。

## 许可证

MIT。详见 [LICENSE](LICENSE) 及 `assets/web/vendor` 中的第三方许可证。
