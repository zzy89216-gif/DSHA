# DeepSeek Harness Android

<p align="center">
  <b>A launcher that runs <a href="https://github.com/deepseek-ai/deepseek-harness">deepseek-harness</a> on Android phones</b><br>
  One APK with a bundled Ubuntu environment; no root and no Termux required
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT"></a>
  <a href="https://github.com/zzy89216-gif/DSHA/releases/latest"><img src="https://img.shields.io/github/v/release/zzy89216-gif/DSHA?sort=date&color=blue" alt="release"></a>
  <a href="https://github.com/zzy89216-gif/DSHA/actions/workflows/build-apk.yml"><img src="https://github.com/zzy89216-gif/DSHA/actions/workflows/build-apk.yml/badge.svg" alt="build"></a>
  <img src="https://img.shields.io/badge/Android-11%2B-3DDC84?logo=android&logoColor=white" alt="android">
  <img src="https://img.shields.io/badge/arch-arm64--v8a-lightgrey" alt="arch">
</p>

<p align="center">
  <b>English</b> · <a href="README.md">简体中文</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="docs/security-model.en.md">Security model</a> · <a href="AGENTS.md">AGENTS.md</a>
</p>

> AI agents and new contributors: read [AGENTS.md](AGENTS.md) first. It covers the layout, the startup flow and known pitfalls, so you don't need to scan the whole repo.

DeepSeek Harness (`@deepseek-ai/dsh`) is DeepSeek's agent tool, written for glibc Linux. This app packs an Ubuntu 24.04 arm64 environment, Node.js, pnpm and dsh into one APK, runs dsh inside a proroot / proot container, and opens its web UI in a built-in WebView.

This repository is maintained independently. It is a community project with no affiliation to DeepSeek;
"DeepSeek" is a trademark of its owner. Provenance and third-party licenses are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Install

Download the APK from [Releases](https://github.com/zzy89216-gif/DSHA/releases/latest). Each APK has a matching `.sha256` file.

- Package name `zzy.dsha.Kotlin`. It differs in both package name and signature from other DSHA builds
  (`zzy.dsha.com`, `com.dsh.client`), so neither can overwrite the other, but all can be installed at once
  with separate data.
- Releases ship the Standard build only: Android 11+, arm64-v8a. The Low build (GeckoView engine, Android 6+) has to be built yourself; see [BUILD.md](BUILD.md).
- From zzy.4 on, "Settings → App updates" upgrades in place. It reads the `updates.json` attached to this repository's latest stable release.

First run:

1. Open the app and wait while it extracts the bundled environment (once, a few minutes).
2. Enter a DeepSeek API key on the Configure page (you can skip this for now).
3. Go back to Launch and tap Start. The web UI opens when it is ready.

After that, opening the app from the home screen shows a loading screen, starts DSH and goes straight to the web UI. Cold start waits for the environment instead of dropping back to the home screen early. Turn off "Open straight into Web" in Settings if you prefer to stay on the launch page. The small round button on the right edge of the web page goes back home or to Settings; you can drag it or hide it in Settings.

## Features

Environment and runtime

- Offline rootfs: setup works with no network. Installation runs in steps (extract, base tools, Node.js, pnpm, dsh, patches). Each step can be reinstalled on its own, and repair touches only what failed.
- Ships dsh 0.2.0-rc.2, rebuilt at build time from the lock file in `tools/dsh-runtime` with every patch checked. The emergency runtime is pinned separately to 0.1.7-rc.2.
- proroot by default (path translation via LD_PRELOAD, no ptrace). You can switch back to proot on the Configure page, and the app falls back automatically if proroot can't start.
- Foreground service with a watchdog that restarts the web process if it exits.
- Environment updates boot in an isolated directory first and are committed only if that works; otherwise the old environment stays.

Data and backups

- Conversations, settings and attachments live in `Internal storage/Documents/dshdata` and survive reinstalling (requires "All files access"; without it data stays in the private directory).
- API keys are encrypted with Android Keystore (AES/GCM).
- Encrypted `.dshbak` backups: back up and restore everything, or only conversations, plugins or settings. Scheduled automatic backups keep the most recent verified copies. Format: [backup-format-v5.md](docs/backup-format-v5.md).
- Corrupt session files move to `corrupt-backup` instead of breaking the whole web UI.

Device capabilities (for the agent)

The agent uses device features through a device bridge (port in `/root/.dsh/.bridge_port`, default 3190). It needs a token, and `/app/help` lists every endpoint.

- Accessibility: read the screen, tap, type, swipe, press keys, take screenshots. No ADB needed.
- Virtual display (experimental, Standard build): launch and drive apps on a separate virtual display.
- Device commands: built-in wireless ADB pairing and keep-alive, or Shizuku, or Root. All three channels share one command allowlist; blocked commands return `[POLICY_BLOCKED]`.
- Also: notifications, vibration, prompts, clipboard, share, export files to `Download/DSHA`, sensors and location (off by default, granted one at a time).
- Read-only SMS queries are a separate sensitive grant and ask for confirmation each time by default.

UI and access

- Standard uses the system WebView; Low uses a bundled GeckoView 143.
- The built-in dsha-mobile web plugin provides the phone UI; see "Built-in plugins" below.
- Picture-in-picture, a streaming overlay (needs overlay permission), dark and light themes, Simplified Chinese / English.
- LAN access: use dsh on the phone from a computer or tablet browser through the LAN proxy port (default 3181), with token authentication.
- The native UI background can be Default, Dynamic glass or a custom image (Settings → Experience → Background). Dynamic glass is off by default.

Terminal

- A PTY terminal built on Termux terminal-emulator. Full-screen programs such as vim, htop and tmux work. It has an extra key row and tabs.

Plugins

- The Plugins page installs, updates, enables, disables, deletes, imports and exports plugins. Sources: GitHub links, HTTPS archives, local files, or `dsha-plugin install` in the terminal. Details in [docs/plugins.md](docs/plugins.md) (Chinese).
- Third-party plugins stay disabled after install until you review them. Lifecycle scripts are not run when dependencies are installed.

Troubleshooting

- The Install & repair page checks each component and fixes what failed. Diagnostic reports can be exported.
- Startup or plugin errors lead to a recovery page. Safe start loads only the official components and keeps your configuration.
- If the main environment is broken, a separate emergency DSH can diagnose and repair it.

## Built-in plugins

| Plugin | Purpose | Default |
|---|---|---|
| `dsha-mobile` | Phone web UI (0.2.1): bottom tab bar (Chat / Sessions / New / Settings), sidebar as a drawer, tapping a session row opens it, full-screen settings panel, tab bar moves out of the way when the keyboard opens. Adds three options under "Settings → General": phone mode, dynamic glass and color scheme. Source: [zzy89216-gif/dsha-mobile](https://github.com/zzy89216-gif/dsha-mobile) | Enabled |
| `dsh-web-mobile` | The older mobile adaptation ([mexiaosqwq/dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile), MIT) | Disabled |
| `dsh-status-overlay` | Streaming overlay | Enabled |
| `dsh-task-notifier` | Notification when a turn finishes | Enabled |
| `dsh-device-shell-guide` | Guide to device capabilities | Enabled |
| `dsh-computer-use-android` | Android Computer Use | Enabled |
| `dsh-tool-vscreen` | Virtual display tools | Enabled |
| `dsh-auto-review` | Official experimental Auto review entry | Enabled |

dsh-web-mobile still ships with the app and is not removed. Upgrading to or freshly installing v0.1.7-rc2-zzy.7 disables it once; if you re-enable it afterwards, it stays enabled. Built-in plugins can't be deleted, and any plugin you disabled stays disabled across upgrades.

## Wireless ADB setup

Once paired, the agent can run device commands without Shizuku. Pairing codes need Android 11+.

1. Enable developer options (tap the build number in "About phone").
2. Turn on "Wireless debugging", open "Pair device with pairing code", and note the IP:port and the 6-digit code.
3. Enter them on the app's "Device capability grants" page and pair.

After pairing the app keeps the connection alive and reconnects, including after a reboot. Run `adb shell id` in the built-in terminal; `uid=2000(shell)` means it works.

To teach the agent how to use it, copy the skill packs from this repository into the agent's skills directory:

```bash
cp -r agent-skills/device-shell ~/.agents/skills/
cp -r agent-skills/screen-ocr-operator ~/.agents/skills/
```

`device-shell` explains the three command channels. `screen-ocr-operator` uses screenshots and OCR for screens that accessibility can't read.

## Security

dsh works without granting any extra permission. Every device capability is off by default and can be revoked at any time. The app does not upload logs or usage data.

One thing to keep in mind: Android does not allow unprivileged user namespaces, so bubblewrap can't run and the bash tool has no sandbox. The only limit is dsh's permission mode, `danger-full-access` by default, which you can change to `workspace-write` or `read-only` on the Configure page.

See the [security model](docs/security-model.en.md) for what each permission exposes and the known weaknesses.

## Known limitations

- arm64-v8a only.
- "Grant wireless debugging keep-alive after ADB pairing" does not work under the `zzy.dsha.Kotlin` package name.
- Running alongside another DSHA build makes both compete for the bridge port. This app defaults to a
different port (3190), so the two can normally run side by side; if you point them at the same port,
whichever starts second loses device tools (the web UI is unaffected).
- The overlay needs overlay permission.
- Without "All files access", data stays in the private directory and is lost on uninstall.

## Building

You need JDK 17, the Android SDK, NDK 26 and Python 3.9+. Full steps in [BUILD.md](BUILD.md) (Chinese).
The main language is being migrated from Java to Kotlin; conventions and pitfalls are in
[docs/kotlin-migration.md](docs/kotlin-migration.md) (Chinese).

```bash
bash build.sh                                # Standard Debug
bash build.sh :app:assembleLowRelease        # Low Release
bash build.sh :app:testStandardDebugUnitTest # unit tests
python tools/verify-stability.py             # stability checks
```

The offline rootfs is not in Git. Releases are built by GitHub Actions, which pulls the offline assets from this repository's `runtime-assets` release.

## Documentation

| Doc | Contents |
|---|---|
| [AGENTS.md](AGENTS.md) | Layout, startup flow, constraints and pitfalls |
| [BUILD.md](BUILD.md) | Local builds, signing, CI builds and releases |
| [HANDOVER.md](HANDOVER.md) | Handover log: status, release process, keys, to-dos (Chinese) |
| [CHANGELOG.md](CHANGELOG.md) | Changelog |
| [docs/plugins.md](docs/plugins.md) | Plugin installation and packaging requirements |
| [docs/security-model.en.md](docs/security-model.en.md) | Security model ([Chinese](docs/security-model.md)) |
| [docs/android-standard.md](docs/android-standard.md) / [docs/android-low.md](docs/android-low.md) | Notes on the two builds |
| [docs/maintenance.md](docs/maintenance.md) | Maintenance handbook: single sources of truth, checks, releases, troubleshooting (Chinese) |
| [docs/kotlin-migration.md](docs/kotlin-migration.md) | Java → Kotlin migration: conventions, pitfalls, batches, verification (Chinese) |
| [docs/接手指南.md](docs/接手指南.md) | Guide for maintainers who don't do Android development (Chinese) |

## Credits

- [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)
- [proot](https://github.com/termux/proot), [proroot](https://github.com/coderredlab/proroot)
- [Termux terminal-view / terminal-emulator](https://github.com/termux/termux-app) (Apache-2.0)
- [dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile) (MIT)
- [Shizuku](https://shizuku.rikka.app/)

Third-party components and their licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Feedback and license

Report problems and ideas in [Issues](https://github.com/zzy89216-gif/DSHA/issues). Licensed under [MIT](LICENSE).
