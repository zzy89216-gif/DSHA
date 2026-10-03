# Security model

> 中文：[security-model.md](security-model.md)

DeepSeek Harness Android (DSHA-zzy) runs an Ubuntu container and dsh on your phone. The agent can run any command inside the container and can call Android features through a local bridge. This document lists what it can reach by default, which capabilities you have to turn on yourself, and where the existing protections stop. Classes mentioned below live in `app/src/main/java/com/deepseekharness/app/`.

## Summary

- There is one real isolation boundary: the Android app sandbox. The container, plugins, terminal and dsh all run under the app's own Android UID and are not isolated from each other.
- dsh's default permission mode is `danger-full-access` (`ConfigStore`). Android's SELinux policy blocks bubblewrap, so dsh has no sandbox inside the container.
- Device commands (ADB / Shizuku / Root) go through the native allowlist `util/DeviceShellPolicy`. It only governs the bundled entry points: `adb-shell`, the device bridge's `/exec`, and the Shizuku Binder service. Python/Node programs written inside the container, a self-written ADB client, and direct access to shared storage are not covered.
- Sensitive capabilities are off by default and can be revoked. dsh works with all of them off.

## Default reach

Fresh install, nothing granted:

| Target | Access | Notes |
|---|---|---|
| Ubuntu in the container | Full control | The agent's workspace; `apt`, builds and services run here |
| App private directory | Read/write | rootfs at `files/linux/ubuntu`; user data at `files/user-data-v5/dsh` or the older `root/.dsh` |
| Shared storage | Depends on Android grants | The container mounts `/storage/emulated/0` at `/sdcard` (`runtime/ContainerRuntime.BINDS`). A mount is not a grant; what can be read or written depends on the storage permission Android gives the app |
| Other apps' private data | No | Android app sandbox |
| `/system` | Not writable | Root inside the container is not Android Root |
| Location | Off | Coarse/fine location are declared, but both the in-app location capability and the system location permission must be on |
| SMS | Off | See "SMS reading" below |
| Microphone | Requested on demand | The system prompt appears only when the web page asks (`ui/BrowserMicrophone`); nothing is pre-granted |

## Capabilities you enable

### All files access (Settings → Device grants)

On Android 11+ this opens the system "All files access" setting; on Android 6–10 it requests `WRITE_EXTERNAL_STORAGE`. Once granted, code in the container can read and write all of shared storage, including photos and downloads. User data still lives in the app's private directory and is removed when you uninstall the app. Export a `.dshbak` backup first if you want to keep it.

### Device command channels (Settings → Device grants)

All three channels share the same allowlist. The first authorized channel is used, in the order Root → Shizuku → ADB (`HttpShellService.deviceExecute`).

- Wireless ADB: runs as `shell` (uid 2000). After pairing it reconnects with a key pair; the pairing code is not stored. To revoke, turn off Wireless debugging in system settings or revoke USB debugging authorizations. The ADB key is stored in the container, so container code can open its own ADB connection; the allowlist does not cover that case.
- Shizuku: calls `ShellService` over Binder, which also runs `DeviceShellPolicy` before executing. SMS queries never go through Shizuku.
- Root: the flag is `allow_root_shell`, default false. The phone must already be rooted, and the root manager must approve `su`. DSHA does not obtain or install Root. The allowlist still applies under Root, and Root is additionally blocked from reading or recursively walking the SMS database directories.

### SMS reading (Settings → Device grants)

Stored as `sms_read` in `dsha_device_grants`, default off. While off, SMS queries return `[POLICY_BLOCKED]`. While on, assistants and plugins can read numbers, message bodies and timestamps, which includes verification codes.

`util/SmsQuery` accepts only `content query --uri content://sms[...]`. Columns, filters and sort order are allowlisted, and queries are limited to the Android user DSHA runs as. It cannot send, change or delete messages, and the switch does not extend to other content providers. This grant is not restored from backups or device transfer.

### Screen actions

The `/app/ui/*` endpoints (read screen, tap, type) use the accessibility service and are separate from the device command allowlist. A grant lasts for the current DSH run and can be revoked in Device grants. When the foreground app is a payment, banking, password-manager or system-settings app, every action needs confirmation.

### Streaming overlay (Settings → Configure)

`overlay_stream`, default off. It needs the system overlay permission. It shows model output and can approve or reject pending confirmations in place. It does not read or capture the screen, but its content is on screen for anyone nearby to see.

### LAN access (Settings → Configure → "Allow LAN access")

`lan_mode`, default off. When on, `LanProxyService` listens on `0.0.0.0:3181` (`Constants.LAN_BRIDGE_PORT`) and forwards to the local dsh.

- Fails closed: an empty, missing or wrong token is rejected (`LanAuth.tokenOk`).
- After the first successful request with the token in the URL, it is swapped for the `HttpOnly; SameSite=Strict` cookie `dsha_lan`, and a redirect drops the token from the URL.
- Plain HTTP, no TLS. On an untrusted network the token and content can be captured. Don't enable it on public Wi-Fi.
- It forwards only to the local dsh. No CONNECT, no arbitrary destinations.
- Header size, field count and connections are bounded; SSE / WebSocket are counted separately. Turning LAN off or entering maintenance closes current connections. Numbers are in the [stability acceptance notes](stability-acceptance.md) (Chinese).

## Device command allowlist

`DeviceShellPolicy.inspect` splits a command into a single argv and checks it. It never runs a user-supplied shell script.

- Rejects pipes, redirects, `;`, `&`, variable and command expansion, control characters, and commands over 8192 characters.
- Read-only commands pass (`ls`, `cat`, `ps`, `getprop`, `settings get/list`, `pm list/path/dump`, selected `dumpsys`, read-only `find` predicates, `logcat -d/-t`, and so on).
- File writes are limited to `mkdir touch cp mv rm rmdir rename` with explicit absolute paths, no wildcards and no `..`. Writable locations are ordinary subdirectories of shared storage and `/data/local/tmp`. The storage root, DCIM, Pictures, Android/data, Android/obb and everything under them are read-only. `cp` may copy out of a read-only directory; the source of `mv` counts as a write.
- Always rejected: `dd`, every `mkfs`/`fsck`, partition tools, `setenforce`/`chcon`, `setprop`, `mount`/`umount`, flashing and reboot commands, `settings put`, `pm install/uninstall/clear`, `app_process`, and any command it does not recognize.
- Stopping processes accepts only `am force-stop|kill <full package>`, `kill <positive PID>`, and `killall/pkill <full package>`. Before running, the channel fetches the full app list again and splits it into user and system apps (`util/DeviceAppPolicy`). System apps, system UIDs, DSHA and Shizuku are protected. If any target in a batch is protected, the whole batch is rejected.

A blocked command returns `[POLICY_BLOCKED]` and `[EXIT=126]`. There is no "allow anyway" option, and the Root switch, the old confirmation switch and environment variables do not bypass it. The legacy `/confirm` endpoint answers YES only for read-only commands. If something fails mid-execution the result is `[EXECUTION_UNKNOWN]` with `[EXIT=125]`: the command may have run, and the client does not retry on another channel.

### Why there is no "dangerous command blacklist"

An early revision shipped `DangerShellGuard`: a list of dangerous commands (`rm -rf`, `mkfs`,
`pm clear`, ...) that triggered a confirmation prompt. The allowlist above replaced it, but the
trade-off behind that removal is worth keeping:

- **A blacklist can never be complete.** shell can compose, encode and indirect its way around
  any pattern table.
- **Over-flagging is more dangerous than under-flagging.** Once plain `>` and `mv` start prompting,
  the dialog becomes noise; users learn to tap "allow" without reading, and at that point the
  genuinely dangerous commands get through too.
- **Confirmation is not the primary defence.** It guards against mistakes and obvious malice,
  not targeted attacks. The three real layers are the device bridge token (unauthorised callers
  cannot get in), the confirmation prompt for critical operations, and the proot container
  boundary (which cannot reach the host system).

So only commands that parse into a single, fully understood argv are judged against the allowlist,
and the default is deny. Missing one is cheaper than making the confirmation prompt meaningless.

## User confirmation

A confirmation request is shown at the same time as a notification, a foreground dialog and, if enabled, on the overlay. All three share one request and the first tap wins. No answer within 60 seconds counts as a refusal (`HttpShellService.requestUserConfirm`). Each request is bound to the current bridge generation and a random ID, so old requests are void after DSH restarts.

## Bridge path guard

`/app/export` copies files into `Download/DSHA/`, which any app with storage permission can read. If any path were allowed, one curl in the container could drop `/root/.dsh/.bridge_token` there, and another app holding that token could read the screen, tap and run device commands. The same directory holds `.credentials.yaml` (API key and session secret) and `adbkeys/adbkey` (the ADB private key).

`util/BridgePathPolicy` blocks this. Both `/app/export` and `/app/readfile` go through it:

- Empty values and relative paths are rejected.
- Rejects `/root/.dsh`, `/root/.android`, `/root/.ssh`, `/root/.aws`, `/root/.config/gcloud`, `/root/.kube`, `/root/.dsha-*`, and on the host side `/data/data` and `/data/user` (except the rootfs itself).
- Normalizes `..`, repeated slashes and backslashes first, then re-checks with `getCanonicalPath()` so a symlink cannot get around it.
- Directory listings hide entries for these credential directories.

Exporting normal output (for example `/root/report.md`) still works. Tests: `BridgePathPolicyTest`.

## Where keys and data live

| Item | Location | Protection |
|---|---|---|
| Native API key | App SharedPreferences | `data/KeyVault`: AES/GCM key in Android Keystore, 12-byte IV prepended, 128-bit tag, Base64. Not configured, device locked, key missing and unreadable are handled separately; a failed decrypt never creates a replacement key |
| API key in exported backups | Not exported by default; included in the encrypted v5 backup if you opt in | Must decrypt on this device first. Records holding only another device's Keystore ciphertext may not work on a new device |
| Conversations, settings, plugins | App private directory | Protected only by the app sandbox. The legacy `Documents/dshdata` is in public storage and readable by any app with storage permission |
| `.dshbak` backups | Wherever you pick in the system file picker, plus a private verified copy | Password-derived key + AES-256-GCM; fully authenticated before restore. Format: [backup-format-v5.md](backup-format-v5.md) (Chinese) |
| dsh credentials, project config | `.credentials.yaml`, `.env`, etc. | May be plaintext and may enter the encrypted backup depending on scope. "Exclude API key" only excludes the native API key; other files are not scanned for secrets |
| Device bridge token | `/root/.dsh/.bridge_token` | Readable inside the container. Not backed up; `HttpShellService.resetTokenAfterRestore()` regenerates it after a restore |
| Device and LAN grants | Private records on this device | Cannot be obtained by restoring a backup |

Backups also handle a few files that belong to this device only (`assets/backup-engine.py`):

| File | Handling |
|---|---|
| `.dsh/.bridge_token` | Not backed up |
| `.dsh/.anonymous-user-id` | Not backed up |
| `.dsh/.credentials.yaml` | Records under `records` starting with `client-connection/` (the signing secret for local login cookies) are removed; the API keys under `refs` are kept. dsh regenerates the missing record itself |

On restore, scripts, plugin declarations and unrecognized content go to quarantine first and are not applied directly.

## Network access

The app has no analytics or log upload. Network requests come from:

- In-app updates, which read `https://github.com/zzy89216-gif/DSHA/releases/latest/download/updates.json` and then download the APK.
- The plugin market and community page, which read an external plugin catalog site. That is the only
  outbound site the app touches (see the known issues in [HANDOVER.md](../HANDOVER.md)); nothing else
  is contacted.
- Plugin and dependency installs, which use the selected npm registry or mirror.
- dsh, which calls the model provider you configure.
- Enabled plugins, which can make their own requests.

The app does not restrict network access from the container or plugins.

The local device bridge listens on `127.0.0.1:3190` and `[::1]:3190` (the port comes from `Constants.SHELL_BRIDGE_PORT`). Other apps on the same phone can reach that port, so every request must carry the token.

## Plugins

Before install there is only a static check: metadata, content digests and actual dependencies. Plugin code is not loaded. Dependencies are installed with `--ignore-scripts` and `--ignore-pnpmfile`, so lifecycle scripts and pnpmfile hooks never run. You must review a plugin before enabling it. Plugins share the container's UID; a quarantine directory is not a sandbox, and a plugin that installs is not thereby safe.

## Checking the APK

Releases are at <https://github.com/zzy89216-gif/DSHA/releases>, with `DSHA-<version>.apk` and a matching `.sha256`.

```bash
sha256sum -c DSHA-<版本>.apk.sha256
apksigner verify --verbose --print-certs DSHA-<版本>.apk
```

- Package name should be `zzy.dsha.Kotlin`.
- Signing certificate SHA-256 should be `79:77:DF:F4:D4:52:C3:90:8D:AA:EA:91:F0:A2:0B:1A:BA:71:18:1B:73:4B:A4:3A:B5:48:98:FF:1E:31:42:8F`.

A checksum only shows the file wasn't altered; it doesn't prove who published it. The certificate fingerprint does. The workflow does not produce a GitHub build attestation.

## Known weaknesses

| Weakness | Status |
|---|---|
| dsh has no sandbox | Default `danger-full-access`; the agent fully controls the container |
| The allowlist is not an OS sandbox | It only governs bundled entry points. Container code can read the ADB key and directly access granted shared storage, limited only by Android permissions |
| Shared UID | Plugins, the terminal and container code can read credentials passed into the runtime and other data in the app's private directory |
| `/sdcard` mount | Once storage access is granted, container code can reach everything in that scope |
| Old plaintext backups | Old `DSHA-backup-*.tar.gz` files and data you copied by hand may still be in public storage. New encrypted exports leave them alone |
| LAN is HTTP | No TLS, see above |
| Single signing key | Every release is signed with the same CI key; changing it would block in-place upgrades. The encrypted backup is described in [.github/signing/README.md](../.github/signing/README.md) |

Report problems at <https://github.com/zzy89216-gif/DSHA/issues>. Security issues get priority.

Provenance and third-party licenses: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
