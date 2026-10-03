package com.deepseekharness.app.ui;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import android.content.Intent;
import androidx.fragment.app.Fragment;
import com.deepseekharness.app.*;
import com.deepseekharness.app.util.UiText;
public final class AboutFragment extends Fragment {
    @Override public View onCreateView(LayoutInflater inflater,ViewGroup container,Bundle saved){
        CardPage ui=new CardPage(requireContext(),UiText.choose("关于 DeepSeek Harness","About DeepSeek Harness"),"");
        android.widget.FrameLayout emblem=new android.widget.FrameLayout(requireContext());android.widget.ImageView mark=new android.widget.ImageView(requireContext());mark.setImageResource(R.drawable.ic_ui2_prompt);mark.setBackgroundResource(R.drawable.bg_ui2_mark);mark.setPadding(ui.dp(14),ui.dp(14),ui.dp(14),ui.dp(14));emblem.addView(mark,new android.widget.FrameLayout.LayoutParams(ui.dp(64),ui.dp(64),Gravity.CENTER));ui.content.addView(emblem,new LinearLayout.LayoutParams(-1,ui.dp(84)));
        TextView brand=ui.text("DeepSeek Harness Android",26,R.color.text);brand.setTypeface(null,android.graphics.Typeface.BOLD);brand.setGravity(Gravity.CENTER);brand.setPadding(0,ui.dp(16),0,ui.dp(10));ui.content.addView(brand);
        TextView version=ui.text("DeepSeek Harness for Android\n"+BuildConfig.VERSION_NAME+" · "+BuildConfig.VERSION_CODE,12,R.color.text_secondary);version.setGravity(Gravity.CENTER);version.setPadding(0,0,0,ui.dp(24));ui.content.addView(version);
        LinearLayout metadata=ui.card();ui.kv(metadata,UiText.choose("包名","Package"),BuildConfig.APPLICATION_ID);ui.kv(metadata,UiText.choose("当前版本","Edition"),BuildConfig.LOW_ANDROID?UiText.choose("兼容版 · Android 6+","Compatibility · Android 6+"):UiText.choose("标准版 · Android 11+","Standard · Android 11+"));ui.kv(metadata,"DSH",com.deepseekharness.app.util.Constants.DSH_VERSION);ui.kv(metadata,UiText.choose("架构","Architecture"),"arm64-v8a");ui.kv(metadata,UiText.choose("开源许可","License"),"MIT");
        ui.label(UiText.choose("了解更多","Learn more"));LinearLayout links=ui.card();
        // 对外只暴露本项目自己的入口；来源声明与第三方许可在仓库的 THIRD_PARTY_NOTICES.md 里。
        ui.entry(links,UiText.choose("项目仓库","Repository"),"github.com/zzy89216-gif/DSHA",R.drawable.ic_ui_link,()->AboutDialog.openBrowser(requireContext(),com.deepseekharness.app.util.ProjectLinks.REPOSITORY));
        ui.entry(links,UiText.choose("问题反馈","Issue tracker"),UiText.choose("在 GitHub 提交问题","Report on GitHub"),R.drawable.ic_ui_chat,()->AboutDialog.openBrowser(requireContext(),com.deepseekharness.app.util.ProjectLinks.ISSUES));
        ui.entry(links,UiText.choose("开源许可","Open-source licenses"),UiText.choose("DeepSeek Harness 与随包第三方组件","DeepSeek Harness and bundled components"),R.drawable.ic_recovery_document,()->CardSheet.show(requireContext(),UiText.choose("开源许可","Licenses"),license()));
        ui.footer.setVisibility(View.GONE);return ui.root;
    }
    private String license(){try(var in=requireContext().getAssets().open("licenses/DSHA-MIT.txt");var out=new java.io.ByteArrayOutputStream()){byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return out.toString("UTF-8")+"\n\n"+UiText.choose("Ubuntu、Node.js、pnpm、Gecko 与其他依赖遵循各自许可。完整清单位于项目 THIRD_PARTY_NOTICES.md。","Ubuntu, Node.js, pnpm, Gecko and other dependencies retain their own licenses. See THIRD_PARTY_NOTICES.md in the repository.");}catch(java.io.IOException unavailable){return "MIT · " + com.deepseekharness.app.util.ProjectLinks.REPOSITORY + "/blob/main/THIRD_PARTY_NOTICES.md";}}
}
