package com.deepseekharness.app.util

/** 运行时文案与 XML 资源共用应用语言；此层不访问 Android 或用户文件。 */
object UiText {

    /** 这些前缀仍用于内部状态识别，只在应用状态控件的边界翻译。 */
    private val PREFIXES = arrayOf("环境任务进行中：", "环境任务进行中", "重置失败：")
    private const val TOOL_RUNNING = "⚙ 正在使用 "

    // 名字不能叫 language：下面有个同名函数，虽然不冲突，读起来会混。
    @Volatile
    private var renderLanguage: String = "zh"

    /**
     * 设置渲染语言。只接受**生效语言** zh/en：`system` 等偏好值会被
     * 解析成当前系统语言，避免把「跟随系统」当成第三种语言塞进渲染层（那会让 choose()
     * 永远走中文分支）。
     */
    @JvmStatic
    fun setLanguage(value: String?) {
        renderLanguage = UiLanguagePreference.resolve(value, SystemLanguage.tag())
    }

    @JvmStatic
    fun language(): String = renderLanguage

    @JvmStatic
    fun choose(chinese: String?, english: String?): String? =
        if ("en" == renderLanguage) english else chinese

    @JvmStatic
    fun text(value: String?): String? {
        if (value == null || "en" != renderLanguage) return value
        return UiMessages.EN[value] ?: value
    }

    @JvmStatic
    fun text(value: CharSequence?): CharSequence? {
        if (value == null) return null
        val translated = text(value.toString())
        return if (translated == value.toString()) value else translated
    }

    @JvmStatic
    fun text(resource: Int): Int = resource

    @JvmStatic
    fun text(values: Array<String?>): Array<String?> {
        val translated = values.clone()
        for (i in translated.indices) translated[i] = text(translated[i])
        return translated
    }

    /**
     * 取译文，参数非空就一定回非空 —— 给 Kotlin 调用点用的入口。
     *
     * 为什么需要它：[text] 要保留 Java 侧「传 null 得 null」的语义，签名只能是 String?，
     * 于是每个 Kotlin 调用点都得写 `?: 原文`。与其在几十个文件里各抄一份小助手
     * （ui/ 里那个 `t(zh,en)` 已经被抄了 14 份），不如在这里给一个明确的非空入口。
     */
    @JvmStatic
    fun translated(value: String): String = text(value) ?: value

    /** 这些前缀仍用于内部状态识别；只在应用状态控件的边界翻译。 */
    @JvmStatic
    fun status(value: String?): String? {
        val translated = text(value)
        if (value == null || value != translated || "en" != renderLanguage) return translated
        for (prefix in PREFIXES) {
            if (value.startsWith(prefix)) return text(prefix) + text(value.substring(prefix.length))
        }
        return value
    }

    /** 仅翻译内置工具状态首行，下面的命令、路径和模型内容保持原样。 */
    @JvmStatic
    fun toolStatus(value: String?): String? {
        if (value == null || "en" != renderLanguage) return value
        val line = value.indexOf('\n')
        val head = if (line < 0) value else value.substring(0, line)
        val tail = if (line < 0) "" else value.substring(line)
        if (!head.startsWith("⚙ ")) return value
        var headTranslated = text(head) ?: head
        if (headTranslated == head && head.startsWith(TOOL_RUNNING)) {
            headTranslated = translated(TOOL_RUNNING) + head.substring(TOOL_RUNNING.length)
        }
        return headTranslated + tail
    }
}
