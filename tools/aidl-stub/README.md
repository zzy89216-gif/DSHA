# AIDL 等价产物

`com/deepseekharness/app/IShellService.java` 是 `app/src/main/aidl/com/deepseekharness/app/IShellService.aidl` 的手写等价产物。仓库只有这一个 AIDL 文件。

## 为什么需要

在 aarch64 Linux 上构建时，Google 仓库给 Linux 的 build-tools 只有 x86_64 版本，sdkmanager 装出来的 `aidl` 执行会报：

```
loader: reject .../build-tools/36.0.0/aidl: bad machine
```

AGP 9.1.1 要求 build-tools ≥ 36.0.0，换不了版本；Debian 打包的 arm64 `aidl` 太旧，解析不了新版 `framework.aidl` 里的 `@JavaOnlyStableParcelable`。也不能用 `-x` 跳过 AIDL 任务，因为下游编译任务依赖它的惰性输出。

## 怎么用

`build.sh` 比较主机架构和 `aidl` 的 ELF `e_machine`：

- 一致：走原生 AIDL。
- 不一致：把 `aidl` 备份成 `aidl.x86_64.disabled`，换成一个 shim。shim 把本目录的 `.java` 复制到 AGP 给的 `-o` 目录，AIDL 任务照常完成。构建退出时恢复原文件。
- 已配好 qemu-user + binfmt 的主机，设 `DSHA_FORCE_AIDL=1` 跳过检测。

`tools/run-unit-tests.py` 不经 Gradle 跑单测时，也直接把本目录的 `.java` 加进编译源。

构建被强杀、没来得及恢复时，手动还原：

```bash
mv "$ANDROID_SDK_ROOT/build-tools/36.0.0/aidl.x86_64.disabled" \
   "$ANDROID_SDK_ROOT/build-tools/36.0.0/aidl"
```

## 接口与事务码

| 方法 | AIDL 声明 ID | Binder 事务码 |
|---|---|---|
| `String exec(String cmd)` | 0 | `FIRST_CALL_TRANSACTION + 0` |
| `String execVirtualScreen(String command)` | 1 | `FIRST_CALL_TRANSACTION + 1` |
| `void destroy()` | 16777113 | 16777114（Shizuku 约定的销毁事务） |

AIDL 会给声明 ID 加上 `FIRST_CALL_TRANSACTION`（1）。手写产物按加完之后的值保存，必须和 aidl 生成的结果一致。

`execVirtualScreen` 是单独的事务，只给原生侧启动虚拟屏用；通用 `exec` 的 shell 文本不能调用 `app_process`。

## 改 `.aidl` 时

加方法、改签名、改 ID 或包名，都要同步改这里的 `Stub`、`Default`、`Proxy` 和 `onTransact`。不改也能编译通过，但 IPC 行为会错。
