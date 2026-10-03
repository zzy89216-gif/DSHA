# 构建说明

本仓库（DSHA）有两个产品 flavor：

| Flavor | 系统 | 网页内核 | 谁来构建 |
|---|---|---|---|
| standard | Android 11+（minSdk 30） | 系统 WebView | GitHub Actions，发行版只有它 |
| low | Android 6+（minSdk 23） | 系统 WebView，旧 WebView 时改用内置 GeckoView 143 | 只能本地构建，见 [docs/android-low.md](docs/android-low.md) |

两者都只有 arm64-v8a，targetSdk 37。正式发布以 CI 产物为准（第 9 节），本地构建用于开发和调试。

## 1. 工具链

| 项 | 版本 |
|---|---|
| JDK | 17（源码与字节码目标都是 Java 17） |
| Kotlin | 由 AGP 9 **内置**（AGP 9.1.1 → Kotlin 2.2.10），`jvmTarget` 17。**不要**应用 `org.jetbrains.kotlin.android`，AGP 9 起会直接构建失败 |
| 本机 kotlinc | 只有在用 `tools/run-unit-tests.py` 时才需要，且必须与上面那个版本一致（见 [docs/kotlin-migration.md](docs/kotlin-migration.md)） |
| Android SDK | `platforms;android-37.0`、`build-tools;36.0.0` |
| Android NDK | `26.3.11579264`（`app/build.gradle` 的 `ndkVersion`） |
| Gradle / AGP | 用仓库自带 Wrapper 9.3.1；AGP 9.1.1 |
| Python | 3.9+，默认 `python3`，可用 `DSHA_PYTHON` 指定 |
| Node | 24（只在重建 dsh 运行时和跑 `.mjs` 检查时需要） |

用 Android Studio 时打开仓库根目录（含 `settings.gradle`），不要只打开 `app/`。

## 2. 离线资产

`offline-rootfs.bin`、`dsh-runtime.bin`、`ubuntu-tools.bin` 等大文件不进 Git（见 `.gitignore`），干净检出直接构建会失败。本地按 CI 同样的步骤准备：

1. 从本仓库 Releases 的 `runtime-assets` 下载 `dsha-0.1.7-rc2.apk`，SHA-256 以 `.github/workflows/build-apk.yml` 里的 `ASSET_APK_SHA256` 为准。
2. 依次运行：

```bash
python3 -B tools/ci-import-prebuilt-assets.py --apk dsha-0.1.7-rc2.apk --sha256 <ASSET_APK_SHA256>
python3 -B tools/prepare-dsh-runtime.py
npm ci --prefix tools/web-compat --ignore-scripts --no-audit --no-fund
node tools/prepare-web-compat.mjs
python3 -B tools/prepare-backup-assets.py --write
python3 -B tools/prepare-runtime-descriptor.py --write
python3 -B tools/test-runtime-descriptor-inputs.py
python3 -B tools/test-dsh-patch-anchors.py
```

- 第一步只取不随 dsh 升级变化的部分：Ubuntu 基底、Ubuntu 工具，以及应急运行时的两份固定归档（按 `tools/recovery-runtime/lock.json` 校验，见 [tools/recovery-runtime/README.md](tools/recovery-runtime/README.md)）。
- `prepare-dsh-runtime.py` 按 `tools/dsh-runtime/package-lock.json` 安装 Linux arm64 依赖并打构建期补丁，需要 npm。
- 两个 `--write` 会改写受跟踪的证明文件，提交前要审阅。普通 Gradle 构建只用 `--check` 核对，不改源码树。
- `test-dsh-patch-anchors.py` 失败说明安装期补丁在当前 dsh 上没命中，这样的包在手机上会启动失败。

Python 补充库与 pnpm（`python-support.bin`、`pnpm-runtime.bin`）已随源码提供。需要重新生成时运行 `python tools/build-standard-runtime.py`，依赖 bsdtar，下载内容按脚本内固定的版本和 SHA-256 校验。

## 3. 本地构建

推荐用 `build.sh`，它会自动找 JDK 17、带 android-37 的 SDK、UTF-8 locale，按可用内存设置 Gradle 堆：

```bash
bash build.sh                              # 默认 :app:assembleStandardDebug
bash build.sh :app:testStandardDebugUnitTest
bash build.sh :app:assembleLowDebug
```

可用环境变量覆盖：`JAVA_HOME`、`ANDROID_SDK_ROOT` / `ANDROID_HOME`、`DSHA_PYTHON`、`GRADLE_USER_HOME`、`DSHA_JVM_MB`（Gradle 堆，MB）、`GRADLE_DIST_URL`（Gradle 发行版镜像，按 Wrapper 里的 SHA-256 校验）。也可以在 `local.properties` 写 `sdk.dir=...`。

不用脚本时直接调 Wrapper：

```bash
./gradlew :app:assembleStandardDebug
```

产物在 `app/build/outputs/apk/<flavor>/<buildType>/`。

在 aarch64 主机上，Google 提供的 Linux build-tools 只有 x86_64，`aidl` 无法执行。`build.sh` 会自动换成 shim，说明见 [tools/aidl-stub/README.md](tools/aidl-stub/README.md)。同样的原因下 aapt2 也跑不了，这时可以用 `python3 tools/run-unit-tests.py` 绕过 Gradle 跑纯逻辑单测 ——
它借 Gradle 的依赖解析结果（`tools/classpath.init.gradle`）用 kotlinc + javac 混编，
所以 Java 和 Kotlin 的改动都能验证。

## 4. 签名

- debug 包用本机调试证书。
- release 签名读 `DSHA_KEYSTORE`（或 `-Pdsha.keystore`），以及 `DSHA_KEYSTORE_PASSWORD`、`DSHA_KEY_ALIAS`、`DSHA_KEY_PASSWORD`。V1/V2/V3 全部开启，low 在 Android 6 上需要 V1。
- `assemble*Release` 默认依赖 `verifyPublishCertificate`：它要求密钥库的证书 SHA-256 等于本 App 的发布证书（见 [HANDOVER.md](HANDOVER.md) 第 3 节）。CI 必须加 `-x verifyPublishCertificate` 跳过 —— CI 的密钥库是运行时从 Secrets 解出来的，这个校验任务是给本地与正式发布用的门。
- Android 只允许同签名覆盖安装。发布包名是 CI 注入的 `zzy.dsha.Kotlin`，源码 `applicationId` 是
  `com.dsh.client`（本地/dev 身份，审计脚手架绑着它，见 `app/build.gradle` 里的说明），所以本地构建的包
  与发布包不同名，可以并存；本地包与 `com.dsh.client` 那个版本同包名不同签名，不能并存。

CI 密钥的加密备份与恢复见 [.github/signing/README.md](.github/signing/README.md)。

## 5. 检查工具

| 命令 | 作用 |
|---|---|
| `python tools/audit-standard-apk.py <apk>` | 静态检查 APK 内宿主 JNI 和离线环境 ELF 的 arm64 / 16 KB 段对齐，不代替真机运行 |
| `python tools/verify-plugin-upgrade-gate.py` | 插件覆盖升级门禁：链接缓存失效、发现与启停、审阅、依赖冻结、安装事务恢复、旧工作流包名兼容等，任一失败即非零退出 |
| `python tools/prepare-test-runtime.py` | 生成 `app/build/test-runtimes/` 下的测试运行时夹具 |
| `python tools/verify-stability.py` | 本仓库的本地验收脚本（来自历史基线那套，身份常量已切到本 App），见 [docs/stability-acceptance.md](docs/stability-acceptance.md) |

## 6. 原生组件

均为 arm64，已随源码提交，正常构建不需要重编。

| 文件 | 说明 | 重编 |
|---|---|---|
| `app/src/main/jniLibs/arm64-v8a/libtermux.so` | Termux 0.118.0 终端 JNI，加 PTY 身份握手，API 23、16 KB 对齐 | [tools/termux-jni/README.md](tools/termux-jni/README.md) |
| `app/src/main/jniLibs/arm64-v8a/libproot.so` 等 | standard 用的 proot 与 loader。打包时保留原字节（`keepDebugSymbols`），应急启动器按签名 APK 中的字节校验 | 不要随意替换 |
| `app/src/low/jniLibs/arm64-v8a/libproot_legacy.so`、`libprootloader_legacy.so` | low 用的 proot，NDK API 23 重编 | `python tools/build-low-proot.py --ndk <NDK 目录>` |

## 7. 版本号

`app/build.gradle` 里是 `versionName "0.1.7-rc2"`、`versionCode 147`（low 在版本名后加 `low`）。这是历史基线的值，本地构建沿用。

发布版本由 CI 注入，不需要改 `build.gradle`：versionCode = 147 + Build APK 工作流的运行序号；正式版 versionName 是标签去掉 `v`（例如 `v0.1.7-rc2-zzy.8` → `0.1.7-rc2-zzy.8`），日常构建是上一个正式标签加 7 位提交号。

## 8. 常见问题

| 现象 | 处理 |
|---|---|
| Gradle / AGP 版本不对 | 用仓库的 `gradlew`，不要用全局 Gradle |
| 找不到 NDK、`abiFilters` 报错 | SDK Manager 装 NDK 26.3.11579264 |
| 找不到 python3 | 设 `DSHA_PYTHON` |
| 缺 `offline-rootfs.bin` 等资产 | 按第 2 节准备 |
| `assemble*Release` 报发布证书不对 | 加 `-x verifyPublishCertificate`，见第 4 节 |
| `aidl: bad machine` | aarch64 主机，用 `build.sh` 构建 |
| JVM 报路径里全是 `?` | locale 不是 UTF-8，`build.sh` 会自动处理 |
| 手机装不上 | 只支持 arm64-v8a；覆盖安装要同包名同签名 |

## 9. 云端构建（GitHub Actions）

工作流是 `.github/workflows/build-apk.yml`，只构建 Standard Release。

| 触发 | 结果 |
|---|---|
| 推送 `main`（只改 `*.md`、`docs/`、`.github/RELEASE_NOTES.md` 时不触发） | 上传 Artifact，刷新预发布 `ui-latest` |
| 手动运行并勾选 `publish` | 创建正式发行版，附 APK、`.sha256`、`updates.json` |

流程：

1. 下载并校验 `runtime-assets` 里的 0.1.7-rc2 APK。本仓库还没有这个发行版时，按固定摘要从来源镜像一次。
2. 执行第 2 节的资产准备步骤。
3. 准备签名：用 Secrets `DSHA_CI_KEYSTORE_B64`、`DSHA_CI_KEYSTORE_PASSWORD`（alias `dsha-ci`）。Secrets 缺失时生成临时密钥并警告，这样的包不能用来发版。
4. 确定版本（见第 7 节）。`tag` 留空时在最新的 `…-zzy.N` 上加 1；格式不对或标签已存在会直接失败。
5. `./gradlew -I .github/ci/ci-build.init.gradle :app:assembleStandardRelease -x verifyPublishCertificate`。init 脚本按 `DSHA_CI_APP_ID`（`zzy.dsha.Kotlin`）、`DSHA_VERSION_CODE`、`DSHA_VERSION_NAME` 改写 applicationId 和版本。Java 包名与 namespace 不变，代码里需要包名时读 `BuildConfig.APPLICATION_ID`。
6. 用 `aapt2` 核对包名、清单版本，并核对 BuildConfig 的版本与清单一致。
7. 正式版用 `tools/make-update-feed.py` 生成 `updates.json`，正文取自 `.github/RELEASE_NOTES.md`。App 从 `releases/latest/download/updates.json` 读取更新。

发版：更新 `CHANGELOG.md` 和 `.github/RELEASE_NOTES.md` 并推送，然后在 Actions 里手动运行 Build APK 并勾选 `publish`。详细步骤见 [HANDOVER.md](HANDOVER.md)。

问题反馈：<https://github.com/zzy89216-gif/DSHA/issues>
