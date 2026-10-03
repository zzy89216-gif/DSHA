#!/usr/bin/env python3
"""锁定三个已修复的回归点：语言可发现性、系统语言识别、通知可点击。

纯静态断言（读源码/资源），不需要 Android 运行时，可在 CI 与本地快速跑：
  python3 tools/test-dsha-ui-regressions.py

为什么用源码断言而不是单测：这三处都不是纯逻辑 —— 它们分别落在布局代码、
偏好解析与 PendingIntent 构建上，跑起来需要 Activity/NotificationManager。
这里钉住的是「修复本身的存在与形状」，防止后来的重构悄悄改回去。
"""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / 'app/src/main/java/com/deepseekharness/app'

SOURCE_EXT = ('.java', '.kt')


def read(path):
    """读源码/资源。给 `.java` 路径时自动回落到同名 `.kt`。

    主语言迁移期间同一个类可能是 .java 也可能是 .kt。查找放宽、**断言不放宽**：
    这里读的是源码文本，某条断言是否还成立必须逐条确认（例如 UiText 的
    resolve 语义），所以文件能读到、内容对不上就该失败，而不是静默跳过。
    """
    target = ROOT / path
    if not target.is_file() and target.suffix in SOURCE_EXT:
        alt = target.with_suffix('.kt' if target.suffix == '.java' else '.java')
        if alt.is_file():
            target = alt
    return target.read_text(encoding='utf-8')


def compact(text):
    """去掉所有空白后比较，让断言不绑死在某一种语言的排版上。"""
    return re.sub(r'\s+', '', text)

class LanguageDiscoverability(unittest.TestCase):
    """语言入口必须让非中文用户找得到：标题带英文，且默认/系统语言要能自动选英文。"""

    def setUp(self):
        self.settings = read('app/src/main/java/com/deepseekharness/app/ui/SettingsFragment.java')

    def test_language_entry_shows_english_on_chinese_ui(self):
        # 中文界面下标题仍含 Latin 的 "Language"（原来只有「语言 · 简体中文」）
        import xml.etree.ElementTree as ET
        root = ET.fromstring(read('app/src/main/res/layout/fragment_settings.xml'))
        a = '{http://schemas.android.com/apk/res/android}'
        row = next(node for node in root.iter() if node.get(a+'id') == '@+id/settings_appearance')
        self.assertEqual(row.get(a+'focusable'), 'true')
        self.assertTrue(any('Language' in node.get(a+'text', '') for node in row.iter()))

    def test_language_entry_uses_stable_resource_id(self):
        self.assertIn('v.findViewById(R.id.settings_language)', self.settings)
        self.assertNotIn('appearance.getChildAt', self.settings)
        self.assertIn('@+id/settings_language', read('app/src/main/res/layout/fragment_settings.xml'))

    def test_language_dialog_offers_follow_system(self):
        self.assertIn('UiLanguagePreference.SYSTEM', self.settings,
                      "语言对话框必须提供「跟随系统」选项")
        self.assertIn('"English"', self.settings,
                      "语言选项必须有原样 English（不翻译），保证任何语言下都认得出")

    def test_preference_key_matches_history(self):
        # 不能改历史 SharedPreferences 键名，否则老用户语言丢失
        config = read('app/src/main/java/com/deepseekharness/app/core/ConfigStore.java')
        self.assertIn('"ui_language"', config)

class PluginRecyclerSetup(unittest.TestCase):
    """插件页的头尾条目必须在 RecyclerView 有 LayoutManager 后创建。"""

    def test_header_footer_are_inflated_after_layout_manager(self):
        src = read('app/src/main/java/com/deepseekharness/app/ui/PluginFragment.java')
        layout = src.index('list.setLayoutManager(')
        header = src.index('R.layout.plugin_list_header')
        footer = src.index('R.layout.plugin_list_footer')
        self.assertLess(layout, header)
        self.assertLess(layout, footer)
        self.assertIn('inflate(R.layout.plugin_list_header, list, false)', src)
        self.assertIn('inflate(R.layout.plugin_list_footer, list, false)', src)

class SystemLanguage(unittest.TestCase):
    """默认跟随系统：非中文系统落英文；显式选择优先。"""

    def setUp(self):
        self.pref = read('app/src/main/java/com/deepseekharness/app/util/UiLanguagePreference.java')

    def test_system_is_a_supported_value(self):
        self.assertIn('String SYSTEM = "system"', self.pref)
        self.assertIn('return SYSTEM.equals(value) || ZH.equals(value) || EN.equals(value);', self.pref)

    def test_resolve_prefers_explicit_choice(self):
        self.assertIn('return SYSTEM.equals(chosen) ? resolveLanguage(languageTag) : chosen;', self.pref)

    def test_non_chinese_falls_back_to_english(self):
        # 只有中文落中文，其它语言（含无法识别）落英文
        self.assertIn('return isChinese(languageTag) ? ZH : EN;', self.pref)

    def test_ui_text_never_stores_system_as_a_render_language(self):
        ui = compact(read('app/src/main/java/com/deepseekharness/app/util/UiText.java'))
        # 渲染层只应看到 zh/en；system 必须被解析掉，否则 choose() 永远走中文分支
        self.assertIn('=UiLanguagePreference.resolve(value,SystemLanguage.tag())', ui)
        self.assertNotIn('UiLanguagePreference.normalize(value)', ui)

    def test_configstore_resolves_against_system(self):
        config = read('app/src/main/java/com/deepseekharness/app/core/ConfigStore.java')
        self.assertIn('SystemLanguage.tag()', config)
        # 备份里保存偏好（可能是 system），而不是解析后的生效语言
        self.assertIn('getUiLanguageForBackup()', config)

class NotificationClickable(unittest.TestCase):
    """智能体通知必须能点回 App，且落到能看结果的地方。"""

    def setUp(self):
        self.shell = read('app/src/main/java/com/deepseekharness/app/HttpShellService.java')

    def test_app_notify_sets_content_intent(self):
        body = re.search(r'private String appNotify\(String path\)\s*\{(.*?)\n    \}', self.shell, re.S)
        self.assertIsNotNone(body, "找不到 appNotify")
        self.assertIn('setContentIntent(', body.group(1),
                      "/app/notify 的通知必须带 setContentIntent，否则点击无反应")

    def test_content_intent_targets_main_activity_with_open_web(self):
        m = re.search(r'private PendingIntent agentNotificationIntent\(\)\s*\{(.*?)\n    \}', self.shell, re.S)
        self.assertIsNotNone(m, "找不到 agentNotificationIntent")
        body = m.group(1)
        self.assertIn('ui.MainActivity.class', body)
        self.assertIn('open_web', body, "通知点击应请求直接进入 Web 会话，而不是只停在启动页")
        self.assertIn('FLAG_IMMUTABLE', body, "Android 12+ 要求 PendingIntent 显式指定可变性")
        self.assertIn('FLAG_ACTIVITY_CLEAR_TOP', body)

    def test_auto_enter_judges_by_auth_url_not_by_failure_message(self):
        # getWebAuthFailure() 是「最近一次鉴权结果消息」，初始值与成功值都非 null
        # （成功时是"鉴权成功"）。拿它当成功判据会导致永不进入。
        launch = read('app/src/main/java/com/deepseekharness/app/ui/LaunchFragment.java')
        self.assertNotIn('getWebAuthFailure() == null', launch,
                         "自动进入不能用 getWebAuthFailure()==null 判成功：该值恒非 null")
        self.assertIn('pendingAutoEnter && !enteringWeb && !webEntryUrl().isEmpty()', launch,
                      "自动进入应以「鉴权链接已就绪」为判据")

    def test_direct_web_survives_recreate_and_relaunch(self):
        # 真机问题「打开后不自动进网页」：原来的判据只在 savedInstanceState==null
        # 的分支里算一次，点桌面图标（进程被回收后重建 / 回前台收到启动 Intent）永远不命中。
        main = read('app/src/main/java/com/deepseekharness/app/ui/MainActivity.java')
        self.assertIn('state.putBoolean(STATE_DIRECT_WEB_ARMED, directWebArmed)', main,
                      "自动进网页的意图必须随实例状态保存，重建后接着走")
        self.assertIn('savedInstanceState.getBoolean(STATE_DIRECT_WEB_ARMED, false)', main)
        self.assertIn('if (mayAutoEnterWeb(intent))', main,
                      "onNewIntent 也要认桌面启动，否则回到前台不会进网页")
        self.assertIn('scheduleDirectWeb();', main)
        launch = read('app/src/main/java/com/deepseekharness/app/ui/LaunchFragment.java')
        self.assertIn('void requestDirectWeb()', launch,
                      "自动进网页只能有一处实现，创建 / 重建 / 回前台都走它")
        self.assertIn('if ((splash != null && splash.showing()) || enteringWeb) return;', launch,
                      "requestDirectWeb 必须幂等，重复调用不能叠出两个加载页")

    def test_direct_web_intent_survives_environment_prepare(self):
        # 覆盖更新后首次打开要先准备环境：ExtractActivity 回主界面时不能丢掉自动进网页。
        main = read('app/src/main/java/com/deepseekharness/app/ui/MainActivity.java')
        extract = read('app/src/main/java/com/deepseekharness/app/ui/ExtractActivity.java')
        self.assertIn('.putExtra("from_home", launchedFromHome(getIntent()))', main)
        self.assertIn('intent.putExtra(MainActivity.EXTRA_DIRECT_WEB', extract)
        self.assertIn('getIntent().getBooleanExtra("from_home", false)', extract)

    def test_open_web_registered_before_nav_selection(self):
        # setSelectedItemId 会同步触发监听器创建 LaunchFragment，
        # 标记必须在它之前登记，否则参数带不进去。
        main = read('app/src/main/java/com/deepseekharness/app/ui/MainActivity.java')
        register = main.index('consumeOpenWeb(getIntent())')
        select = main.index('nav.setSelectedItemId(getIntent().getBooleanExtra("open_plugins"')
        self.assertLess(register, select,
                        "consumeOpenWeb 必须在 setSelectedItemId 之前调用，否则 open_web 参数丢失")

    def test_system_language_is_pinned_early(self):
        # 真机（vivo/Android 16）实测：Locale.setDefault 会污染 Resources.getSystem()，
        # 导致「跟随系统」自我锁死。必须在进程最早时 initialize() 锁存。
        src = read('app/src/main/java/com/deepseekharness/app/util/SystemLanguage.java')
        self.assertIn('private static volatile String cached', src, "必须有锁存字段")
        self.assertIn('public static void initialize()', src, "必须提供 initialize()")
        self.assertIn('if (!initialized) initializeFromSystemTag(', src, "initialize 只生效第一次")
        app = read('app/src/main/java/com/deepseekharness/app/DshaApp.java')
        # 必须在 LanguageController.apply() 之前（后者会 Locale.setDefault）
        init_at = app.index('SystemLanguage.initialize(')
        apply_at = app.index('LanguageController.apply(this)')
        self.assertLess(init_at, apply_at,
                        "SystemLanguage.initialize() 必须在 LanguageController.apply() 之前")

    def test_system_language_supports_api_23(self):
        # 兼容版 minSdk 23，而 Configuration.getLocales() 是 API 24；
        # 必须回退 Configuration.locale 字段，否则会退到已被改写的 Locale.getDefault()
        # 让「跟随系统」自我锁死。
        src = read('app/src/main/java/com/deepseekharness/app/util/SystemLanguage.java')
        self.assertIn('localeFieldTag', src, "缺少 API 23 的 Configuration.locale 回退")
        self.assertIn('getLocales', src)

    def test_main_activity_consumes_open_web(self):
        main = read('app/src/main/java/com/deepseekharness/app/ui/MainActivity.java')
        self.assertIn('consumeOpenWeb', main)
        self.assertIn('"open_web"', main)
        launch = read('app/src/main/java/com/deepseekharness/app/ui/LaunchFragment.java')
        self.assertIn('ARG_OPEN_WEB', launch, "LaunchFragment 必须消费自动进入 Web 的意图")

    def test_dead_task_notifier_is_gone(self):
        # TaskNotifier 从未被实例化，它的 appInForeground 恒为 false（前台抑制实际失效）
        self.assertFalse((JAVA / 'TaskNotifier.java').exists(),
                         "TaskNotifier 是死代码；前台判断应统一用 ForegroundActivity")

    def test_foreground_suppression_uses_real_foreground_state(self):
        body = re.search(r'private String appNotify\(String path\)\s*\{(.*?)\n    \}', self.shell, re.S).group(1)
        self.assertIn('ForegroundActivity.current()', body)

class BridgeCredentialProtection(unittest.TestCase):
    """设备桥不得把凭据导出/读取到公共目录。

    真机实测过的攻击链：/app/export?path=/root/.dsh/.bridge_token
    → 文件落到 /sdcard/Download/DSHA/（任何 App 可读）
    → 同机任意应用拿到桥 token → 完全接管设备桥。
    """

    def setUp(self):
        self.shell = read('app/src/main/java/com/deepseekharness/app/HttpShellService.java')

    def test_export_checks_path_policy(self):
        body = re.search(r'private String appExport\(String path\)\s*\{(.*?)\n    \}', self.shell, re.S)
        self.assertIsNotNone(body, "找不到 appExport")
        self.assertIn('BridgePathPolicy.denied(', body.group(1),
                      "/app/export 必须先过凭据路径判据")

    def test_readfile_checks_path_policy(self):
        body = re.search(r'private String appReadFile\(String path\)\s*\{(.*?)\n    \}', self.shell, re.S)
        self.assertIsNotNone(body, "找不到 appReadFile")
        self.assertIn('BridgePathPolicy.denied(', body.group(1),
                      "/app/readfile 必须先过凭据路径判据")

    def test_canonical_recheck_defeats_symlink(self):
        # 只看字符串不够：容器里可先建软链接指向凭据
        self.assertIn('exportDeniedByCanonical', self.shell)
        self.assertIn('getCanonicalPath()', self.shell)

    def test_canonical_recheck_does_not_blanket_deny_rootfs(self):
        # 自伤回归：rootfs 就在 /data/data 下，通用拒绝表会封死整个 rootfs
        src = read('app/src/main/java/com/deepseekharness/app/util/BridgePathPolicy.java')
        self.assertIn('deniedGuestView', src)
        self.assertNotIn('"/data/data",\n            "/data/user"', src.split('DENIED_HOST')[0],
                         "通用 DENIED 表里不能有 /data/data：会封死整个 rootfs")

    def test_policy_covers_real_credential_files(self):
        src = read('app/src/main/java/com/deepseekharness/app/util/BridgePathPolicy.java')
        for needle in ['"/root/.dsh"', '"/root/.android"', '"/root/.ssh"', '"/root/.dsha-"']:
            self.assertIn(needle, src, "凭据路径缺失：" + needle)

    def test_help_text_mentions_the_limit(self):
        self.assertIn('凭据区', self.shell, "端点清单要说明凭据区不可读/不可导出")


class BackupLocalCredentialProtection(unittest.TestCase):
    """备份包不得携带本机设备凭据（它落在公共目录，任何应用可读）。"""

    def setUp(self):
        self.engine = read('app/src/main/assets/backup-engine.py')

    def test_local_device_files_excluded(self):
        self.assertIn('LOCAL_DEVICE_FILES', self.engine)
        self.assertIn('".bridge_token"', self.engine, "桥 token 必须从备份排除")
        self.assertIn('".anonymous-user-id"', self.engine, "本机标识必须从备份排除")
        self.assertIn('if scope == "full" and name in LOCAL_DEVICE_FILES:', self.engine)

    def test_credentials_trimmed_by_field_not_wholesale(self):
        # 整文件排除会让用户换机后 API key 全丢，必须字段级剔除
        self.assertIn('def trim_local_records', self.engine)
        self.assertIn('def copy_credentials', self.engine)
        self.assertIn('"client-connection/"', self.engine, "本机会话密钥的记录前缀")
        self.assertIn('pruned_credentials = copy_credentials(', self.engine)

    def test_local_record_prefix_covers_browser_session(self):
        # dsh 的实际记录键是 client-connection/browser-session
        self.assertIn('CREDENTIAL_RECORDS = ("client-connection/",)', self.engine)

    def test_restore_rotates_local_token(self):
        # resetTokenAfterRestore 曾是死代码：老备份恢复后桥会拒绝所有请求
        src = read('app/src/main/java/com/deepseekharness/app/BackupManager.java')
        self.assertIn('HttpShellService.resetTokenAfterRestore()', src,
                      "恢复提交后必须轮换本机凭据，否则老备份恢复后桥不可用")


class CatalogCoverage(unittest.TestCase):
    """语言入口新文案必须在翻译目录里，否则英文界面出现中文。"""

    def setUp(self):
        self.messages = json.loads(read('tools/i18n/messages.json'))

    def test_new_ui_strings_are_translated(self):
        zh = {item['zh'] for item in self.messages if item.get('en')}
        for needed in ['语言 / Language', '界面语言 / Interface language',
                       '跟随系统', '简体中文']:
            self.assertIn(needed, zh, "缺少英文译文：" + needed)

    def test_plugin_notification_strings_stay_translated(self):
        # 官方插件 dsh-task-notifier 硬编码中文，经设备桥进入通知，必须有译文
        zh = {item['zh']: item.get('en', '') for item in self.messages}
        for needed in ['DSHA · 任务完成', '智能体已结束任务，点击查看结果',
                       'DSHA · 已达到输出上限', 'DSHA · 任务已停止',
                       'DSHA · 任务需要处理']:
            self.assertTrue(zh.get(needed), "插件通知文案缺少译文：" + needed)

    def test_ids_unique(self):
        ids = [item['id'] for item in self.messages]
        self.assertEqual(len(ids), len(set(ids)), "messages.json 存在重复 id")

if __name__ == '__main__':
    unittest.main(verbosity=2)
