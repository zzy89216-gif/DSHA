package com.deepseekharness.app.ui;

import android.app.ActivityManager;
import android.content.Context;
import android.os.Build;
import android.os.Looper;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;

import com.deepseekharness.app.R;

/**
 * 内置 Web 工作台的渲染调优，只改宿主 WebView 参数，不改页面与鉴权逻辑。
 *
 * <ul>
 *   <li>背景与主题一致：首帧不再闪白（深色模式尤其明显）。</li>
 *   <li>非低内存设备开启离屏预光栅化：长对话滚动、切回前台时更少白块。</li>
 *   <li>前台渲染进程优先级设为 IMPORTANT，后台自动降级，不额外耗电。</li>
 *   <li>关闭越界发光：去掉每次滚动到底的额外重绘。</li>
 *   <li>启动页空闲时预热 WebView 内核：首次进入工作台少一次几百毫秒的 Chromium 加载。</li>
 * </ul>
 */
final class WebViewTuning {
    private static volatile boolean warmed;

    private WebViewTuning() { }

    static void apply(Context context, WebView view) {
        try {
            view.setBackgroundColor(context.getColor(R.color.surface));
            view.setOverScrollMode(View.OVER_SCROLL_NEVER);
            WebSettings settings = view.getSettings();
            if (Build.VERSION.SDK_INT >= 23 && !lowRam(context)) settings.setOffscreenPreRaster(true);
            if (Build.VERSION.SDK_INT >= 26)
                view.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, true);
        } catch (RuntimeException ignored) {
            // 个别厂商 WebView 不支持某项参数时保持默认，不影响进入工作台。
        }
    }

    /** 主线程空闲时加载 WebView 提供方；失败或无系统 WebView（兼容版 Gecko）时静默跳过。 */
    static void prewarm(Context context) {
        if (warmed) return;
        warmed = true;
        final Context app = context.getApplicationContext();
        Looper.getMainLooper().getQueue().addIdleHandler(() -> {
            try { WebSettings.getDefaultUserAgent(app); } catch (Throwable ignored) { }
            return false;
        });
    }

    private static boolean lowRam(Context context) {
        ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        return manager == null || manager.isLowRamDevice();
    }
}
