# Agent skills for DSHA

Skills for an agent running inside the DeepSeek Harness Android (DSHA) Ubuntu container. They describe how to reach the phone through what the app actually exposes: the authenticated bridge on
`127.0.0.1:$BRIDGE_PORT` and the `adb-shell` command. **Never hardcode the bridge port** — the app writes
its live port to `/root/.dsh/.bridge_port` (each DSHA build has its own port, so a hardcoded one can reach
the wrong app when several are running).

| Skill | Use it for |
|---|---|
| [device-shell](device-shell/SKILL.md) | Picking a device channel, running policy-checked device commands, reading the result markers. |
| [screen-ocr-operator](screen-ocr-operator/SKILL.md) | Operating the screen through the accessibility endpoints, with screenshot + vision model as a fallback when the UI dump has no usable text. |

## Install

Each skill is a folder with one `SKILL.md`. Copy the folders into the agent's skills directory:

```bash
cp -r agent-skills/device-shell ~/.agents/skills/
cp -r agent-skills/screen-ocr-operator ~/.agents/skills/
```

## What must be in place

- The DSHA app is running, so the bridge answers and `/root/.dsh/.bridge_token` + `/root/.dsh/.bridge_port` exist.
- Screen endpoints need the DSHA accessibility service. Screenshots need Android 11 or later.
- `adb-shell` needs one authorized channel: root (granted in the root manager), Shizuku, or wireless ADB paired on the app's Device permissions page (设备能力授权).
- `screen-ocr-operator` fallback only: an OpenAI-compatible vision model endpoint and your own API key.

The skills contain no keys, endpoints, or device identifiers. Replace placeholders like `<YOUR_VISION_MODEL>` yourself.
