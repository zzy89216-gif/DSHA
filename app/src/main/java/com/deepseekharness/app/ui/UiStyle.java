package com.deepseekharness.app.ui;

import android.app.Activity;
import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.util.TypedValue;
import android.view.View;
import android.widget.ImageView;

import androidx.annotation.DrawableRes;

import com.deepseekharness.app.R;

import java.io.File;

/**
 * 界面风格的唯一入口：苹果式分组卡片、统一的浅色图标块，以及「背景」三选一：
 * 默认纯色 / 动态玻璃 / 自定义图片。
 *
 * <p>非默认背景时在 Activity 创建前叠加 {@code ThemeOverlay.DSHA.Translucent}：页面层透明、
 * 卡片和底栏半透明，统一透出窗口内容层上的那一张背景。布局与业务代码不需要分支。
 * 偏好存在独立的 {@code dsha_ui_style} 文件中，不改动任何历史 SharedPreferences 键。
 */
public final class UiStyle {
    /** 取值沿用历史存储：0 默认、1 动态玻璃、2 自定义图片。 */
    public static final int BG_DEFAULT = 0, BG_GLASS = 1, BG_IMAGE = 2;

    private static final String PREFS = "dsha_ui_style";
    private static final String KEY_BACKGROUND = "background";
    private static final String IMAGE_FILE = "ui_background.jpg";

    private UiStyle() { }

    public static int background(Context context) {
        int mode = prefs(context).getInt(KEY_BACKGROUND, BG_DEFAULT);
        if (mode == BG_IMAGE && !imageFile(context).isFile()) return BG_DEFAULT;
        if (mode == BG_GLASS) return BG_GLASS;
        return mode == BG_IMAGE ? BG_IMAGE : BG_DEFAULT;
    }

    private static final String KEY_DIRECT_WEB = "direct_web";
    private static final String KEY_WEB_HANDLE = "web_handle";
    private static final String KEY_WEB_HANDLE_Y = "web_handle_y";

    /** 从桌面打开时直接启动并进入网页（默认开启）；关闭后停在原生启动页。 */
    public static boolean directWeb(Context context) { return prefs(context).getBoolean(KEY_DIRECT_WEB, true); }
    public static void setDirectWeb(Context context, boolean enabled) { prefs(context).edit().putBoolean(KEY_DIRECT_WEB, enabled).apply(); }

    /** 网页右侧的悬浮入口（返回主界面 / 设置），默认显示。 */
    public static boolean webHandle(Context context) { return prefs(context).getBoolean(KEY_WEB_HANDLE, true); }
    public static void setWebHandle(Context context, boolean visible) { prefs(context).edit().putBoolean(KEY_WEB_HANDLE, visible).apply(); }
    /** 悬浮入口的纵向位置，取值为屏幕高度比例 0..1。 */
    static float webHandleY(Context context) { return prefs(context).getFloat(KEY_WEB_HANDLE_Y, 0.42f); }
    static void setWebHandleY(Context context, float ratio) { prefs(context).edit().putFloat(KEY_WEB_HANDLE_Y, ratio).apply(); }

    public static void setBackground(Context context, int mode) {
        prefs(context).edit().putInt(KEY_BACKGROUND, mode).apply();
        if (mode != BG_IMAGE) {
            // 不再使用的自定义图片立即删除，不在私有目录残留用户照片。
            //noinspection ResultOfMethodCallIgnored
            imageFile(context).delete();
            BackdropDrawable.clearImageCache();
        }
    }

    /** 是否为半透明（非纯色）背景：卡片、底栏、弹窗改为玻璃质感。 */
    public static boolean translucent(Context context) {
        return background(context) != BG_DEFAULT;
    }

    static File imageFile(Context context) {
        return new File(context.getApplicationContext().getFilesDir(), IMAGE_FILE);
    }

    /** 必须在 Activity 的 setContentView 之前调用；只作用于本应用自己的、非全屏 Web 页面。 */
    static void applyTheme(Activity activity) {
        if (!eligible(activity)) return;
        if (translucent(activity)) activity.getTheme().applyStyle(R.style.ThemeOverlay_DSHA_Translucent, true);
    }

    /** Web 工作台、画中画、虚拟屏被内容完全覆盖：保持不透明，不为看不见的背景耗电。 */
    static boolean eligible(Activity activity) {
        String name = activity.getClass().getName();
        return name.startsWith("com.deepseekharness.app.")
                && !(activity instanceof WebFullscreenUi.Host)
                && !name.endsWith(".PictureInPictureActivity")
                && !name.startsWith("com.deepseekharness.app.vscreen.");
    }

    /** 窗口内容层背景：默认纯色 surface；自定义图片由 {@link BackdropDrawable} 绘制。 */
    static Drawable windowBackground(Activity activity) {
        int mode = eligible(activity) ? background(activity) : BG_DEFAULT;
        if (mode == BG_IMAGE) {
            Drawable image = BackdropDrawable.image(activity, imageFile(activity));
            if (image != null) return image;
        }
        if (mode == BG_GLASS) return BackdropDrawable.glass(activity);
        return new ColorDrawable(activity.getColor(R.color.surface));
    }

    public static void page(View view) {
        set(view, R.attr.dshaPageBackground, R.color.surface);
    }

    public static void card(View view) {
        set(view, R.attr.dshaCardBackground, R.drawable.bg_card);
    }

    static void bar(View view) {
        set(view, R.attr.dshaBarBackground, R.drawable.bg_bar);
    }

    /**
     * 图标块：统一为主色浅底 + 主色图标。
     * 旧版每行一种饱和色，和其余克制的配色放在一起显得跳脱（用户反馈的「割裂感」之一）。
     */
    static void tile(ImageView view, @DrawableRes int icon) {
        view.setImageResource(icon);
        view.setBackgroundResource(tileFor(icon));
        view.setImageTintList(ColorStateList.valueOf(view.getContext().getColor(R.color.tile_on)));
        int pad = Math.round(6 * view.getResources().getDisplayMetrics().density);
        view.setPadding(pad, pad, pad, pad);
    }

    static int tileFor(@DrawableRes int icon) {
        // 危险 / 维护类保留暖色提示，其余统一主色浅底。
        if (icon == R.drawable.ic_recovery_wrench) return R.drawable.bg_tile_orange;
        return R.drawable.bg_tile_blue;
    }

    private static android.content.SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static void set(View view, int attr, int fallback) {
        view.setBackground(drawable(view.getContext(), attr, fallback));
    }

    private static Drawable drawable(Context context, int attr, int fallback) {
        TypedValue value = new TypedValue();
        if (context.getTheme().resolveAttribute(attr, value, true)) {
            if (value.resourceId != 0) return context.getDrawable(value.resourceId);
            if (value.type >= TypedValue.TYPE_FIRST_COLOR_INT && value.type <= TypedValue.TYPE_LAST_COLOR_INT)
                return new ColorDrawable(value.data);
        }
        return context.getDrawable(fallback);
    }
}
