# Android 6—12 兼容版（low）

low 是本仓库的第二个 product flavor，不是单独一套代码。它和 standard 共用 main 源码、离线环境和 `applicationId`（源码里是 `com.dsh.client`）。CI 只出 Standard 发行版；low 只能自己构建。

| 项 | 值 |
|---|---|
| flavor | `low` |
| minSdk | 23（Android 6） |
| targetSdk | 37 |
| ABI | 仅 arm64-v8a |
| 版本名 | `app/build.gradle` 里的 `versionName` 加上后缀 `low` |
| 版本码 | 与 standard 相同（本地构建 147） |
| 网页内核 | 系统 WebView；Android 6/7，或 Chrome 低于 118 时自动切到内置 GeckoView 143 |
| 签名 | 本地 release 开启 V1/V2/V3，Android 6 需要 V1 |

没有 maxSdk。Android 13+ 用 [standard](android-standard.md)。两 flavor 同包名、同签名时可以互相覆盖，不能同时安装。

## 和 standard 的差异

- 依赖：`lowImplementation` 引入 GeckoView 143 和 Shizuku 12.2.0；standard 不带 Gecko，Shizuku 是 13.1.5。
- 自动切 Gecko：Android 8 以下，或系统 WebView 的 UA 里 Chrome 主版本低于 118。设置里也可手动打开（`gecko_core`）。
- Gecko 页面：`GeckoPreviewActivity` 带 cookie、返回、桌面模式、重试、系统文件选择和麦克风代理。
- Java 8+ API 用 core library desugaring（`desugar_jdk_libs:2.0.4`）。
- Android 6—10 声明存储权限（`maxSdkVersion=29`），Android 10 申请 `requestLegacyExternalStorage`。11+ 走所有文件访问。
- 清单用 `tools:overrideLibrary` 覆盖 `com.termux.view` / `com.termux.terminal` 的 minSdk 24 声明。
- proot 用 `app/src/low/jniLibs/arm64-v8a/libproot_legacy.so` 和 `libprootloader_legacy.so`（NDK API 23 重编），不替换 standard 的 `libproot.so`。`getifaddrs` 走动态查找。终端 JNI 仍是共用的 `libtermux.so`（API 23）。

系统能力 APK 补不了：无线调试配对码需要 Android 11+；无障碍手势需要 7+，无障碍截图需要 11+。旧系统仍可用读屏/节点操作、Shizuku 或已建立的 ADB 通道。

GeckoView 143 固定在这个版本，不能指望它跟新版 Firefox 同步更新。见 [Mozilla 最低 Android 版本](https://support.mozilla.org/en-US/kb/will-firefox-work-my-mobile-device)、[Java API 回补](https://developer.android.com/studio/write/java8-support)。

## 构建

环境见 [BUILD.md](../BUILD.md)。

```bash
bash build.sh :app:assembleLowDebug
# 或
./gradlew :app:assembleLowRelease -x verifyPublishCertificate
```

产物：`app/build/outputs/apk/low/<debug|release>/`。`build.sh` 不带参数只构建 standard debug。

重编 low 的 proot：

```bash
python tools/build-low-proot.py --ndk /path/to/android-sdk/ndk/26.3.11579264
```

终端 JNI 见 [tools/termux-jni/README.md](../tools/termux-jni/README.md)，默认 `-MinApi 23`。
