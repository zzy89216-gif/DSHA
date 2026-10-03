---
name: screen-ocr-operator
description: Use when an agent inside the DSHA container must read or operate the phone screen. Start with the accessibility UI dump and text taps; use a screenshot plus an OpenAI-compatible vision model only when the dump has no usable text or bounds. Keep the loop short and verify after each step.
---

# Screen operator for DSHA

Screen actions go through the DSHA accessibility service on the bridge (`127.0.0.1:$BRIDGE_PORT/app/ui/*`;
read the live port from `/root/.dsh/.bridge_port`). ADB `input`, `screencap`, and `am start` are blocked by the
device policy, so don't plan around them.

If the session exposes the `dsh-computer-use-android` MCP tools (`android_get_state`, `android_screenshot`, `android_click`, `android_type`, `android_key`, `android_swipe`), use those. They call the same endpoints. Otherwise use `curl` as shown below.

## Loop

1. Observe: `dump` the screen.
2. Act once: tap, type, key, or swipe.
3. Observe again before the next action. Screens change after taps, scrolls, and animations, so don't chain actions from an old observation.
4. Call the vision model only when step 1 can't locate the target.

The user may be asked to approve dumps, taps, inputs, and screenshots. A reply like `[ERR] 你拒绝了这次点击` / `[ERR] You declined this tap` means they declined. Stop and ask; don't retry.

## Endpoints

```bash
T=$(cat /root/.dsh/.bridge_token)
B=http://127.0.0.1:$(cat /root/.dsh/.bridge_port)/app/ui   # 端口由 App 写在这里，不要写死

curl -s "$B/dump?token=$T"
# one line per node with text or a clickable/editable flag:
# [3] "设置" 可点击 中心=(540,1200) 区域=480,1160,600,1240
# flags: 可点击 clickable, 可输入 editable, 已选中 checked, 不可用 disabled; 中心 = center, 区域 = bounds

curl -s -G "$B/tap"   --data-urlencode "text=设置" --data-urlencode "token=$T"   # tap by visible text (preferred)
curl -s -G "$B/tap"   --data-urlencode "x=540" --data-urlencode "y=1200" --data-urlencode "token=$T"
curl -s -G "$B/input" --data-urlencode "text=hello" --data-urlencode "token=$T"  # into the focused field; tap it first
curl -s "$B/key?name=back&token=$T"     # back/home/recents/notifications/quicksettings/lock
curl -s "$B/swipe?x1=540&y1=1600&x2=540&y2=600&ms=300&token=$T"
curl -s "$B/screenshot?token=$T"        # Android 11+; replies with the saved PNG path and size
```

Start apps with `/app/launch?pkg=<package>`. Find the package with `/app/apps?q=<name>`.

Tap by text when the label is visible. Text stays put while coordinates move. Use coordinates from the latest dump's `中心=` when a control has no text.

`/app/ui/input` replaces the focused field's text through accessibility, so the IME language doesn't matter. An empty `text=` clears the field. Submit with the app's send button, found in the next dump.

## Vision fallback

Use this for canvas or game UIs, images with text, and controls the dump lists without text or bounds.

1. Take a screenshot. The reply gives the file path and pixel size, e.g. `OK 截屏已保存：/storage/emulated/0/Android/data/<包名>/files/Pictures/DSHA/screen-...png（1080x2400）`（用回复里的真实路径，不要照抄包名）. The `android_screenshot` MCP tool returns the image directly.
2. Optionally downscale to about 720 px wide JPEG before sending. Smaller images return faster. Scale coordinates back to the original size before tapping.
3. Send the image with the task to the vision model. Ask for exactly one next action in JSON, in original-image coordinates:

   ```json
   {"action": "tap", "x": 630, "y": 1090, "reason": "Send button, bottom right"}
   ```

4. Do that action, then `dump` (or screenshot again) to confirm before asking for the next one.

Vision model call (generic OpenAI-compatible):

- `POST <YOUR_ENDPOINT>/chat/completions`, header `Authorization: Bearer <YOUR_API_KEY>`
- `model`: `<YOUR_VISION_MODEL>`
- Image as a content part: `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`

Screenshots can contain private data. Send them only to an endpoint the user configured, and delete local copies you made when done.
