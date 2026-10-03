package com.deepseekharness.app.util

import java.util.Locale

/** 进度/速率/时长的格式化 + 平滑速率估算（纯逻辑，可单测）。 */
object Fmt {

    @JvmStatic
    fun bytes(b: Long): String {
        if (b < 1024) return "$b B"
        val kb = b / 1024.0
        if (kb < 1024) return String.format(Locale.US, "%.1f KB", kb)
        val mb = kb / 1024.0
        if (mb < 1024) return String.format(Locale.US, "%.1f MB", mb)
        return String.format(Locale.US, "%.2f GB", mb / 1024.0)
    }

    @JvmStatic
    fun rate(bps: Double): String {
        if (bps < 1024) return String.format(Locale.US, "%.0f B/s", bps)
        if (bps < 1024 * 1024) return String.format(Locale.US, "%.0f KB/s", bps / 1024.0)
        return String.format(Locale.US, "%.1f MB/s", bps / 1024.0 / 1024.0)
    }

    @JvmStatic
    fun eta(seconds: Long): String {
        if (seconds < 0) return "--"
        if (seconds < 60) return "$seconds" + UiText.translated(" 秒")
        val m = seconds / 60
        if (m < 60) {
            return "$m" + UiText.translated(" 分 ") + (seconds % 60) + UiText.translated(" 秒")
        }
        return (m / 60).toString() + UiText.translated(" 时 ") + (m % 60) + UiText.translated(" 分")
    }

    /** 平滑速率估算：每 500ms 采样一次，避免数字乱跳。 */
    class RateMeter {
        private var lastDone = 0L
        private var lastTime = 0L
        private var rate = 0.0

        fun feed(done: Long): Double {
            val now = System.currentTimeMillis()
            if (lastTime == 0L) {
                lastTime = now
                lastDone = done
                return 0.0
            }
            val dt = now - lastTime
            if (dt >= 500) {
                rate = if (dt > 0) (done - lastDone) * 1000.0 / dt else 0.0
                lastTime = now
                lastDone = done
            }
            return rate
        }

        fun eta(done: Long, total: Long): Long =
            if (rate > 0 && total > done) ((total - done) / rate).toLong() else -1L
    }
}
