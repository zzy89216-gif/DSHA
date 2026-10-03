"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.installShortcutModalKeyboardGuard = installShortcutModalKeyboardGuard;
const phone_chrome = require("./effects/phone-chrome.js");

// DSHA：只抑制 rc2 首次挂载期间的自动搜索聚焦。原生触摸、Tab、读屏和后续
// focus 请求保留；弹层本身获得焦点，以便 Escape/Tab 和读屏仍拥有正确上下文。
// 此片段由 apply-mobile-client-patches.mjs 放入锁定上游 bundle，行为测试执行产物。
function installShortcutModalKeyboardGuard(ctx) {
    phone_chrome.installMobileEffect(ctx, 'dsh-web-mobile: shortcut modal keyboard guard', () => {
        const proto = HTMLInputElement.prototype;
        const descriptor = Object.getOwnPropertyDescriptor(proto, 'focus');
        const previous = proto.focus;
        // 某些宿主/插件会锁住原型；此时保持浏览器默认聚焦，不让适配导致整页失败。
        if (typeof previous !== 'function' || descriptor?.configurable === false ||
            (!descriptor && !Object.isExtensible(proto))) return;
        const selector = '[data-shortcut-modal="shortcuts"] [data-modal-autofocus]';
        // 断点切回移动布局时，已存在的输入框不是首次挂载。
        const initialized = new WeakSet(document.querySelectorAll(selector));
        const pending = new WeakSet();
        let active = true;
        const wrapper = function focus(options) {
            if (active && this.matches(selector)) {
                // focusWithoutRing 是当前宿主明确的自动聚焦入口。一次 commit 内
                // Modal 和快捷键组件各有 layoutEffect，必须一起抑制，然后立即解除。
                if (!initialized.has(this) && this.hasAttribute('data-dsh-automatic-focus')) {
                    if (!pending.has(this)) {
                        pending.add(this);
                        Promise.resolve().then(() => initialized.add(this));
                        const dialog = this.closest('[role="dialog"][aria-modal="true"]');
                        if (dialog && !dialog.contains(document.activeElement)) {
                            // 官方 Modal 已带 tabindex=-1，不修改 React 管理的属性。
                            dialog.focus({ preventScroll: true });
                        }
                    }
                    return;
                }
                initialized.add(this);
            }
            return previous.call(this, options);
        };
        try {
            Object.defineProperty(proto, 'focus', {
                configurable: true, writable: true,
                enumerable: descriptor?.enumerable ?? false, value: wrapper,
            });
        } catch { return; }
        // 在移动效果生命周期内提前安装，直接快捷键打开也不依赖 observer 的时序。
        // 同一属性若后来被别的插件包装，停用本层即可；不能拆掉别人的包装。
        return () => {
            active = false;
            if (Object.getOwnPropertyDescriptor(proto, 'focus')?.value !== wrapper) return;
            try {
                if (descriptor) Object.defineProperty(proto, 'focus', descriptor);
                else delete proto.focus;
            } catch {
                // 原型可能在安装后被冻结；active=false 已使残留包装完全透传。
            }
        };
    });
}
