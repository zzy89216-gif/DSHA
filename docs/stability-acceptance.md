# 稳定性验收入口

`tools/verify-stability.py` 是本仓库的本地软件验收脚本（来自历史基线那套实现，身份常量已切到本 App）。它会跑两 flavor 的 JUnit、Lint、Release 打包、若干 Node/Python 检查，以及 APK 资产/ELF/签名核对。本仓库的日常发布不走这条路径，以 GitHub Actions 的 Build APK 为准（见 [BUILD.md](../BUILD.md) 第 9 节）。

## 运行

需要本机 JDK 17、Android SDK、Node，以及测试运行时夹具：

```bash
python tools/prepare-test-runtime.py
python tools/verify-stability.py
```

脚本会把报告写到 `app/build/stability-acceptance/<UUID>/manifest.json`。源码或资产在检查过程中被改过会失败。

可选参数：

| 参数 | 作用 |
|---|---|
| `--node` | Node 可执行文件 |
| `--java-home` / `--sdk` | JDK 与 SDK 路径 |
| `--deliver` | 检查通过后把 APK 和 SHA-256 复制到仓库 `release/` |
| `--device-evidence <JSON>` | `--deliver` 必需。真机非破坏性覆盖安装的独立记录 |

`--device` 旧审计包流程已停用，不会再生成独立测试 APK。

脚本按**本 App 的身份**核对：只有设置了 `DSHA_KEYSTORE` 才打 Release，打出的 APK 用 apksigner 核对时
必须是脚本常量 `CERT`（= 本 App 的发布证书，见 [HANDOVER.md](../HANDOVER.md) 第 3 节），包名必须是
`PACKAGE`（`zzy.dsha.Kotlin`）。这两个常量原先写的是别的身份的证书与 `com.dsh.client`，已随本 App 换成独立包名
和独立签名一起改过。

这套脚本不参与 CI（以 Build APK 为准）；要用它得在本机提供上面那把密钥库，否则到 APK 核对
就会失败。`--deliver` 写的是 `release/dsha-<versionName>.apk`，和 CI 的 `DSHA-*.apk` 命名无关。

`--device-evidence` JSON 必须含：`schema: 1`、`package: "zzy.dsha.Kotlin"`、`versionCode`、`certificateSha256`（本 App 的发布证书）、实际 `serial`、`firstInstallTimePreserved: true`、`nonDestructive: true`；`flavors.standard` 与 `flavors.low` 分别写本轮候选 APK 的小写 `sha256`、`result: "PASS"`，以及已完成的 `checks`：`web-ready`、`existing-data-preserved`、`plugins-visible`、`recovery-ready`、`no-crash`。原始设备输出另存，不要把旧包的记录挪给新包。

## 脚本实际检查什么

- 两 flavor 的 `test*DebugUnitTest`、`lint*Release`、`assemble*Release`。
- Node：`test-startup-diagnostics.mjs`、`test-issue67-startup.mjs` 等。
- Python：`test-plugin-{discovery,dependencies,transactions,review}.py`。
- 对打出的 APK 跑 `verify-dsh-upgrade-apk.py`、`audit-standard-apk.py`、apksigner、aapt。
- 通过后把变更过的源码和文档打进 `source-changes.zip`（`docs/`、`README.md`、`README.en.md`、`BUILD.md`、`AGENTS.md`、`CHANGELOG.md`、`THIRD_PARTY_NOTICES.md`）。它只按文件名收档，不解析文档内容。

## 相关代码边界（仍有效）

这些是当前源码里的限制，不是某次构建的流水账。

HTTP 与连接：`util/HttpProtocol` 限制行、字段、总量和数量，未鉴权头有 5 秒绝对预算。LAN 总头 64 KiB、请求行与字段各 16 KiB、最多 100 字段。本地设备桥总头 128 KiB、请求行 96 KiB，以容纳 `DeviceShellPolicy` 8192 字符命令百分号编码后的最坏情况。SSE/WebSocket 不被头期限截断。LAN 连接由 `SocketDispatch` 限流。歧义 framing 直接拒绝。依据：[RFC 9112 §6.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)、[RFC 9110 §7.6.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-7.6.1)、[RFC 6455 §4](https://www.rfc-editor.org/rfc/rfc6455.html#section-4)。只做本项目需要的 HTTP/1.1 原点请求和 chunked，不扩展 CONNECT。

插件：锁文件证明可复现解析和文件完整性，不证明作者可信。安装脚本和 pnpmfile 不执行。审阅是静态检查，同 UID 插件不是恶意代码沙箱。激活观察绑定启动 ID。回退只恢复插件组合和对应原生记录。

保留数据：没有自动删除。旧树默认只读；恢复先预检再确认。`DataFormatEvidence` 在缺少可靠格式声明时把 `formatId` / `formatEpoch` 标为 unknown。APK 版本、运行时版本和数据格式不是同一代次。发件人声明不构成本机验证。保留副本入口见 `RetainedCatalogue` / `RetainedDataActivity`。

凭据：`CredentialRead` / `KeyVault` 区分未配置、可读、暂不可用、需处理。解密失败时保留密文，不写空配置覆盖原件。

设备审计代码在 `app/src/deviceAudit/`，只有用 `--init-script tools/device-backup-audit.init.gradle` 构建时才会注入，普通 release 不含这些入口。

## 本仓库不声称的内容

本文件不记录具体某次构建的验收结果。静态 16 KiB 对齐、JVM 单测通过，都不等于真机验收完成。
