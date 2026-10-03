package com.deepseekharness.app.ui;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ObjectAnimator;
import android.animation.PropertyValuesHolder;
import android.animation.ValueAnimator;
import android.app.Activity;
import android.graphics.Outline;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewOutlineProvider;
import android.view.animation.PathInterpolator;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.Nullable;

import com.deepseekharness.app.R;
import com.deepseekharness.app.util.UiText;
import com.google.android.material.progressindicator.LinearProgressIndicator;

/**
 * 打开 App 直接进入网页时的加载页：盖在启动页上方，显示品牌图标、启动进度和一个「留在主界面」出口。
 *
 * <p>只在本次自动进入期间存在；进入网页后保留到网页盖住它，返回时立即移除，不再挡住启动页。
 * 系统关闭动画时不做呼吸和淡入淡出。
 */
final class StartupSplash {
    private static final PathInterpolator EASE = new PathInterpolator(0.2f, 0f, 0f, 1f);

    private final FrameLayout root;
    private final View content;
    private final ImageView icon;
    private final TextView status;
    private final boolean motion;
    @Nullable private ObjectAnimator breathe;
    private boolean dismissed;

    private StartupSplash(Activity activity, Runnable stay) {
        motion = motionEnabled(activity);
        float density = activity.getResources().getDisplayMetrics().density;
        root = new FrameLayout(activity);
        root.setBackgroundColor(activity.getColor(R.color.surface));
        root.setClickable(true); // 吞掉触摸，避免误点到下面的启动页
        root.setFocusable(true);

        LinearLayout column = new LinearLayout(activity);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setGravity(Gravity.CENTER_HORIZONTAL);
        content = column;

        icon = new ImageView(activity);
        icon.setImageResource(R.drawable.launcher_foreground_v2);
        icon.setScaleType(ImageView.ScaleType.CENTER_CROP);
        icon.setContentDescription(null);
        icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        final float corner = 24 * density;
        icon.setOutlineProvider(new ViewOutlineProvider() {
            @Override public void getOutline(View view, Outline outline) {
                outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(), corner);
            }
        });
        icon.setClipToOutline(true);
        icon.setElevation(6 * density);
        int iconSize = Math.round(96 * density);
        column.addView(icon, new LinearLayout.LayoutParams(iconSize, iconSize));

        TextView title = new TextView(activity);
        title.setText("DeepSeek Harness");
        title.setTextSize(22);
        title.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
        title.setTextColor(activity.getColor(R.color.text));
        title.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(-2, -2);
        titleParams.topMargin = Math.round(22 * density);
        column.addView(title, titleParams);

        LinearProgressIndicator progress = new LinearProgressIndicator(activity);
        progress.setIndeterminate(true);
        progress.setTrackCornerRadius(Math.round(2 * density));
        progress.setTrackThickness(Math.round(3 * density));
        progress.setIndicatorColor(activity.getColor(R.color.primary));
        progress.setTrackColor(activity.getColor(R.color.line));
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(Math.round(132 * density), -2);
        progressParams.topMargin = Math.round(26 * density);
        column.addView(progress, progressParams);

        status = new TextView(activity);
        status.setTextSize(13);
        status.setTextColor(activity.getColor(R.color.text_secondary));
        status.setGravity(Gravity.CENTER);
        status.setMaxLines(2);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        status.setText(UiText.choose("正在启动…", "Starting…"));
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(-1, -2);
        statusParams.topMargin = Math.round(14 * density);
        int side = Math.round(40 * density);
        statusParams.leftMargin = side; statusParams.rightMargin = side;
        column.addView(status, statusParams);

        root.addView(column, new FrameLayout.LayoutParams(-1, -2, Gravity.CENTER));

        TextView stayButton = new TextView(activity);
        stayButton.setText(UiText.choose("留在主界面", "Stay on home screen"));
        stayButton.setTextSize(14);
        stayButton.setTextColor(activity.getColor(R.color.primary));
        int padH = Math.round(20 * density), padV = Math.round(12 * density);
        stayButton.setPadding(padH, padV, padH, padV);
        stayButton.setMinHeight(Math.round(48 * density));
        stayButton.setGravity(Gravity.CENTER);
        android.util.TypedValue ripple = new android.util.TypedValue();
        activity.getTheme().resolveAttribute(android.R.attr.selectableItemBackgroundBorderless, ripple, true);
        stayButton.setBackgroundResource(ripple.resourceId);
        stayButton.setOnClickListener(v -> stay.run());
        FrameLayout.LayoutParams stayParams = new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER_HORIZONTAL | Gravity.BOTTOM);
        stayParams.bottomMargin = Math.round(36 * density);
        root.addView(stayButton, stayParams);
        // 底部按钮避开手势导航条
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            @SuppressWarnings("deprecation")
            int bottom = android.os.Build.VERSION.SDK_INT >= 30
                    ? insets.getInsets(android.view.WindowInsets.Type.systemBars()).bottom
                    : insets.getSystemWindowInsetBottom();
            stayParams.bottomMargin = Math.round(36 * density) + bottom;
            stayButton.setLayoutParams(stayParams);
            return insets;
        });
    }

    /** 盖到 Activity 内容最上层。 */
    static StartupSplash show(Activity activity, Runnable stay) {
        StartupSplash splash = new StartupSplash(activity, stay);
        ViewGroup host = activity.findViewById(android.R.id.content);
        host.addView(splash.root, new ViewGroup.LayoutParams(-1, -1));
        splash.enter();
        return splash;
    }

    private void enter() {
        if (!motion) return;
        float lift = 18 * root.getResources().getDisplayMetrics().density;
        content.setAlpha(0f); content.setTranslationY(lift);
        content.animate().alpha(1f).translationY(0f).setDuration(420).setInterpolator(EASE).start();
        icon.setScaleX(0.86f); icon.setScaleY(0.86f);
        icon.animate().scaleX(1f).scaleY(1f).setDuration(520).setInterpolator(EASE)
                .withEndAction(this::startBreathing).start();
    }

    private void startBreathing() {
        if (dismissed || !motion) return;
        breathe = ObjectAnimator.ofPropertyValuesHolder(icon,
                PropertyValuesHolder.ofFloat(View.SCALE_X, 1f, 1.045f),
                PropertyValuesHolder.ofFloat(View.SCALE_Y, 1f, 1.045f));
        breathe.setDuration(1300);
        breathe.setRepeatCount(ValueAnimator.INFINITE);
        breathe.setRepeatMode(ValueAnimator.REVERSE);
        breathe.setInterpolator(new android.view.animation.AccelerateDecelerateInterpolator());
        breathe.start();
    }

    void setStatus(@Nullable CharSequence text) {
        if (dismissed || text == null || text.toString().trim().isEmpty()) return;
        if (text.toString().contentEquals(status.getText())) return;
        status.setText(text);
    }

    boolean showing() { return !dismissed; }

    /** 淡出并移除；{@code animate=false} 用于从网页返回时立即撤掉。 */
    void dismiss(boolean animate) {
        if (dismissed) return;
        dismissed = true;
        if (breathe != null) { breathe.cancel(); breathe = null; }
        icon.animate().cancel(); content.animate().cancel();
        if (!animate || !motion || !root.isAttachedToWindow()) { detach(); return; }
        root.animate().alpha(0f).setDuration(220).setInterpolator(EASE)
                .setListener(new AnimatorListenerAdapter() {
                    @Override public void onAnimationEnd(Animator animation) { detach(); }
                }).start();
        content.animate().scaleX(1.04f).scaleY(1.04f).setDuration(220).setInterpolator(EASE).start();
    }

    private void detach() {
        ViewGroup parent = (ViewGroup) root.getParent();
        if (parent != null) parent.removeView(root);
    }

    static boolean motionEnabled(android.content.Context context) {
        try {
            return Settings.Global.getFloat(context.getContentResolver(), Settings.Global.ANIMATOR_DURATION_SCALE, 1f) > 0f;
        } catch (RuntimeException ignored) {
            return true;
        }
    }
}
