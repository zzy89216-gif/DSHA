package com.deepseekharness.app.ui;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.provider.Settings;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.deepseekharness.app.R;

import java.io.File;

/**
 * 窗口背景：自定义图片（居中裁切 + 主题色遮罩）或可选动态玻璃（低帧率径向渐变斑点）。
 * 玻璃约 12 fps；不可见、省电模式或系统关闭动画时静止。Web 工作台不走这里。
 */
final class BackdropDrawable extends Drawable {
    private static final long FRAME_MS = 80;
    private static Bitmap cachedImage;
    private static String cachedKey = "";

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint scrim = new Paint();
    private final Paint blob = new Paint(Paint.ANTI_ALIAS_FLAG);
    @Nullable private final Bitmap image;
    private final boolean glass;
    private final int baseColor;
    private final int[] blobColors;
    private final Rect source = new Rect();
    private final Handler frames = new Handler(Looper.getMainLooper());
    private final boolean still;
    private final Runnable tick;
    private boolean scheduled;

    private BackdropDrawable(Context context, @Nullable Bitmap image) {
        this.image = image;
        this.glass = image == null;
        this.baseColor = context.getColor(R.color.backdrop_base);
        scrim.setColor(context.getColor(R.color.backdrop_scrim));
        blobColors = new int[] {
                withAlpha(context.getColor(R.color.primary), 0x55),
                withAlpha(context.getColor(R.color.primary_dark), 0x40),
                withAlpha(context.getColor(R.color.ok), 0x28)
        };
        still = shouldStayStill(context);
        tick = () -> {
            scheduled = false;
            if (still || !isVisible() || getCallback() == null) return;
            invalidateSelf();
        };
    }

    private static int withAlpha(int color, int alpha) {
        return (color & 0x00FFFFFF) | (alpha << 24);
    }

    private static boolean shouldStayStill(Context context) {
        try {
            float scale = Settings.Global.getFloat(context.getContentResolver(),
                    Settings.Global.ANIMATOR_DURATION_SCALE, 1f);
            if (scale <= 0f) return true;
        } catch (RuntimeException ignored) { }
        PowerManager power = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        return power != null && power.isPowerSaveMode();
    }

    @Nullable static Drawable image(Context context, File file) {
        Bitmap bitmap = load(file);
        return bitmap == null ? null : new BackdropDrawable(context, bitmap);
    }

    static Drawable glass(Context context) {
        return new BackdropDrawable(context, null);
    }

    static synchronized void clearImageCache() {
        cachedImage = null;
        cachedKey = "";
    }

    private static synchronized Bitmap load(File file) {
        if (!file.isFile()) return null;
        String key = file.getAbsolutePath() + ":" + file.lastModified() + ":" + file.length();
        if (key.equals(cachedKey) && cachedImage != null) return cachedImage;
        try {
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inPreferredConfig = Bitmap.Config.RGB_565;
            cachedImage = BitmapFactory.decodeFile(file.getAbsolutePath(), options);
            cachedKey = cachedImage == null ? "" : key;
            return cachedImage;
        } catch (OutOfMemoryError | RuntimeException error) {
            clearImageCache();
            return null;
        }
    }

    @Override public void draw(@NonNull Canvas canvas) {
        Rect b = getBounds();
        if (b.isEmpty()) return;
        if (glass) {
            canvas.drawColor(baseColor);
            float t = still ? 0f : SystemClock.uptimeMillis() / 1000f;
            drawBlob(canvas, b, 0.28f + 0.08f * (float) Math.sin(t * 0.35),
                    0.30f + 0.07f * (float) Math.cos(t * 0.27), 0.62f, blobColors[0]);
            drawBlob(canvas, b, 0.72f + 0.07f * (float) Math.cos(t * 0.31),
                    0.68f + 0.08f * (float) Math.sin(t * 0.23), 0.70f, blobColors[1]);
            drawBlob(canvas, b, 0.50f + 0.10f * (float) Math.sin(t * 0.19),
                    0.42f + 0.06f * (float) Math.cos(t * 0.41), 0.48f, blobColors[2]);
            canvas.drawRect(b, scrim);
            if (!still) schedule();
            return;
        }
        float scale = Math.max(b.width() / (float) image.getWidth(), b.height() / (float) image.getHeight());
        int w = Math.round(b.width() / scale), h = Math.round(b.height() / scale);
        int left = (image.getWidth() - w) / 2, top = (image.getHeight() - h) / 2;
        source.set(left, top, left + w, top + h);
        canvas.drawBitmap(image, source, b, paint);
        canvas.drawRect(b, scrim);
    }

    private void drawBlob(Canvas canvas, Rect b, float rx, float ry, float radiusRatio, int color) {
        float cx = b.left + b.width() * rx;
        float cy = b.top + b.height() * ry;
        float radius = Math.max(b.width(), b.height()) * radiusRatio;
        if (radius <= 0f) return;
        blob.setShader(new RadialGradient(cx, cy, radius, color, 0x00000000, Shader.TileMode.CLAMP));
        canvas.drawCircle(cx, cy, radius, blob);
        blob.setShader(null);
    }

    private void schedule() {
        if (scheduled || still) return;
        scheduled = true;
        frames.postDelayed(tick, FRAME_MS);
    }

    @Override public boolean setVisible(boolean visible, boolean restart) {
        boolean changed = super.setVisible(visible, restart);
        if (visible && glass && !still) schedule();
        else { frames.removeCallbacks(tick); scheduled = false; }
        return changed;
    }

    @Override public void setAlpha(int alpha) { paint.setAlpha(alpha); }
    @Override public void setColorFilter(@Nullable ColorFilter filter) { paint.setColorFilter(filter); }
    @SuppressWarnings("deprecation")
    @Override public int getOpacity() { return PixelFormat.OPAQUE; }
}
