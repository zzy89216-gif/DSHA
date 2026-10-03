#!/usr/bin/env python3
"""生成应用内更新清单 updates.json（schemaVersion 1，与 core/UpdateEngine 的解析一致）。

由 GitHub Actions 在正式发版时调用，清单作为发行版附件上传；App 读取
https://github.com/<repo>/releases/latest/download/updates.json。

用法：
  make-update-feed.py --apk X.apk --badging badging.txt --repo owner/name --tag v0.1.7-rc2-zzy.4 \
      --asset DSHA-0.1.7-rc2-zzy.4.apk [--notes-file .github/RELEASE_NOTES.md] --out updates.json
badging.txt 为 `aapt2 dump badging X.apk` 的输出。
"""
import argparse, hashlib, json, os, re, sys

def parse_badging(text):
    pkg = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", text)
    sdk = re.search(r"(?:minSdkVersion|sdkVersion):'(\d+)'", text)
    abi = re.search(r"native-code: (.+)", text)
    if not pkg or not sdk: raise ValueError('badging 缺少 package / minSdk 信息')
    abis = re.findall(r"'([^']+)'", abi.group(1)) if abi else []
    return dict(package=pkg[1], versionCode=int(pkg[2]), versionName=pkg[3], minSdk=int(sdk[1]), abis=abis)

def notes_summary(path, limit=600):
    if not path or not os.path.isfile(path): return ''
    lines = [l.strip() for l in open(path, encoding='utf8') if l.strip() and not l.startswith('#')]
    text = '\n'.join(lines)
    return text if len(text) <= limit else text[:limit].rstrip() + '…'

def build(apk, badging, repo, tag, asset, notes='', expect_package=None):
    info = parse_badging(badging)
    if expect_package and info['package'] != expect_package:
        raise ValueError(f"包名 {info['package']} 与预期 {expect_package} 不符")
    if info['abis'] and 'arm64-v8a' not in info['abis']:
        raise ValueError('APK 不含 arm64-v8a')
    if not re.fullmatch(r'v\d+\.\d+\.\d+[0-9A-Za-z.\-]*', tag): raise ValueError('标签格式不对：' + tag)
    if info['versionName'] != tag[1:]: raise ValueError(f"versionName {info['versionName']} 与标签 {tag} 不一致")
    h = hashlib.sha256(); size = 0
    with open(apk, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk); size += len(chunk)
    base = f'https://github.com/{repo}/releases'
    release = dict(version=info['versionName'], versionCode=info['versionCode'],
                   # 只有正式发版生成清单，一律是稳定通道。
                   channel='stable', notes=notes, pageUrl=f'{base}/tag/{tag}',
                   artifacts=[dict(flavor='standard', minSdk=info['minSdk'], abi='arm64-v8a',
                                   url=f'{base}/download/{tag}/{asset}', sha256=h.hexdigest(), bytes=size)])
    return dict(schemaVersion=1, releases=[release])

def main():
    p = argparse.ArgumentParser()
    for a in ('apk', 'badging', 'repo', 'tag', 'asset', 'out'): p.add_argument('--' + a, required=True)
    p.add_argument('--notes-file'); p.add_argument('--expect-package')
    a = p.parse_args()
    feed = build(a.apk, open(a.badging, encoding='utf8').read(), a.repo, a.tag, a.asset,
                 notes_summary(a.notes_file), a.expect_package)
    with open(a.out, 'w', encoding='utf8') as f: json.dump(feed, f, ensure_ascii=False, indent=2)
    r = feed['releases'][0]
    print(f"updates.json: {r['version']} code={r['versionCode']} bytes={r['artifacts'][0]['bytes']}")

if __name__ == '__main__':
    try: main()
    except ValueError as e: print('错误：' + str(e), file=sys.stderr); sys.exit(1)
