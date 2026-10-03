# Termux 终端 JNI（libtermux.so）

`app/src/main/jniLibs/arm64-v8a/libtermux.so` 由本目录的源码编译，standard 和 low 共用。Gradle 用 `pickFirsts` 让它覆盖 terminal-emulator 0.118.0 AAR 里自带的旧库。

## 文件

| 文件 | 说明 |
|---|---|
| `termux.c` | Termux v0.118.0 原版，提交 [`6e2689f5`](https://github.com/termux/termux-app/blob/6e2689f55295fa444be8ac8592c527c2c5ef3253/terminal-emulator/src/main/jni/termux.c)，不改动 |
| `dsha-pty.c` / `dsha-pty.h` | PTY 身份握手 |
| `dsha-process.c` | 额外导出 `NativeProcess.sessionId`，用 `getsid` 查会话号 |
| `build.ps1` | 构建脚本 |
| `LICENSE.upstream.md`、`LICENSE-2.0.txt` | 上游许可说明（含 terminal-emulator 的 Apache 2.0 例外）和 Apache 2.0 全文 |

## 身份握手做了什么

`build.ps1` 不修改 `termux.c`，而是在 `app/build/termux-jni/termux-patched.c` 生成补丁版。六个锚点每个必须恰好命中一次，否则停止。

补丁后的流程：fork 前建一对 socketpair；子进程 `setsid` 后自读身份，通过 socketpair 发给父进程；父进程登记成功并确认后，子进程才 exec。握手失败时还没有 guest 进程，父进程会回收子进程并抛异常。这样 Java 层不需要在启动后再读 `/proc`，也不会认领未知 PID。

## 构建

只支持 Windows PowerShell（用 NDK 的 `windows-x86_64` 工具链），不下载工具，不调用 Gradle：

```powershell
./tools/termux-jni/build.ps1 -Ndk <NDK 26.3.11579264 目录> [-MinApi 23|26]
```

- 不给 `-Ndk` 时依次找 `ANDROID_NDK_HOME`、`%LOCALAPPDATA%/Android/Sdk/ndk/26.3.11579264`、`$ANDROID_SDK_ROOT/ndk/26.3.11579264`。
- `-MinApi` 默认 23，目标 `aarch64-linux-android23`。仓库里的库就是 23。
- 链接参数：`-z max-page-size=16384`、`-z common-page-size=4096`、`-z relro -z now`。LOAD 段 16 KB 对齐；RELRO 按 4 KB 收尾，避免旧 linker 对未映射空洞 mprotect 报 ENOMEM。

脚本在复制到 `jniLibs` 前会检查：

1. `termux.c` 的 SHA-256 等于固定的 v0.118.0 值。
2. 每个 LOAD 段对齐不小于 16 KB，偏移与地址同余。
3. 只有一个 GNU_RELRO，且在 4 KB 和 16 KB 页映射下都没有空洞。
4. 导出集合正好是 Termux 原有 5 个（`close`、`createSubprocess`、`setPtyUTF8Mode`、`setPtyWindowSize`、`waitFor`）加 `NativeProcess.sessionId`。

输出与现有文件字节相同时不覆盖。当前仓库里文件的 SHA-256：

```
0c6b87759cb35f2ae8265155d3d669d511b43dbddab5831b6f55904833676147
```

改了 C 源码或参数后，用 `python tools/audit-standard-apk.py <apk>` 再核对一次 APK 内的 ELF 对齐。第三方许可汇总见仓库根目录 `THIRD_PARTY_NOTICES.md`。
