# 备份格式 v5（.dshbak）

DSHA 导出的数据备份是一个加密文件，名字固定为 `DSHA-data-v5-<UUID>.dshbak`。文件分两层：外层是密码加密，解密后是 `DSHADATA` 记录容器。代码在 `app/src/main/java/com/deepseekharness/app/backup/`：

| 类 | 职责 |
|---|---|
| `PortableBackupCrypto` | 外层加密与解密 |
| `BackupArchive` | 明文容器的写入、读取和校验 |
| `BackupLimits` | 数量、大小和路径规则 |
| `LegacyTarReader`、`LegacyBackupImporter` | 读取旧版 tar.gz 备份并转换为 v5 |
| `VerifiedBackupCopy` | 重新导出本机已验证过的副本 |
| `DataFormatEvidence` | 清单中的数据格式声明 |

文件名不能用 `DSHA-backup-*.tar.gz`：旧版本会把这种名字当作全量备份来恢复。导出时必须设置密码，没有明文导出。

## 外层：加密

整数一律大端。文件头 48 字节：

| 偏移 | 长度 | 内容 |
|---:|---:|---|
| 0 | 8 | ASCII `DSHABAK5` |
| 8 | 4 | 版本，固定 5 |
| 12 | 4 | PBKDF2 迭代次数，新文件写 600000 |
| 16 | 4 | 算法套件，固定 1 |
| 20 | 16 | salt |
| 36 | 12 | GCM nonce |

套件 1：

- 密钥：PBKDF2-HMAC-SHA256，输出 256 位。
- 加密：AES-256-GCM，128 位认证标签。整个 48 字节头作为附加认证数据（AAD）。
- 头之后是密文，最后 16 字节是认证标签。
- salt 和 nonce 每次导出用 `SecureRandom` 重新生成。

读取时先检查头：魔数、版本、套件不对，或者迭代次数不在 600000–1200000 之间，直接拒绝，不做密钥派生。

密码按 UTF-8 编码，不做 Unicode 归一化，长度 12–1024 个 Java `char`。任务结束时，密码字节、派生密钥和读写缓冲区都会清零，但 JVM 或闪存里可能还残留副本，这一点不做保证。

参数选择参考了 [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)。实现用 Bouncy Castle 轻量 API，不替换系统 Provider；版本和摘要锁定在 `tools/backup-dependencies.lock.json`，许可证见 `THIRD_PARTY_NOTICES.md`。

GCM 要读到最后才能校验标签，所以解密过程中写出的明文只放在本次任务的私有隔离文件里，等 `doFinal` 校验通过、外层读完以后，才开始解析和预检。认证通过只能说明文件没被改过，证明不了是谁发的。

不导出原生 API Key 不等于备份里没有秘密：对话、项目文件、`.env`、插件配置里都可能有，所以必须加密。

## 内层：明文容器

顺序：

1. ASCII `DSHADATA`，再跟 4 字节版本 5。
2. 若干条记录。每条依次是：4 字节元数据长度、UTF-8 JSON 元数据、8 字节载荷长度、载荷。
3. 4 字节 `-1` 作为结束标记，然后是 4 字节清单长度和 UTF-8 JSON 清单。
4. 32 字节 SHA-256，覆盖前面所有字节（包括结束标记和清单）。这之后必须是文件末尾。

### 记录

| 字段 | 要求 |
|---|---|
| `root` | 逻辑根 ID，匹配 `[a-z][a-z0-9_-]{0,79}` |
| `path` | 根内相对路径，空串表示根本身 |
| `kind` | `FILE`、`DIRECTORY`、`LINK`、`MISSING`、`UNREADABLE`、`EXCLUDED` 之一 |
| `scope` | `application`、`sessions`、`settings`、`plugins`、`projects` 之一 |
| `size` | 载荷长度 |
| `sha256` | `FILE` 必须是 64 位小写十六进制；其他类型必须为空，且 `size` 为 0 |
| `mode` | 可选，0–0777 |
| `target` | `LINK` 必填，最长 2048，不能含 NUL 或反斜杠 |

空目录、缺失的目录和读不出来的目录分别记为 `DIRECTORY`、`MISSING`、`UNREADABLE`，不会混为一谈。父目录必须写在子项之前。一个路径不能既是文件又是目录。

### 清单

必须包含 `formatVersion`（5）、`entries`、`bytes`、`operation`、`integrity`、`createdAt`、`appVersion`、`runtime`、`dataFormat`、`sensitivePolicy`、`plugins`、`roots`。

- `entries` 和 `bytes` 必须等于实际读到的记录数和载荷总字节数。
- `operation` 取 `EXPORT`、`MAINTENANCE`、`RESCUE` 之一。
- `roots` 列出每个逻辑根的 `id` 和 `scope`，不能重复，集合必须跟记录里出现的根完全一致。`scope` 为 `application` 的根可以包含任意分类的记录；其他根只能包含自己那一类。
- 导出时额外写 `requestedScope`，即你选择的备份范围。
- `dataCompatibility` 记录数据格式声明。拿不到可靠声明时，`formatId` 和 `formatEpoch` 留空，`status` 为 `unknown`。APK 版本、运行时版本、数据格式是三个独立的版本号。别的设备写的声明不算本机验证过：预检照样显示格式未确认，不会据此自动降级，也不会删除原件。

`integrity` 表示备份时数据有多稳定：

| 值 | 含义 |
|---|---|
| `QUIESCENT` | 已停止应用的写入任务，并对所有来源复核过 |
| `EXTERNAL_CHECKED` | 应用写入已停止；有些来源其他应用也能改，只做了重复读取校验，没有冻结它们 |
| `BEST_EFFORT` | 只读救援，没有静止保证 |
| `PARTIAL` | 有缺失、读不到或备份过程中变化的条目，清单里有记录 |

记录里出现 `MISSING` 或 `UNREADABLE` 时，`integrity` 只能是 `PARTIAL` 或 `BEST_EFFORT`。

## 上限与路径规则

上限见 `BackupLimits`，按实际读写的字节数计算，不相信文件自己声明的大小：

| 项 | 上限 |
|---|---|
| 载荷总量 | 16 GiB |
| 记录数 | 100000 |
| 逻辑根 | 512 |
| 单条元数据 | 16 KiB |
| 所有元数据合计 | 32 MiB |
| 清单 | 2 MiB |
| 路径长度 / 层数 | 2048 字符 / 64 层 |
| 链接深度 | 40 |
| 加密流在载荷之外的额外开销 | 256 MiB |

路径不能以 `/` 开头，不能带盘符、反斜杠、NUL、换行，也不能有空段、`.` 或 `..`。判断重名时先做 NFC 归一化再转小写，这样在大小写不敏感的文件系统上会撞名的两个条目会被直接拒绝；遇到无法处理的命名，读取报错，不会悄悄丢掉条目。

## 恢复

载荷先按顺序写进私有目录下的编号槽位，归档里的路径不会直接当作写入目标。真正写到哪里由本机决定（`NativeRestoreTargets`），再按白名单核对一遍：

- 原生设置走白名单导入。
- 插件、可执行脚本、插件声明进入隔离区，不直接生效。
- PID、环境标记、桥凭据、旧事务状态只保留在输入副本里，不会应用到当前设备。
- 不认识的逻辑根或范围直接拒绝，不会当作全量恢复。

## 旧版备份

`LegacyTarReader` 读旧的 tar.gz：

- 校验 tar 头校验和、PAX 长度、成员类型，以及 gzip 的 CRC 和 ISIZE，并一直读到外层文件末尾。
- 拒绝特殊文件、稀疏文件、逃出根目录的路径、重复成员、拼接的 gzip 和尾部多余数据。

`LegacyBackupImporter` 把 v1–v4 转成 v5，然后跟 v5 走同一套预检：

- `formatVersion` 不在 1–4 之间直接拒绝。
- v3/v4 的清单 inventory 必须与实际成员逐一对上，而且不能含链接。
- v1/v2 的链接只能指向包里已经校验过的载荷，不会去读归档里写的宿主路径。
- 旧包没写 scope 时，只能从已知的历史文件名推出来，推出来的还要你确认；不认识的 scope 直接拒绝。

现有测试主要用合成样本，不代表所有历史备份都验证过。

## 导出与重新导出

一次导出的步骤：

1. 在私有目录生成加密文件，完整读一遍并重新解密验证。
2. 写到你在系统文件选择器里新建的位置。
3. 如果能读回，比较整个密文的 SHA-256。读不回时显示「已写入，目标读回未验证」，保留私有副本，不更新 `latest.json`。

取消或失败不会覆盖上一次成功的记录。

数据页可以把保留下来的私有加密副本再导出一次。`VerifiedBackupCopy` 读 `verified.json`，核对类型、大小、文件头魔数和整个密文的 SHA-256 后才复制。内容不重新加密，密码还是原来的。这项检查依赖本机之前做过完整验证，不是对发件人身份的认证。

- 范围取 `requestedScope`；早期记录没有这个字段时，从 `roots` 推出。推不出或者不认识就拒绝。
- 重新导出不会把 `PARTIAL`、`BEST_EFFORT` 或插件依赖警告变成「完整」。新位置读不回时同样不更新 `latest.json`。

## 测试向量

`tools/generate-backup-vector.mjs` 用 Node 的 OpenSSL 生成 `app/src/test/resources/backups/v5-aesgcm-vector.json`。里面的密码、salt、nonce、明文和密钥都是公开的测试数据，不要用于其他地方。`PortableBackupCryptoTest.independentOpenSslFixedVectorAndJceInteroperate` 检查 Bouncy Castle 和 JCE 解出的结果一致。
