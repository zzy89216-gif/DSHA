#!/usr/bin/env python3
"""文档一致性：文档里引用的东西必须真的存在。

文档最容易烂的方式不是写错，而是**慢慢失真**：文件改名/搬家/删掉之后，文档里的链接和路径
还指着旧位置，而没有任何东西会因此失败。这个检查把那些引用逐条落到实处。

三类引用会检查：
  1. Markdown 相对链接 `[文字](路径)` —— 相对该文档所在目录解析；
  2. 反引号里的仓库相对路径（`docs/x.md`、`tools/x.py`、`app/src/.../X.java`）；
  3. 反引号里的源码文件名（`Xyz.java`）—— 允许它已经迁成 `.kt`（迁移期两种后缀并存）。

不检查的：外链（http/https）、锚点（#...）、以及明显是示例/占位的路径（带 `<` `>` `*`）。

用法：
    python3 -B tools/test-doc-consistency.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_EXT = ('.java', '.kt')

# 反引号里的仓库相对路径：以这些开头才算，避免把普通文字当路径
ROOTS = ('app/', 'tools/', 'docs/', 'scripts/', 'gradle/', '.github/', 'agent-skills/')
# 顶层的固定文件同样检查
TOP_FILES = ('AGENTS.md', 'BUILD.md', 'CHANGELOG.md', 'HANDOVER.md', 'README.md',
             'README.en.md', 'THIRD_PARTY_NOTICES.md', 'LICENSE')
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
CODE_PATH = re.compile(r'`([^`\n]+)`')
JAVA_NAME = re.compile(r'\b([A-Za-z_][A-Za-z0-9_$]*\.java)\b')


def tracked():
    out = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return set(out.splitlines())


# 构建产物：干净检出时本来就不存在，文档提它们是对的，只是不该检查
BUILD_OUTPUT = ('app/build/', 'build/')
# 第三方许可证正文里的路径是上游仓库内部结构，不是本仓库的
THIRD_PARTY_TEXTS = ('LICENSE.upstream.md', 'LICENSE.txt', 'LICENSE-2.0.txt')


def looks_like_placeholder(text):
    return any(ch in text for ch in '<>*$') or text.startswith('...')


def is_build_output(text):
    return text.startswith(BUILD_OUTPUT)


def resolve(base_dir, raw):
    path = raw.split('#', 1)[0].split('?', 1)[0]
    if not path or looks_like_placeholder(path):
        return None
    return (base_dir / path).resolve()


def main():
    files = tracked()
    names = {}
    for name in files:
        names.setdefault(Path(name).name, []).append(name)

    docs = [n for n in sorted(files)
            if n.endswith('.md') and Path(n).name not in THIRD_PARTY_TEXTS]
    errors = []

    for name in docs:
        text = (ROOT / name).read_text(encoding='utf-8', errors='replace')
        base = (ROOT / name).parent

        # 1. Markdown 链接
        for raw in LINK.findall(text):
            if raw.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            target = resolve(base, raw)
            if target is not None and not target.exists():
                errors.append(f'{name}: 链接指向不存在的路径 → {raw}')

        # 2. 反引号里的仓库相对路径
        for raw in CODE_PATH.findall(text):
            candidate = raw.strip().rstrip('.,;:')
            if (not candidate.startswith(ROOTS) or looks_like_placeholder(candidate)
                    or is_build_output(candidate)):
                continue
            target = (ROOT / candidate.split('#')[0]).resolve()
            if not target.exists():
                errors.append(f'{name}: 引用了不存在的路径 → {candidate}')
            # 顶层固定文件
        for raw in CODE_PATH.findall(text):
            candidate = raw.strip().rstrip('.,;:')
            if candidate in TOP_FILES and not (ROOT / candidate).is_file():
                errors.append(f'{name}: 引用了不存在的文件 → {candidate}')

        # 3. 源码文件名（允许 .java ↔ .kt）
        for raw_name in JAVA_NAME.findall(text):
            if raw_name in names:
                continue
            alt = raw_name[:-len('.java')] + '.kt'
            if alt in names:
                continue
            errors.append(f'{name}: 提到的源码文件既没有 .java 也没有 .kt → {raw_name}')

    if errors:
        print('文档一致性检查失败：', file=sys.stderr)
        for error in errors:
            print('  - ' + error, file=sys.stderr)
        print('\n改完文件名/位置后，同步更新文档里的引用。', file=sys.stderr)
        return 1
    print(f'文档一致性通过：{len(docs)} 个 Markdown 文件里的链接与路径引用都落到实处')
    return 0


if __name__ == '__main__':
    sys.exit(main())
