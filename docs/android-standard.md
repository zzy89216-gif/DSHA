# Android 11+ 标准版（standard）

standard 是 CI 发布的唯一 flavor。源码 `applicationId` 是 `com.dsh.client`，发行包由 CI 改成 `zzy.dsha.Kotlin`。旧系统见 [low 兼容版](android-low.md)。APK 在仓库 Releases 页。

| 项 | 值 |
|---|---|
| flavor | `standard` |
| minSdk | 30（Android 11） |
| compileSdk / targetSdk | 37（Android 17） |
| ABI | 仅 arm64-v8a |
| 网页内核 | 系统 WebView，不带 Gecko |
| 离线环境 | 随 APK：Ubuntu 基底、Node/dsh、pnpm、Python 补充库、ADB wheels |
| 本地源码版本 | `0.1.7-rc2` / versionCode 147；发行版由 CI 注入 |

## 离线资产怎么变小

`app/src/main/assets/offline-rootfs.bin` 保持原字节。构建时 `prepareStandardAssets` 生成 `app/build/generated/standardAssets`，按输入和脚本的 SHA-256 缓存。减重规则在 `tools/prepare-standard-assets.py`，报告在 `app/build/generated/standard-assets-report.json`。不要手改生成目录。

当前做法：

- 去掉预装 npm 缓存、非 Linux arm64 二进制、重复的 Termux Python。
- 容器内用 Ubuntu Python；ADB 的 Python wheels 保留。
- 压缩资产用 `.bin` 扩展名，避免 aapt 提前解 gzip。
- 不把 `runtime-python/` 打进 APK。
- 环境版本写在 `app/src/main/assets/offline-rootfs.version`（当前 10）。只压缩减重不要改这个数字，否则会清空旧用户 rootfs。

rootfs 仍占 APK 的大部分。再压体积需要改成首次联网下载，或把 ADB 依赖改成按需下载，那会丢掉离线可用范围，当前没做。提高最低 Android 版本对这块体积帮助很小。

Python 补充库和 pnpm 作为小型离线资产随源码提供。重新生成：`python tools/build-standard-runtime.py`（需要 bsdtar）。

## 新系统相关行为

- Android 17 局域网权限：`ACCESS_LOCAL_NETWORK`。LAN 或无线 ADB 需要它；拒绝后本机回环对话仍可用（`bridge/LocalNetworkAccess`）。
- 前台服务：`HarnessService` 是 `specialUse|connectedDevice`（用户启动的本地开发服务器）；无线 ADB 用 `DeviceBridgeService` 的 `connectedDevice`。系统拒绝启动时退出服务或提示回到前台，不在没有通知的情况下继续跑。下载和备份仍用 `dataSync`。
- 全面屏：状态栏、挖孔、导航栏、键盘边距走 WindowInsets，避免提高 targetSdk 后页面被系统区域挡住。
- 16 KB 页：Termux JNI 已按 16 KB LOAD 对齐。可用 `python tools/audit-standard-apk.py <apk>` 检查 APK 内宿主和容器 ELF，这是静态检查。

## 签名与覆盖安装

debug 包是本机调试证书，不能覆盖 CI 发布包。发行包由本仓库 CI 密钥签名（见 [BUILD.md](../BUILD.md) 第 4、9 节）。不要为了装调试包卸载带用户数据的正式版。

参考：[局域网权限](https://developer.android.com/privacy-and-security/local-network-permission)、[前台服务类型](https://developer.android.com/develop/background-work/services/fgs/service-types)、[16 KB 页大小](https://developer.android.com/guide/practices/page-sizes)、[AGP 9.1](https://developer.android.com/build/releases/agp-9-1-0-release-notes)。
