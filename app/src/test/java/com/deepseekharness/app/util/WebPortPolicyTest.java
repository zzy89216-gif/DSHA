package com.deepseekharness.app.util;
import org.junit.Test;
import java.net.*;
import java.io.*;
import static org.junit.Assert.*;

public class WebPortPolicyTest {
    @Test public void retainsPreferredAndReusesOnlyAvailableCachedPort() throws Exception {
        assertEquals(Constants.DSH_WEB_PORT,WebPortPolicy.choose(Constants.DSH_WEB_PORT,40000,port->true).listen);
        assertEquals(40000,WebPortPolicy.choose(Constants.DSH_WEB_PORT,40000,port->port==40000).listen);
        assertEquals(0,WebPortPolicy.choose(Constants.DSH_WEB_PORT,40000,port->false).listen);
        assertEquals(0,WebPortPolicy.choose(Constants.SHELL_BRIDGE_PORT,Constants.LAN_BRIDGE_PORT,
                port->{throw new AssertionError("reserved port probed");}).listen);
    }
    @Test public void bindsWithoutConnectingToOrDisturbingOccupiedListener() throws Exception {
        try(ServerSocket owner=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"))) {
            assertFalse(WebPortPolicy.available(owner.getLocalPort()));
            assertEquals(0,WebPortPolicy.choose(owner.getLocalPort(),0,WebPortPolicy::available).listen);
            assertFalse(owner.isClosed());
        }
    }
    @Test public void probeFailuresDoNotPretendToBePortCollisions() {
        try {WebPortPolicy.choose(Constants.DSH_WEB_PORT,0,port->{throw new IOException("permission denied");});fail();}
        catch(IOException expected){assertEquals("permission denied",expected.getMessage());}
    }
    @Test public void dynamicPortRequiresUnambiguousOfficialLoopbackStartupLine() {
        String token="a".repeat(43),url="http://127.0.0.1:45678/?token="+token;
        assertEquals(url,WebPortPolicy.authentication("dsh web: "+url+"\n",0));
        assertNull(WebPortPolicy.authentication("plugin example "+url,0));
        assertNull(WebPortPolicy.authentication("dsh web: "+url+"\ndsh web: http://127.0.0.1:45679/?token="+token,0));
        assertNull(WebPortPolicy.authentication("dsh web: http://localhost:45678/?token="+token,0));
        assertNull(WebPortPolicy.authentication("dsh web: http://127.0.0.1:"+Constants.SHELL_BRIDGE_PORT+"/?token="+token,0));
        assertNull(WebPortPolicy.authentication("dsh web: "+url,Constants.DSH_WEB_PORT));
    }
    @Test public void identifiesTheReportedWebBindFailureWithoutMisclassifyingOtherPluginErrors() {
        String error="@deepseek-ai/dsh-host-webserver: listen EADDRINUSE: address already in use 127.0.0.1:"+Constants.DSH_WEB_PORT;
        assertEquals(Constants.DSH_WEB_PORT,WebPortPolicy.conflictPort(error));
        assertEquals(-1,WebPortPolicy.conflictPort("a-plugin: listen EADDRINUSE 127.0.0.1:3090"));
        assertEquals(-1,WebPortPolicy.conflictPort("@deepseek-ai/dsh-host-webserver: Cannot find module example"));
        StartupTrace trace=new StartupTrace();trace.begin(1,0,false);trace.issue(1,10,"@deepseek-ai/dsh-web-app",error);
        assertTrue(trace.snapshot(20,"en").log.contains("Web port in use: " + Constants.DSH_WEB_PORT));
        assertFalse(trace.snapshot(20,"en").issues.containsKey("@deepseek-ai/dsh-web-app"));
    }
}
