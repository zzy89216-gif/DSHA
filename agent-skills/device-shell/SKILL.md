---
name: device-shell
description: Use when an agent inside the DSHA Ubuntu container needs to query or act on the Android phone. Explains the three channels (workspace tools, the /app/* bridge, the policy-checked adb-shell command), what the device policy allows, and how to read its result markers.
---

# DSHA device shell

The agent runs in an Ubuntu container on the phone. It reaches the device in three ways. Use the first one that can do the job.

| Channel | Use for | How |
|---|---|---|
| 1. Workspace tools | Files and processes inside the container | Normal bash/file tools |
| 2. App bridge `/app/*` | Device info, apps, screen, clipboard, notifications, sensors, file export | `curl` to `127.0.0.1:$BRIDGE_PORT` with the bridge token. No ADB or Shizuku needed |
| 3. `adb-shell` | Device logs, system queries, writes to allowed device folders, stopping user apps | `adb-shell '<command>'` |

To change files on the device, use channel 3. The bridge can read device files (`/app/readfile`). It can also hand a container file to the user with `/app/export`, which copies it to `Download/DSHA`.

## Channel 2: the bridge

```bash
T=$(cat /root/.dsh/.bridge_token)
P=$(cat /root/.dsh/.bridge_port)                       # 端口由 App 写在这里，不要写死
curl -s "http://127.0.0.1:$P/app/help?token=$T"        # full endpoint list, read it once
curl -s "http://127.0.0.1:$P/app/device?token=$T"      # model, Android version, battery, storage
curl -s -G "127.0.0.1:$P/app/launch" --data-urlencode "pkg=<package>" --data-urlencode "token=$T"
```

- Every request needs the token, as `?token=` or an `X-Token` header. Without it the reply is `[UNAUTHORIZED]`.
- Only `GET` is accepted. Pass non-ASCII or spaced values with `-G --data-urlencode`.
- Replies are JSON: `{"result":"..."}`.
- Older app builds have no `/app/help`. If the reply doesn't look like an endpoint list, don't retry it; use the endpoints you already know.

## Channel 3: adb-shell

`adb-shell` lives in `/root/dsh-bin` (on `PATH`). The app picks the transport: root if granted, then Shizuku, then paired wireless ADB.

```bash
adb-shell id                        # check which identity you got; don't assume uid=2000 or root
adb-shell getprop ro.build.version.release
adb-shell pm list packages -3
adb-shell dumpsys activity top
adb-shell logcat -d -t 200
adb-shell --su '<command>'          # only when root is really required and granted
```

Don't call `adb` or `/root/dsh-bin/adb` directly. That is a guard wrapper and will fail.

### What the policy accepts

Each call must be one plain command. Pipes, redirects, `;`, `&&`, `$()`, variables, and multi-line scripts are rejected. Run several calls and filter output in the container instead.

- Read: `id`, `getprop`, `ps`, `ls`, `cat`, `grep`, `stat`, `df`, `du`, `find <abs-dir>` with read-only tests (no `-exec`/`-delete`), checksums, read-only `date`.
- Narrow forms: `pm list|path|dump`, `settings get|list`, a fixed set of `dumpsys` services, `logcat -d` / `-t N`.
- Files: `mkdir`, `touch`, `cp`, `mv`, `rm`, `rmdir` outside protected paths. Root and system directories, `DCIM`, `Pictures`, `Android/data`, and `Android/obb` are read-only. `Download` is writable.
- Stop apps: `am force-stop <package>`, `kill <pid>`, `pkill <package>`. Full package names or positive PIDs only. System apps and critical processes can't be stopped.
- SMS: `content query --uri content://sms` asks the user each time, unless they enabled SMS reading on the Device permissions page. Never send, change, or delete messages.
- Always blocked: partitions and block devices, SELinux, `setprop`, `settings put`, mounting, flashing, reboot, install/uninstall/clear data, and any command the policy doesn't recognize. That includes `input`, `screencap`, and `am start`; use the bridge for those.

### Result markers

| Output | Exit code | Meaning | What to do |
|---|---|---|---|
| `[EXIT=n]` | n | Command ran; n is the device exit code | Read the output |
| `[POLICY_BLOCKED] ...` | 126 | Not executed | Don't retry or work around it. Use another endpoint or ask the user |
| `CONNECT_FAIL: ...` | 124 | Never reached the device | Tell the user to check the Device permissions page |
| `EXECUTION_UNKNOWN: ...` | 125 | May have run | Check the actual state first. Don't replay it or switch channel |
| `NO_KEY` / `DEPS_MISSING` | 1 | ADB isn't paired or ready | Ask the user to finish pairing in the app |

If a bridge endpoint answers `DISABLED` or `NO_PERMISSION`, pass that message to the user and stop. Repeating the call won't change the setting.
