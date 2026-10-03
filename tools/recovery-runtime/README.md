# 应急运行时归档

应急运行时固定在一个旧版本，不跟随主 dsh 升级。`lock.json` 记录它的两份归档，独立于主运行时的 `tools/dsh-runtime` 锁：

| 逻辑名 | 对应主资产 |
|---|---|
| `recovery-rootfs.bin` | `offline-rootfs.bin` |
| `recovery-dsh-runtime.bin` | `dsh-runtime.bin` |

锁里还有 `dshVersion`、`baseVersion` 和每份归档的 SHA-256。当前锁定的 dsh 是 `0.1.7-rc.2`，Ubuntu 基底 10。

## archives/

归档放在 `tools/recovery-runtime/archives/`，不进 Git（本目录 `.gitignore`）。获取方式：

- CI 和本地都用 `tools/ci-import-prebuilt-assets.py` 从 0.1.7-rc2 APK 提取，按锁里的摘要校验，不符就失败。
- `archives/` 里缺文件时，`prepare-recovery-assets.py` 会尝试锁里的 `seed` 路径，摘要完全一致才复制。
- 从已经去重的 APK 提取时，先读 `assets/recovery-asset-locations.json` 的 `source` 找包内实际文件，再按 `asset` 逻辑名保存。`tools/recovery_apk_assets.py` 的 `archive_locations` 负责核对映射和摘要。

摘要不符时补回原归档，不要改锁。只有在应急运行时独立完成启动、能力限制、网页和停止验收之后才能更新锁。

## 构建时

Gradle 的 `prepareRecoveryAssets` 调 `tools/prepare-recovery-assets.py`，输出到 `app/build/generated/recoveryAssets`：

- `recovery-runtime.json`：应急运行时的独立描述和逐文件证明。内容身份 `id` 由归档摘要、展开文件、网页覆盖层、启动器和 profile 的摘要算出。它不读主运行时的描述，也不从主版本号推导应急版本。
- `recovery-asset-locations.json`：每份归档在 APK 里的实际位置。

去重：应急归档和主资产 SHA-256 相同时，APK 只存一份，`recovery-asset-locations.json` 指向主资产；不同时单独打包应急归档。物理位置不计入内容身份，所以去重与否不会让已验收的应急环境重建。解压后的根目录、数据、锁、身份和启动流程仍与主环境分开，不读主环境已解压的目录。
