package com.deepseekharness.app.ui;

import android.content.Context;
import android.content.SharedPreferences;
import android.view.View;
import android.view.ViewGroup;

import androidx.core.view.ViewCompat;

import com.deepseekharness.app.R;

/**
 * 苹果式折叠区：点标题行展开 / 收起正文，箭头旋转，用户选择按 key 记住。
 *
 * <p>{@link #reveal()} 用于「需要用户注意」（启动异常、凭据不可用）时自动展开，
 * 但不改写记住的偏好，问题解决后下次进入仍按用户习惯收起。
 */
final class Disclosure {
    private static final String PREFS = "dsha_ui_disclosure";
    private final View header, body, chevron;
    private final SharedPreferences prefs;
    private final String key;

    private Disclosure(View header, View body, View chevron, String key) {
        this.header = header; this.body = body; this.chevron = chevron; this.key = key;
        this.prefs = header.getContext().getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static Disclosure bind(View root, int headerId, int bodyId, int chevronId, String key, boolean defaultOpen) {
        Disclosure d = new Disclosure(root.findViewById(headerId), root.findViewById(bodyId),
                chevronId == 0 ? null : root.findViewById(chevronId), key);
        d.show(d.prefs.getBoolean(key, defaultOpen), false);
        d.header.setOnClickListener(v -> d.toggle());
        return d;
    }

    boolean open() { return body.getVisibility() == View.VISIBLE; }

    void toggle() {
        boolean next = !open();
        prefs.edit().putBoolean(key, next).apply();
        show(next, true);
    }

    /** 自动展开且不记住；已展开时什么都不做。 */
    void reveal() {
        if (!open()) show(true, true);
    }

    private void show(boolean visible, boolean animate) {
        if (animate) {
            View scene = sceneRoot();
            if (scene instanceof ViewGroup) {
                android.transition.AutoTransition transition = new android.transition.AutoTransition();
                transition.setDuration(220);
                android.transition.TransitionManager.beginDelayedTransition((ViewGroup) scene, transition);
            }
        }
        body.setVisibility(visible ? View.VISIBLE : View.GONE);
        if (chevron != null) {
            if (animate) chevron.animate().rotation(visible ? 180f : 0f).setDuration(220).start();
            else chevron.setRotation(visible ? 180f : 0f);
        }
        ViewCompat.setStateDescription(header, header.getContext().getString(
                visible ? R.string.apple_expanded : R.string.apple_collapsed));
    }

    /** 过渡在最近的滚动容器内执行，让下方内容一起平滑移动。 */
    private View sceneRoot() {
        View current = body;
        while (current.getParent() instanceof View) {
            View parent = (View) current.getParent();
            if (parent instanceof android.widget.ScrollView) return current;
            current = parent;
        }
        return body.getParent() instanceof View ? (View) body.getParent() : null;
    }
}
