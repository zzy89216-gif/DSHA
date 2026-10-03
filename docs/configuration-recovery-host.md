# 宿主配置检查点与恢复

配置检查点只覆盖六个固定文件，由 Android 宿主文件系统执行，不经过命令行，也不碰会话、附件、工作区或 KeyVault。实现：`backup/ConfigurationSnapshots.java`，入口：`core/StartupRepairs.java`。

固定文件：

- `profiles/web/package.json`
- `profiles/web/cordis.patch.yml`
- `profiles/web/pnpm-workspace.yaml`
- `profiles/web/pnpm-lock.yaml`
- `settings.yaml`
- `cordis.patch.yml`

符号链接和不可读路径报错，不当成空文件。单文件上限 4 MiB。原生偏好和 Keystore 不在这六个文件的事务里。

## 命令

`StartupRepairs` 接受：`list`、`prepare`、`healthy`、`before`、`new`、`restore`、`recover`。`new` / `restore` / `recover` 必须在维护屏障内。插件的安装和删除走独立管理器，失败不会挡住原生配置记录显示。

## 存储位置

| 路径（均在应用 files 下） | 内容 |
|---|---|
| `startup-config-snapshots/<UUID>/` | 新检查点。0–5 是六个文件的独立正文，`metadata.json` 记存在状态、大小和 SHA-256 |
| `startup-config-operations/<UUID>/` | 一次恢复事务，复用 `HostDataTransaction` |
| `host-backup-operations/<UUID>/config-reset.json` | 「重置配置」的记录，见下一节 |

生成检查点后会重新读取来源和私有副本，校验通过才更新小型目录索引。槽位：三次 `healthy-1..3`、三次 `before-1..3`，启动前 `candidate` 单独引用。恢复期间选中的检查点会钉住，避免被「修复前」轮换删掉。

健康检查点必须同时满足：启动 ID 和六文件内容都与启动前捕获值一致。界面变化、源文件变化或检查点损坏不能写出假的健康记录。

## 事务顺序

先留「修复前」检查点 → 准备候选和逐文件前后摘要 → 写 switching 意图 → 切换文件并确认 → finalized。配置正文不走命令行。

处理中断的旧 `dsha-startup-checkpoints/pending.json` 时，先固定私有输入副本。Native 事务已经 finalized 而旧日志还没搬走，只收尾旧日志，不会再用旧配置盖住后来的用户改动。只剩旧状态标记、没有日志时，把标记留到私有记录，当前配置不变。

界面会列出检查点里原本缺失、恢复后仍会缺失的固定文件。部分修复只作用于所选固定文件。Rootfs 损坏、检查点损坏、缺日志、恢复成功分别记录，不用「新建空目录」假装环境就绪。

## 旧格式

v1 JSON/base64 检查点（dsh 目录下 `dsha-startup-checkpoints/<槽位>.json`）仍可读：整份上限 36 MiB、单文件 4 MiB，逐个解码校验。界面标识为 `legacy-healthy-*` / `legacy-before-*`。不跑 Python，也不任意反序列化配置内容。

## 重置配置

「重置配置」走 `NativeConfigurationReset`，只动 `settings.yaml` 和当前私有工作目录的 `.env`，与上面六文件检查点无关。凭据先检查解密，失败就不生成空配置覆盖原件。外部目录、配置软链接、跨文件系统目标不强行重置。中断由统一宿主恢复入口处理。

## 测试

`ConfigurationSnapshotsTest`、`ConfigurationCrashProcess`。进程强杀测试用真实临时目录。
