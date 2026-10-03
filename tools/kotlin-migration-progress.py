#!/usr/bin/env python3
"""Java → Kotlin 迁移进度。数字必须可复现 —— 不要在文档里手写，手写的一定会漂。

口径说明
- 只统计 `app/src/` 下的 `.java` / `.kt`。`tools/` 里的夹具（`tools/aidl-stub/`、
  `tools/fixtures/`）不是产品源码，不跟着迁，算进来只会把进度显得更难看。
- 主指标是**行数**：文件数会被 util/ 那种几十行的小类撑高（util/ 平均 63 行/文件，
  ui/ 平均 137 行），字节数受资源与长文案影响。行数最接近"还剩多少活"。
- 统计的是**工作区**（含已改未提交），因为"迁移了没有"看的是磁盘上的事实。
- 行数不等于难度：`ui/` 那 76 个类零测试覆盖，同样的行数要贵得多。所以这个百分比
  只用来回答"到哪了"，不用来估工时。

用法：
    python3 tools/kotlin-migration-progress.py
    python3 tools/kotlin-migration-progress.py --markdown   # 可直接贴进文档的表格
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'app/src/'
EXTS = ('.kt', '.java')


def tracked_sources():
    """工作区里真实存在的源码：已跟踪的 + 新增未忽略的。

    不能用 `git ls-files` 单独取：那样刚写出来还没 `git add` 的 .kt 不算数，
    进度会虚低；也不能用裸的目录遍历，那会把 build/ 下的生成代码算进去。
    """
    out = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for name in sorted(set(out.splitlines())):
        path = ROOT / name
        if not name.startswith(SCOPE) or path.suffix not in EXTS or not path.is_file():
            continue
        yield name, path


def measure():
    stats = {ext: {'files': 0, 'lines': 0, 'bytes': 0} for ext in EXTS}
    for _, path in tracked_sources():
        ext = path.suffix
        stats[ext]['files'] += 1
        stats[ext]['lines'] += len(path.read_text(encoding='utf-8', errors='replace').splitlines())
        stats[ext]['bytes'] += path.stat().st_size
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--markdown', action='store_true', help='输出可直接贴进文档的 Markdown 表格')
    args = parser.parse_args()

    stats = measure()
    total = {k: sum(s[k] for s in stats.values()) for k in ('files', 'lines', 'bytes')}
    kt, java = stats['.kt'], stats['.java']
    if not total['lines']:
        print('ERROR: app/src 下一个 .java/.kt 都没找到', file=sys.stderr)
        return 1

    def pct(value, whole):
        return (value / whole * 100) if whole else 0.0

    if args.markdown:
        print('| 语言 | 文件 | 行 | 占比（按行） |')
        print('|---|---:|---:|---:|')
        for ext, label in (('.kt', 'Kotlin'), ('.java', 'Java')):
            s = stats[ext]
            print(f"| {label} | {s['files']} | {s['lines']} | {pct(s['lines'], total['lines']):.2f}% |")
        print(f"| **合计** | **{total['files']}** | **{total['lines']}** | 100% |")
        return 0

    print(f"Kotlin  {kt['files']:>4} 文件  {kt['lines']:>6} 行  {kt['bytes']:>9} 字节"
          f"   {pct(kt['lines'], total['lines']):6.2f}%（按行）")
    print(f"Java    {java['files']:>4} 文件  {java['lines']:>6} 行  {java['bytes']:>9} 字节"
          f"   {pct(java['lines'], total['lines']):6.2f}%（按行）")
    print(f"合计    {total['files']:>4} 文件  {total['lines']:>6} 行  {total['bytes']:>9} 字节")
    print()
    print('已迁（Kotlin）：')
    for name, path in tracked_sources():
        if path.suffix == '.kt':
            lines = len(path.read_text(encoding='utf-8', errors='replace').splitlines())
            print(f"  {lines:>4} 行  {name}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
