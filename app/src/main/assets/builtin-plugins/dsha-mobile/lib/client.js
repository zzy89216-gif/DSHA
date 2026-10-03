/*
 * dsha-mobile 网页端：为手机重做的 DSHA 外壳。
 *
 * 只用 dsh 0.2 公开的插槽与服务，不改内核：
 *   - shell.overlay：底部标签栏（对话 / 会话 / 新建 / 设置）
 *   - settings.general.item：手机模式、动态玻璃、配色三项设置
 *   - theme.overrideTokens：配色与玻璃的颜色层（同一层提交，避免互相覆盖）
 *   - layout / uiWorkspace：开关侧栏、新建会话
 * 布局只认稳定的 data-* 属性，不依赖会随版本变化的哈希类名。
 *
 * 流畅度约定：动画只用 transform / opacity；不做全页扫描（只观察一个属性）；
 * 毛玻璃只给底栏这一小块；页面隐藏、系统「减少动画」时玻璃静止。
 */
window.__ModuleLoader__.load({
  id: "dsha-mobile",
  factory: (require) => {
    const React = require("react");
    let primitives = {};
    try { primitives = require("@deepseek-ai/dsh-client-ui-primitives") || {}; } catch (_) { /* 退回自带开关 */ }
    const h = React.createElement;

    const PLUGIN_ID = "dsha-mobile";
    const NS = "dsha-mobile";
    const STORAGE_KEY = "dsha-mobile:prefs:v1";
    const MOBILE_QUERY = "(max-width: 1023px)"; // 与上游侧栏自动收起阈值 1024 对齐
    const PALETTES = ["default", "warm", "cyan", "oled"];
    const DEFAULTS = Object.freeze({ mobile: true, glass: false, palette: "default" });

    // ---------- 偏好：localStorage + 极简订阅 ----------
    function readPrefs() {
      try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        return {
          mobile: typeof raw.mobile === "boolean" ? raw.mobile : DEFAULTS.mobile,
          glass: typeof raw.glass === "boolean" ? raw.glass : DEFAULTS.glass,
          palette: PALETTES.includes(raw.palette) ? raw.palette : DEFAULTS.palette,
        };
      } catch (_) {
        return { ...DEFAULTS };
      }
    }
    let prefs = readPrefs();
    const prefListeners = new Set();
    function setPrefs(patch) {
      prefs = Object.freeze({ ...prefs, ...patch });
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (_) { /* 隐私模式 */ }
      prefListeners.forEach((fn) => fn());
    }
    const prefStore = {
      get: () => prefs,
      subscribe: (fn) => { prefListeners.add(fn); return () => prefListeners.delete(fn); },
    };
    const usePrefs = () => React.useSyncExternalStore(prefStore.subscribe, prefStore.get, prefStore.get);

    // ---------- 侧栏抽屉开合：只观察框架上的一个属性 ----------
    let frameEl = null;
    let drawerOpen = false;
    const drawerListeners = new Set();
    let frameObserver = null;
    /** 本插件最后一次请求的开合状态与时刻：同一个意图的重复调用不再 toggle 一次。 */
    let drawerWanted = false;
    let drawerWantedAt = 0;
    const DRAWER_TOGGLE_DEBOUNCE_MS = 800;
    function findFrame() {
      const overlay = document.querySelector("[data-shell-overlay]");
      return overlay ? overlay.parentElement : null;
    }
    /** 框架上的真实开合状态（缓存值可能比 DOM 慢一帧）。 */
    function drawerOpenNow() {
      const el = frameEl || findFrame();
      return !!el && !el.hasAttribute("data-sidebar-collapsed");
    }
    function bindFrame() {
      const el = findFrame();
      if (!el || el === frameEl) return !!el;
      frameEl = el;
      if (frameObserver) frameObserver.disconnect();
      const sync = () => {
        const open = !el.hasAttribute("data-sidebar-collapsed");
        if (open === drawerOpen) return;
        drawerOpen = open;
        document.documentElement.toggleAttribute("data-dsha-m-drawer", open);
        drawerListeners.forEach((fn) => fn());
      };
      frameObserver = new MutationObserver(sync);
      frameObserver.observe(el, { attributes: true, attributeFilter: ["data-sidebar-collapsed"] });
      sync();
      return true;
    }
    const drawerStore = {
      get: () => drawerOpen,
      subscribe: (fn) => { drawerListeners.add(fn); return () => drawerListeners.delete(fn); },
    };

    // ---------- 样式：一次性注入 ----------
    const M = "html[data-dsha-m]";
    const CSS = [
      // 底栏高度与安全区
      `${M}{--dsha-tab-h:56px;--dsha-safe-b:env(safe-area-inset-bottom,0px);--dsha-tab-space:calc(var(--dsha-tab-h) + var(--dsha-safe-b));}`,
      `${M},${M} body{overscroll-behavior:none;-webkit-tap-highlight-color:transparent;}`,
      `${M} button,${M} [role=button],${M} a{touch-action:manipulation;}`,

      // 侧栏：收起时不占列（去掉电脑版 56px 窄栏），对话区占满全宽
      `${M} [data-shell-overlay]{z-index:20;}`,
      `${M} [data-shell-overlay][data-rightbar-collapsed]{}`,
      `${M} :is([data-sidebar-collapsed][data-rightbar-collapsed]){grid-template-columns:0px minmax(0,1fr) 0px !important;}`,
      `${M} [data-sidebar-collapsed] > div:has(> [data-slot=sidebar]){visibility:hidden;}`,

      // 侧栏展开：改成从左侧滑出的抽屉，盖在对话上，不再把对话挤成一条
      `${M} :not([data-sidebar-collapsed]) > div:has(> [data-slot=sidebar]){overflow:visible;}`,
      `${M} div:has(> [data-shell-overlay]):not([data-sidebar-collapsed]):is([data-rightbar-collapsed]){grid-template-columns:0px minmax(0,1fr) 0px !important;}`,
      `${M} div:has(> [data-shell-overlay]) > div:has(> [data-slot=sidebar]) > [data-slot=sidebar] > *{position:fixed;top:0;bottom:0;left:0;width:min(86vw,340px) !important;z-index:60;`
        + `transform:translate3d(-104%,0,0);transition:transform .26s cubic-bezier(.2,.8,.2,1);will-change:transform;box-shadow:0 0 0 .5px var(--dsw-alias-border-l3),8px 0 28px rgba(0,0,0,.18);`
        + `overscroll-behavior:contain;padding-bottom:calc(8px + var(--dsha-safe-b));box-sizing:border-box;}`,
      `${M} div:has(> [data-shell-overlay]):not([data-sidebar-collapsed]) > div:has(> [data-slot=sidebar]) > [data-slot=sidebar] > *{transform:translate3d(0,0,0);}`,
      // 抽屉里的电脑版「展开/收起」按钮在手机上多余
      `${M} [data-slot=sidebar] [data-window-drag] button[aria-label]:last-child{display:none;}`,

      // 抽屉遮罩：点空白处收起。层级必须低于抽屉（60），否则会把会话行上的点击吃掉。
      `.dsha-m-scrim{position:fixed;inset:0;z-index:29;background:rgba(0,0,0,.32);opacity:0;pointer-events:none;transition:opacity .22s ease;}`,
      `${M}[data-dsha-m-drawer] .dsha-m-scrim{opacity:1;pointer-events:auto;}`,

      // 给底栏让位；打字时底栏让给键盘，下面的占位也跟着撤掉
      `${M}:not([data-dsha-m-typing]) div:has(> [data-slot=main]){padding-bottom:var(--dsha-tab-space);box-sizing:border-box;}`,
      `${M}[data-dsha-m-typing] div:has(> [data-slot=main]){padding-bottom:0;}`,

      // 弹窗（设置面板等）不超出手机屏
      `${M} [role=dialog]{max-width:100vw !important;max-height:100dvh !important;}`,
      // 设置面板：全屏，左侧分类栏改为顶部横排（手机上内容区不再只剩一条）
      `${M} [data-shortcut-modal=settings]{flex-direction:column !important;width:100vw !important;height:100dvh !important;border-radius:0 !important;}`,
      `${M} [data-shortcut-modal=settings] > nav{flex:none !important;flex-direction:row !important;width:auto !important;height:auto !important;padding:10px 12px 6px !important;padding-right:52px !important;overflow-x:auto;scrollbar-width:none;border:0 !important;}`,
      `${M} [data-shortcut-modal=settings] > nav > div:first-child{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}`,
      `${M} [data-shortcut-modal=settings] > nav > div:last-child{flex-direction:row !important;gap:6px;margin:0 !important;padding:0 !important;}`,
      `${M} [data-shortcut-modal=settings] > nav button{flex:none !important;width:auto !important;white-space:nowrap;padding:0 14px !important;height:36px !important;border-radius:18px !important;}`,
      `${M} [data-shortcut-modal=settings] > div{flex:1 1 auto !important;min-height:0 !important;width:auto !important;}`,
      `${M} [data-shortcut-modal=settings] > div > div:first-child{position:absolute;top:0;right:0;width:auto !important;height:56px;display:flex !important;align-items:center !important;padding:0 10px 0 18px !important;z-index:2;background:linear-gradient(90deg,transparent,var(--dsw-alias-bg-layer-2) 30%);}`,
      `${M} [data-shortcut-modal=settings] > div > div:first-child > div:first-child{display:none !important;}`,
      // 面板底部给手势条留白（面板全屏盖住底栏，不需要再算底栏高度）
      `${M} [data-shortcut-modal=settings] > div > div:last-child{padding:0 24px calc(24px + var(--dsha-safe-b)) !important;}`,

      // 底部标签栏。层级要高于抽屉遮罩（29），否则抽屉打开时点底栏只会关抽屉、切不了页；
      // 但仍低于抽屉本体（60）。
      `.dsha-m-tabbar{display:none;}`,
      `${M} .dsha-m-tabbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:40;height:var(--dsha-tab-space);padding-bottom:var(--dsha-safe-b);box-sizing:border-box;`
        + `background:var(--dsw-alias-bg-base);border-top:.5px solid var(--dsw-alias-border-l3);transform:translate3d(0,0,0);transition:transform .2s ease;}`,
      `${M}[data-dsha-m-typing] .dsha-m-tabbar{transform:translate3d(0,110%,0);}`,
      `.dsha-m-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;border:0;background:none;padding:0;margin:0;`
        + `color:var(--dsw-alias-label-tertiary);font:500 11px/1 inherit;font-family:inherit;cursor:pointer;min-height:48px;}`,
      `.dsha-m-tab svg{width:23px;height:23px;transition:transform .15s ease;}`,
      `.dsha-m-tab:active svg{transform:scale(.88);}`,
      `.dsha-m-tab[aria-current=page]{color:var(--dsw-alias-label-primary);}`,
      `.dsha-m-tab-new svg{width:26px;height:26px;}`,

      // 设置行
      `.dsha-m-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 0;}`,
      `.dsha-m-row-title{font-size:14px;line-height:22px;color:var(--dsw-alias-label-primary);}`,
      `.dsha-m-row-desc{font-size:12px;line-height:18px;color:var(--dsw-alias-label-secondary);margin-top:2px;}`,
      `.dsha-m-row-warn{font-size:12px;line-height:18px;color:var(--dsw-alias-state-warn-label);margin-top:4px;}`,
      `.dsha-m-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}`,
      `.dsha-m-chip{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;border-radius:16px;border:1px solid var(--dsw-alias-border-l3);`
        + `background:var(--dsw-alias-bg-layer-1);color:var(--dsw-alias-label-primary);font:inherit;font-size:13px;cursor:pointer;}`,
      `.dsha-m-chip[aria-pressed=true]{border-color:var(--dsw-alias-label-primary);box-shadow:inset 0 0 0 .5px var(--dsw-alias-label-primary);}`,
      `.dsha-m-dot{width:12px;height:12px;border-radius:50%;box-shadow:inset 0 0 0 .5px rgba(0,0,0,.2);}`,
      `.dsha-m-switch{position:relative;flex:none;width:44px;height:26px;border-radius:13px;border:0;padding:0;cursor:pointer;background:var(--dsw-alias-border-l4);transition:background .2s;}`,
      `.dsha-m-switch[aria-checked=true]{background:var(--dsw-alias-brand-primary);}`,
      `.dsha-m-switch::after{content:"";position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;transition:transform .2s;}`,
      `.dsha-m-switch[aria-checked=true]::after{transform:translateX(18px);}`,

      // ---------- 动态玻璃 ----------
      // 玻璃层：固定在最底下，自带底色；大块渐变只画一次，动的只有三团光斑的 transform。
      `.dsha-glass{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden;contain:strict;background:var(--dsha-glass-base);}`,
      `.dsha-glass i{position:absolute;width:62vmax;height:62vmax;border-radius:50%;will-change:transform;animation:dsha-drift 26s ease-in-out infinite alternate;}`,
      `.dsha-glass i:nth-child(1){left:-18vmax;top:-14vmax;background:radial-gradient(closest-side,var(--dsha-g1),transparent);}`,
      `.dsha-glass i:nth-child(2){right:-22vmax;top:22vh;background:radial-gradient(closest-side,var(--dsha-g2),transparent);animation-duration:31s;animation-delay:-9s;}`,
      `.dsha-glass i:nth-child(3){left:6vmax;bottom:-26vmax;background:radial-gradient(closest-side,var(--dsha-g3),transparent);animation-duration:37s;animation-delay:-17s;}`,
      `@keyframes dsha-drift{0%{transform:translate3d(0,0,0) scale(1);}50%{transform:translate3d(8vmax,6vmax,0) scale(1.12);}100%{transform:translate3d(-6vmax,10vmax,0) scale(.94);}}`,
      `html[data-dsha-still] .dsha-glass i{animation-play-state:paused;}`,
      `@media (prefers-reduced-motion:reduce){.dsha-glass i{animation:none;}}`,
      // 让玻璃透出来：外层框架和中间列不再自己刷底色
      `html[data-dsha-glass],html[data-dsha-glass] body{background:transparent !important;}`,
      `html[data-dsha-glass] div:has(> [data-shell-overlay]),html[data-dsha-glass] div:has(> [data-slot=main]){background:transparent !important;}`,
      // 只有底栏用真毛玻璃（面积小，代价低）
      `html[data-dsha-glass] .dsha-m-tabbar{background:color-mix(in srgb,var(--dsha-glass-base) 62%,transparent);-webkit-backdrop-filter:blur(18px) saturate(1.5);backdrop-filter:blur(18px) saturate(1.5);}`,
      // 玻璃配色（亮 / 暗 × 四套）
      `html{--dsha-glass-base:#f4f6fb;--dsha-g1:#7aa6ff66;--dsha-g2:#b98cff55;--dsha-g3:#5fd6e04d;}`,
      `html:has(body[data-ds-dark-theme]){--dsha-glass-base:#0e1118;--dsha-g1:#3b6cff59;--dsha-g2:#8a4dff4d;--dsha-g3:#1fb6c447;}`,
      `html[data-dsha-palette=warm]{--dsha-glass-base:#fbf6f1;--dsha-g1:#ffab6b66;--dsha-g2:#ff7aa055;--dsha-g3:#ffd16b4d;}`,
      `html[data-dsha-palette=warm]:has(body[data-ds-dark-theme]){--dsha-glass-base:#15100c;--dsha-g1:#e8743a52;--dsha-g2:#d94b7a47;--dsha-g3:#c9952f3d;}`,
      `html[data-dsha-palette=cyan]{--dsha-glass-base:#f1f8f8;--dsha-g1:#4fd1c566;--dsha-g2:#5aa9ff55;--dsha-g3:#8be3a94d;}`,
      `html[data-dsha-palette=cyan]:has(body[data-ds-dark-theme]){--dsha-glass-base:#0a1214;--dsha-g1:#14a89a52;--dsha-g2:#2f7fe047;--dsha-g3:#3fae6a3d;}`,
      `html[data-dsha-palette=oled]{--dsha-glass-base:#f5f5f6;--dsha-g1:#9aa3b555;--dsha-g2:#c5cad44d;--dsha-g3:#7d869a40;}`,
      `html[data-dsha-palette=oled]:has(body[data-ds-dark-theme]){--dsha-glass-base:#000;--dsha-g1:#3a466640;--dsha-g2:#5b3a6638;--dsha-g3:#22404a38;}`,
    ].join("\n");

    function installStyles() {
      const tag = document.createElement("style");
      tag.dataset.plugin = PLUGIN_ID;
      tag.dataset.pluginCss = PLUGIN_ID + "/mobile.css";
      tag.textContent = CSS;
      document.head.appendChild(tag);
      return () => tag.remove();
    }

    // ---------- 配色 + 玻璃的颜色层 ----------
    const PALETTE_TOKENS = {
      default: {},
      warm: {
        "--dsw-alias-brand-primary": { light: "#c2410c", dark: "#fb923c" },
        "--dsw-alias-button-primary-fill": { light: "#c2410c", dark: "#fb923c" },
        "--dsw-alias-button-primary-hover": { light: "#9a3412", dark: "#fdba74" },
        "--dsw-alias-link": { light: "#c2410c", dark: "#fdba74" },
        "--dsw-specific-bubble": { light: "#fff1e6", dark: "#3a2416" },
        "--dsw-specific-bubble-highlight": { light: "#ffd9bf", dark: "#5a351f" },
        "--dsw-alias-bg-base": { light: "#fffbf7", dark: "#17120e" },
        "--dsw-specific-sidebar-fill": { light: "#fbf3ea", dark: "#1e1712" },
      },
      cyan: {
        "--dsw-alias-brand-primary": { light: "#0f766e", dark: "#2dd4bf" },
        "--dsw-alias-button-primary-fill": { light: "#0f766e", dark: "#2dd4bf" },
        "--dsw-alias-button-primary-hover": { light: "#115e59", dark: "#5eead4" },
        "--dsw-alias-link": { light: "#0e7490", dark: "#67e8f9" },
        "--dsw-specific-bubble": { light: "#e6f7f5", dark: "#12302d" },
        "--dsw-specific-bubble-highlight": { light: "#c3ece7", dark: "#1b4842" },
        "--dsw-alias-bg-base": { light: "#f8fcfc", dark: "#0d1414" },
        "--dsw-specific-sidebar-fill": { light: "#eef7f6", dark: "#121b1b" },
      },
      oled: {
        "--dsw-alias-bg-base": { light: "#ffffff", dark: "#000000" },
        "--dsw-alias-bg-layer-1": { light: "#ffffff", dark: "#0b0b0c" },
        "--dsw-alias-bg-layer-2": { light: "#ffffff", dark: "#121214" },
        "--dsw-specific-sidebar-fill": { light: "#f7f7f8", dark: "#050506" },
        "--dsw-specific-input-major": { light: "#ffffff", dark: "#0e0e10" },
        "--dsw-specific-bubble": { light: "#eef1f6", dark: "#16181d" },
        "--dsw-alias-markdown-code-block": { light: "#f6f7f9", dark: "#0c0d10" },
      },
    };
    const BASE_FALLBACK = {
      "--dsw-alias-bg-base": { light: "#ffffff", dark: "#151517" },
      "--dsw-specific-sidebar-fill": { light: "#f9fafb", dark: "#1b1b1c" },
    };
    function tokensFor(p) {
      const palette = PALETTE_TOKENS[p.palette] || {};
      const out = { ...palette };
      if (p.glass) {
        // 玻璃：底色半透明，透出下层光斑；侧栏抽屉保持高不透明度，保证文字清晰
        const base = palette["--dsw-alias-bg-base"] || BASE_FALLBACK["--dsw-alias-bg-base"];
        const side = palette["--dsw-specific-sidebar-fill"] || BASE_FALLBACK["--dsw-specific-sidebar-fill"];
        out["--dsw-alias-bg-base"] = {
          light: `color-mix(in srgb, ${base.light} 58%, transparent)`,
          dark: `color-mix(in srgb, ${base.dark} 52%, transparent)`,
        };
        out["--dsw-specific-sidebar-fill"] = {
          light: `color-mix(in srgb, ${side.light} 90%, transparent)`,
          dark: `color-mix(in srgb, ${side.dark} 90%, transparent)`,
        };
      }
      return out;
    }

    // ---------- 文案 ----------
    const zh = {
      "tab.chat": "对话", "tab.sessions": "会话", "tab.new": "新建", "tab.settings": "设置",
      "tab.label": "主导航",
      "mobile.title": "手机模式",
      "mobile.desc": "底部标签栏、侧栏改成抽屉、对话区占满屏宽。仅在窄屏（小于 1024 像素）生效。",
      "mobile.conflict": "检测到 dsh-web-mobile 也在改手机布局，建议在插件页停用其中一个。",
      "glass.title": "动态玻璃",
      "glass.desc": "缓慢流动的光斑背景，底栏毛玻璃。系统开启「减少动画」或页面在后台时自动静止。",
      "palette.title": "配色",
      "palette.default": "默认", "palette.warm": "暖橙", "palette.cyan": "青蓝", "palette.oled": "纯黑",
    };
    const en = {
      "tab.chat": "Chat", "tab.sessions": "Sessions", "tab.new": "New", "tab.settings": "Settings",
      "tab.label": "Main navigation",
      "mobile.title": "Mobile layout",
      "mobile.desc": "Bottom tab bar, drawer sidebar and full-width chat. Applies below 1024 px.",
      "mobile.conflict": "dsh-web-mobile is also changing the mobile layout. Disable one of them in Plugins.",
      "glass.title": "Dynamic glass",
      "glass.desc": "Slowly drifting light background with a frosted tab bar. Stays still with Reduce motion or in the background.",
      "palette.title": "Color palette",
      "palette.default": "Default", "palette.warm": "Warm", "palette.cyan": "Teal", "palette.oled": "True black",
    };
    let boundT = null;
    function fallbackT(key) {
      const lang = (document.documentElement.lang || navigator.language || "zh").toLowerCase();
      return (lang.startsWith("zh") ? zh : en)[key] || key;
    }
    function tr(t, key) {
      if (typeof t === "function") {
        const v = t(key);
        if (typeof v === "string" && v !== key) return v;
      }
      if (boundT) {
        const v = boundT(key);
        if (typeof v === "string" && v !== key) return v;
      }
      return fallbackT(key);
    }

    // ---------- 图标 ----------
    const svg = (paths) => h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true },
      ...paths.map((d, i) => h("path", { key: i, d })));
    const ICONS = {
      chat: () => svg(["M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4H6.5A2.5 2.5 0 0 1 4 13.5z"]),
      sessions: () => svg(["M4 6h16", "M4 12h16", "M4 18h10"]),
      new: () => svg(["M12 5v14", "M5 12h14"]),
      settings: () => svg(["M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
        "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"]),
    };

    // ---------- 动作 ----------
    let ctxRef = null;
    function service(name) {
      try { return ctxRef && ctxRef.get(name); } catch (_) { return undefined; }
    }
    function clickByLabel(labels) {
      const root = document.querySelector("[data-slot=sidebar]") || document;
      for (const label of labels) {
        const el = root.querySelector(`button[aria-label="${label}"]`);
        if (el) { el.click(); return true; }
      }
      return false;
    }
    function setDrawer(open) {
      bindFrame();
      // 以框架上的真实属性为准：缓存值在「刚点了会话、导航事件又来收一次」的窗口里
      // 比 DOM 慢一帧，照着缓存 toggle 会把抽屉重新打开。
      const live = drawerOpenNow();
      if (live === open) { drawerWanted = open; return; }
      const now = performance.now();
      if (open === drawerWanted && now - drawerWantedAt < DRAWER_TOGGLE_DEBOUNCE_MS) return;
      drawerWanted = open;
      drawerWantedAt = now;
      const layout = service("layout");
      if (layout && typeof layout.toggleSidebar === "function") layout.toggleSidebar();
      else clickByLabel(open ? ["打开侧边栏", "Open sidebar"] : ["收起侧边栏", "Collapse sidebar"]);
    }
    /**
     * 会话行的会话 id：宿主自己写在 `data-dsha-session-select` 上（没有这个标记的
     * 上游版本回退读 `data-row-key="session:<id>"`）。不猜 id 的形状。
     */
    function sessionIdOf(row) {
      if (!row || typeof row.getAttribute !== "function") return "";
      const marked = row.getAttribute("data-dsha-session-select");
      if (marked) return marked;
      const key = row.getAttribute("data-row-key") || "";
      return key.startsWith("session:") ? key.slice(8) : "";
    }
    /** 手指抬起当作「滚列表」的最大位移（像素）。 */
    const ROW_TAP_SLOP = 12;
    /** 超过这个时长的按压算长按（改名 / ⋯ 菜单），不是「要进这个会话」。 */
    const ROW_LONG_PRESS_MS = 450;
    /**
     * 抽屉里点一下会话行该怎么处理（纯逻辑，见 test/client.test.mjs）。
     *
     * <p>`open` = 直接进这个会话；`close` = 本来就是当前会话，只收抽屉；
     * `ignore` = 长按、拖列表或正在合成点击，什么都不做。
     */
    function rowTapAction(state) {
      if (state.suppressed || state.longPress || state.moved) return "ignore";
      return state.selected ? "close" : "open";
    }
    /**
     * 真正打开一个会话。
     *
     * <p>DSHA 宿主把会话行改成了「单击=选中、双击=打开」（`DSHA_SESSION_INTERACTION_V2`）。
     * 抽屉里点一下就行是手机的直觉，而且原来的实现会在第一次单击就把抽屉收掉，
     * 第二次点击永远落不到行上 —— 表现就是「侧边栏进的去、历史对话进不去」。
     * 所以这里直接打开：宿主有新式会话服务（`sessions.open`）就用它，否则合成一次
     * 「显式激活」点击（`detail === 0`，也就是宿主给键盘 Enter 走的那条路），
     * 让宿主自己的打开逻辑收尾 —— 不猜路由，也不伪造双击的时间戳。
     */
    function openSession(row) {
      const id = sessionIdOf(row);
      const sessions = service("sessions");
      if (id && sessions && typeof sessions.open === "function") {
        try { sessions.open(id); return true; } catch (error) { console.warn("[dsha-mobile] 打开会话失败", error); }
      }
      try { row.click(); return true; } catch (_) { return false; }
    }
    const actions = {
      chat() {
        setDrawer(false);
        const layout = service("layout");
        try {
          const info = layout && layout.panelInfo && layout.panelInfo.getSnapshot();
          if (info && info.activePanelId !== null) layout.selectPanel(null);
        } catch (_) { /* 没有面板可退 */ }
      },
      sessions() { setDrawer(!drawerOpenNow()); },
      newSession() {
        const ws = service("uiWorkspace");
        let ok = false;
        try { if (ws && typeof ws.startSession === "function") { ws.startSession(); ok = true; } } catch (_) { ok = false; }
        if (!ok) clickByLabel(["新建会话", "New session"]);
        setDrawer(false);
      },
      settings() {
        setDrawer(false);
        if (!clickByLabel(["设置", "Settings"])) {
          const any = document.querySelector('button[aria-label="设置"],button[aria-label="Settings"]');
          if (any) any.click();
        }
      },
    };

    // ---------- 组件 ----------
    function TabBar(props) {
      const p = usePrefs();
      const open = React.useSyncExternalStore(drawerStore.subscribe, drawerStore.get, drawerStore.get);
      React.useEffect(() => {
        if (bindFrame()) return undefined;
        let tries = 0;
        const id = setInterval(() => { if (bindFrame() || ++tries > 20) clearInterval(id); }, 250);
        return () => clearInterval(id);
      }, []);
      if (!p.mobile) return null;
      const t = props && props.t;
      const tab = (key, onClick, current, extraClass) => h("button", {
        key, type: "button", className: "dsha-m-tab" + (extraClass ? " " + extraClass : ""),
        "aria-current": current ? "page" : undefined, onClick,
      }, ICONS[key](), h("span", null, tr(t, "tab." + key)));
      return h(React.Fragment, null,
        h("div", { className: "dsha-m-scrim", "aria-hidden": true, onClick: () => setDrawer(false) }),
        h("nav", { className: "dsha-m-tabbar", "aria-label": tr(t, "tab.label") },
          tab("chat", actions.chat, !open),
          tab("sessions", actions.sessions, open),
          tab("new", actions.newSession, false, "dsha-m-tab-new"),
          tab("settings", actions.settings, false)));
    }

    function Toggle({ checked, onChange, label }) {
      if (typeof primitives.Switch === "function") return h(primitives.Switch, { checked, onChange, label });
      return h("button", { type: "button", role: "switch", "aria-checked": checked, "aria-label": label, className: "dsha-m-switch", onClick: () => onChange(!checked) });
    }

    function MobileRow(props) {
      const p = usePrefs();
      const t = props && props.t;
      const conflict = !!document.querySelector('style[data-plugin="dsh-web-mobile"]');
      return h("div", { className: "dsha-m-row" },
        h("div", null,
          h("div", { className: "dsha-m-row-title" }, tr(t, "mobile.title")),
          h("div", { className: "dsha-m-row-desc" }, tr(t, "mobile.desc")),
          conflict && p.mobile ? h("div", { className: "dsha-m-row-warn", role: "note" }, tr(t, "mobile.conflict")) : null),
        h(Toggle, { checked: p.mobile, label: tr(t, "mobile.title"), onChange: (v) => setPrefs({ mobile: v }) }));
    }

    function GlassRow(props) {
      const p = usePrefs();
      const t = props && props.t;
      return h("div", { className: "dsha-m-row" },
        h("div", null,
          h("div", { className: "dsha-m-row-title" }, tr(t, "glass.title")),
          h("div", { className: "dsha-m-row-desc" }, tr(t, "glass.desc"))),
        h(Toggle, { checked: p.glass, label: tr(t, "glass.title"), onChange: (v) => setPrefs({ glass: v }) }));
    }

    const DOTS = { default: "#4176e6", warm: "#ea7a32", cyan: "#14a89a", oled: "#000000" };
    function PaletteRow(props) {
      const p = usePrefs();
      const t = props && props.t;
      return h("div", { className: "dsha-m-row", style: { display: "block" } },
        h("div", { className: "dsha-m-row-title" }, tr(t, "palette.title")),
        h("div", { className: "dsha-m-chips", role: "group", "aria-label": tr(t, "palette.title") },
          ...PALETTES.map((id) => h("button", {
            key: id, type: "button", className: "dsha-m-chip", "aria-pressed": p.palette === id,
            onClick: () => setPrefs({ palette: id }),
          }, h("span", { className: "dsha-m-dot", style: { background: DOTS[id] } }), tr(t, "palette." + id)))));
    }

    // ---------- 根属性：手机模式 / 玻璃 / 配色 / 打字 / 后台 ----------
    function installRootSync() {
      const html = document.documentElement;
      const mq = window.matchMedia(MOBILE_QUERY);
      const apply = () => {
        html.toggleAttribute("data-dsha-m", prefs.mobile && mq.matches);
        html.toggleAttribute("data-dsha-glass", prefs.glass);
        if (prefs.palette === "default") html.removeAttribute("data-dsha-palette");
        else html.setAttribute("data-dsha-palette", prefs.palette);
      };
      apply();
      const offPrefs = prefStore.subscribe(apply);
      mq.addEventListener("change", apply);

      const editable = (el) => !!el && (el.isContentEditable || el.tagName === "TEXTAREA"
        || (el.tagName === "INPUT" && !["checkbox", "radio", "button", "range", "submit"].includes(el.type)));
      // 「在打字」= 输入框有焦点 且 可视高度明显变小（键盘真的弹出来了）。
      // 只看焦点不行：页面自动聚焦输入框时并不会弹键盘，底栏不该消失。
      const vv = window.visualViewport;
      const viewH = () => (vv ? vv.height : window.innerHeight);
      const fullH = new Map(); // 按屏幕宽度记录最大高度，横竖屏各一份
      const syncTyping = () => {
        const w = Math.round(window.innerWidth);
        const hNow = viewH();
        if (!fullH.has(w) || hNow > fullH.get(w)) fullH.set(w, hNow);
        const keyboard = fullH.get(w) - hNow > 140;
        html.toggleAttribute("data-dsha-m-typing", keyboard && editable(document.activeElement));
      };
      const onFocus = () => setTimeout(syncTyping, 0);
      const onBlur = () => setTimeout(syncTyping, 60);
      document.addEventListener("focusin", onFocus, true);
      document.addEventListener("focusout", onBlur, true);
      (vv || window).addEventListener("resize", syncTyping);
      syncTyping();

      const onVisible = () => html.toggleAttribute("data-dsha-still", document.hidden);
      document.addEventListener("visibilitychange", onVisible);
      onVisible();

      // 手机模式下点了会话行：直接打开那个会话，抽屉等导航落地再收起。
      // 不能在第一次点击就收抽屉（宿主单击只选中、双击才打开，收早了第二次点击落在对话区），
      // 也不能把长按（改名 / ⋯ 菜单）或拖列表当成「要进去」。
      let rowDownRow = null;
      let rowDownAt = 0;
      let rowDownX = 0;
      let rowDownY = 0;
      let synthesizing = false;
      const onRowPointerDown = (e) => {
        rowDownRow = null;
        if (!html.hasAttribute("data-dsha-m") || !drawerOpen) return;
        if (!e.target || !e.target.closest) return;
        const row = e.target.closest('[data-slot=sidebar] [data-row-key^="session:"]');
        if (!row) return;
        rowDownRow = row;
        rowDownAt = performance.now();
        rowDownX = e.clientX || 0;
        rowDownY = e.clientY || 0;
      };
      const onSessionTap = (e) => {
        const down = rowDownRow;
        const longPress = down !== null && performance.now() - rowDownAt > ROW_LONG_PRESS_MS;
        const moved = down !== null
          && (Math.abs((e.clientX || 0) - rowDownX) > ROW_TAP_SLOP || Math.abs((e.clientY || 0) - rowDownY) > ROW_TAP_SLOP);
        rowDownRow = null;
        if (!html.hasAttribute("data-dsha-m") || !drawerOpen) return;
        if (!e.target || !e.target.closest) return;
        const row = e.target.closest('[data-slot=sidebar] [data-row-key^="session:"]');
        if (!row) return;
        if (e.target.closest("button[aria-haspopup], [role=menu], [role=dialog]")) return;
        const action = rowTapAction({
          suppressed: synthesizing || e.defaultPrevented,
          longPress, moved,
          selected: row.getAttribute("aria-selected") === "true",
        });
        if (action === "ignore") return;
        if (action === "open") {
          synthesizing = true;
          openSession(row);
          synthesizing = false;
        }
        setTimeout(() => setDrawer(false), action === "open" ? 180 : 0);
      };
      document.addEventListener("pointerdown", onRowPointerDown, true);
      document.addEventListener("click", onSessionTap, true);
      // 宿主的双击路径真的打开了会话时也会派发这个事件：那时再收抽屉最稳。
      const onSessionOpen = () => { setTimeout(() => setDrawer(false), 60); };
      document.addEventListener("dsha-session-open", onSessionOpen);

      return () => {
        offPrefs();
        mq.removeEventListener("change", apply);
        document.removeEventListener("focusin", onFocus, true);
        document.removeEventListener("focusout", onBlur, true);
        (vv || window).removeEventListener("resize", syncTyping);
        document.removeEventListener("visibilitychange", onVisible);
        document.removeEventListener("pointerdown", onRowPointerDown, true);
        document.removeEventListener("click", onSessionTap, true);
        document.removeEventListener("dsha-session-open", onSessionOpen);
        if (frameObserver) frameObserver.disconnect();
        frameObserver = null; frameEl = null;
        for (const a of ["data-dsha-m", "data-dsha-glass", "data-dsha-palette", "data-dsha-m-typing", "data-dsha-still", "data-dsha-m-drawer"]) html.removeAttribute(a);
      };
    }

    function installGlassLayer() {
      let layer = null;
      const sync = () => {
        if (prefs.glass && !layer) {
          layer = document.createElement("div");
          layer.className = "dsha-glass";
          layer.setAttribute("aria-hidden", "true");
          layer.append(document.createElement("i"), document.createElement("i"), document.createElement("i"));
          document.body.prepend(layer);
        } else if (!prefs.glass && layer) {
          layer.remove();
          layer = null;
        }
      };
      sync();
      const off = prefStore.subscribe(sync);
      return () => { off(); if (layer) layer.remove(); layer = null; };
    }

    function installTokenLayer(ctx) {
      let dispose = null;
      let last = "";
      const sync = () => {
        const theme = ctx.theme || service("theme");
        if (!theme || typeof theme.overrideTokens !== "function") return;
        const tokens = tokensFor(prefs);
        const key = JSON.stringify(tokens);
        if (key === last) return;
        last = key;
        if (dispose) { dispose(); dispose = null; }
        if (Object.keys(tokens).length === 0) return;
        try {
          dispose = theme.overrideTokens.length >= 2 ? theme.overrideTokens(PLUGIN_ID, tokens) : theme.overrideTokens(tokens);
        } catch (error) {
          console.warn("[dsha-mobile] 颜色层没有生效", error);
        }
      };
      sync();
      const off = prefStore.subscribe(sync);
      return () => { off(); if (dispose) dispose(); dispose = null; last = ""; };
    }

    // ---------- 插件入口 ----------
    const inject = ["slots", "locale", "theme"];
    function apply(ctx) {
      ctxRef = ctx;
      ctx.effect(() => ctx.locale.register(NS, { zh, en }), "dsha-mobile: dictionaries");
      try { boundT = ctx.locale.bind(NS); } catch (_) { boundT = null; }
      ctx.effect(installStyles, "dsha-mobile: styles");
      ctx.effect(installRootSync, "dsha-mobile: root attributes");
      ctx.effect(installGlassLayer, "dsha-mobile: glass layer");
      ctx.effect(() => installTokenLayer(ctx), "dsha-mobile: color layer");

      ctx.slots.inject("shell.overlay", () => ctx.slots.register({
        name: "shell.overlay", id: "dsha-mobile-tabbar", order: 50, locale: NS,
      }, TabBar));
      ctx.slots.inject("settings.general.item", function* () {
        yield ctx.slots.register({ name: "settings.general.item", id: "dsha-mobile-mode", order: 12, locale: NS }, MobileRow);
        yield ctx.slots.register({ name: "settings.general.item", id: "dsha-mobile-glass", order: 13, locale: NS }, GlassRow);
        yield ctx.slots.register({ name: "settings.general.item", id: "dsha-mobile-palette", order: 14, locale: NS }, PaletteRow);
      });
      ctx.effect(() => () => { ctxRef = null; boundT = null; }, "dsha-mobile: context");
    }

    // __test 只给 test/client.test.mjs 用（纯逻辑，dsh 只认 apply / inject）。
    return { apply, inject, __test: { sessionIdOf, rowTapAction, ROW_TAP_SLOP, ROW_LONG_PRESS_MS } };
  },
});
