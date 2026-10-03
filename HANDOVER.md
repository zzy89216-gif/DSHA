# 交接日志

接手这个仓库，按这个顺序读：本文 → [AGENTS.md](AGENTS.md) → [BUILD.md](BUILD.md)。更早的设计背景和踩坑在 [docs/接手指南.md](docs/接手指南.md)。

- 已发布：`v0.1.7-rc2-zzy.10`，独立包名 `zzy.dsha.Kotlin` + 独立签名，内置 dsh 0.2.0-rc.2
- 仓库沿革：本项目原先在 `DSHA-zzy`（`zzy.dsha.com`）与过渡仓库 `DSHA-zzy-kotlin` 上，
  按所有者要求**两个仓库都已删除**，再以**全新历史**建了本仓库（去掉历史贡献者）。
  完整提交历史、已发布 APK、签名密钥与 CI 必需资产包都有本机备份
  （`backup-DSHA-zzy-kotlin/`，含一份迁移说明）。

## 1. 基本信息

- 仓库：<https://github.com/zzy89216-gif/DSHA>，独立仓库，不是 fork。
  来源声明与第三方许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- **本仓库是一个独立 App**：包名 `zzy.dsha.Kotlin`，用本仓库自己的 CI 签名密钥。
  与 `zzy.dsha.com`（已删除的 DSHA-zzy）和 `com.dsh.client`（另一个 DSHA 版本）都不同包名也不同签名，
  三者可以同时安装、数据互不影响；代价是没有从旧包升级的路径。
  迁移约定见 [docs/kotlin-migration.md](docs/kotlin-migration.md)。
- **本仓库是全新历史**（单提交起步），不带此前仓库的贡献者记录。改代码前先读
  [AGENTS.md](AGENTS.md) 与 [docs/maintenance.md](docs/maintenance.md)。
- 包名：发布包是 `zzy.dsha.Kotlin`，由 CI 按 `DSHA_CI_APP_ID` 注入；`app/build.gradle` 里的
  `applicationId` 仍是 `com.dsh.client`（本地/dev 身份，审计脚手架绑着它，别随手改）。
- 版本：CI 注入。versionCode = 1000 + Build APK 的运行序号（基数在 `.github/workflows/build-apk.yml`，
  必须高于已发布过的版本码，否则同包名无法覆盖安装）；正式版 versionName 是标签去掉 `v`，日常构建是「上一个正式标签 + 7 位提交号」。
- 构建：只在 GitHub Actions 上构建，只出 Standard 版（Android 11+，arm64-v8a）。
- 改动范围：主要是原生界面（`ui/`、`res/`）、包名适配、发布流程和内置 dsh 版本。运行时、备份等核心逻辑沿用历史基线。
- 更早还有一个 `zzy89216-gif/DSHA_zzy`（下划线）的 fork，是历史遗留，同样不再更新。

## 2. 怎么发版

1. 改代码，推到 `main`。Build APK 工作流会构建、检查包名和版本号，并刷新预发布 `ui-latest`。
2. 写好 [CHANGELOG.md](CHANGELOG.md) 和 [.github/RELEASE_NOTES.md](.github/RELEASE_NOTES.md)，推送。发行版正文和应用内的更新说明都取自 RELEASE_NOTES.md。
3. 在 Actions 里手动运行 Build APK，勾选 `publish`。`tag` 不填时，自动在最新的 `…-zzy.N` 上加 1。
4. 工作流重新构建，创建标记为 Latest 的发行版，附件是 APK、`.sha256` 和 `updates.json`。已安装的用户在「设置 → 检查更新」里会看到新版。

发布前工作流会拒绝这些情况：标签格式不对、标签已存在、APK 包名不对、清单和 BuildConfig 里的版本码 / 版本名不一致。

只改 `*.md`、`docs/` 或 `.github/RELEASE_NOTES.md` 时，推送不会触发构建。

## 3. 签名

| 名称 | 放在哪 | 作用 |
|---|---|---|
| `DSHA_CI_KEYSTORE_B64` | 仓库 Secrets | 本 App 的签名密钥库（PKCS12，alias `dsha-ci`，4096 位 RSA）的 base64 |
| `DSHA_CI_KEYSTORE_PASSWORD` | 仓库 Secrets | 密钥库密码（store 与 key 同密码） |
| `.github/signing/dsha-kotlin-ci-signing.tar.enc` | 仓库里 | 上面两项的加密备份（AES-256-CBC / PBKDF2-SHA256 / 600000 次），口令由仓库所有者离线保管 |

- 证书 SHA-256：`79:77:DF:F4:D4:52:C3:90:8D:AA:EA:91:F0:A2:0B:1A:BA:71:18:1B:73:4B:A4:3A:B5:48:98:FF:1E:31:42:8F`
- 有效期到 2054-02-18。RSA 4096 位，PKCS12。
- **这是本 App 永久的发布身份，一旦发过版就换不了**：换了以后已安装的用户只能卸载重装、数据会丢。
- `app/build.gradle` 的 `verifyPublishCertificate` 按这个指纹拦打包；CI 用 `-x verifyPublishCertificate`
  跳过（CI 的密钥库是运行时从 Secrets 解出来的，这个校验任务是给本地/正式发布用的门）。
- Secrets 缺失时，工作流会用临时密钥签名并给出警告。这样的包不能用来发版。
- `.github/signing/dsha-ci-signing.tar.enc` 是**旧 App `zzy.dsha.com` 的密钥备份**，与本 App 无关，
  留着只为不丢历史（原仓库里也有同一份）。

## 4. 应用内更新

- 更新清单地址在 `util/ProjectLinks.UPDATE_FEED`：`https://github.com/zzy89216-gif/DSHA/releases/latest/download/updates.json`。
- 清单由 `tools/make-update-feed.py` 在发版时生成（测试：`tools/test-make-update-feed.py`），schemaVersion 1。下载、SHA-256、包名、版本和签名的校验在 `core/UpdateEngine`，没有改过。
- App 只接受「版本码更大、包名相同、签名相同」的包，所以 versionCode 必须一直递增。它依赖 Build APK 的运行序号：如果给 `build-apk.yml` 改名，序号会从 1 重新开始，这时要调大工作流里的 `VERSION_CODE_BASE`。
- zzy.3 及更早版本读的是旧的更新清单地址，需要手动装一次 zzy.4 或更新版本。
- 覆盖安装后首次启动会更新一次受管组件（dsh 等）。Ubuntu 基础版本不变时不重建环境。

## 5. 构建依赖

- 离线 rootfs 等大文件不进 Git。工作流先从本仓库的 `runtime-assets` 发行版下载 0.1.7-rc2 APK，按 `build-apk.yml` 里固定的 SHA-256 校验；本仓库还没有这个发行版时，按固定摘要从来源镜像一次，之后只用本仓库的副本。
- `tools/ci-import-prebuilt-assets.py` 只从这个 APK 里取不随 dsh 升级变化的部分：Ubuntu 基底 `offline-rootfs.bin`、`ubuntu-tools.bin`，以及应急运行时的两份归档（按 `tools/recovery-runtime/lock.json` 校验）。
- dsh 运行时在 CI 里重建：`tools/prepare-dsh-runtime.py` 按 `tools/dsh-runtime/package-lock.json` 安装 Linux arm64 依赖并打构建期补丁；之后重新生成网页兼容层、备份资产和运行时描述，最后用 `tools/test-dsh-patch-anchors.py` 检查安装期补丁在新 dsh 上全部命中。没命中的补丁会让手机上启动失败，所以这一步失败就不能发。
- 包名注入在 `.github/ci/ci-build.init.gradle`。
- 构建时跳过 `verifyPublishCertificate`（CI 的密钥库是运行时从 Secrets 解出来的，这个校验任务是给本地与正式发布用的门）。其余准备和校验任务都正常执行。

升级内置 dsh 要改这些地方：

1. `tools/dsh-runtime/package.json` 里所有 `@deepseek-ai/dsh*` 的版本，然后重新生成锁文件：`npm install --package-lock-only --os=linux --cpu=arm64 --libc=glibc --ignore-scripts`。
2. `util/Constants.DSH_VERSION`。
3. `app/src/main/assets/` 下各 `*-patch.json` 的 `dshVersion`。不要动这几类：`recovery-*-patch.json`（属于应急运行时），以及已停用、版本停在旧值的 `agent-preset`、`models-navigation`、`web-integration/tooltip`。
4. `tools/prepare-runtime-descriptor.py` 里的版本链，以及内置插件 `package.json` 的依赖版本。

推送后看 CI；补丁锚点不命中就按报错修补丁。

升级 Ubuntu 基底需要在有完整工具链的环境里重新生成 `offline-rootfs.bin` 并更新 `runtime-assets`，目前还没做过。

## 6. 改代码要注意

- `app/src/main/assets/managed-runtime-inputs.json` 里 `launcherSources` 列出的文件和 `runtime/` 目录参与运行时描述的哈希。改了它们必须重新生成运行时描述，等同于升级运行时。
- 需要当前包名时用 `BuildConfig.APPLICATION_ID`。
- 界面相关的入口文件：
  - `ui/UiStyle.java`：背景模式、卡片、图标块，以及「打开直接进入网页」和网页悬浮按钮的偏好
  - `ui/BackdropDrawable.java`：自定义图片和动态玻璃背景
  - `ui/StartupSplash.java`：从桌面打开时的加载页
  - `ui/WebHomeHandle.java`：网页上的悬浮按钮
  - `ui/WebPageScripts.java`：注入网页的增强脚本
  - `ui/Disclosure.java`：折叠区
- 页面背景用主题属性（如 `?attr/dshaPageBackground`），不要写死颜色。
- 改颜色后运行 `python3 tools/test-ui-colors.py`，文字对比度要 ≥ 4.5:1。
- 手机上没有 Android SDK，编不了 APK，一切以云端构建为准。

## 7. 内置网页插件

- dsha-mobile（zzy.7 起，zzy.8 起为 0.2.0）：手机专属的网页界面，默认启用。源码在 <https://github.com/zzy89216-gif/dsha-mobile>，纯逻辑测试在那边 `node --test test/client.test.mjs`；随包副本改完后要同步回那个仓库（只复制 `lib/client.js` 和 `package.json`，其余文件保持一致）。
  - 会话行：宿主是「单击=选中、双击=打开」（`DSHA_SESSION_INTERACTION_V2`），抽屉原来在第一次单击就收起，第二次点击落不到行上 —— 这是「侧栏进的去、历史对话进不去」的根因。现在点行直接打开（走 `sessions.open`，没有就合成一次 `detail===0` 的显式激活点击），抽屉按 DOM 真实开合状态收起并做去抖，避免「收两次又打开」。
- dsh-web-mobile 3.0.3：沿用历史基线的移动插件，源码固定在提交 `a094288883b343e848d7f9cf302d73ad8ed4794b`，本地改动由 `tools/apply-mobile-client-patches.mjs` 管理。zzy.7 起仍随包提供，但升级和新装后会默认停用一次；用户之后手动启用会保持启用。

## 8. 测试情况

在容器（非 Android 环境）里能跑的：

| 检查 | 当前结果 |
|---|---|
| CI：Java/Kotlin 编译、资源合并、Release Lint | 以 Actions 结果为准 |
| `python3 tools/run-unit-tests.py` | 本机可跑（需要 JDK 17 + android.jar + kotlinc）。807 个测试 / 166 个测试类；Java 与 Kotlin 混编 |
| `tools/test-ui-colors.py` | 通过，最低对比度 4.521:1 |
| `tools/test-architecture-boundaries.py` | 通过（双后缀，扫不到源码会失败） |
| `tools/test-port-consistency.py` | 通过（端口单一来源：网页 3180 / 设备桥 3190 / LAN 3181） |
| `tools/test-release-acceptance.py` | 通过（15 项，含「每个 pattern 必须命中真实文件」的自检） |
| `tools/test-make-update-feed.py` | 通过 |
| `tools/test-dsha-ui-regressions.py` | 通过（34 项）：修好 `test_system_language_is_pinned_early` 的源码锚点，并补上「自动进网页要跨重建 / 回前台 / 环境准备」的断言 |
| `tools/test-plugin-discovery.py` | 通过（16 项） |
| `tools/test-device-shell-policy.py` | 通过（20 项） |
| dsha-mobile `node --test test/client.test.mjs` | 通过（6 项）：会话 id 解析、会话行点击决策、抽屉层级与去抖 |
| `tools/test-dsh-patch-anchors.py` | 在 CI 里跑，失败会阻止构建 |

- 其余 `tools/test-*.py` 里有不少依赖 Windows 路径、真机或本地生成的资产，在 CI 和容器里跑不了。
- 真机验收还没有系统做过。zzy.5 以来的界面改动和 dsh 升级只经过静态检查和 CI 构建。

## 9. 已知问题

- ~~「ADB 配对后自动授予无线调试保活」不起作用~~：**已修**（`adb-pair.py` 改为由宿主传 `--package`，
  `AdbBridge` 传 `BuildConfig.APPLICATION_ID`）。顺带订正：这个文件**不在**运行时输入契约里
  （`assetFiles` / `installs` / `launcherSources` 都没有它，只有 `adb-shell.py` 在 `installs` 里），
  所以当时「受哈希保护」的说法是错的。
- 和其它 DSHA 版本同时运行时抢设备桥端口：本 App 的默认端口会独立成另一组（见 `util/Constants`），

- 插件市场和社区页目前仍会读取一个**外部**插件目录站点（`ui/CommunityActivity`、`ui/PluginFragment`、
  `util/PluginInstallLink`）。这是目前唯一的外站依赖，不由本项目维护、与本项目没有隶属关系；
  计划改为不依赖外部目录（或直接移除该入口）。
- 只有 Standard 版的云端构建，Low 版（Android 6–10，GeckoView）没有。
- dsh 0.2.0-rc.2 是预发布版：定时任务（schedule / time-context）被拆成可选插件，0.1.7 的一些模型 ID 被移除。旧会话能否全部打开需要真机确认。
- 应急运行时固定在 dsh 0.1.7-rc.2，和正式环境版本不同，这是有意的。

## 10. 待办

按优先级：

0. **把主语言迁到 Kotlin**（进行中）。批次、约定和雷区见 [docs/kotlin-migration.md](docs/kotlin-migration.md)。
   - 已完成：构建接入（AGP 9 内置 Kotlin 2.2.10）、本机验证链混编、三处静默失效的门禁、
     `util/ProjectLinks` / `util/ShellQuote`。
   - **踩过的坑**：`launcherSources` 里那 23 个类不能单独迁 —— 清单按 `.java` 文件名登记，
     改后缀必须和 `runtime_input_contract.py`、`runtime-descriptor.json` 一起动（P3 批次）。
     本机能拦住它：`python3 -B tools/test-runtime-input-contract.py`。
   - 已完成（P0 之二）：删死类 `DangerShellGuard` / `bridge/AppBridge`；`util/Rc1MigrationResult`
     的 `util → backup` 反向依赖改成注入 `StrictJsonRecord`。
   - 未完成：`util/Compat` 抽接口；包环（查清是 `HarnessController` / `ProotBootstrap` 两个上帝类的
     症状，跟着 P6/P7 的拆分一起消散，不单独塞接口）与 P1 剩余、P2–P8 各批次。
   - 发版前必须补：`.github/RELEASE_NOTES.md`、本文件第 11 节的版本记录，以及
     `python3 -B tools/prepare-runtime-descriptor.py --write`（动了 `launcherSources` 相关文件时）。
1. 真机验收 zzy.8：从桌面打开（冷启动 / 进程被回收后重建 / 回前台 / 覆盖更新先准备环境这四种）都要进网页；dsha-mobile 抽屉里点会话行要能进历史对话，抽屉打开时底栏仍可用，键盘弹出不挡输入区。
2. 真机验收 zzy.7 / zzy.6 遗留项：底部标签栏、全屏设置、动态玻璃的耗电和深色模式对比度、网页复制按钮和会话搜索、数据页自动备份入口、升级后 dsh-web-mobile 只被停用一次、覆盖安装后的组件更新和应急运行时。
4. ~~找一个能构建运行时的环境，修好 `adb-pair.py` 的包名并重新生成运行时描述。~~ 已完成，且不需要
   重新生成运行时描述（该文件不在契约里）。
5. 需要的话加上 Low 版云端构建。

## 11. 版本记录

| 版本 | 日期 | 内容 |
|---|---|---|
| zzy.1 | 2026-10-02 | 原生界面改版、折叠区、WebView 优化、云端构建、包名 `zzy.dsha.com` |
| zzy.2 | 2026-10-02 | 背景三选一、修复加载页重叠、视觉统一、首页精简 |
| zzy.3 | 2026-10-02 | 迁到独立仓库 DSHA-zzy，构建资产镜像到本仓库，签名密钥加密备份入库，新增本日志 |
| zzy.4 | 2026-10-02 | 应用内更新改读本项目 Releases，反馈入口改为 Issues，发版并入 Build APK |
| zzy.5 | 2026-10-02 | 改名 DeepSeek Harness Android、新图标、打开直接进网页、过渡动画、dsh 0.2.0-rc.2 并在 CI 重建运行时 |
| zzy.6 | 2026-10-03 | 修复加载页过早消失、动态玻璃改回可选、网页增强脚本、设置和数据页入口 |
| zzy.7 | 2026-10-03 | 内置 dsha-mobile 并默认启用，dsh-web-mobile 默认停用一次 |
| zzy.8 | 2026-10-03 | 修复打开不自动进网页（重建 / 回前台 / 环境准备后都算一次打开）、启动请求补发 3 次；内置 dsha-mobile 升到 0.2.0（侧栏进历史对话、底栏被遮罩挡住、键盘留白、设置面板色差） |
| **0.1.7-rc2-zzy.9** | 2026-10-03 | **本仓库第一个发行版**：独立包名 `zzy.dsha.Kotlin` 与独立签名（与原线可同时安装）；
端口自成一组 3180/3190/3181 并与其它 DSHA 版本错开，可同时运行；主语言开始迁到 Kotlin；
修掉 adb-pair.py 写死包名的老 bug；新增端口一致性与维护手册 |

每个版本的细节见 [CHANGELOG.md](CHANGELOG.md)。
