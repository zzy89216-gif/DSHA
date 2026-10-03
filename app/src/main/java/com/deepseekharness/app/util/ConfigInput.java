package com.deepseekharness.app.util;

/** 配置输入先整体校验，再写入，避免一半保存或静默改成另一个值。 */
public final class ConfigInput {
    private ConfigInput() { }

    public static int port(String value) {
        int port = number(value, com.deepseekharness.app.util.UiText.text("端口请输入 1—65535 的整数"));
        if (port < 1 || port > 65535) throw new IllegalArgumentException(com.deepseekharness.app.util.UiText.text("端口请输入 1—65535 的整数"));
        if (port == Constants.LAN_BRIDGE_PORT || port == Constants.SHELL_BRIDGE_PORT)
            // 可翻译部分保持为不含数字的常量串（否则 UiMessages 的精确匹配永远命不中），
            // 具体端口号拼在译文之外。
            throw new IllegalArgumentException(com.deepseekharness.app.util.UiText.text("该端口已被 App 桥接占用，请换一个端口")
                    + "（LAN " + Constants.LAN_BRIDGE_PORT
                    + " / 设备桥 " + Constants.SHELL_BRIDGE_PORT + "）");
        return port;
    }

    private static int number(String value, String error) {
        try { return Integer.parseInt(value == null ? "" : value.trim()); }
        catch (NumberFormatException e) { throw new IllegalArgumentException(error); }
    }
}
