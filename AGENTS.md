# AGENTS.md

给 AI 和新贡献者的仓库说明。先读 [HANDOVER.md](HANDOVER.md)（现状、发版、签名、待办），再读本文，不必先扫全库。

DeepSeek Harness Android（DSHA）。来源声明与第三方许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 一句话架构

App 把 Ubuntu rootfs 解到应用私有目录，用 proot / proroot 在里面跑 Node 24 + pnpm + `@deepseek-ai/dsh`，再用内置 WebView 打开 dsh 的网页界面。App 本身是宿主：装环境、起停进程、备份恢复，并通过本地 HTTP 桥把 Android 能力交给 agent。

| 端口 | 用途 |
|---|---|
| 3180 | dsh 网页界面（`Constants.DSH_WEB_PORT`，冲突时会换端口，见下文） |
| 3190 | App 能力桥，agent 调 Android 的入口（`HttpShellService`，端口取自 `Constants.SHELL_BRIDGE_PORT`） |
| 3181 | 局域网反向代理（`LanProxyService`） |

这三个数**只在 `util/Constants` 里定义一次**，别处一律引用；容器脚本、内置插件与 agent
提示词都不写死端口，而是读 App 写进 rootfs 的 `/root/.dsh/.bridge_port`。
数值刻意与其它 DSHA 版本（3080 / 3090 / 3081）错开，好让两版同时运行时不抢桥端口。
`python3 tools/test-port-consistency.py` 会检查这套约定。

## 工程概况

- 单 Gradle 模块 `:app`，Java 17 + Kotlin（JVM 目标 17）。包 `com.deepseekharness.app`。
- **主语言正在从 Java 迁到 Kotlin**：约定、雷区、批次和验证方式见 [docs/kotlin-migration.md](docs/kotlin-migration.md)。迁移期间两种后缀并存，任何只认 `.java` 的脚本或过滤器都是漏洞 —— 它们会静默放行，不会报错。
- 发布包名 `zzy.dsha.Kotlin`，由 CI 按 `DSHA_CI_APP_ID` 注入。源码 `applicationId` 仍是 `com.dsh.client` ——
  那是本地/dev 身份，审计脚手架（`tools/device-backup-audit.init.gradle` 的源码改写与 applicationIdSuffix）
  绑着它，不要随手改。代码里需要**当前**包名就用 `BuildConfig.APPLICATION_ID`。
- 两个 flavor 共用功能代码：`standard`（minSdk 30，系统 WebView）和 `low`（minSdk 23，GeckoView 143）。只支持 arm64-v8a。CI 只构建 Standard。
- 内置 dsh 版本在 `util/Constants.DSH_VERSION`（当前 0.2.0-rc.2）。应急运行时单独固定在 0.1.7-rc.2。
- 本机命令行构建和单测：`bash build.sh :app:testStandardDebugUnitTest`。手机容器里没有 Android SDK，以 CI 结果为准。

## 代码在哪

`app/src/main/java/com/deepseekharness/app/` 按包分层：

| 包 | 放什么 | 代表类 |
|---|---|---|
| 根包 | 设备与系统服务 | `HttpShellService`（设备桥）、`DshaAccessibilityService`（读屏 / 点按 / 截屏）、`DeviceBridgeService`（ADB / Shizuku / Root 通道）、`DeviceShellExecutor`、`LanProxyService`、`OverlayController`（悬浮条）、`HarnessService`（前台服务）、`PtySession`、`DshaDocumentsProvider`、`DshaApp` |
| `ui/` | 界面与启动流程 | `MainActivity`、`WelcomeActivity`、各 Fragment、`WebPreviewActivity`、`StartupRecoveryActivity` |
| `core/` | 编排 | `HarnessController`（启停 dsh、捕获鉴权链接）、`ConfigStore`（配置唯一读写入口）、`UpdateEngine`（应用内更新） |
| `runtime/` | 容器 | `ProotBootstrap`（拼 proot 命令）、`ContainerRuntime`、`WebProcessManager`（停止 Web）、`InstallPipeline`、`RuntimeTrial` |
| `backup/` | 数据 | v5 加密备份与恢复、`HostDataTransaction`、`AutomaticBackups`、`FactoryReset` |
| `recovery/` | 独立应急 DSH | `RecoveryController`、`RecoveryRuntime`、`RecoveryRepairBroker` |
| `vscreen/` | 虚拟屏 | `VirtualScreenManager`、`VirtualScreenPreviewView` |
| `bridge/` | 桥接口与 ADB | `AdbBridge`（无线配对）、`LocalNetworkAccess` |
| `data/` | 本机密钥等 | `KeyVault`（Keystore AES/GCM 加密 API key） |
| `util/` | 纯逻辑 | 不 import 任何 Android API，必须有单测 |

几条分层规则：

- `util/` 零 Android 依赖，由 `tools/test-architecture-boundaries.py` 检查；`tools/run-unit-tests.py` 也靠这一点在没有 Android 运行时的环境里跑单测。
- 端口只能在 `util/Constants` 定义一次，由 `tools/test-port-consistency.py` 检查（见上面的端口表）。
- `HarnessController` 已经很大，新逻辑写成独立的协作类，不要继续往里加。
- 设备桥的 `/exec` 与 `/app/*` 端点都要校验 token。
- PTY 和普通容器命令共用 `ProotBootstrap` 的同一套 proot 参数构造，不要另写一份。
- 不要改历史 SharedPreferences 键名（见 `util/Constants`）。

## 本仓库的界面约定

- 只改原生界面时，范围是 `ui/` 和 `res/`。
- `app/src/main/assets/managed-runtime-inputs.json` 里 `launcherSources` 列出的文件和 `runtime/` 目录参与运行时描述哈希，改了就要重新生成运行时描述。
- 风格入口是 `ui/UiStyle.java`。页面、卡片、底栏背景用主题属性 `?attr/dshaPageBackground`、`dshaCardBackground`、`dshaBarBackground`，不要写死 `@color/surface` 或 `@drawable/bg_card`。
- 背景有三种：默认、动态玻璃、自定义图片。非默认时叠加 `ThemeOverlay.DSHA.Translucent`，窗口背景由 `ui/BackdropDrawable.java` 绘制。动态玻璃约 12 fps，不可见、省电或系统关闭动画时停住。Web 工作台、画中画、虚拟屏始终不透明。
- 折叠区用 `ui/Disclosure.java` 的 `bind` / `reveal`。需要用户处理的状态要 `reveal()`，别让错误藏在收起的区域里。
- 弹窗用 `DshaDialogBuilder`，自定义内容要能在短屏和大字体下滚动。
- 改颜色后跑 `python3 tools/test-ui-colors.py`，文字对比度 ≥ 4.5:1。
- 对外地址（仓库、Issues、Releases、更新清单）只写在 `util/ProjectLinks`。
- 应用名 DeepSeek Harness Android，界面里简称 DeepSeek Harness。`Download/DSHA`、日志 tag、协议标记这类内部标识保留旧名。
- 图标用 `tools/prepare-app-icon.py <图片>` 生成。换图标时把资源后缀递增（当前 `ic_launcher_v2`），让桌面刷新缓存。
- 从桌面打开直接进网页：「这次是打开」由 `MainActivity.directWebArmed` 记在实例里（`savedInstanceState` 恢复、`onNewIntent` 重新武装），四条路径——冷启动、进程被回收后重建、回前台、`ExtractActivity` 准备完环境回主界面——都交给 `LaunchFragment.requestDirectWeb()` 走同一段实现（幂等）；进了网页、点「留在主界面」或放弃重试才调 `onDirectWebFinished()` 清掉。`StartupSplash` 盖住启动页，失败或取消时撤掉并显示原因。网页里回主界面走 `PictureInPictureActivity.leavePreview()` / `leavePreviewTo("open_settings")`。
- 网页增强脚本在 `ui/WebPageScripts.java`，网页悬浮按钮在 `ui/WebHomeHandle.java`。

## 内置网页插件

内置插件在 `app/src/main/assets/builtin-plugins/`。

- dsha-mobile（zzy.8 起 0.2.0）：手机专属网页界面，zzy.7 起内置并默认启用。源码 <https://github.com/zzy89216-gif/dsha-mobile>，随包副本在 `app/src/main/assets/builtin-plugins/dsha-mobile/`。改完要同步回源码仓库并跑那边的 `node --test test/client.test.mjs`。抽屉里的会话行必须直接打开会话：宿主是「单击=选中、双击=打开」（`DSHA_SESSION_INTERACTION_V2`），抽屉若在第一次单击就收起，历史对话就永远进不去。
- dsh-web-mobile 3.0.3：源码固定在 `a094288883b343e848d7f9cf302d73ad8ed4794b`，本地改动用 `tools/apply-mobile-client-patches.mjs` 管理（`tools/test-mobile-update.mjs` 会检查这个提交号）。zzy.7 起保留但升级和新装后默认停用一次，用户手动启用后保持启用。

## 安全边界

详见 [docs/security-model.md](docs/security-model.md)。写代码和写文档都按这些边界来：

- 设备命令走 `util/DeviceShellPolicy` 白名单，默认拒绝。只接受能完整识别的单条 argv；格式化、分区、SELinux、系统属性写入一律拒绝。被拦截时返回 `[POLICY_BLOCKED]` 和 `[EXIT=126]`，没有「仍然允许」的出口。Root、Shizuku、ADB 三个通道用同一套策略。
- `/app/export`、`/app/readfile` 由 `util/BridgePathPolicy` 拒绝凭据目录（`/root/.dsh`、`.ssh`、`.android`、云凭据等），字符串判断之外再用 `getCanonicalPath()` 复核，防软链接绕过。
- ADB、Root、短信、传感器、位置、悬浮窗、LAN 等敏感能力默认关闭，可以撤销。不开它们，dsh 也能正常跑。
- 短信只允许当前 Android 用户的 `content query`，不能发送、修改或删除。
- 这不是内核级沙箱：容器、插件和终端都以 App 的 Android UID 运行。白名单只约束随包入口，不约束任意自写代码。文档里不要写「安全隔离」。
- 已知弱点写在安全模型文档里，不要删。

## 不能改坏的行为

### 启动

- `welcomed` 为 false 时先进 `WelcomeActivity`；`MainActivity` 每次进入都检查它。
- 环境就绪要看 `.offline-extracted` 和完整的环境身份。维护页可以进入受限主界面看配置和日志，但不能借此伪造就绪标记；终端、Web 和插件仍要过环境门禁。
- dsh 启动命令是 `dsh web --no-open --host 127.0.0.1 --port <端口>`，环境变量含 `DSH_HOME=/root/.dsh`、`DSH_PERMISSION_MODE`、`DSH_CONFIRM`、`BROWSER=true`（见 `HarnessController`）。
- proot 从 `nativeLibraryDir/libproot.so` 执行；Android 10+ 的 W^X 限制不允许从 filesDir 执行。
- 部分机型的应用私有目录不支持硬链接：`ContainerRuntime` 探测到这种情况才给 proot 加 `--link2symlink`，并映射好 `PROOT_L2S_DIR`；恢复运行时始终带它。
- 启动后等待鉴权本身不算故障：60 秒只提示变慢，不强制终止。启动失败进入 `StartupRecoveryActivity`。
- 首选端口被占用时保留用户配置，改用其他端口；保活、鉴权和 LAN 都要用实际端口。
- proroot 在鉴权前确认退出、且没有明确的插件故障时，可以按 `util/WebRuntimeFallback` 用 proot 重试一次。超时不能触发重试；proot 成功不能报告成 proroot 成功。
- 系统语言要在进程最早的时候锁存（`DshaApp` 里调用 `SystemLanguage.initialize()`），否则「跟随系统」切换一次就失效。语言偏好只有 `system`（默认）、`zh`、`en`，文案在 `tools/i18n/messages.json`。

### 停止进程

- 停止靠 pid 文件和出生身份核验（`WebProcessManager`、`util/WebProcSel`），不靠端口反查：非 root 读不到 `/proc/net/tcp`，`/proc` 也有 hidepid。
- 停止前写哨兵 `/root/.dsha-stopped`，看门狗看到就退出，否则进程会被立刻拉起。
- 绝不能误杀 proot / proroot，那会把整个环境连 App 一起带走。不按裸 PID、端口或进程名强杀。
- 数据维护前先关 PTY 和简易终端，再拿 `RuntimeTasks` 屏障。

### 数据与备份

- 部分备份的文件名绝不能以 `DSHA-backup-` 开头：老版本会把它当全量备份恢复，清掉配置和插件（`util/BackupScope`）。
- 宿主备份文件名是 `DSHA-data-v5-<UUID>.dshbak`，加密归档，先完整认证再预检恢复。
- 桥 token 不进备份。
- 自动备份默认开启，支持每天定时、1–168 小时间隔、停止后备份三种模式（`util/AutomaticBackupPolicy`），只保留最近 3 份自动副本。
- 受管运行时试运行记录保留最近 3 条成功、5 条失败（`RuntimeTrialRecords`）。
- 系统插件源码不进用户备份，由当前 APK 重建；插件启用状态与旧实体冲突时，以禁用为准。

### 虚拟屏与设备

- 虚拟屏的每次输入必须带最新帧号（`util/VirtualScreenPolicy.fresh`），动作失败不能换通道重放。
- Shizuku：清单注册 `rikka.shizuku.ShizukuProvider`；Standard 用 13.1.5，Low 用 12.2.0。
- 麦克风：清单声明 `RECORD_AUDIO` 和 `MODIFY_AUDIO_SETTINGS`，由 `ui/BrowserMicrophone` 在网页请求时才申请，不预授权。
- 设备桥用 `/app/version` 报告 `BRIDGE_PROTOCOL`（当前 2）。插件判断版本用 `>=`。

## 单测

测试在 `app/src/test/java/com/deepseekharness/app/`，大部分在 `util/` 和 `backup/`。这些测试守着上面的关键行为，重构时不能让它们失败：

- `ShellQuoteTest`：POSIX 单引号转义，恶意值逃不出去。
- `QueryTest`：按参数名精确匹配；「参数为空」和「参数不存在」是两回事。
- `BackupScopeTest`：部分备份命名规则。
- `WebProcSelTest`：认出 dsh 进程，不误判 proot / proroot。
- `DeviceShellPolicyTest`：白名单默认拒绝。
- `HttpProtocolTest`、`SocketDispatchTest`：请求头和总时长各自有上限，连接数有界。

本机（没有可用的 aapt2 时）用 `python3 tools/run-unit-tests.py` 编译并跑这些测试，它同时认 `.java` 和 `.kt`；`DSHA_ONLY=ShellQuoteTest` 可以只跑指定的几个。

`tools/` 下还有一批 Python / Node 检查脚本，哪些能在 CI 或容器里跑见 [HANDOVER.md](HANDOVER.md) 第 8 节。

## 提交与发版

- 注释和界面文案用中文；提交信息用中文，带 `type:` 前缀（如 `fix:`、`feat:`、`docs:`）。
- 版本变化写进 [CHANGELOG.md](CHANGELOG.md)，发行说明写进 `.github/RELEASE_NOTES.md`（发版工作流会读取它）。
- 发版：在 Actions 手动运行 Build APK 并勾选 publish，流程见 [HANDOVER.md](HANDOVER.md) 第 2 节和 [BUILD.md](BUILD.md) 第 9 节。

## 其他文档

| 文档 | 内容 |
|---|---|
| [HANDOVER.md](HANDOVER.md) | 现状、发版、签名、已知问题、待办 |
| [BUILD.md](BUILD.md) | 构建环境、打包与云端构建 |
| [docs/security-model.md](docs/security-model.md) | 安全模型与已知弱点 |
| [docs/plugins.md](docs/plugins.md) | 插件安装与打包约定 |
| [docs/android-low.md](docs/android-low.md) | Low 版的兼容差异 |
| [docs/repo-migration.md](docs/repo-migration.md) | 仓库迁移记录：为什么以全新历史起步、哪些保留了 |
| [docs/maintenance.md](docs/maintenance.md) | **维护手册**：单一事实源、改一处要连带改哪些、本机验证、重生成运行时描述、发版与排障 |
| [docs/kotlin-migration.md](docs/kotlin-migration.md) | Java → Kotlin 迁移约定、雷区、批次与验证 |
| [docs/接手指南.md](docs/接手指南.md) | 设计背景与踩坑记录 |
| [CHANGELOG.md](CHANGELOG.md) | 更新记录 |
