package com.deepseekharness.app.ui;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.net.Uri;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** 自定义背景图片的读取与保存：只保存一份缩放后的 JPEG，原图不复制、不上传。 */
final class BackgroundImageStore {
    private static final int MAX_EDGE = 1440;

    private BackgroundImageStore() { }

    static boolean save(Context context, Uri uri, File target) {
        File temp = new File(target.getPath() + ".tmp");
        try {
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            try (InputStream in = context.getContentResolver().openInputStream(uri)) {
                if (in == null) return false;
                BitmapFactory.decodeStream(in, null, bounds);
            }
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return false;
            int sample = 1;
            while (Math.max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= MAX_EDGE) sample *= 2;
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inSampleSize = sample;
            Bitmap bitmap;
            try (InputStream in = context.getContentResolver().openInputStream(uri)) {
                if (in == null) return false;
                bitmap = BitmapFactory.decodeStream(in, null, options);
            }
            if (bitmap == null) return false;
            Matrix matrix = new Matrix();
            int rotation = rotation(context, uri);
            if (rotation != 0) matrix.postRotate(rotation);
            float scale = Math.min(1f, MAX_EDGE / (float) Math.max(bitmap.getWidth(), bitmap.getHeight()));
            if (scale < 1f) matrix.postScale(scale, scale);
            if (!matrix.isIdentity()) {
                Bitmap transformed = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
                if (transformed != bitmap) bitmap.recycle();
                bitmap = transformed;
            }
            try (FileOutputStream out = new FileOutputStream(temp)) {
                if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 88, out)) return false;
            } finally {
                bitmap.recycle();
            }
            return temp.renameTo(target);
        } catch (Exception | OutOfMemoryError error) {
            return false;
        } finally {
            //noinspection ResultOfMethodCallIgnored
            temp.delete();
        }
    }

    private static int rotation(Context context, Uri uri) {
        if (android.os.Build.VERSION.SDK_INT < 24) return 0;
        try (InputStream in = context.getContentResolver().openInputStream(uri)) {
            if (in == null) return 0;
            int orientation = new android.media.ExifInterface(in).getAttributeInt(
                    android.media.ExifInterface.TAG_ORIENTATION, android.media.ExifInterface.ORIENTATION_NORMAL);
            return orientation == android.media.ExifInterface.ORIENTATION_ROTATE_90 ? 90
                    : orientation == android.media.ExifInterface.ORIENTATION_ROTATE_180 ? 180
                    : orientation == android.media.ExifInterface.ORIENTATION_ROTATE_270 ? 270 : 0;
        } catch (Exception ignored) {
            return 0;
        }
    }
}
