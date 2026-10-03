#!/usr/bin/env python3
"""Guard the reviewed ownership boundaries, without pretending to prove all Java dependencies.

双后缀（.java / .kt）：主语言迁移期间两种源码并存，任何一处写死 `*.java` 都会在看
起来 PASS 的情况下把该条契约放空 —— 这是这个脚本最危险的失效方式，所以每条检查都
额外断言「真的扫到了东西」。
"""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/'app/src/main/java/com/deepseekharness/app'
EXT=('.java','.kt')
errors=[]


def sources(directory,recursive=False):
    """目录下参与检查的源码；同时认 .java 和 .kt。"""
    it=directory.rglob('*') if recursive else directory.glob('*')
    return sorted(p for p in it if p.is_file() and p.suffix in EXT)


def source_of(stem_path):
    """按类名取源码文件：迁移期间同名的 .java/.kt 不会共存，但不能写死后缀。"""
    for ext in EXT:
        candidate=stem_path.with_suffix(ext)
        if candidate.is_file():return candidate
    errors.append(f'{stem_path}.[java|kt]: 找不到源码（改名后忘了同步这个守卫？）')
    return None


def expect(condition,message):
    """扫不到东西和违反契约同样致命，都要报出来。"""
    if not condition:errors.append(message)


util_files=sources(JAVA/'util')
expect(util_files,f'{JAVA/"util"} 下一个源码都没扫到：架构守卫静默失效')
for file in util_files:
    source=file.read_text(encoding='utf8')
    if re.search(r'^import\s+(?:android|androidx)\.',source,re.M):errors.append(str(file)+': Android import in pure policy')
runtime_files=sources(JAVA/'runtime')
expect(runtime_files,f'{JAVA/"runtime"} 下一个源码都没扫到：架构守卫静默失效')
for file in runtime_files:
    source=file.read_text(encoding='utf8')
    if re.search(r'com\.deepseekharness\.app\.(?:BackupManager|core\.(?:RuntimeTasks|MaintenanceCoordinator|ConfigStore|ColdInstallDiagnostics))\b',source):
        errors.append(str(file)+': runtime depends on Android maintenance authority')
for tree in ('main','standard','low'):
    tree_files=sources(ROOT/f'app/src/{tree}/java',recursive=True)
    expect(tree_files,f'app/src/{tree}/java 下一个源码都没扫到：架构守卫静默失效')
    for file in tree_files:
        source=file.read_text(encoding='utf8')
        if file.stem!='HarnessController' and re.search(r'new\s+(?:com\.deepseekharness\.app\.core\.)?HarnessController\s*\(',source):
            errors.append(str(file)+': independent production controller owner')
coordinator_path=source_of(JAVA/'core/MaintenanceCoordinator')
coordinator=coordinator_path.read_text(encoding='utf8') if coordinator_path else ''
if re.search(r'\b(?:PtyTerminalFragment|TerminalFragment)\b',coordinator):
    errors.append('MaintenanceCoordinator depends on terminal view owners')
for name in ('PtyTerminalFragment','TerminalFragment'):
    path=source_of(JAVA/f'ui/{name}')
    source=path.read_text(encoding='utf8') if path else ''
    if re.search(r'new\s+TerminalTabs\s*<',source):
        errors.append(name+': independent terminal tab owner')
    if re.search(r'\b(?:ptyTabs|simpleTabs)\(\)\.(?:add|remove|select|beginClose|closeFailed)\s*\(',source):
        errors.append(name+': terminal view mutates owner table')
owner_path=source_of(JAVA/'core/TerminalSessionOwner')
owner=owner_path.read_text(encoding='utf8') if owner_path else ''
if re.search(r'public\s+TerminalTabs<[^>]+>\s+(?:ptyTabs|simpleTabs)\s*\(',owner):
    errors.append('TerminalSessionOwner exposes mutable tab table')
tabbar_path=source_of(JAVA/'ui/TerminalTabBar')
tabbar=tabbar_path.read_text(encoding='utf8') if tabbar_path else ''
if not re.search(r'render\s*\(View\s+root,\s*TerminalTabs\.ReadOnly<',tabbar):
    errors.append('TerminalTabBar must consume read-only tab view')
if errors:raise SystemExit('\n'.join(errors))
print('PASS pure policies; runtime maintenance/configuration/diagnostic ports; single production controller construction')
