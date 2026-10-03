#!/usr/bin/env python3
"""端口只能有一个来源：`util/Constants`。

这个仓库反复栽在同一种跟头上：同一份判断散落多处，改了一处忘了另一处，而且**不报错**。
端口正是这样 —— 源码常量、容器脚本、内置插件、agent 提示词、文档、界面文案里都有过写法，
改动只做一半时 App 照样编译、照样启动，只是设备工具连不上桥。

所以这里把「单一来源」变成可执行的检查：
  1. `Constants.kt` 是唯一定义处；
  2. Java/Kotlin 里的端口**必须**引用常量，不能写数字字面量；
  3. 容器脚本与内置插件的兜底值必须等于常量（它们平时读 /root/.dsh/.bridge_port）；
  4. 文档里声明的端口必须等于常量；
  5. **界面文案（可翻译字符串）里不许出现端口号** —— 数字会随配置变化，翻译也没法跟着变。

改端口时只改 `Constants.kt`，然后把这里报出来的位置一起改掉，再跑一遍。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = ROOT / 'app/src/main/java/com/deepseekharness/app/util/Constants.kt'

NAMES = ('DSH_WEB_PORT', 'SHELL_BRIDGE_PORT', 'LAN_BRIDGE_PORT')


def canonical():
    """从 Constants.kt 读出三个端口。这是唯一的定义处。"""
    text = CONSTANTS.read_text(encoding='utf-8')
    values = {}
    for name in NAMES:
        match = re.search(rf'const val {name} = (\d+)', text)
        if not match:
            raise SystemExit(f'Constants.kt 里找不到 {name}')
        values[name] = int(match.group(1))
    if len(set(values.values())) != len(values):
        raise SystemExit(f'三个端口必须互不相同：{values}')
    for name, port in values.items():
        if not 1 <= port <= 65535:
            raise SystemExit(f'{name} 不是合法端口：{port}')
    return values


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


def main():
    ports = canonical()
    errors = []

    # ---- 2. Java/Kotlin：端口必须引用常量 ----
    derived = {
        'app/src/main/java/com/deepseekharness/app/HttpShellService.java': [
            (r'public static final int PORT = (.*?);', 'Constants.SHELL_BRIDGE_PORT')],
        'app/src/main/java/com/deepseekharness/app/LanProxyService.java': [
            (r'public static final int LAN_PORT = (.*?);', 'Constants.LAN_BRIDGE_PORT'),
            (r'public static final int DEFAULT_BACKEND_PORT = (.*?);', 'Constants.DSH_WEB_PORT')],
        'app/src/main/java/com/deepseekharness/app/util/DshAuthUrl.java': [
            (r'public static final String LOOPBACK_BASE_URL = (.*?);', 'Constants.DSH_WEB_PORT')],
    }
    for relative, rules in derived.items():
        text = read(relative)
        for pattern, expected in rules:
            match = re.search(pattern, text)
            if not match:
                errors.append(f'{relative}: 找不到 {pattern}')
                continue
            body = match.group(1)
            if expected not in body:
                errors.append(f'{relative}: 端口没有引用常量 {expected}，而是 {body.strip()!r}')
            if re.search(r'\b(?:3080|3081|3090|3180|3181|3190)\b', body):
                errors.append(f'{relative}: 端口表达里还有数字字面量：{body.strip()!r}')

    reserved = read('app/src/main/java/com/deepseekharness/app/util/WebPortPolicy.java')
    if 'Constants.LAN_BRIDGE_PORT' not in reserved or 'Constants.SHELL_BRIDGE_PORT' not in reserved:
        errors.append('WebPortPolicy.reserved 必须引用 Constants 的两个保留端口常量')

    # ---- 3. 容器脚本 / 内置插件的兜底值 ----
    fallbacks = {
        'app/src/main/assets/adb-shell.py': ports['SHELL_BRIDGE_PORT'],
        'app/src/main/assets/selftest.py': ports['SHELL_BRIDGE_PORT'],
        'app/src/main/assets/rootfs-confirm-install.sh': ports['SHELL_BRIDGE_PORT'],
        'app/src/main/assets/builtin-plugins/dsh-task-notifier/lib/index.js': ports['SHELL_BRIDGE_PORT'],
        'app/src/main/assets/builtin-plugins/dsh-status-overlay/lib/index.js': ports['SHELL_BRIDGE_PORT'],
        'tools/device-policy-device-audit.py': ports['SHELL_BRIDGE_PORT'],
    }
    for relative, expected in fallbacks.items():
        text = read(relative)
        values = {int(v) for v in re.findall(r'\b(\d{4,5})\b', text)}
        if relative.startswith('app/') and '.bridge_port' not in text:
            errors.append(f'{relative}: 没有读 /root/.dsh/.bridge_port')
        if expected not in values:
            errors.append(f'{relative}: 兜底端口不是 {expected}（文件里出现的四/五位数字：{sorted(values)}）')

    # ---- 4. 文档必须与常量一致 ----
    docs = {
        'AGENTS.md': [(ports['DSH_WEB_PORT'], '网页'), (ports['SHELL_BRIDGE_PORT'], '能力桥'),
                      (ports['LAN_BRIDGE_PORT'], '局域网')],
        'docs/接手指南.md': [(ports['DSH_WEB_PORT'], ''), (ports['SHELL_BRIDGE_PORT'], ''),
                             (ports['LAN_BRIDGE_PORT'], '')],
    }
    for relative, expected in docs.items():
        text = read(relative)
        for port, hint in expected:
            if str(port) not in text:
                errors.append(f'{relative}: 没写端口 {port}{("（" + hint + "）") if hint else ""}')

    # ---- 5. 界面文案里不许出现端口号 ----
    catalog = json.loads(read('tools/i18n/messages.json'))
    stale = []
    for entry in catalog:
        for field in ('zh', 'en'):
            value = entry.get(field) or ''
            if re.search(r'\b(?:3080|3081|3090|3180|3181|3190)\b', value):
                stale.append(f"{entry['id']}.{field}: {value[:60]!r}")
    if stale:
        errors.append('界面文案里出现了端口号（数字会随配置变化，翻译跟不上）：\n    ' + '\n    '.join(stale))

    if errors:
        print('端口一致性检查失败：', file=sys.stderr)
        for error in errors:
            print('  - ' + error, file=sys.stderr)
        print('\n端口只应在 app/src/main/java/com/deepseekharness/app/util/Constants.kt 里定义；'
              '容器侧读 /root/.dsh/.bridge_port。', file=sys.stderr)
        return 1
    print('端口一致性通过：网页 %(DSH_WEB_PORT)s · 设备桥 %(SHELL_BRIDGE_PORT)s · LAN %(LAN_BRIDGE_PORT)s'
          % ports)
    return 0


if __name__ == '__main__':
    sys.exit(main())
