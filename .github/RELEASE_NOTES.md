## v0.1.7-rc2-zzy.10

迁到新仓库 <https://github.com/zzy89216-gif/DSHA>，成为一个独立的 App：
包名 `zzy.dsha.Kotlin`，用本仓库自己的 CI 签名密钥。与原 `DSHA-zzy`（`zzy.dsha.com`）、
上游 `com.dsh.client` 都不同包名也不同签名，三者可以同时安装、数据互不影响。
**没有从旧包升级的路径**，装这个版本等于新装一个 App。原 `DSHA-zzy` 与过渡仓库 `DSHA-zzy-kotlin`
已删除，本项目以**全新历史**重建于本仓库。

- 包名与签名都是自己的，可以与 `zzy.dsha.com`（原 DSHA-zzy）同时安装、互不影响。
- 端口自成一组（网页 3180 / 设备桥 3190 / LAN 3181），与其它 DSHA 版本错开，
  **两版可以同时运行**，不会再抢设备桥端口。
- 主语言开始从 Java 迁到 Kotlin：`util/` 里最高扇入的几个类已迁完，构建改走 AGP 9 内置 Kotlin。
  约定与雷区见 `docs/kotlin-migration.md`。
- 修掉「ADB 配对后自动授予无线调试保活」一直授给不存在包名的老 bug。
- 新增 `docs/maintenance.md` 维护手册。
- 构建改用 AGP 9 内置的 Kotlin（编译器 2.2.10），`jvmTarget` 17。
- 本机验证链支持 Java/Kotlin 混编：没有可执行的 aapt2 时也能编译并跑单测。
- `util/ProjectLinks`、`util/ShellQuote`、`util/GuestCommandOutcome` 已迁到 Kotlin。
- 应用内更新改为读取本仓库的发行版（`updates.json` 由发版工作流生成）。

## 安装与升级

- 包名 `zzy.dsha.Kotlin`，Android 11+、arm64-v8a。与上游 `com.dsh.client` 签名不同，可同时安装，数据分开。
- 已装 zzy.4 及之后版本：在「设置 → 版本更新」直接升级。zzy.3 及更早版本需手动安装一次。
- APK 的 SHA-256 见同名 `.sha256` 文件。

## 已知限制

- 「ADB 配对后自动授予无线调试保活」在本包名下不生效。
- 与其它 DSHA 版本同时运行时会抢设备桥端口。本 App 的端口与它们错开（设备桥 3190），正常情况下可以并行跑。
- 主语言迁移尚未完成，仓库里 Java 与 Kotlin 并存。

DSHA-zzy-kotlin 源自 DSH-APP/DSHA 0.1.7-rc2（MIT），与 DeepSeek 官方无关。完整记录见仓库 CHANGELOG.md。
