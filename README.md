# DeepSeek Harness Android

<p align="center">
  <b>在安卓手机上运行 <a href="https://github.com/deepseek-ai/deepseek-harness">deepseek-harness</a> 的启动器</b><br>
  一个 APK，内置 Ubuntu 环境；不需要 Root，也不需要 Termux
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT"></a>
  <a href="https://github.com/zzy89216-gif/DSHA/releases/latest"><img src="https://img.shields.io/github/v/release/zzy89216-gif/DSHA?sort=date&color=blue" alt="release"></a>
  <a href="https://github.com/zzy89216-gif/DSHA/actions/workflows/build-apk.yml"><img src="https://github.com/zzy89216-gif/DSHA/actions/workflows/build-apk.yml/badge.svg" alt="build"></a>
  <img src="https://img.shields.io/badge/Android-11%2B-3DDC84?logo=android&logoColor=white" alt="android">
  <img src="https://img.shields.io/badge/arch-arm64--v8a-lightgrey" alt="arch">
</p>

<p align="center">
  <a href="README.en.md">English</a> · <b>简体中文</b> · <a href="CHANGELOG.md">更新记录</a> · <a href="docs/security-model.md">安全模型</a> · <a href="AGENTS.md">AGENTS.md</a>
</p>

> AI 或新贡献者：先读 [AGENTS.md](AGENTS.md)，里面有目录结构、启动流程和已知的坑，不必先扫全库。

DeepSeek Harness（`@deepseek-ai/dsh`）是 DeepSeek 的 agent 工具，原本面向 glibc Linux。本 App 把一个 Ubuntu 24.04 arm64 环境、Node.js、pnpm 和 dsh 一起打进 APK，在 proroot / proot 容器里运行 dsh，再用内置 WebView 打开它的网页界面。

本仓库独立维护。这是社区项目，与 DeepSeek 官方无关；「DeepSeek」商标归其所有者。
来源声明与第三方组件的许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 安装

从 [Releases](https://github.com/zzy89216-gif/DSHA/releases/latest) 下载 APK，每个 APK 旁边有对应的 `.sha256`。

- 包名 `zzy.dsha.Kotlin`。它与其它 DSHA 版本（`zzy.dsha.com`、`com.dsh.client`）包名与签名都不同，
  不能互相覆盖，但可以同时装着，数据互不影响。
- 发行版只提供 Standard 版：Android 11+，arm64-v8a。支持 Android 6+ 的 Low 版（GeckoView 内核）需要自己构建，见 [BUILD.md](BUILD.md)。
- zzy.4 起可以在「设置 → 版本更新」里直接升级；它读取本仓库最新正式版附带的 `updates.json`。

第一次使用：

1. 打开 App，等它解压内置环境（只需一次，要几分钟）。
2. 在「配置」页填 DeepSeek API key（也可以先跳过）。
3. 回「启动」页点启动，就绪后自动进入网页。

之后从桌面打开会显示加载页、自动启动并直接进入网页：冷启动会等环境就绪，不会提前退回主界面；进程被系统回收后重建、从后台回到前台，或覆盖更新后先准备环境再回主界面，也都算一次「打开」，同样会进网页。不想自动进入，可以在设置里关掉「打开直接进入网页」。网页右侧的小圆按钮用来回到主界面或设置，可以拖动，也可以在设置里隐藏。

## 主要功能

环境与运行

- 离线 rootfs：无网也能完成部署。安装分步骤进行（解压、基础工具、Node.js、pnpm、dsh、补丁），每步可以单独重装，修复时只处理失败项。
- 当前内置 dsh 0.2.0-rc.2，构建时按 `tools/dsh-runtime` 的锁文件重建并校验补丁；应急运行时单独固定在 0.1.7-rc.2。
- 默认用 proroot（LD_PRELOAD 做路径翻译，不走 ptrace），可在「配置」页切回 proot；proroot 起不来时自动回退。
- 前台服务加看门狗，Web 进程退出后会自动拉起。
- 环境更新先在隔离目录试启动，通过后再切换，失败回到原环境。

数据与备份

- 会话、设置和附件放在 `内部存储/Documents/dshdata`，卸载重装后还在（需要授予「所有文件访问」，否则留在私有目录）。
- API key 用 Android Keystore（AES/GCM）加密保存。
- `.dshbak` 加密备份：可按全量、对话、插件、设置分别备份和恢复；支持定时自动备份，保留最近几份已验证的副本。格式见 [backup-format-v5.md](docs/backup-format-v5.md)。
- 损坏的会话文件会移到 `corrupt-backup`，不会让整个网页起不来。

设备能力（给 agent 用）

agent 通过本机设备桥（端口见 `/root/.dsh/.bridge_port`，默认 3190）调用设备能力，需要 token，`/app/help` 列出全部端点。

- 无障碍：读屏、点按、输入、滑动、按键、截屏，不需要 ADB。
- 虚拟屏（实验，Standard 版）：在独立虚拟屏里启动应用并操作。
- 设备命令：内置无线 ADB 配对与保活，也可以用 Shizuku 或 Root。三个通道走同一套命令白名单，拦截时返回 `[POLICY_BLOCKED]`。
- 其他：通知、震动、弹窗提问、剪贴板、分享、导出文件到 `Download/DSHA`、传感器与定位（默认关闭，逐项授权）。
- 短信只读查询是单独的敏感授权，默认每次确认。

界面与访问

- Standard 版用系统 WebView，Low 版用内置 GeckoView 143。
- 内置网页插件 dsha-mobile 提供手机界面，见下面「内置插件」。
- 画中画小窗、流式悬浮条（需要悬浮窗权限）、深浅色、简体中文 / English。
- 局域网访问：电脑或平板的浏览器通过局域网代理端口（默认 3181）使用手机上的 dsh，按 token 鉴权。
- 原生界面背景可选默认、动态玻璃、自定义图片（设置 → 使用体验 → 背景）；动态玻璃默认关闭。

终端

- 基于 Termux terminal-emulator 的 PTY 终端，支持 vim、htop、tmux 等全屏程序；有扩展键行和多标签。

插件

- 在「插件」页安装、更新、启停、删除、导入导出。支持 GitHub 链接、HTTPS 压缩包、本地文件和终端 `dsha-plugin install`，详见 [docs/plugins.md](docs/plugins.md)。
- 第三方插件装完先保持停用，审阅后才启用；安装依赖时不执行生命周期脚本。

故障处理

- 「安装与修复」页检查各组件并按需修复；诊断报告可以导出。
- 启动或插件出错会进入恢复页；安全启动只加载官方组件，原配置保留。
- 正式环境坏掉时可以进入独立的应急 DSH 做诊断和修复。

## 内置插件

| 插件 | 作用 | 默认 |
|---|---|---|
| `dsha-mobile` | 手机专属网页界面（0.2.0）：底部标签栏（对话 / 会话 / 新建 / 设置），侧栏改为抽屉，点会话行直接进那个会话，设置面板全屏，键盘弹出时底栏让开；在「设置 → 通用设置」增加手机模式、动态玻璃、配色三项。源码 [zzy89216-gif/dsha-mobile](https://github.com/zzy89216-gif/dsha-mobile) | 启用 |
| `dsh-web-mobile` | 旧的移动端适配（[mexiaosqwq/dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile)，MIT） | 停用 |
| `dsh-status-overlay` | 流式悬浮条 | 启用 |
| `dsh-task-notifier` | 回合完成通知 | 启用 |
| `dsh-device-shell-guide` | 设备能力引导 | 启用 |
| `dsh-computer-use-android` | Android Computer Use | 启用 |
| `dsh-tool-vscreen` | 虚拟屏工具 | 启用 |
| `dsh-auto-review` | 官方实验性 Auto review 入口 | 启用 |

dsh-web-mobile 仍随包提供，不会被删除。升级到或新装 v0.1.7-rc2-zzy.7 后它会被停用一次；之后手动重新启用，它会一直保持启用。内置插件不能删除，用户停用过的插件升级后保持停用。

## 配置无线 ADB

配好后 agent 能执行设备命令，不需要 Shizuku。无线调试配对需要 Android 11+。

1. 打开开发者选项（「关于手机」里连点版本号）。
2. 开启「无线调试」，进入「使用配对码配对设备」，记下 IP:端口和 6 位配对码。
3. 在 App 的「设备能力授权」页填入并配对。

配对后 App 会自己保活和重连，重启手机后也会恢复。在内置终端执行 `adb shell id`，看到 `uid=2000(shell)` 就说明可用。

需要让 agent 掌握用法，可以把仓库里的技能包复制到 agent 的技能目录：

```bash
cp -r agent-skills/device-shell ~/.agents/skills/
cp -r agent-skills/screen-ocr-operator ~/.agents/skills/
```

`device-shell` 说明三种命令通道的用法；`screen-ocr-operator` 用截屏加 OCR 处理无障碍读不到内容的画面。

## 安全

不授予任何额外权限也能正常使用 dsh；每项设备能力默认关闭，可以随时撤销。App 不上传日志或使用数据。

要注意的一点：Android 不允许非特权用户命名空间，bubblewrap 用不了，所以 bash 工具没有沙箱隔离。约束只靠 dsh 的权限档位，默认 `danger-full-access`，可以在「配置」页改成 `workspace-write` 或 `read-only`。

各项权限的边界和已知弱点见 [安全模型](docs/security-model.md)。

## 已知限制

- 只支持 arm64-v8a。
- 「ADB 配对后自动授予无线调试保活」在 `zzy.dsha.Kotlin` 包名下不生效。
- 与其它 DSHA 版本同时运行时会抢设备桥端口。本 App 的默认端口与它们错开（设备桥 3190），
  所以正常情况下两版可以并行跑；如果你把端口改成与另一版相同，后启动的一方设备工具会不可用（网页不受影响）。
- 悬浮条需要悬浮窗权限。
- 没有「所有文件访问」权限时，数据留在私有目录，卸载即丢。

## 构建

需要 JDK 17、Android SDK、NDK 26 和 Python 3.9+，完整步骤见 [BUILD.md](BUILD.md)。
主语言正在从 Java 迁到 Kotlin，约定与雷区见 [docs/kotlin-migration.md](docs/kotlin-migration.md)。

```bash
bash build.sh                                # Standard Debug
bash build.sh :app:assembleLowRelease        # Low Release
bash build.sh :app:testStandardDebugUnitTest # 单元测试
python tools/verify-stability.py             # 稳定性验收
```

离线 rootfs 不进 Git。发行版由 GitHub Actions 构建，离线资产取自本仓库的 `runtime-assets` 发行版。

## 文档

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | 项目结构、启动流程、约束与踩坑记录 |
| [BUILD.md](BUILD.md) | 本地构建、签名、云端构建与发版 |
| [HANDOVER.md](HANDOVER.md) | 交接日志：现状、发版流程、密钥、待办 |
| [CHANGELOG.md](CHANGELOG.md) | 更新记录 |
| [docs/plugins.md](docs/plugins.md) | 插件安装与打包要求 |
| [docs/security-model.md](docs/security-model.md) | 安全模型（[英文](docs/security-model.en.md)） |
| [docs/android-standard.md](docs/android-standard.md) / [docs/android-low.md](docs/android-low.md) | 两个版本的适配说明 |
| [docs/repo-migration.md](docs/repo-migration.md) | 仓库迁移记录（全新历史的原因与保留项） |
| [docs/maintenance.md](docs/maintenance.md) | 维护手册：单一事实源、验证命令、发版与排障 |
| [docs/kotlin-migration.md](docs/kotlin-migration.md) | Java → Kotlin 迁移约定、雷区、批次与验证 |
| [docs/接手指南.md](docs/接手指南.md) | 写给不做安卓开发的接手者 |

## 致谢

- [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)
- [proot](https://github.com/termux/proot)、[proroot](https://github.com/coderredlab/proroot)
- [Termux terminal-view / terminal-emulator](https://github.com/termux/termux-app)（Apache-2.0）
- [dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile)（MIT）
- [Shizuku](https://shizuku.rikka.app/)

第三方组件及其许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 反馈与许可

问题和建议请提到 [Issues](https://github.com/zzy89216-gif/DSHA/issues)。本项目采用 [MIT](LICENSE) 许可。
