package com.deepseekharness.app.util;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Set;

/** 迁移输出只接受一条完整结构化回执；错误文字中的 status 不能授予启动许可。 */
public final class Rc1MigrationResult {

    /**
     * 严格 JSON 记录解析器，实现通常传 {@code backup.BackupJson::read}。
     *
     * <p>为什么当参数注入而不是直接 import：{@code util/} 是被 {@code backup/}、{@code core/}
     * 依赖的最底层，反过来 import {@code backup/} 会形成包环（{@code backup/} 有 7 个类
     * import {@code util/}）。注入之后回执的契约 —— 只认唯一一条带前缀的行、64 KiB 上限、
     * UTF-8 字节 —— 仍然只写在这一处，调用方只是把「怎么解析 JSON」带进来。
     * 顺带这个类也不再需要 Android 之外的任何 app 内依赖，单测可以自己控制解析器。
     */
    @FunctionalInterface
    public interface StrictJsonRecord {
        Map<String, Object> read(byte[] utf8, int limit) throws IOException;
    }

    private static final String PREFIX = "DSHA_RC1_MIGRATION=";
    /** 单条回执的字节上限，与原来的调用约定一致。 */
    private static final int LIMIT = 65536;

    private Rc1MigrationResult() { }

    public static Map<String,Object> parse(String output, StrictJsonRecord reader) throws IOException {
        Map<String,Object> result=null;
        if(output!=null)for(String line:output.split("\\r?\\n"))if(line.startsWith(PREFIX)) {
            if(result!=null)throw new IOException("RC1_MIGRATION_DUPLICATE_RESULT");
            result=reader.read(line.substring(PREFIX.length()).getBytes(StandardCharsets.UTF_8), LIMIT);
        }
        if(result==null)throw new IOException("RC1_MIGRATION_RESULT_MISSING");
        return result;
    }

    public static boolean allowsStart(Map<String,Object> value) {
        String status=String.valueOf(value.get("status"));
        return "skipped".equals(status)&&"DSH_MISSING".equals(value.get("reason"))
                || Set.of("prepared","already").contains(status)&&Boolean.TRUE.equals(value.get("protectionComplete"));
    }
}
