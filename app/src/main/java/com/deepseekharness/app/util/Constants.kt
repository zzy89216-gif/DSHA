package com.deepseekharness.app.util

/**
 * 全局常量统一管理：端口 / 路径 / SharedPreferences 键 / dsh 版本。
 * 骨架阶段只保留框架不变式，其余（通知 ID、ADB、LAN token 等）按需回填。
 *
 * 全部是 `const val`：Java 侧照旧写 `Constants.XXX`，编译期常量内联的语义也不变。
 */
object Constants {

    /** SharedPreferences 文件名（全 App 统一） */
    const val PREFS = "deepseekharness"

    // ================= 端口契约（框架不变式，见 AGENTS.md） =================
    //
    // 这三个数是**全 App 的唯一来源**：别处一律引用它们，不要再写数字字面量。
    // `tools/test-port-consistency.py` 会检查这一点。
    //
    // 数值刻意与其它 DSHA 版本（3080 / 3090 / 3081）错开：设备桥端口是独占的，
    // 两版同时装着又同时运行时，后启动的一方绑不上，设备工具就用不了。
    // 错开之后两个 App 可以并行跑，各自容器里的 agent 只会连到自己的桥。
    //
    // 容器侧（`assets/adb-shell.py`、内置插件）不写死这些数，而是读 App 写进 rootfs 的
    // `/root/.dsh/.bridge_port`（见 `HttpShellService.writeBridgePort`），
    // 所以以后再调端口只需要改这里。
    /** WebUI 默认端口 */
    const val DSH_WEB_PORT = 3180
    /** App 能力桥（agent 调 Android）端口 */
    const val SHELL_BRIDGE_PORT = 3190
    /** 局域网反向代理端口 */
    const val LAN_BRIDGE_PORT = 3181
    /** ADB 传统连接端口（兜底，非可靠路径） */
    const val ADB_DEFAULT_CONNECT_PORT = 5555

    // ================= 通知 ID（全局唯一，禁止重复） =================
    /** 危险命令确认通知（设备桥） */
    const val NOTIF_SHELL_CONFIRM = 3003

    // ================= dsh 版本（采用最新 @deepseek-ai/dsh） =================
    /**
     * 当前 APK 内置 dsh 版本（不是远端 latest 标签）。
     * 对应上游 deepseek-ai/deepseek-harness 仓库。
     */
    const val DSH_VERSION = "0.2.0-rc.2"
    const val DSH_RUNTIME_ID = "dsh-v" + DSH_VERSION
    /** 全局安装路径下的 dsh 入口（容器内路径，见 WebProcSel 的 cmdline 判据）。 */
    const val DSH_BIN_JS =
        "/usr/local/lib/node_modules/@deepseek-ai/dsh/lib/bin.js"

    // ================= SharedPreferences 键（历史键名保持兼容，见 AGENTS.md） =================
    const val KEY_API_KEY = "api_key"
    const val KEY_PORT = "port"
    const val KEY_MODEL = "model"
    const val KEY_WORKDIR = "workdir"
    const val KEY_PERMISSION_MODE = "permission_mode"
    const val KEY_WELCOMED = "welcomed"
    /** 强制用 GeckoView 内核（系统 WebView 过旧时兜底）。 */
    const val KEY_GECKO_CORE = "gecko_core"
    /** 危险 shell 操作需确认（DSH_CONFIRM）。 */
    const val KEY_CONFIRM_SHELL = "confirm_shell"
    /** 允许 root shell（--su 提权）。 */
    const val KEY_ALLOW_ROOT_SHELL = "allow_root_shell"
    /** 启动时检查更新。 */
    const val KEY_CHECK_UPDATE = "check_update"
    /** 电脑模式（预览用桌面浏览器 UA）。 */
    const val KEY_DESKTOP_MODE = "desktop_mode"
    /** 仅内置 DSH 网页支持画中画，默认关闭。 */
    const val KEY_PICTURE_IN_PICTURE = "picture_in_picture"
    const val KEY_PICTURE_IN_PICTURE_LAYOUT = "picture_in_picture_layout"
    /** 备份是否包含 API key。 */
    const val KEY_BACKUP_KEY = "backup_key"
    /** 局域网访问开关。 */
    const val KEY_LAN_MODE = "lan_mode"
    /** 局域网桥凭据（256-bit，等长比对，v2 键名）。 */
    const val KEY_LAN_TOKEN_V2 = "lan_token_v2"
    /** 容器运行时：proroot / proot。 */
    const val KEY_CONTAINER_RUNTIME = "container_runtime"
    /** 历史自动备份键，仅供升级时移除。 */
    const val KEY_AUTO_BACKUP = "auto_backup_launches"

    /** 默认工作目录（容器内路径）。 */
    const val DEFAULT_WORKDIR = "/root/deepseek-harness"
}
