# Java → Kotlin 主语言迁移

本仓库（`zzy89216-gif/DSHA`）是这一个 App 的 Kotlin 主线，也是一个**独立的 App**：包名
`zzy.dsha.Kotlin`，用本仓库自己的 CI 签名密钥。历史上还有 `zzy.dsha.com`（原 DSHA-zzy）与
`com.dsh.client`（另一个 DSHA 版本）两个包名，与它不同包名也不同签名，可以同时安装、数据互不影响；
代价是没有从旧包升级的路径，装了等于多一个 App。

> 原 `DSHA-zzy` 与过渡仓库 `DSHA-zzy-kotlin` 已按所有者要求删除（目的：新仓库不带历史贡献者）。
> 完整历史备份见本机 `backup-DSHA-zzy-kotlin/`。

## 构建怎么接的

**不要**在 `build.gradle` 里写 `id 'org.jetbrains.kotlin.android'`。AGP 9 起 Kotlin 是内置的，
显式应用那个插件会直接构建失败：

```
The 'org.jetbrains.kotlin.android' plugin is no longer required for Kotlin support since AGP 9.0.
```

内置 Kotlin 的编译器版本跟着 AGP 走（9.1.1 → Kotlin 2.2.10）。它把 `src/<源集>/java` 和
`src/<源集>/kotlin` **都**登记为 Kotlin 源根，所以本仓库把 `.kt` 和 `.java` 放同一个目录是可行的，
不需要搬家。

## 为什么不能"直接把 .java 改名成 .kt"

这个仓库里有一批**靠类名/文件名活着**的契约，改名或换语言形态会静默打断它们：

| 契约 | 位置 | 改坏的后果 |
|---|---|---|
| 清单注册的 24 个 `android:name` | `app/src/main/AndroidManifest.xml` 及各 flavor 的清单 | 组件直接不启动 |
| `RootShellMain.class.getName()` 交给 `app_process` | `RootShell.java:61` | root 通道整体失效 |
| `com.deepseekharness.app.vscreen.VirtualScreenCore` | `util/DeviceShellPolicy.java`、`assets/device-shell-policy.py`、`vscreen/VirtualScreenManager.java` | 虚拟屏被白名单判成 `[POLICY_BLOCKED]` |
| JNI 符号 `Java_com_deepseekharness_app_runtime_NativeProcess_*` | `runtime/NativeProcess.java` ↔ `tools/termux-jni/dsha-pty.c` | C 侧 `GetStaticMethodID` 返回 NULL，进而 `kill(pid, SIGKILL)` 杀掉终端子进程 |
| `testInstrumentationRunner` 的 `Rc13Instrumentation` | `app/build.gradle`、`androidTest` | 仪器测试起不来 |
| ProGuard keep 规则 | `proguard-rules.pro` | 发布包被裁掉入口 |

因此**禁止**把上述类写成 Kotlin 顶层函数 —— 顶层函数会生成 `XxxKt` 类，名字就变了。
同理，`proguard-rules.pro` 里按类名写的 keep 规则在改名后要同步。

## 转换约定

1. **类名与文件名保持不变。** 只换语言，不换身份。
2. **受检异常必须写 `@Throws`。** Kotlin 默认不生成受检异常声明，Java 调用点普遍写成
   `try { ... } catch (IOException e)`，缺了这个注解会以
   "exception IOException is never thrown in body of corresponding try statement" 编译失败。
3. **Java 侧要静态调用就加 `@JvmStatic`。** `object` 的成员默认只能通过 `INSTANCE` 访问；
   本项目 172 个 Java 单测直接调 app 类，少一个 `@JvmStatic` 就是一片 cannot find symbol。
   字段用 `@JvmField`，带默认参数的构造函数用 `@JvmOverloads`。
4. **`internal` 不等于 Java 包私有。** 它是模块级可见。`util/` 里有大量类依赖包内可见性，
   迁移时要逐个判断，不要机械替换。
5. **可空性按 Java 原语义来。** Java 里能传 `null` 的参数必须声明成可空类型；声明成非空会让
   Kotlin 插入 `checkNotNullParameter`，把原来"返回 null"的行为变成运行时异常 —— 这是最
   难发现的静默行为变化。
6. **不写 `!!`。** 真需要断言就用 `requireNotNull` 并给出可读信息。
7. **纯数据载体直接上 `data class`**，但对外的方法/字段形状（包括 getter 名字）不能变，
   否则 Java 调用点要跟着改，扩散面失控。
8. 注释与文案用中文，保持原文件里"为什么这么做"的说明，不要降级成复述代码。

## 本机验证链

aarch64 主机上 Google 只发 x86_64 的 build-tools，`aapt2` 跑不起来，Gradle **只能跑到配置阶段**。
所以本机验证走 `tools/run-unit-tests.py`：它借 Gradle 的依赖解析能力拿到精确编译类路径
（`tools/classpath.init.gradle`），再用 `kotlinc` + `javac` 两遍编译跑 JUnit。

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_SDK_ROOT=/opt/android-sdk
export GRADLE_USER_HOME=/opt/toolchains/gradle-user-home

python3 tools/run-unit-tests.py                        # 全量
DSHA_ONLY=ShellQuoteTest python3 tools/run-unit-tests.py   # 只跑指定测试类
```

工具链怎么准备见 [BUILD.md](../BUILD.md) 第 3 节。`tools/run-unit-tests.py` 会校验本机
`kotlinc` 与 **AGP 内置的 Kotlin** 同版本，不一致直接失败（`DSHA_ANY_KOTLIN=1` 可显式跳过）——
编译器版本决定语言特性能不能用，两边不一致会造出"本机编得过、CI 编不过"这种最难查的差异。

## 每批必须过的门禁

| 检查 | 为什么 |
|---|---|
| `python3 tools/run-unit-tests.py` | 编译 + 单测，迁移的主要安全网 |
| `python3 tools/test-architecture-boundaries.py` | `util/` 不得依赖 Android；扫不到源码会直接失败 |
| `python3 -B tools/test-port-consistency.py` | 端口只能定义在 `util/Constants`；容器侧读 `.bridge_port`；界面文案里不许有端口号 |
| `python3 -B tools/test-doc-consistency.py` | 文档里的链接与文件/源码引用必须真实存在（改名后不同步会失败） |
| `python3 -B tools/test-doc-consistency.py` | 文档里的链接与文件/源码引用必须真实存在（改名后不同步会失败） |
| `python3 tools/test-release-acceptance.py` | 真机验收契约；含"每个 pattern 必须命中真实文件"的自检 |
| `python3 tools/test-dsha-ui-regressions.py` | 34 项界面行为断言（它读源码文本，改名要同步） |
| `python3 tools/test-device-shell-policy.py` | 设备命令白名单 |

> `tools/localize-android-ui.py` **没有干跑模式**，一跑就直接改写源码字面量
> （`--scope` 默认只覆盖 `ui/`）。它已经改成双后缀：跳过名单按类名判断，主扫描同时认
> `.java` 和 `.kt`。在没有明确意图时不要顺手跑它。
| `python3 tools/test-runtime-input-contract.py` | **动任何源码改名/迁移前都跑**：它校验真实工作树里 `launcherSources` 的 23 个文件都还在（本机可跑，不需要离线资产） |
| `python3 tools/test-runtime-descriptor-inputs.py` | 动了 `launcherSources` 相关文件时必须跑 |

## 受哈希/回执保护、改名会连带失效的东西

1. `app/src/main/assets/runtime-descriptor.json` 的 `runtimeId`。它由 `launcherTrees` +
   `launcherSources` 算出。**先**确认 `app/build.gradle` 里的源码过滤器认得 `.kt`，
   **再**跑 `python3 -B tools/prepare-runtime-descriptor.py --write`；顺序反了会让 Kotlin 文件
   悄悄退出哈希。
2. `app/src/main/assets/managed-runtime-inputs.json` 的 `launcherSources` 列的是 23 个 `.java`
   文件名，改后缀必须同步 `tools/prepare-runtime-descriptor.py` 与 `tools/runtime_input_contract.py`，
   并重新生成 `runtime-descriptor.json`。**不要单独迁这类**：清单里还有一条隐式约束 ——
   `runtime_input_contract.launcher_paths()` 要求每个名字都能落到文件上，只把 `.java` 改成 `.kt`
   会让 `prepare-runtime-descriptor.py` 抛 `RUNTIME_INPUT_MISSING_OR_OUTSIDE`。
   本地先跑 `python3 -B tools/test-runtime-input-contract.py` 就能发现。
   23 个类见 `launcherSources` 字段（`DshaApp`、`PtySession`、`core/HarnessController`、
   `util/GuestCommandOutcome`、`util/TerminalSession` 等）。
3. `tools/release-acceptance.json` 的 `contractSha256` 进历史交付回执。
4. `tools/verify-stability.py` 的软件回执：`sourceSnapshot` 来自 `git ls-files`（后缀无关，
   `.kt` 会自动纳入），但内容全变，`--deliver-from` 复用旧回执会抛 `DELIVERY_SOURCE_CHANGED`。

## 批次安排

| 批次 | 范围 | 说明 |
|---|---|---|
| P0 | 前置清理 | 删死类（`DangerShellGuard`、`bridge/AppBridge`）；`util/Compat` 的 Android 依赖抽成接口；解 `backup↔runtime`、`backup↔core` 包环 |
| P1 | `util` 高扇入类 | `UiText`(169 处引用)、`SensitiveData`、`Constants`、`ShellQuote`、`Fmt`… 现有 112 个 util 单测就是回归网 |
| P2 | `util` 其余纯策略类 | 约 107 个文件 |
| P3 | `launcherSources` 引用的类 | 单独成批，编译后必须重生成运行时描述 |
| P4 | `data` + `bridge` + `vscreen` 纯策略部分 | |
| P5 | `backup`（62 文件） | 45 个现有单测是最强安全网 |
| P6 | `core`（27 文件） | 先拆 `HarnessController`(988 行) 再迁 |
| P7 | `runtime`（18 文件） | 先拆 `ProotBootstrap`(1579 行) 再迁 |
| P8 | `ui` + 根包（103 文件） | 界面零测试覆盖，要先补测试再迁 |
| — | `debug/`(45 文件 7342 行) | 是非产品脚手架，建议重写而非逐行迁移 |

## 进度

数字一律现算，不要手写（手写的一定会漂）：

```bash
python3 tools/kotlin-migration-progress.py             # 当前进度
python3 tools/kotlin-migration-progress.py --markdown  # 可直接贴进文档的表格
```

它按 `app/src` 下 `.java` / `.kt` 的**行数**算主指标（文件数会被 `util/` 那种几十行的小类
撑高，字节数受长文案影响），并且只统计工作区里真实存在的文件 —— 刚写出来还没 `git add`
的 `.kt` 也算数。一个诚实的提醒：迁过来的文件普遍比原来长（KDoc 写得更足），所以按行数算会
略微**高估**进度；而且行数不等于难度，`ui/` 那 76 个类零测试覆盖，同样的行数要贵得多。

| 语言 | 文件 | 行 | 占比（按行） |
|---|---:|---:|---:|
| Kotlin | 6 | 300 | 0.46% |
| Java | 599 | 65124 | 99.54% |
| **合计** | **605** | **65424** | 100% |

> 上面的表格只是本文件最后一次更新时的快照，以脚本输出为准。

### 已做

- [x] 构建接入 Kotlin（走 AGP 9 内置 Kotlin，编译器 2.2.10，`jvmTarget` 17）
- [x] 本机验证链支持 Java/Kotlin 混编，并校验本机 kotlinc 与 AGP 内置版本一致
- [x] 门禁双后缀化：`test-architecture-boundaries.py`、`release_acceptance.py`、
      `localize-android-ui.py`
- [x] `test-runtime-input-contract.py` 加了「真实工作树的 launcher 输入必须都存在」的守卫
- [x] `util/`：`ProjectLinks`、`ShellQuote`、`UiText`、`SensitiveData`、`Constants`、`Fmt`
- [x] P0 之一：删掉两个确认无引用的死类 `DangerShellGuard`（127 行）与 `bridge/AppBridge`
      （后者是零实现的骨架接口）。删 `DangerShellGuard` 前把它那段「黑名单为什么不可靠」
      的论证搬进了 [security-model.md](security-model.md)（中英双版），那是安全模型的一部分，
      不该随代码消失。
- [x] P0 之二：`util/Rc1MigrationResult` 原本 `import backup.BackupJson`，是 `util → backup`
      的反向依赖。改成把严格 JSON 解析器作为 {@code StrictJsonRecord} 参数注入
      （调用方传 `BackupJson::read`），回执契约仍只写在一处。顺带给测试加了两条
      原本只靠约定维持的断言：注入的解析器必须收到 UTF-8 字节与 65536 上限；
      重复回执要在读到第二条**之前**就拒绝。

### 未做

- [ ] P0 剩余：`util/Compat` 的 Android 依赖抽成接口（它用全限定名直调 `android.system.Os`
      等 24 处，绕过了只查 `^import (android|androidx)` 的架构守卫 —— 修完才能把守卫收紧）
- [ ] **包环不单独修**（`backup↔runtime`、`backup↔core`）。查过之后：`backup → runtime` 只有
      1 处（`ProfileSettingsTransaction` 用 `ProfileSettingsTrial`）；`backup → core` 有 10 处，
      其中 4 处指向 `HarnessController` 这个上帝类。**这些环是上帝类的症状，不是独立缺陷**：
      现在硬塞接口只是让依赖图好看，耦合一点没少。正确顺序是先拆
      `HarnessController`(988 行) 与 `ProotBootstrap`(1579 行)（见下面 P6/P7），环会自然消散。
- [ ] `util/` 其余纯策略类
- [ ] `util/GuestCommandOutcome` 等 23 个 `launcherSources` 类（P3，必须和清单、
      `runtime_input_contract.py`、`runtime-descriptor.json` 一起改）
- [ ] `data` + `bridge` + `vscreen` 纯策略部分
- [ ] `backup`（62 文件，45 个现有单测是最强安全网）
- [ ] `core`（27 文件，先拆 `HarnessController` 988 行）
- [ ] `runtime`（18 文件，先拆 `ProotBootstrap` 1579 行）
- [ ] `ui` + 根包（103 文件，界面零测试覆盖，先补测试再迁）
- [ ] `debug`（45 文件 7342 行，非产品脚手架，建议重写而非逐行迁移）
