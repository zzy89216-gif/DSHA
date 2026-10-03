#!/usr/bin/env python3
"""从已发布的 DSHA APK 取出不在 git 中、也不随 dsh 升级变化的大体积资产。

只取三类字节，其余资产（补丁、描述符、证明、网页兼容层）全部由源码重建：
- offline-rootfs.bin：已剥离 dsh 的 Ubuntu 基底（split-runtime-v1），原样放入 src/main/assets；
- ubuntu-tools.bin：按 tools/ubuntu-tools/packages.lock.json 锁定的 deb 集合，核对包清单与逐包摘要后
  生成 ubuntu-tools.inputs.json（格式同 tools/prepare-ubuntu-tools.py）；
- 固定应急运行时的两份归档：按 tools/recovery-runtime/lock.json 的摘要放入 archives/。
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
RECOVERY = ROOT / 'tools/recovery-runtime'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def extract(apk, name, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.part')
    with apk.open('assets/' + name) as source, temporary.open('wb') as output:
        shutil.copyfileobj(source, output, 1024 * 1024)
    temporary.replace(target)
    return digest(target)


def tools_metadata(archive):
    spec = importlib.util.spec_from_file_location('ubuntu_tools_builder', ROOT / 'tools/prepare-ubuntu-tools.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    lock = json.loads(builder.LOCK.read_text())
    if lock['format'] != 1 or lock['architecture'] != 'arm64':
        raise ValueError('不支持的 Ubuntu 工具锁')
    rows = lock['packages']
    with tarfile.open(archive, 'r:gz') as tree:
        names = {item.name for item in tree if item.isfile()}
        sums = tree.extractfile('SHA256SUMS').read().decode()
        packages = tree.extractfile('packages.txt').read().decode()
    files = {row['Filename'].rsplit('/', 1)[1] for row in rows}
    if names != files | {'SHA256SUMS', 'packages.txt', 'version.txt'}:
        raise ValueError('ubuntu-tools.bin 的文件集合与锁不一致')
    if sums != ''.join(row['SHA256'] + '  ' + row['Filename'].rsplit('/', 1)[1] + '\n' for row in rows):
        raise ValueError('ubuntu-tools.bin 的逐包摘要与锁不一致')
    if packages != ' '.join(row['Package'] for row in rows) + '\n':
        raise ValueError('ubuntu-tools.bin 的包清单与锁不一致')
    return {'inputs': builder.inputs(), 'archive_sha256': digest(archive),
            'installed_bytes': sum(int(row['Installed-Size']) * 1024 for row in rows),
            'base_status_sha256': lock['baseStatusSha256'], 'packages': len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--sha256', required=True, help='APK 的固定 SHA-256')
    args = parser.parse_args()
    if digest(args.apk) != args.sha256:
        raise SystemExit('资产 APK 摘要不符')
    lock = json.loads((RECOVERY / 'lock.json').read_text(encoding='utf8'))
    pinned = {row['asset']: row['sha256'] for row in lock['archives']}
    with zipfile.ZipFile(args.apk) as apk:
        if apk.read('assets/offline-rootfs.layout').decode().strip() != 'split-runtime-v1':
            raise SystemExit('资产 APK 不是分包布局，不能直接复用基底')
        if apk.read('assets/offline-rootfs.version').decode().strip() != (ASSETS / 'offline-rootfs.version').read_text().strip():
            raise SystemExit('资产 APK 的基底版本与源码不一致')
        base = extract(apk, 'offline-rootfs.bin', ASSETS / 'offline-rootfs.bin')
        if base != apk.read('assets/offline-rootfs.sha256').decode().strip():
            raise SystemExit('offline-rootfs.bin 与包内摘要不符')
        tools = ASSETS / 'ubuntu-tools.bin'
        extract(apk, 'ubuntu-tools.bin', tools)
        # 应急运行时固定在旧版本：两份归档必须与独立锁逐字节一致。
        for asset, source in (('recovery-rootfs.bin', 'offline-rootfs.bin'), ('recovery-dsh-runtime.bin', 'dsh-runtime.bin')):
            target = RECOVERY / 'archives' / asset
            if target.is_file() and digest(target) == pinned[asset]:
                continue
            if extract(apk, source, target) != pinned[asset]:
                raise SystemExit('应急归档与 lock.json 不符：' + asset)
    metadata = tools_metadata(tools)
    tools.with_suffix('.inputs.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'offline-rootfs.bin': base, 'ubuntu-tools': metadata,
                      'recovery': pinned}, indent=2))


if __name__ == '__main__':
    main()
