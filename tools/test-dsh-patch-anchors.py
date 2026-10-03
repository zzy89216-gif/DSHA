#!/usr/bin/env python3
"""校验安装期补丁能在新构建的 dsh 运行时上逐条命中。

设备上 RuntimeTools 只在补丁的 dshVersion 等于已装 dsh 版本时应用补丁；版本相等但锚点不符会让
启动失败。这里按 ExactTextPatch 语义（未打补丁时 before 恰好出现 1 次、after 不出现；已打补丁时
after 恰好 1 次）在 dsh-runtime.bin 里的实际文件上模拟，同一份配方内按顺序累积应用。
"""
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
PREFIX = 'usr/local/lib/node_modules/@deepseek-ai/dsh/node_modules/'

# 没有 module 字段的配方，目标文件写死在 RuntimeTools.java 里。
FIXED_MODULES = {
    'composer-enter-patch.json': '@deepseek-ai/dsh-client-ui-conversation/lib/client.js',
    'session-interaction-patch.json': '@deepseek-ai/dsh-client-ui-workspace/lib/client.js',
    'client-combo-patch.json': '@deepseek-ai/dsh-client-modules/lib/index.js',
}
# 应急运行时专用配方固定在旧版本，由 recovery 测试负责。
SKIP = {'recovery-language-patch.json', 'recovery-pdf-compat-patch.json'}


def count(text, part):
    found, start = 0, 0
    while True:
        at = text.find(part, start)
        if at < 0:
            return found
        found, start = found + 1, at + len(part)


def apply(text, before, after, label, errors):
    old, done = count(text, before), count(text, after)
    if done == 1 and old == count(after, before):
        return text
    if old != 1 or done != 0:
        errors.append(f'{label}: before 命中 {old} 次，after 命中 {done} 次')
        return text
    return text.replace(before, after)


def main():
    version = json.loads((ROOT / 'tools/dsh-runtime/package.json').read_text(encoding='utf8'))['dependencies']['@deepseek-ai/dsh']
    archive = ASSETS / 'dsh-runtime.bin'
    with tarfile.open(archive, 'r:gz') as tree:
        members = {m.name.lstrip('./'): m for m in tree.getmembers() if m.isfile()}

        def read(module):
            member = members.get(PREFIX + module)
            return None if member is None else tree.extractfile(member).read().decode('utf8')

        errors, checked = [], 0
        specs = sorted(ASSETS.glob('*-patch.json')) + sorted((ASSETS / 'web-integration').glob('*-patch.json'))
        for path in specs:
            if path.name in SKIP:
                continue
            spec = json.loads(path.read_text(encoding='utf8'))
            if spec.get('dshVersion') != version:
                continue
            module = spec.get('module') or FIXED_MODULES.get(path.name)
            if not module:
                errors.append(f'{path.name}: 不知道目标文件，请在 FIXED_MODULES 里登记')
                continue
            text = read(module)
            if text is None:
                errors.append(f'{path.name}: 运行时里缺少 {module}')
                continue
            for index, patch in enumerate(spec.get('patches') or []):
                text = apply(text, patch['before'], patch['after'], f'{path.name}#{index}', errors)
                checked += 1
            # PDF 兼容：主线程与 Worker 两处锚点，外加资源协议模块。
            for key in ('mainBefore', 'workerBefore'):
                if key in spec:
                    hits = count(text, spec[key])
                    if hits != 1:
                        errors.append(f'{path.name}.{key}: 命中 {hits} 次')
                    checked += 1
            if 'resourceModule' in spec:
                resource = read(spec['resourceModule'])
                if resource is None:
                    errors.append(f'{path.name}: 运行时里缺少 {spec["resourceModule"]}')
                else:
                    apply(resource, spec['resourceBefore'], spec['resourceAfter'], f'{path.name}.resource', errors)
                    checked += 1
    if errors:
        print('安装期补丁与 dsh %s 不符：' % version)
        for line in errors:
            print('  -', line)
        sys.exit(1)
    print(f'安装期补丁锚点全部命中（dsh {version}，{checked} 处）')


if __name__ == '__main__':
    main()
