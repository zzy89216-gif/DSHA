# dsh-web-mobile（DSHA 内置副本）

本目录是第三方插件 [mexiaosqwq/dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile) 的随包副本，作者 mexiaosqwq，MIT 许可，许可证原文见 [LICENSE](LICENSE)。用途是让 DSH Web UI 在手机竖屏下可用。

## 在 DSHA 里的状态

- 从 v0.1.7-rc2-zzy.7 起，手机界面改由内置插件 `dsha-mobile`（[zzy89216-gif/dsha-mobile](https://github.com/zzy89216-gif/dsha-mobile)）负责，默认启用。
- dsh-web-mobile 仍随 APK 提供，不删除。升级或新装后会被停用一次（`register-builtin-plugins.py` 的 `DEFAULT_DISABLED_ONCE`，凭证文件 `.dsha-default-disabled-v1`）。
- 在插件页手动重新启用后，它会一直保持启用，以后升级不会再停用。

## 版本与改动

- 上游版本 3.0.3，固定在 commit `a094288883b343e848d7f9cf302d73ad8ed4794b`。`package.json` 的 `dshaUpstream` 字段记录了来源和上游 `lib/client.js` 的 SHA-256。
- `lib/client.js` 由 `tools/apply-mobile-client-patches.mjs` 在上游产物上打 DSHA 补丁生成：触摸与快捷键守卫、按 `visualViewport` 限制弹窗高度（软键盘和分屏时按钮仍可达）、保留手机端搜索行等。脚本会先核对上游哈希，不匹配就拒绝生成。
- 副本只含运行所需文件：`package.json`、`cordis.patch.yml`、`lib/`、`LICENSE`。上游源码、截图和构建脚本不随包提供，需要时去上游仓库获取。

## 测试

`tools/test-mobile-update.mjs`、`test-mobile-auth.mjs`、`test-mobile-delete.mjs`、`test-mobile-gesture-guard.mjs`、`test-mobile-modal-behavior.mjs` 会检查本目录 `lib/` 和 `package.json`（版本号、上游 commit、客户端哈希、关键标记）。更新副本时要同步这些断言。

功能说明、更新记录和问题反馈请看上游仓库。
