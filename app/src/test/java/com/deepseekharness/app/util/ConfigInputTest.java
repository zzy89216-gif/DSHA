package com.deepseekharness.app.util;

import org.junit.Test;
import static org.junit.Assert.*;

public class ConfigInputTest {
    @Test public void usablePorts() {
        assertEquals(Constants.DSH_WEB_PORT, ConfigInput.port(" " + Constants.DSH_WEB_PORT + " "));
        assertEquals(1, ConfigInput.port("1"));
        assertEquals(1024, ConfigInput.port("1024"));
        assertEquals(65535, ConfigInput.port("65535"));
    }
    @Test public void reservedAndMalformedPortsNeverSilentlyFallback() {
        for (String value : new String[]{String.valueOf(Constants.LAN_BRIDGE_PORT),
                String.valueOf(Constants.SHELL_BRIDGE_PORT), "0", "-1", "65536", "", "x", "999999999999", "30.80"})
            assertThrows(value, IllegalArgumentException.class, () -> ConfigInput.port(value));
    }
}
