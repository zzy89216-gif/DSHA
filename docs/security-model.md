# 安全模型

> English: [security-model.en.md](security-model.en.md)

DeepSeek Harness Android（DSHA-zzy）在手机上运行 Ubuntu 容器和 dsh，agent 能在容器里执行任意命令，并能通过本机桥调用 Android 能力。本文列出它默认能访问什么、哪些能力要你手动开启，以及现有防护的边界。下文提到的类都在 `app/src/main/java/com/deepseekharness/app/`。

## 先说结论

- 只有一道真正的隔离：Android 应用沙箱。容器、插件、终端和 dsh 都以 App 自己的 Android UID 运行，彼此之间没有隔离。
- dsh 默认权限档位是 `danger-full-access`（`ConfigStore`）。Android 的 SELinux 策略不允许 bubblewrap，dsh 在容器内没有沙箱。
- 设备命令（ADB / Shizuku / Root）经过原生白名单 `util/DeviceShellPolicy`。这层只约束随包入口：`adb-shell`、设备桥的 `/exec`、Shizuku Binder 服务。容器里自己写的 Python/Node 程序、自写的 ADB 客户端、对共享存储的直接读写，都不受它约束。
- 敏感能力默认关闭，都可以撤销。全部不开，dsh 照样能用。

## 默认能访问的范围

刚装好、什么都没授权时：

| 对象 | 能否访问 | 说明 |
|---|---|---|
| 容器内的 Ubuntu | 完全控制 | agent 的工作区，`apt`、编译、起服务都在这里 |
| App 私有目录 | 可读写 | rootfs 在 `files/linux/ubuntu`，用户数据在 `files/user-data-v5/dsh` 或旧位置 `root/.dsh` |
| 共享存储 | 看 Android 授权 | 容器把 `/storage/emulated/0` 挂到 `/sdcard`（`runtime/ContainerRuntime.BINDS`）。挂载不等于授权，能读写多少取决于系统给 App 的存储权限 |
| 其他应用的私有数据 | 不能 | Android 应用沙箱 |
| `/system` | 不能写 | 容器里的 root 不是手机 Root |
| 位置 | 默认关 | 清单声明了粗略/精确定位，但要同时打开 App 内的位置能力和系统定位权限 |
| 短信 | 默认关 | 见下文「短信读取」 |
| 麦克风 | 按需申请 | 网页请求时才弹系统授权（`ui/BrowserMicrophone`），不预先授予 |

## 需要手动开启的能力

### 所有文件访问（设置 → 设备能力授权）

Android 11+ 跳到系统的「所有文件访问」设置，Android 6–10 申请 `WRITE_EXTERNAL_STORAGE`。开了以后，容器里的代码可以读写整个共享存储，包括相册和下载目录。用户数据仍在 App 私有目录，卸载 App 会一起删掉；要保留数据，先导出 `.dshbak` 备份。

### 设备命令通道（设置 → 设备能力授权）

三个通道共用同一套白名单，按 Root → Shizuku → ADB 的顺序选择已授权的那个（`HttpShellService.deviceExecute`）。

- 无线 ADB：身份是 `shell`（uid 2000）。配对后靠密钥对重连，配对码不保存。撤销方法：在系统设置里关掉无线调试，或撤销 USB 调试授权。ADB 密钥存在容器里，所以容器代码也能自己连 ADB，白名单管不到这种情况。
- Shizuku：通过 Binder 调 `ShellService`，执行前同样经过 `DeviceShellPolicy`。短信查询不走 Shizuku。
- Root：开关是 `allow_root_shell`，默认 false。需要手机本身已经 root，并由 root 管理器批准 `su`。DSHA 不获取也不安装 Root。用 Root 执行时白名单照常生效，另外禁止 Root 读取或递归遍历短信数据库目录。

### 短信读取（设置 → 设备能力授权）

偏好存在 `dsha_device_grants` 的 `sms_read`，默认关闭。关闭时短信查询直接返回 `[POLICY_BLOCKED]`；打开后，助手和插件可以查到号码、正文和时间，验证码也在其中。

`util/SmsQuery` 只接受 `content query --uri content://sms[...]`，字段、筛选条件和排序都有白名单，只能查 DSHA 所在的 Android 用户。不能发送、修改、删除短信，也不能借这个开关查询其他内容提供者。这项授权不会从备份或换机迁移中恢复。

### 屏幕操作

读屏、点按、输入等 `/app/ui/*` 端点走无障碍服务，跟设备命令白名单是两套机制。授权只在本次 DSH 运行期间有效，可在设备能力授权里撤销。前台是支付、银行、密码管理器或系统设置这类敏感应用时，每次操作都要确认。

### 流式悬浮条（设置 → 配置）

`overlay_stream`，默认关。需要系统悬浮窗权限，用来显示模型输出，也可以在悬浮条上直接批准或拒绝待确认的操作。它不读屏也不截屏，但内容显示在屏幕上，旁边的人看得到。

### 局域网访问（设置 → 配置 →「允许局域网访问」）

`lan_mode`，默认关。开启后 `LanProxyService` 监听 `0.0.0.0:3181`（`Constants.LAN_BRIDGE_PORT`），把请求转发给本机 dsh。

- 鉴权失败即拒绝：token 为空、缺失或不匹配都会被拒绝（`LanAuth.tokenOk`）。
- 首次用 URL 里的 token 访问成功后，换成 `HttpOnly; SameSite=Strict` 的 Cookie `dsha_lan`，再重定向去掉 URL 里的 token。
- 走的是 HTTP，没有 TLS。在不可信的网络上，token 和内容都可能被抓包。不要在公共 Wi-Fi 上开。
- 只转发到本机 dsh，不支持 CONNECT 或转发到任意目标。
- 请求头大小、字段数和连接数都有上限，SSE / WebSocket 单独计数。关闭 LAN 或进入维护时，现有连接会被断开。具体数值见[稳定性验收](stability-acceptance.md)。

## 设备命令白名单

`DeviceShellPolicy.inspect` 把命令拆成单条 argv 再判断，不执行用户给的 shell 脚本。

- 拒绝管道、重定向、`;`、`&`、变量和命令展开、控制字符，以及超过 8192 字符的命令。
- 只读命令（`ls`、`cat`、`ps`、`getprop`、`settings get/list`、`pm list/path/dump`、部分 `dumpsys`、`find` 的只读条件、`logcat -d/-t` 等）放行。
- 文件写入只允许 `mkdir touch cp mv rm rmdir rename`，必须写明确的绝对路径，不能用通配符或 `..`。可写范围只有共享存储里的普通子目录和 `/data/local/tmp`。存储根目录、DCIM、Pictures、Android/data、Android/obb 及其子目录只读。`cp` 可以从只读目录复制出来，`mv` 的源路径算写入。
- 直接拒绝：`dd`、各种 `mkfs`/`fsck`、分区工具、`setenforce`/`chcon`、`setprop`、`mount`/`umount`、刷机和重启类命令、`settings put`、`pm install/uninstall/clear`、`app_process`，以及所有不认识的命令。
- 结束进程只接受 `am force-stop|kill <完整包名>`、`kill <正数 PID>`、`killall/pkill <完整包名>`。执行前通道会重新拉取完整的应用清单，分成用户应用和系统应用两组（`util/DeviceAppPolicy`）；系统应用、系统 UID、DSHA 和 Shizuku 自己都受保护。同一批里有一个目标受保护，整批拒绝。

被拦截的命令返回 `[POLICY_BLOCKED]` 和 `[EXIT=126]`，没有「仍然允许」的选项。Root 开关、旧版确认开关和环境变量都放不过去。旧的 `/confirm` 端点只对只读命令返回 YES。执行过程中出错返回 `[EXECUTION_UNKNOWN]` 和 `[EXIT=125]`，表示命令可能已经执行，客户端不会自动换通道重试。

### 为什么不用「危险命令黑名单」

早期有一版 `DangerShellGuard`：列一批危险命令（`rm -rf`、`mkfs`、`pm clear`…），命中就弹确认。
它已被这里的白名单取代，但留下的取舍值得记住：

- **黑名单追不完。** shell 的表达能力决定了变量拼接、编码执行、间接调用都能绕过，任何模式表都有漏网。
- **滥判比漏判更危险。** 把 `>`、`mv` 这类整体判危，确认弹窗立刻变成噪音；用户点几次「允许」之后
  就不再读内容，那时真正危险的命令也拦不住了。这是「宁可漏判，不可滥判」的由来。
- **确认不是主防线。** 它防的是误操作和明显的恶意命令，**不是**定向攻击。真正的三道防线是：
  设备桥的 token 鉴权（未授权者进不来）、关键操作的用户确认（要人真的点一下）、以及 proot
  容器边界（碰不到宿主系统）。

所以现在只对**能完整识别的单条 argv** 做白名单判断、默认拒绝 —— 少判一条的代价，比让确认弹窗
失去意义小得多。

## 用户确认

需要确认的操作会同时发通知、在前台弹窗、显示在悬浮条上（如果开了）。三处共用同一个请求，第一次点击生效；60 秒没人处理就当作拒绝（`HttpShellService.requestUserConfirm`）。每个请求绑定当前桥的运行代次和一个随机 ID，DSH 重启后旧请求作废。

## 桥的路径保护

`/app/export` 能把文件导出到 `Download/DSHA/`，那里任何有存储权限的应用都能读。如果允许导出任意路径，容器里一条 curl 就能把 `/root/.dsh/.bridge_token` 放进公共目录，别的应用拿到 token 后就能读屏、点按、执行设备命令。同一目录下还有 `.credentials.yaml`（API Key 和会话密钥）和 `adbkeys/adbkey`（ADB 私钥）。

`util/BridgePathPolicy` 负责拦截，`/app/export` 和 `/app/readfile` 都要经过它：

- 拒绝空值和相对路径。
- 拒绝 `/root/.dsh`、`/root/.android`、`/root/.ssh`、`/root/.aws`、`/root/.config/gcloud`、`/root/.kube`、`/root/.dsha-*`，以及宿主侧的 `/data/data`、`/data/user`（rootfs 自身除外）。
- 先规范化 `..`、重复斜杠、反斜杠，再用 `getCanonicalPath()` 复核，防止用软链接绕过。
- 列目录时不显示这些凭据目录的条目。

导出普通产物（例如 `/root/report.md`）不受影响。单测见 `BridgePathPolicyTest`。

## 密钥和数据放在哪

| 内容 | 位置 | 保护方式 |
|---|---|---|
| 原生 API Key | App 的 SharedPreferences | `data/KeyVault`：Android Keystore 里的 AES/GCM 密钥，12 字节 IV 放在密文前，128 位认证标签，Base64 编码。未配置、设备未解锁、密钥丢失、无法读取分开处理，解密失败不会生成新密钥覆盖旧的 |
| 导出备份里的 API Key | 默认不导出；勾选后进入加密的 v5 备份 | 必须先在本机解密成功。只有旧设备 Keystore 密文的记录可能无法在新设备上使用 |
| 对话、设置、插件 | App 私有目录 | 只有应用沙箱保护。旧版的 `Documents/dshdata` 在公共存储，有存储权限的应用都能读 |
| `.dshbak` 备份 | 你在系统文件选择器里选的位置，另有一份私有验证副本 | 密码派生密钥 + AES-256-GCM，先完整认证再恢复，格式见 [backup-format-v5.md](backup-format-v5.md) |
| dsh 凭据、项目配置 | `.credentials.yaml`、`.env` 等 | 可能是明文，可能随所选范围进入加密备份。「不包含 API Key」只排除原生 API Key，不会扫描其他文件里的密钥 |
| 设备桥 token | `/root/.dsh/.bridge_token` | 容器内可读。不进备份；恢复后 `HttpShellService.resetTokenAfterRestore()` 会重新生成 |
| 设备授权、LAN 授权 | 本机私有记录 | 不能通过恢复备份获得 |

备份时还会处理几个只属于本机的文件（`assets/backup-engine.py`）：

| 文件 | 处理 |
|---|---|
| `.dsh/.bridge_token` | 不备份 |
| `.dsh/.anonymous-user-id` | 不备份 |
| `.dsh/.credentials.yaml` | 删掉 `records` 下 `client-connection/` 开头的记录（本机登录 Cookie 的签名密钥），保留 `refs` 里的 API Key。dsh 发现记录缺失会自己重新生成 |

恢复时，脚本、插件声明和不认识的内容先放进隔离区，不直接生效。

## 网络访问

App 里没有统计或日志上传。会产生网络请求的地方：

- 应用内更新读 `https://github.com/zzy89216-gif/DSHA/releases/latest/download/updates.json`，然后下载对应 APK。
- 插件市场和社区页目前会读取一个外部插件目录站点，这是全 App 唯一的外站访问入口（见 [HANDOVER.md](../HANDOVER.md) 的已知问题）。除此之外，App 不访问项目外的站点。
- 安装插件和依赖时访问所选的 npm registry 或镜像。
- dsh 访问你配置的模型服务。
- 已启用的插件可以自己发请求。

App 不限制容器和插件的网络访问。

本机设备桥监听 `127.0.0.1:3190` 和 `[::1]:3190`（端口由 `Constants.SHELL_BRIDGE_PORT` 决定）。同一台手机上的其他应用也能连这个端口，所以每个请求都要带 token。

## 插件

安装前只做静态检查：元数据、内容摘要、实际依赖。不会加载插件代码。依赖安装带 `--ignore-scripts` 和 `--ignore-pnpmfile`，生命周期脚本和 pnpmfile 钩子都不执行。启用前要你审阅确认。插件和容器同一个 UID，隔离目录不是沙箱，能装上不代表它安全。

## 核对安装包

发行版在 <https://github.com/zzy89216-gif/DSHA/releases>，附件是 `DSHA-<版本>.apk` 和同名的 `.sha256`。

```bash
sha256sum -c DSHA-<版本>.apk.sha256
apksigner verify --verbose --print-certs DSHA-<版本>.apk
```

- 包名应为 `zzy.dsha.Kotlin`。
- 签名证书 SHA-256 应为 `79:77:DF:F4:D4:52:C3:90:8D:AA:EA:91:F0:A2:0B:1A:BA:71:18:1B:73:4B:A4:3A:B5:48:98:FF:1E:31:42:8F`。

哈希只说明文件没被改过，证明不了是谁发布的；证书指纹才能证明发布方。工作流没有生成 GitHub 构建证明（attestation）。

## 已知弱点

| 弱点 | 现状 |
|---|---|
| dsh 没有沙箱 | 默认 `danger-full-access`，agent 对容器有完全控制权 |
| 白名单不是系统沙箱 | 只约束随包入口。容器代码能读 ADB 密钥、直接访问已授权的共享存储，这些只受 Android 权限限制 |
| 同 UID | 插件、终端和容器代码能读到传给运行环境的凭据，以及 App 私有目录里的其他数据 |
| `/sdcard` 挂载 | 授予存储权限后，容器代码能访问授权范围内的所有文件 |
| 旧版明文备份 | 旧的 `DSHA-backup-*.tar.gz` 和你手动复制的数据可能还在公共目录。新的加密导出不会去处理它们 |
| LAN 是 HTTP | 没有 TLS，见上文 |
| 只有一把签名密钥 | 发行版都用同一把 CI 密钥签名，换密钥会导致无法覆盖升级。加密备份见 [.github/signing/README.md](../.github/signing/README.md) |

发现问题请到 <https://github.com/zzy89216-gif/DSHA/issues> 反馈，安全问题优先处理。

来源声明与第三方许可见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。
