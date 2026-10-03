package com.deepseekharness.app.util

/** 本项目（DSHA）的对外地址：仓库、问题反馈、发行版与应用内更新清单。
 *
 *  这是**唯一**写对外地址的地方。界面上不要另写 URL —— 换仓库时改一处就够。 */
object ProjectLinks {
    const val REPOSITORY = "https://github.com/zzy89216-gif/DSHA"
    const val ISSUES = "$REPOSITORY/issues"
    const val RELEASES = "$REPOSITORY/releases"

    /** 每个正式发行版都附带 updates.json；latest 始终指向最新的正式版。 */
    const val UPDATE_FEED = "$RELEASES/latest/download/updates.json"
}
