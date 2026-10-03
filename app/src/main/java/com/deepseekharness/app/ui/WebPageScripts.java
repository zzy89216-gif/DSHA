package com.deepseekharness.app.ui;
import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
public final class WebPageScripts {
    private WebPageScripts() { }
    /** 应急页只注入语言与语法兼容，不注册正式设备/插件桥。 */
    public static String emergencyCompatibility(Context context) {
        return language(context)+"\n"+read(context,"web-integration/es-compat.js")+"\n"+read(context,"web-integration/compat.js");
    }
    public static String compatibility(Context context) {
        String section="";
        if(context instanceof android.app.Activity){String url=((android.app.Activity)context).getIntent().getStringExtra("url");
            if(((android.app.Activity)context).getIntent().getBooleanExtra("dsha_open_models",false)||(url!=null&&url.endsWith("#dsha-models")))section="window.__DSHA_OPEN_MODELS__=true;window.dispatchEvent(new Event('dsha-open-models'));\n";}
        return "window.__DSHA_NATIVE_PLUGINS__=true;\n"+section + language(context) + "\n" + read(context, "web-integration/es-compat.js") + "\n"
                + read(context, "web-integration/compat.js") + "\n" + read(context, "web-integration/startup.js")
                + "\n" + ux();
    }

    /** 手机网页体验：代码块复制、Markdown 间距、输入区留白、流式区域少跳动、会话列表轻量搜索。不改 dsh 内核。 */
    private static String ux() {
        return "(function(){if(window.__dshaZzyUx)return;window.__dshaZzyUx=true;"
                + "var css='pre,code{border-radius:10px;}pre{position:relative;max-height:min(60vh,28rem);overflow:auto;}"
                + ".dsha-copy{position:absolute;top:8px;right:8px;z-index:2;font:12px/1.2 sans-serif;padding:6px 10px;"
                + "border-radius:8px;border:0;background:rgba(0,0,0,.55);color:#fff;}"
                + "article p,article li,article h1,article h2,article h3,.markdown p,.markdown li{margin:.55em 0;line-height:1.65;}"
                + "textarea,[contenteditable=true],[role=textbox]{scroll-margin-bottom:96px;}"
                + "[data-streaming],.streaming,[aria-live=polite]{contain:layout style;}"
                + "#dsha-session-search{width:calc(100% - 16px);margin:8px;padding:8px 10px;border-radius:10px;"
                + "border:1px solid rgba(128,128,128,.35);font-size:14px;box-sizing:border-box;}';"
                + "var s=document.createElement('style');s.textContent=css;"
                + "(document.head||document.documentElement).appendChild(s);"
                + "function zh(){return window.__DSHA_LANGUAGE__!=='en';}"
                + "function copyBtn(pre){if(!pre||pre.querySelector('.dsha-copy'))return;"
                + "var b=document.createElement('button');b.className='dsha-copy';b.type='button';"
                + "b.textContent=zh()?'复制':'Copy';b.addEventListener('click',function(ev){ev.preventDefault();ev.stopPropagation();"
                + "var t=(pre.innerText||'').replace(/\\s*(复制|Copied|Copy|已复制)\\s*$/,'');"
                + "function ok(){b.textContent=zh()?'已复制':'Copied';setTimeout(function(){b.textContent=zh()?'复制':'Copy';},1200);}"
                + "if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(ok).catch(function(){});"
                + "else ok();});pre.appendChild(b);}"
                + "function scan(){document.querySelectorAll('pre').forEach(copyBtn);search();}"
                + "function search(){if(document.getElementById('dsha-session-search'))return;"
                + "var items=document.querySelectorAll('[data-session-id]');"
                + "if(items.length<3)return;var host=items[0].parentElement;if(!host||host.dataset.dshaSearch)return;"
                + "host.dataset.dshaSearch='1';var i=document.createElement('input');i.id='dsha-session-search';i.type='search';"
                + "i.placeholder=zh()?'搜索会话':'Search chats';i.addEventListener('input',function(){var q=i.value.toLowerCase();"
                + "Array.prototype.forEach.call(host.children,function(el){if(el===i)return;"
                + "var text=(el.textContent||'').toLowerCase();el.style.display=!q||text.indexOf(q)>=0?'':'none';});});"
                + "host.insertBefore(i,host.firstChild);}"
                + "scan();new MutationObserver(function(){scan();}).observe(document.documentElement,{childList:true,subtree:true});"
                + "})();";
    }
    public static String language(Context context) {
        String id=new com.deepseekharness.app.core.ConfigStore(context).getUiLanguage();
        return "window.__DSHA_LANGUAGE__='"+id+"';window.dispatchEvent(new CustomEvent('dsha-language'));"
            +"if(!window.__dshaLanguageSelectionBound){window.__dshaLanguageSelectionBound=true;window.addEventListener('dsha-language-selected',e=>{if(e.detail==='en'||e.detail==='zh')window.DshaLanguage?.postMessage(e.detail);});}";
    }
    private static String read(Context context, String path) {
        try (InputStream in = context.getAssets().open(path)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[4096]; int n;
            while ((n = in.read(buffer)) != -1) out.write(buffer,0,n);
            return new String(out.toByteArray(),StandardCharsets.UTF_8);
        } catch(IOException error) { return ""; }
    }
    public static String back(Context context) {
        try (InputStream in = context.getAssets().open("web-integration/page.js")) {
            ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[4096]; int n;
            while ((n = in.read(buffer)) != -1) out.write(buffer,0,n);
            return "(function(){" + new String(out.toByteArray(), StandardCharsets.UTF_8) + ";return window.__dshaPageBack();})()";
        } catch (IOException error) { return "false"; }
    }
}
