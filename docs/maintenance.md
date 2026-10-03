# 维护手册

给长期维护者（和接手的人/AI）用。目标只有一句话：**让"改一处忘了另一处"这种错误尽可能变成可执行的检查，而不是靠记性。**

## 1. 单一事实源

这些东西只在一个地方定义，别处一律引用。每一条都有对应的检查脚本，改错了会失败。

| 事实 | 唯一定义处 | 检查 |
|---|---|---|
| 端口（网页 / 设备桥 / LAN） | `util/Constants.kt` | `python3 -B tools/test-port-consistency.py` |
| 对外地址（仓库 / Issues / Releases / 更新清单） | `util/ProjectLinks.kt` | 人工（只在界面里读它） |
| 发布包名 | CI 的 `DSHA_CI_APP_ID`（`.github/workflows/build-apk.yml`） | 工作流用 `aapt2` 核对 |
| 源码身份（本地/dev 包名） | `app/build.gradle` 的 `applicationId` | 审计脚手架依赖它，见 §3 |
| 签名证书指纹 | 密钥库本身 + `app/build.gradle` / `tools/release_acceptance.py` / `tools/verify-stability.py` / 文档 | `tools/test-release-acceptance.py`、`tools/test-release-evidence.py` |
| 内置 dsh 版本 | `tools/dsh-runtime/package.json` + `util/Constants.DSH_VERSION` | `tools/test-dsh-patch-anchors.py`（锚点必须全命中） |
| 运行时身份输入 | `app/src/main/assets/managed-runtime-inputs.json` | `tools/test-runtime-input-contract.py` + `prepare-runtime-descriptor.py --check` |
| 界面文案与翻译 | `tools/i18n/messages.json` | `tools/test-dsha-ui-regressions.py` 的 CatalogCoverage |
| 应用名与图标 | `AGENTS.md` 的界面约定 + `tools/prepare-app-icon.py` | 人工 |

## 2. 改一处要连带改哪些

### 换端口

1. `util/Constants.kt` —— 只改这里。
2. 跑 `python3 -B tools/test-port-consistency.py`，它会报出所有还没跟上的地方：
   容器脚本与内置插件的兜底值、文档里声明的端口、以及**界面文案里不允许出现的端口号**。
3. 容器侧不写死端口：脚本与插件都读 `/root/.dsh/.bridge_port`（由 `HttpShellService.writeBridgePort`
   写进 rootfs），所以正常情况下不用动它们，只有"兜底值"要改。
4. 改了 `app/src/main/assets/adb-shell.py` 这类**受运行时哈希保护**的文件，必须重生成运行时描述
   （见 §4）。

### 换 dsh 版本

1. `tools/dsh-runtime/package.json` 里所有 `@deepseek-ai/dsh*` 版本，然后
   `npm install --package-lock-only --os=linux --cpu=arm64 --libc=glibc --ignore-scripts`。
2. `util/Constants.DSH_VERSION`。
3. `python3 -B tools/test-dsh-patch-anchors.py` —— 安装期补丁必须逐条命中，没命中的补丁
   会让手机上启动失败，这一步不过就不能发版。
4. 重生成运行时描述（§4）。

### 换包名或签名

见 [BUILD.md](../BUILD.md) 第 4、9 节与 [HANDOVER.md](../HANDOVER.md) 第 3 节。
两个提醒：

- 换了包名或签名就是**另一个 App**，已安装用户不能覆盖升级。这是产品决定，不是技术细节。
- 源码 `applicationId`（`com.dsh.client`）不要跟着改：`tools/device-backup-audit.init.gradle`
  按这个字符串做源码改写，`debug/`、`deviceAudit/`、`androidTest/` 里 37 处
  `am start -n com.dsh.client/...` 是它的改写锚点。

### 改界面文案

1. 文案进 `tools/i18n/messages.json`（`zh` 是代码里的字面量原文，`en` 是译文）。
2. **不要在可翻译字符串里拼数字或变量**：`UiMessages` 是按整串精确匹配的，拼过就永远命不中，
   英文界面会掉回中文。端口号这类要拼的值放在 `UiText.text("固定文案") + 变量` 里。
3. 改颜色跑 `python3 tools/test-ui-colors.py`（对比度 ≥ 4.5:1）。

### 动 Java → Kotlin 迁移相关

见 [kotlin-migration.md](kotlin-migration.md)：类名/JNI/清单硬契约、`@Throws`、`@JvmStatic`、
`launcherSources` 的 23 个类不能单独迁。

## 3. 本机（手机容器）上的验证

| 目的 | 命令 |
|---|---|
| 编译 + 跑单测（Java/Kotlin 混编） | `python3 tools/run-unit-tests.py` |
| 只跑几个测试 | `DSHA_ONLY=ShellQuoteTest python3 tools/run-unit-tests.py` |
| 架构边界 | `python3 tools/test-architecture-boundaries.py` |
| 端口单一来源 | `python3 -B tools/test-port-consistency.py` |
| 运行时输入契约（含真实工作树） | `python3 -B tools/test-runtime-input-contract.py` |
| 发行验收 / 证据 | `python3 -B tools/test-release-acceptance.py`、`tools/test-release-evidence.py` |
| 界面回归 | `python3 tools/test-dsha-ui-regressions.py` |
| 设备命令白名单 | `python3 tools/test-device-shell-policy.py` |
| 文档一致性（链接与文件引用） | `python3 -B tools/test-doc-consistency.py` |
| 运行时描述是否仍与输入一致 | `python3 -B tools/prepare-runtime-descriptor.py --check`（大资产就位时本机可直接跑） |
| 文档一致性（链接与文件引用） | `python3 -B tools/test-doc-consistency.py` |
| 运行时描述是否仍与输入一致 | `python3 -B tools/prepare-runtime-descriptor.py --check`（大资产就位时本机可直接跑） |
| 内核更新清单 | `python3 tools/test-make-update-feed.py` |

需要的环境变量（`tools/run-unit-tests.py` 会读）：

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export ANDROID_SDK_ROOT=/opt/android-sdk
export GRADLE_USER_HOME=/opt/toolchains/gradle-user-home
```

### 这台机器上的两个硬限制（都会**静默**咬人）

1. **没有可执行的 aapt2**：Google 只发 x86_64 的 build-tools，本机是 aarch64。
   所以 Gradle 只能跑到配置阶段；编译与单测走 `tools/run-unit-tests.py` 的 kotlinc+javac 链路，
   完整 APK 以 CI 为准。
2. **`/sdcard` 不支持符号链接**（FUSE），`chmod +x` 也无效。于是 `npm ci` 会因为建不出
   `node_modules/.bin/*` 软链而失败，esbuild 这类需要可执行位的包也跑不起来。
   **绕法**：把仓库复制到 `/tmp`（那里是正常文件系统），在 `/tmp` 里跑需要 npm/esbuild 的步骤，
   再把产物拷回来：

   ```bash
   cp -a "/sdcard/Download/dsha工作区/DSHA-zzy" /tmp/dsha-build
   cd /tmp/dsha-build && npm ci --prefix tools/web-compat --ignore-scripts --no-audit --no-fund
   node tools/prepare-web-compat.mjs
   ```

## 4. 重生成运行时描述（受哈希保护的改动之后）

`app/src/main/assets/runtime-descriptor.json` 由受管输入算出：`assetFiles`、`installs` 的资产、
`assetTrees`、`launcherSources`、`launcherTrees`。**动了其中任何一个文件就必须重生成**，
否则手机上会认为环境身份不符。

顺序（与 CI 一致，见 `.github/workflows/build-apk.yml` 的资产品备步骤）：

```bash
python3 -B tools/ci-import-prebuilt-assets.py --apk <0.1.7-rc2 APK> --sha256 <SHA-256>
python3 -B tools/prepare-dsh-runtime.py          # 需要 npm；/sdcard 上要用 §3 的 /tmp 绕法
node tools/prepare-web-compat.mjs
python3 -B tools/prepare-backup-assets.py --write
python3 -B tools/prepare-runtime-descriptor.py --write
python3 -B tools/test-runtime-descriptor-inputs.py
python3 -B tools/test-dsh-patch-anchors.py
```

- 大资产（`offline-rootfs.bin`、`dsh-runtime.bin` 等）不进 Git，从本仓库 `runtime-assets`
  发行版下载；没有这个发行版时从上游镜像一次。
- `--write` 会改写受跟踪文件，提交前要审阅；普通构建用的是 `--check`，不一致会直接失败。
- `python3 -B tools/test-runtime-input-contract.py` 能在**不需要大资产**的情况下先拦住
  「改名/迁移把 `launcherSources` 里某个文件弄没了」这类错误。

## 5. 发版

1. 更新 `CHANGELOG.md`、`.github/RELEASE_NOTES.md`，推送到 `main`。
2. 在 Actions 手动运行 **Build APK** 并勾选 `publish`（`tag` 留空会在最新的 `…-zzy.N` 上加 1）。
3. 工作流会核对包名、版本，用仓库 Secrets 里的密钥签名，建一个标记为 Latest 的发行版，
   附件是 APK、`.sha256` 和 `updates.json`。

注意：**只推送就会触发一次日常构建**（刷新预发布 `ui-latest`）。不要再手动 dispatch 同一个提交 ——
两者会落进同一个 concurrency 组，先跑的那次被取消，提交列表上就会挂一个叉。

## 6. 排障入口

| 现象 | 先看哪里 |
|---|---|
| 设备工具全不可用 | 容器里 `cat /root/.dsh/.bridge_status`（App 写下的绑定结果）；`selftest.py` 的「设备桥」项 |
| 桥连不上但进程在 | `cat /root/.dsh/.bridge_port` 与 `cat /root/.dsh/.bridge_token` 是否与 App 状态一致 |
| 环境身份不符 | `runtime-descriptor.json` 的 `runtimeId` 与实际资产是否同代（§4） |
| 界面文案没翻译 | 该字符串是否是"拼过变量"的（§2 改界面文案） |
| 迁移后某个门禁"通过"得很可疑 | 那个脚本是不是只认 `.java`（见 kotlin-migration.md 的雷区表） |

## 7. 提交习惯

- 注释与界面文案用中文；提交信息用中文，带 `type:` 前缀（`fix:` / `feat:` / `docs:` / `refactor:`）。
- 每批改动**先跑 §3 的检查，再推送**；推送即触发 CI，不要额外手动 dispatch。
- 说「改好了」要有可复现的证据：跑了什么、结果是什么。
