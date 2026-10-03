package com.deepseekharness.app.util

/**
 * 日志脱敏：把会泄露到 logcat / 活动日志的敏感值打码。
 * 骨架版只覆盖最关键的 API key 环境变量形态；完整版按原 SensitiveData 回填（含备份路径等）。
 *
 * 用预编译的 [Regex] 而不是 Java 的 `String.replaceAll`：Kotlin 把后者标记成隐藏
 * （建议改用 `replace(Regex, ...)`），而且原来的写法每次调用都要重新编译一遍模式。
 */
object SensitiveData {

    @JvmStatic
    fun redact(s: String?): String? {
        if (s == null) return null
        var safe = s.replace(PRIVATE_KEY, UiText.translated("[私钥已隐藏]"))
        // 替换串里的 $1 写成 \$1：Kotlin 字符串里 `$1` 虽然因「$ 后跟数字不是模板」
        // 而恰好是字面量，但那是靠规则巧合读懂的，写清楚才不会被后人「顺手改成 ${1}」。
        safe = safe.replace(HEADER_CREDENTIALS, "\$1***")
        safe = safe.replace(QUERY_CREDENTIALS, "\$1***")
        safe = safe.replace(KEY_VALUE_CREDENTIALS, "\$1***")
        safe = safe.replace(URL_USERINFO, "\$1***@")
        safe = safe.replace(BEARER, "Bearer ***")
        return safe.replace(TOKEN_SHAPES, "***")
    }

    private val PRIVATE_KEY = Regex(
        "(?s)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    private val HEADER_CREDENTIALS =
        Regex("(?im)((?:authorization|proxy-authorization|cookie|set-cookie)\\s*:\\s*)[^\\r\\n]+")
    private val QUERY_CREDENTIALS = Regex(
        "(?i)([?&](?:token|api[_-]?key|access[_-]?token|refresh[_-]?token|auth|secret|password)=)[^\\s&#'\"<>]+")
    private val KEY_VALUE_CREDENTIALS = Regex(
        "(?i)(\\b(?:[A-Z0-9_]*API_KEY|api[_-]?key|authorization|cookie|access[_-]?token|refresh[_-]?token|token|password|passwd|secret)\\b[\"']?\\s*[:=：]\\s*)(?:\"[^\"]*\"|'[^']*'|[^\\s,;<>]+)")
    private val URL_USERINFO = Regex("(?i)(https?://)[^\\s/@:]+:[^\\s/@]+@")
    private val BEARER = Regex("(?i)\\bBearer\\s+[A-Za-z0-9._~+/-]+=*")
    private val TOKEN_SHAPES = Regex(
        "\\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
}
