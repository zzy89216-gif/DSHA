package com.deepseekharness.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.deepseekharness.app.R;
import com.deepseekharness.app.core.HarnessController;

import java.util.function.Supplier;

/**
 * 设置页：模块入口（安装/配置/数据与备份）+ 其他（更新/自检/重新解压/关于）。
 */
public class SettingsFragment extends Fragment {
    private TextView backgroundValue;
    private final androidx.activity.result.ActivityResultLauncher<String> pickBackground =
            registerForActivityResult(new androidx.activity.result.contract.ActivityResultContracts.GetContent(), this::onBackgroundPicked);

    private void renderBackground() {
        if (backgroundValue == null) return;
        int mode = UiStyle.background(requireContext());
        backgroundValue.setText(mode == UiStyle.BG_IMAGE ? R.string.apple_bg_image
                : mode == UiStyle.BG_GLASS ? R.string.apple_bg_glass : R.string.apple_bg_default);
    }

    private void chooseBackground() {
        int mode = UiStyle.background(requireContext());
        int checked = mode == UiStyle.BG_GLASS ? 1 : mode == UiStyle.BG_IMAGE ? 2 : 0;
        String[] items = {getString(R.string.apple_bg_default),
                getString(R.string.apple_bg_glass),
                getString(mode == UiStyle.BG_IMAGE ? R.string.apple_bg_image_change : R.string.apple_bg_image)};
        new DshaDialogBuilder(requireContext()).setTitle(R.string.apple_background)
                .setSingleChoiceItems(items, checked, (dialog, which) -> {
                    dialog.dismiss();
                    if (which == 2) {
                        try { pickBackground.launch("image/*"); }
                        catch (android.content.ActivityNotFoundException e) { toast(R.string.apple_bg_failed); }
                    } else if (which == 1) {
                        UiStyle.setBackground(requireContext(), UiStyle.BG_GLASS);
                        recreateHost();
                    } else if (mode != UiStyle.BG_DEFAULT) {
                        UiStyle.setBackground(requireContext(), UiStyle.BG_DEFAULT);
                        recreateHost();
                    }
                })
                .setNegativeButton(android.R.string.cancel, null).show();
    }

    /** 读取所选图片：按 EXIF 方向校正、缩放到长边 ≤1440 后存入应用私有目录。在后台线程完成。 */
    private void onBackgroundPicked(android.net.Uri uri) {
        if (uri == null || getContext() == null) return;
        final android.content.Context app = requireContext().getApplicationContext();
        new Thread(() -> {
            boolean ok = BackgroundImageStore.save(app, uri, UiStyle.imageFile(app));
            android.app.Activity host = getActivity();
            if (host == null) return;
            host.runOnUiThread(() -> {
                if (!isAdded()) return;
                if (!ok) { toast(R.string.apple_bg_failed); return; }
                BackdropDrawable.clearImageCache();
                UiStyle.setBackground(app, UiStyle.BG_IMAGE);
                recreateHost();
            });
        }, "dsha-background").start();
    }

    private void recreateHost() {
        renderBackground();
        android.app.Activity host = getActivity();
        View root = getView();
        if (host == null || root == null) return;
        root.postDelayed(() -> { if (!host.isFinishing() && !host.isDestroyed()) host.recreate(); }, 160);
    }

    private void toast(int text) {
        android.widget.Toast.makeText(requireContext(), text, android.widget.Toast.LENGTH_SHORT).show();
    }



    private TabOption[] tabOptions() {
        return new TabOption[] {
                new TabOption(com.deepseekharness.app.util.UiText.choose("安装", "Install"),
                        com.deepseekharness.app.util.UiText.choose("安装与修复运行环境", "Install and repair the runtime"),
                        R.drawable.ic_ui2_box, InstallFragment::new),
                new TabOption(com.deepseekharness.app.util.UiText.choose("配置", "Configure"),
                        com.deepseekharness.app.util.UiText.choose("接口、模型、显示与运行", "API, models, display and runtime"),
                        R.drawable.ic_settings, ConfigFragment::new),
                new TabOption(com.deepseekharness.app.util.UiText.choose("数据与备份", "Data and backup"),
                        com.deepseekharness.app.util.UiText.choose("备份恢复 · 工作目录文件", "Backup, restore and workspace files"),
                        R.drawable.ic_ui2_folder, WorkspaceFragment::new),
                new TabOption(com.deepseekharness.app.util.UiText.choose("设备能力授权", "Device grants"),
                        com.deepseekharness.app.util.UiText.choose("Root · Shizuku · ADB · 权限", "Root, Shizuku, ADB and permissions"),
                        R.drawable.ic_ui_shield, DeviceGrantsFragment::new),
        };
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_settings, container, false);

        LinearLayout tabs = v.findViewById(R.id.settings_tabs);
        TabOption[] options = tabOptions();
        for (int i = 0; i < options.length; i++) {
            LinearLayout.LayoutParams spacing = new LinearLayout.LayoutParams(-1, -2);
            if (i > 0) spacing.topMargin = 0;
            tabs.addView(buildRow(options[i]), spacing);
        }
        LinearLayout power = v.findViewById(R.id.settings_power);
        power.setOrientation(LinearLayout.HORIZONTAL);power.setGravity(Gravity.CENTER_VERTICAL);power.setPadding(dp(16),dp(6),dp(13),dp(6));power.setMinimumHeight(dp(60));
        android.widget.ImageView powerIcon=new android.widget.ImageView(requireContext());UiStyle.tile(powerIcon,R.drawable.ic_launch);
        powerIcon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);power.addView(powerIcon,new LinearLayout.LayoutParams(dp(30),dp(30)));
        LinearLayout words=new LinearLayout(requireContext());words.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams wordsParams=new LinearLayout.LayoutParams(0,-2,1);wordsParams.leftMargin=dp(12);power.addView(words,wordsParams);
        TextView heading=new TextView(requireContext());heading.setText(com.deepseekharness.app.util.UiText.text("省电模式"));heading.setTextSize(16);heading.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.NORMAL));heading.setTextColor(requireContext().getColor(R.color.text));heading.setIncludeFontPadding(false);words.addView(heading);
        TextView powerHint=new TextView(requireContext());powerHint.setTextSize(13);powerHint.setTextColor(requireContext().getColor(R.color.text_secondary));powerHint.setPadding(0,dp(3),dp(8),0);powerHint.setIncludeFontPadding(false);words.addView(powerHint);
        com.google.android.material.materialswitch.MaterialSwitch eco=new com.google.android.material.materialswitch.MaterialSwitch(requireContext());eco.setMinHeight(dp(48));eco.setContentDescription(com.deepseekharness.app.util.UiText.text("省电模式"));
        com.deepseekharness.app.core.ConfigStore config=HarnessController.get(requireContext()).config();eco.setChecked(config.isEcoMode());power.addView(eco);
        java.util.function.Consumer<Boolean> describe = enabled -> powerHint.setText(enabled
                ? com.deepseekharness.app.util.UiText.text("熄屏空闲 1 分钟后减少保活；有任务时继续运行。")
                : com.deepseekharness.app.util.UiText.text("持续保持运行，适合长时间任务。"));
        describe.accept(config.isEcoMode());
        eco.setOnCheckedChangeListener((button, checked) -> {
            config.setEcoMode(checked); com.deepseekharness.app.HarnessService.refreshPowerMode(); describe.accept(checked);
        });

        switchRow(v.findViewById(R.id.settings_direct_web), R.drawable.ic_launch,
                com.deepseekharness.app.util.UiText.choose("打开直接进入网页", "Open straight into Web"),
                com.deepseekharness.app.util.UiText.choose("从桌面打开时自动启动并进入网页。", "Starts and opens Web when launched from the home screen."),
                com.deepseekharness.app.util.UiText.choose("打开后停在启动页，手动进入。", "Stays on the launch page; enter manually."),
                UiStyle.directWeb(requireContext()), checked -> UiStyle.setDirectWeb(requireContext(), checked));
        switchRow(v.findViewById(R.id.settings_web_handle), R.drawable.ic_ui2_box,
                com.deepseekharness.app.util.UiText.choose("网页悬浮入口", "Web shortcut button"),
                com.deepseekharness.app.util.UiText.choose("网页右侧显示小按钮，可回到主界面或设置；可上下拖动。", "Shows a small button on the Web page edge to return home or open settings; drag to move."),
                com.deepseekharness.app.util.UiText.choose("已隐藏；在网页根页面按返回键也能回到主界面。", "Hidden; press Back on the Web start page to return home."),
                UiStyle.webHandle(requireContext()), checked -> UiStyle.setWebHandle(requireContext(), checked));

        // 背景：默认 / 动态玻璃 / 自定义图片。保存后只重建当前界面，终端、Web 和后台任务不受影响。
        backgroundValue = v.findViewById(R.id.settings_background_value);
        renderBackground();
        v.findViewById(R.id.settings_background).setOnClickListener(x -> chooseBackground());

        String version = "unknown";
        try {
            version = requireContext().getPackageManager()
                    .getPackageInfo(requireContext().getPackageName(), 0).versionName;
        } catch (Exception ignored) {
        }
        TextView ver = v.findViewById(R.id.settings_ver);
        ver.setText(com.deepseekharness.app.util.UiText.text("DeepSeek Harness v" + version + com.deepseekharness.app.util.UiText.choose(" · MIT 许可", " · MIT License")));
        TextView updateSub = v.findViewById(R.id.settings_update_sub);
        updateSub.setText(com.deepseekharness.app.util.UiText.text("稳定版与预览版更新"));

        v.findViewById(R.id.settings_about).setOnClickListener(x -> UiMotion.page(requireContext(),getParentFragmentManager().beginTransaction()).replace(R.id.fragment_container,new AboutFragment()).addToBackStack("settings").commit());
        v.findViewById(R.id.settings_update).setOnClickListener(x -> checkUpdate());
        v.findViewById(R.id.settings_selftest).setOnClickListener(x -> runSelftest());

        // 语言入口：标题在中文界面下也带英文「Language」（只写「语言 · 简体中文」时，
        // 非中文用户根本认不出这是语言开关）；摘要直接显示当前生效语言。
        // 放在「常用设置」分组最前面，不用滚动就能看到。
        String preference = config.getUiLanguagePreference();
        boolean followSystem = com.deepseekharness.app.util.UiLanguagePreference.followsSystem(preference);
        String effective = config.getUiLanguage();
        String[] optionValues = {
                com.deepseekharness.app.util.UiLanguagePreference.SYSTEM,
                com.deepseekharness.app.util.UiLanguagePreference.ZH,
                com.deepseekharness.app.util.UiLanguagePreference.EN};
        String[] optionLabels = {
                com.deepseekharness.app.util.UiText.choose("跟随系统", "Follow system"),
                com.deepseekharness.app.util.UiText.choose("简体中文", "Simplified Chinese"),
                "English"};
        int checked = followSystem ? 0 : ("en".equals(preference) ? 2 : 1);
        // 摘要始终显示当前**生效**语言的名字：跟随系统时补上来由，用户一眼能看出实际结果。
        String currentLabel = "en".equals(effective)
                ? com.deepseekharness.app.util.UiText.choose("English", "English")
                : com.deepseekharness.app.util.UiText.choose("简体中文", "Simplified Chinese");
        String summary = followSystem
                ? com.deepseekharness.app.util.UiText.choose("跟随系统 · ", "Follow system · ") + currentLabel
                : currentLabel;
        LinearLayout appearance=v.findViewById(R.id.settings_appearance);
        TextView languageSummary=v.findViewById(R.id.settings_language);
        languageSummary.setText(summary);
        View.OnClickListener openLanguageDialog = x -> new com.deepseekharness.app.ui.DshaDialogBuilder(requireContext())
                .setTitle(com.deepseekharness.app.util.UiText.choose("界面语言 / Interface language", "Interface language"))
                .setSingleChoiceItems(optionLabels, checked,
                        (dialog, which) -> {
                            String selected=optionValues[which];
                            if (dialog instanceof android.app.Dialog)
                                ((android.app.Dialog)dialog).setOnDismissListener(ignored -> new android.os.Handler(android.os.Looper.getMainLooper())
                                        .post(() -> LanguageController.select(requireContext(), selected)));
                            dialog.dismiss();
                        })
                .setNegativeButton(com.deepseekharness.app.util.UiText.choose("取消", "Cancel"), null).show();
        appearance.setOnClickListener(openLanguageDialog);
        languageSummary.setOnClickListener(openLanguageDialog);
        v.findViewById(R.id.settings_overlay).setOnClickListener(x->UiMotion.page(requireContext(),getParentFragmentManager().beginTransaction()).replace(R.id.fragment_container,new OverlayFragment()).addToBackStack("settings").commit());
        return v;
    }

    private void runSelftest() {
        startActivity(new Intent(requireContext(), DiagnosticActivity.class));
    }

    private void checkUpdate() {
        startActivity(new Intent(requireContext(), UpdateActivity.class));
    }

    /** 与「省电模式」同款的开关行：图标块 + 标题 + 随状态变化的说明 + 开关。 */
    private void switchRow(LinearLayout row, int iconRes, String title, String hintOn, String hintOff,
                           boolean checked, java.util.function.Consumer<Boolean> onChange) {
        row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), dp(6), dp(13), dp(6)); row.setMinimumHeight(dp(60));
        android.widget.ImageView icon = new android.widget.ImageView(requireContext()); UiStyle.tile(icon, iconRes);
        icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        row.addView(icon, new LinearLayout.LayoutParams(dp(30), dp(30)));
        LinearLayout words = new LinearLayout(requireContext()); words.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams wordsParams = new LinearLayout.LayoutParams(0, -2, 1); wordsParams.leftMargin = dp(12);
        row.addView(words, wordsParams);
        TextView heading = new TextView(requireContext()); heading.setText(title); heading.setTextSize(16);
        heading.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
        heading.setTextColor(requireContext().getColor(R.color.text)); heading.setIncludeFontPadding(false); words.addView(heading);
        TextView hint = new TextView(requireContext()); hint.setTextSize(13); hint.setTextColor(requireContext().getColor(R.color.text_secondary));
        hint.setPadding(0, dp(3), dp(8), 0); hint.setIncludeFontPadding(false); words.addView(hint);
        com.google.android.material.materialswitch.MaterialSwitch toggle = new com.google.android.material.materialswitch.MaterialSwitch(requireContext());
        toggle.setMinHeight(dp(48)); toggle.setContentDescription(title); toggle.setChecked(checked); row.addView(toggle);
        hint.setText(checked ? hintOn : hintOff);
        toggle.setOnCheckedChangeListener((button, on) -> { onChange.accept(on); hint.setText(on ? hintOn : hintOff); });
    }

    private LinearLayout buildRow(TabOption opt) {
        LinearLayout row = new LinearLayout(requireContext());
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), dp(10), dp(14), dp(10));
        row.setMinimumHeight(dp(60)); row.setFocusable(true);
        row.setBackgroundResource(R.drawable.bg_ui2_row);

        LinearLayout body = new LinearLayout(requireContext());
        body.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams bodyParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        bodyParams.leftMargin = dp(12); bodyParams.rightMargin = dp(8); body.setLayoutParams(bodyParams);

        TextView title = new TextView(requireContext());
        title.setText(opt.title);
        title.setTextSize(16);
        title.setTextColor(requireContext().getColor(R.color.text));
        title.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));

        TextView sub = new TextView(requireContext());
        sub.setText(opt.sub);
        sub.setTextSize(13);
        sub.setTextColor(requireContext().getColor(R.color.text_secondary));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.topMargin = dp(2);
        sub.setLayoutParams(slp);

        body.addView(title);
        body.addView(sub);

        android.widget.ImageView chev = new android.widget.ImageView(requireContext());
        chev.setImageResource(R.drawable.ic_ui2_chevron);
        chev.setLayoutParams(new LinearLayout.LayoutParams(dp(14), dp(14)));
        chev.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);

        android.widget.ImageView icon = new android.widget.ImageView(requireContext());
        UiStyle.tile(icon, opt.icon);
        icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        row.addView(icon,new LinearLayout.LayoutParams(dp(30),dp(30)));
        row.addView(body);
        row.addView(chev);
        row.setOnClickListener(v -> UiMotion.page(requireContext(), getParentFragmentManager().beginTransaction())
                .replace(R.id.fragment_container, opt.factory.get())
                .addToBackStack("settings")
                .commit());
        return row;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private static final class TabOption {
        final String title;
        final String sub;
        final int icon;
        final Supplier<Fragment> factory;

        TabOption(String title, String sub, int icon, Supplier<Fragment> factory) {
            this.title = title;
            this.sub = sub;
            this.icon = icon;
            this.factory = factory;
        }
    }
}
