#!/usr/bin/env python3
"""回归防护：proot 的 NEEDED 依赖必须无条件就位。

背景（2026-09-19 真机事故）：用户偏好 proroot 时，ensureRuntimeFiles() 把
libtalloc.so.2 / libandroid-shmem.so 的复制圈在 `runtime().id()=="proot"` 里，
而环境维护事务（MaintenanceTransaction）把 files/linux 整棵换新——lib/ 包含在内，
新环境的 libDir 就是空目录。紧接着的个人数据迁移（runPersonalMaintenance fast=false）
固定用 proot，exec 阶段直接 CANNOT LINK EXECUTABLE（libtalloc.so.2 not found），
维护卡死在「个人文件迁移失败（退出码 1）」，用户数据停在中间态。

旧维护路径锁两条不变式（源码级断言，无需 Android 工具链）：
1. ensureRuntimeFiles 里的库复制不受运行时开关圈住（即不能出现
   `if ("proot".equals(runtime().id()))` 包住 copyExec(libtalloc) 的情况）；
2. runPersonalMaintenance 自身对 proot 路径补齐依赖（与 execRootfsForInstall
   的既有先例一致），不能假设别的调用点已经跑过。

rc2 的个人维护已委托独立恢复工具，不经过旧 rootfs 的执行路径。该分支直接
核对实际 runRecoveryMaintenance 入口无条件补齐两份库，再创建 proot 并启动；
不能把旧入口方法体是否包含 copyExec 当成新结构的保护依据。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'app/src/main/java/com/deepseekharness/app/runtime/ProotBootstrap.java'


def method_body(source: str, signature: str) -> str:
    """按签名截取方法体（简单大括号配平，足够本文件的规整风格）。"""
    idx = source.find(signature)
    if idx < 0:
        raise AssertionError(f'找不到方法签名: {signature}')
    start = source.index('{', idx)
    depth, i = 0, start
    while i < len(source):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f'方法体未闭合: {signature}')


def validate(source):
    maint = method_body(
        source, 'public com.deepseekharness.app.util.BoundedProcessRunner.Result runPersonalMaintenance(')
    if re.search(r'return\s+runRecoveryMaintenance\(command,\s*onLine,\s*timeoutMs\);', maint):
        recovery = method_body(
            source, 'public com.deepseekharness.app.util.BoundedProcessRunner.Result runRecoveryMaintenance(')
        assert 'runtime().id()' not in recovery, '独立恢复依赖不能受用户运行时偏好控制'
        assert 'new ContainerRuntime.Proot(' in recovery, '独立恢复必须选择 proot'
        for library in ('libtalloc.so.2', 'libandroid-shmem.so'):
            copy = re.search(r'copyExec\([^;]*new File\(libDir,\s*"' + re.escape(library) + r'"\)\);', recovery)
            assert copy, '独立恢复缺少依赖复制: ' + library
            assert copy.start() < recovery.index('new ContainerRuntime.Proot(') < recovery.index('pb.start()'), (
                '独立恢复必须先准备依赖再启动: ' + library)
        return

    ensure = method_body(source, 'public void ensureRuntimeFiles()')

    # 不变式 1：库复制无条件执行——ensureRuntimeFiles 里不得再用运行时开关圈住 copyExec。
    gated = re.search(
        r'if\s*\(\s*"proot"\.equals\(\s*runtime\(\)\.id\(\)\s*\)\s*\)\s*\{[^}]*copyExec\([^)]*libtalloc',
        ensure, re.S)
    assert gated is None, (
        'ensureRuntimeFiles 仍把 libtalloc/libandroid-shmem 的复制圈在 '
        '"proot".equals(runtime().id()) 里——proroot 偏好下维护换环境后 libDir 为空，'
        '固定用 proot 的维护迁移会 CANNOT LINK EXECUTABLE（真机事故 2026-09-19）')

    unconditional = re.search(r'new File\(libDir,\s*"libtalloc\.so\.2"\)', ensure) and 'copyExec' in ensure
    assert unconditional, 'ensureRuntimeFiles 缺少对 libtalloc.so.2 的无条件复制'

    # 不变式 2：维护迁移入口自带兜底，不依赖外部调用顺序。
    assert 'copyExec' in maint and 'libtalloc' in maint, (
        'runPersonalMaintenance 缺少 proot 依赖兜底复制——它固定用 proot，'
        '维护事务刚换完环境时 libDir 可能为空，必须像 execRootfsForInstall 一样先补齐')

def main():
    validate(SRC.read_text(encoding='utf-8'))
    print('PASS: 实际个人维护路径在启动 proot 前补齐 NEEDED 依赖，不依赖用户运行时偏好')


if __name__ == '__main__':
    main()
