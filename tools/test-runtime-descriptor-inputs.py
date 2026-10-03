#!/usr/bin/env python3
"""Validate the shared installer/identity manifest and Gradle consumer contract."""
import re
from pathlib import Path
from runtime_input_contract import load, asset_paths, launcher_paths

ROOT = Path(__file__).resolve().parents[1]
spec = load(ROOT)
assets, launchers = asset_paths(ROOT, spec), launcher_paths(ROOT, spec)
installer = (ROOT / 'app/src/main/java/com/deepseekharness/app/runtime/RuntimeTools.java').read_text(encoding='utf8')
if '"managed-runtime-inputs.json"' not in installer or 'manifest.getJSONArray("installs")' not in installer:
    raise SystemExit('RuntimeTools 未消费受管输入契约')
identified = {p.relative_to(ROOT / 'app/src/main/assets').as_posix() for p in assets}
reads = set(re.findall(r'(?:assetText|patchClientModule)\(context,\s*(?:rootfs,\s*)?"([^"]+)"', installer))
reads.discard('runtime-descriptor.json')
if reads - identified:
    raise SystemExit('实际补丁资产未进入运行时身份: ' + ','.join(sorted(reads - identified)))
builtin_source = (ROOT / 'app/src/main/java/com/deepseekharness/app/util/BuiltinPlugins.java').read_text(encoding='utf8')
defaults = builtin_source.split('DEFAULT_BUILTINS =', 1)[1].split('));', 1)[0]
builtin_names = set(re.findall(r'"(dsha?-[a-z-]+)"', defaults))
installed_names = {row['asset'].split('/')[1] for row in spec['installs'] if row['asset'].startswith('builtin-plugins/')}
if builtin_names != installed_names:
    raise SystemExit('签名内置插件声明与安装表不同')
for row in spec['installs']:
    if row['asset'].startswith('builtin-plugins/'):
        _, name, suffix = row['asset'].split('/', 2)
        entity = name[4:] if name.startswith('dsh-') else name
        if row['target'] != 'root/dsha-' + entity + '/' + suffix:
            raise SystemExit('内置插件安装目标与既有实体契约不同')
gradle = (ROOT / 'app/build.gradle').read_text(encoding='utf8')
task = gradle.split('def prepareRuntimeDescriptor = tasks.register("prepareRuntimeDescriptor", Exec) {', 1)[1].split('def verifyRuntimeDescriptorInputs', 1)[0]
for required in ['inputs.file(runtimeInputContractFile)', 'runtimeInputContract.assetFiles', 'runtimeInputContract.installs', 'runtimeInputContract.assetTrees', 'runtimeInputContract.launcherTrees', 'runtimeInputContract.launcherSources', 'tools/runtime_input_contract.py', 'tools/dsh-runtime/package.json']:
    if required not in task:
        raise SystemExit('Gradle 未消费完整输入契约: ' + required)
print(f'单源运行时输入契约通过：{len(spec["installs"])} 安装项、{len(assets)} 资产、{len(launchers)} 启动输入')

