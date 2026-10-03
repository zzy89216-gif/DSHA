package com.deepseekharness.app.ui;

import android.annotation.SuppressLint;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;

import com.deepseekharness.app.R;
import com.deepseekharness.app.util.UiText;

/**
 * 网页右侧边缘的小圆按钮：点按弹出「主界面 / 设置 / 刷新网页 / 隐藏按钮」，可上下拖动，位置会记住。
 *
 * <p>半透明、贴边、不遮挡输入区；画中画时隐藏。设置页可整体关闭，关闭后网页根页面按返回键仍回主界面。
 */
final class WebHomeHandle {
    interface Actions {
        void home();
        void settings();
        void reload();
    }

    private final ImageView button;
    private final FrameLayout.LayoutParams params;
    private final float density;
    private boolean suppressed;

    @SuppressLint("ClickableViewAccessibility")
    private WebHomeHandle(FrameLayout parent, Actions actions) {
        android.content.Context context = parent.getContext();
        density = context.getResources().getDisplayMetrics().density;
        button = new ImageView(context);
        button.setImageResource(R.drawable.launcher_foreground_v2);
        button.setScaleType(ImageView.ScaleType.CENTER_CROP);
        button.setContentDescription(UiText.choose("主界面与设置", "Home and settings"));
        GradientDrawable ring = new GradientDrawable();
        ring.setShape(GradientDrawable.OVAL);
        ring.setColor(context.getColor(R.color.launcher_background));
        ring.setStroke(Math.max(1, Math.round(density)), 0x33FFFFFF);
        button.setBackground(ring);
        button.setClipToOutline(true);
        button.setElevation(6 * density);
        button.setAlpha(0.72f);
        int size = dp(40);
        params = new FrameLayout.LayoutParams(size, size, Gravity.END | Gravity.TOP);
        params.rightMargin = dp(6);
        parent.addView(button, params);

        int slop = ViewConfiguration.get(context).getScaledTouchSlop();
        final float[] start = new float[2];
        final boolean[] dragging = {false};
        button.setOnTouchListener((view, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    start[0] = event.getRawY(); start[1] = params.topMargin; dragging[0] = false;
                    button.animate().alpha(1f).scaleX(1.08f).scaleY(1.08f).setDuration(120).start();
                    return true;
                case MotionEvent.ACTION_MOVE:
                    float dy = event.getRawY() - start[0];
                    if (!dragging[0] && Math.abs(dy) > slop) dragging[0] = true;
                    if (dragging[0]) { params.topMargin = clamp(Math.round(start[1] + dy)); button.setLayoutParams(params); }
                    return true;
                case MotionEvent.ACTION_UP:
                    release();
                    if (dragging[0]) {
                        int height = Math.max(1, parentHeight());
                        UiStyle.setWebHandleY(context, params.topMargin / (float) height);
                    } else {
                        view.performClick();
                    }
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    release();
                    return true;
                default:
                    return false;
            }
        });
        button.setOnClickListener(view -> showMenu(actions));
        parent.addOnLayoutChangeListener((v, l, t, r, b, ol, ot, orr, ob) -> {
            if (b - t != ob - ot) place();
        });
        place();
    }

    /** 偏好开启时挂到网页容器上；关闭时返回 null。 */
    static WebHomeHandle attach(FrameLayout parent, Actions actions) {
        if (!UiStyle.webHandle(parent.getContext())) return null;
        return new WebHomeHandle(parent, actions);
    }

    /** 画中画、全屏视频等场景临时隐藏。 */
    void setSuppressed(boolean value) {
        suppressed = value;
        button.setVisibility(value ? View.GONE : View.VISIBLE);
    }

    private void showMenu(Actions actions) {
        if (suppressed) return;
        String[] items = {
                UiText.choose("返回主界面", "Back to home"),
                UiText.choose("设置", "Settings"),
                UiText.choose("刷新网页", "Reload page"),
                UiText.choose("隐藏这个按钮", "Hide this button"),
        };
        new DshaDialogBuilder(button.getContext())
                .setItems(items, (dialog, which) -> {
                    if (which == 0) actions.home();
                    else if (which == 1) actions.settings();
                    else if (which == 2) actions.reload();
                    else {
                        UiStyle.setWebHandle(button.getContext(), false);
                        button.animate().alpha(0f).scaleX(0.6f).scaleY(0.6f).setDuration(160)
                                .withEndAction(() -> { ViewGroup p = (ViewGroup) button.getParent(); if (p != null) p.removeView(button); }).start();
                        android.widget.Toast.makeText(button.getContext(),
                                UiText.choose("已隐藏，可在「设置 → 网页悬浮入口」重新打开", "Hidden. Turn it back on in Settings → Web shortcut button"),
                                android.widget.Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void release() {
        button.animate().alpha(0.72f).scaleX(1f).scaleY(1f).setDuration(160).start();
    }

    private void place() {
        int height = parentHeight();
        if (height <= 0) { button.post(this::place); return; }
        params.topMargin = clamp(Math.round(UiStyle.webHandleY(button.getContext()) * height));
        button.setLayoutParams(params);
    }

    private int clamp(int top) {
        int height = parentHeight();
        int min = dp(72), max = Math.max(min, height - dp(160));
        return Math.max(min, Math.min(max, top));
    }

    private int parentHeight() {
        View parent = (View) button.getParent();
        return parent == null ? 0 : parent.getHeight();
    }

    private int dp(int value) {
        return Math.round(value * density);
    }
}
