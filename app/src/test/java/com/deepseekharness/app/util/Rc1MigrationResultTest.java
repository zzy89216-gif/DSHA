package com.deepseekharness.app.util;

import com.deepseekharness.app.backup.BackupJson;
import org.junit.Test;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import static org.junit.Assert.*;

public class Rc1MigrationResultTest {

    /** 记下注入的解析器收到了什么，用来钉住编码与上限这两条原本只靠约定维持的契约。 */
    private static final class Recorder implements Rc1MigrationResult.StrictJsonRecord {
        byte[] bytes;int limit;int calls;
        @Override public Map<String,Object> read(byte[] utf8,int limit)throws IOException {
            this.bytes=utf8;this.limit=limit;this.calls++;
            return BackupJson.read(utf8,limit);
        }
    }

    private static Map<String,Object> parse(String output)throws IOException {
        return Rc1MigrationResult.parse(output,BackupJson::read);
    }

    @Test public void parsesExactRecordWithBothLineEndings()throws Exception {
        assertTrue(Rc1MigrationResult.allowsStart(parse("notice\r\nDSHA_RC1_MIGRATION={\"status\":\"prepared\",\"protectionComplete\":true}\r\n")));
        assertTrue(Rc1MigrationResult.allowsStart(parse("DSHA_RC1_MIGRATION={\"status\":\"already\",\"protectionComplete\":true}\n")));
    }

    @Test public void statusTextCannotReplaceProtection()throws Exception {
        assertFalse(Rc1MigrationResult.allowsStart(Map.of("status","prepared")));
        assertFalse(Rc1MigrationResult.allowsStart(Map.of("status","failed","protectionComplete",true)));
        assertFalse(Rc1MigrationResult.allowsStart(Map.of("status","skipped","reason","ERROR")));
        assertTrue(Rc1MigrationResult.allowsStart(Map.of("status","skipped","reason","DSH_MISSING")));
        assertThrows(IOException.class,()->parse("ERROR: {\"status\":\"prepared\"}"));
        assertThrows(IOException.class,()->parse("DSHA_RC1_MIGRATION={}\nDSHA_RC1_MIGRATION={}"));
    }

    @Test public void readerGetsUtf8BytesAndTheSixtyFourKibLimit()throws Exception {
        Recorder recorder=new Recorder();
        Rc1MigrationResult.parse("DSHA_RC1_MIGRATION={\"状态\":\"prepared\"}",recorder);
        assertEquals(1,recorder.calls);
        assertEquals(65536,recorder.limit);
        assertArrayEquals("{\"状态\":\"prepared\"}".getBytes(StandardCharsets.UTF_8),recorder.bytes);
    }

    @Test public void duplicateRecordIsRejectedBeforeTheSecondIsRead()throws Exception {
        // 两条回执必须在读到第二条**之前**就拒绝：既不能后一条覆盖前一条，
        // 也不能把不可信的后续内容喂给解析器。
        Recorder recorder=new Recorder();
        assertThrows(IOException.class,()->Rc1MigrationResult.parse(
                "DSHA_RC1_MIGRATION={\"status\":\"prepared\"}\nDSHA_RC1_MIGRATION={\"status\":\"already\"}",recorder));
        assertEquals(1,recorder.calls);
    }
}
