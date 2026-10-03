"""Select required device behaviors from actual changes against a sealed source baseline."""
import fnmatch
import hashlib
import json
from pathlib import Path

CONTRACT=Path(__file__).with_name('release-acceptance.json')
CERT='7977dff4d452c3908daaea91f0a20b1aba71181b734ba43ab54898ff1e31428f'
PACKAGE='zzy.dsha.Kotlin'
SOURCE_SUFFIXES=('.java','.kt')


def _language_neutral(path):
    """把源码路径归一化成与语言无关的形态。

    契约描述的是**类**（`*/util/SystemLanguage.java`），而主语言迁到 Kotlin 之后
    同一个类在 git 里叫 `.kt`。不归一化，规则就会因为后缀对不上而永不命中 ——
    而它的失效方式恰恰是静默的：`requirements()` 只是少选中几条真机检查，
    没有任何报错，`--deliver-from` 照常放行。
    """
    for suffix in SOURCE_SUFFIXES:
        if path.endswith(suffix):
            return path[:-len(suffix)]
    return path


def matches_path(name,patterns):
    """changed 列表里的路径是否命中该规则的任一 pattern（后缀无关）。"""
    normalized=_language_neutral(name)
    return any(fnmatch.fnmatchcase(normalized,_language_neutral(pattern)) for pattern in patterns)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline_from_receipt(path):
    """A raw current snapshot is not a baseline: require a completed two-flavor delivery receipt."""
    path=Path(path).resolve()
    receipt=json.loads(path.read_text(encoding='utf8'))
    if receipt.get('status')!='PASS_FOR_EXECUTED_SCOPE':
        raise ValueError('ACCEPTANCE_BASELINE_NOT_DELIVERED')
    apks=receipt.get('apks',[])
    if len(apks)!=2 or {a.get('flavor') for a in apks}!={'standard','low'} \
            or any(a.get('certificateSha256')!=CERT or a.get('package')!=PACKAGE for a in apks):
        raise ValueError('ACCEPTANCE_BASELINE_IDENTITY')
    source=receipt.get('sourceSnapshot',{});snapshot=Path(source.get('path','')).resolve()
    if snapshot.parent!=path.parent or not snapshot.is_file() or digest(snapshot)!=source.get('sha256'):
        raise ValueError('ACCEPTANCE_BASELINE_SNAPSHOT')
    return json.loads(snapshot.read_text(encoding='utf8')),{'receiptSha256':digest(path),'sourceSha256':digest(snapshot)}


def requirements(baseline, current, contract=CONTRACT, provenance=None):
    rules=json.loads(Path(contract).read_text(encoding='utf8'))
    if rules.get('schema')!=1 or not isinstance(baseline,dict) or not isinstance(current,dict):
        raise ValueError('ACCEPTANCE_BASELINE_FORMAT')
    if not baseline or not current:
        raise ValueError('ACCEPTANCE_BASELINE_EMPTY')
    changed=sorted(name for name in set(baseline)|set(current) if baseline.get(name)!=current.get(name))
    selected={flavor:set(rules['baseDeviceChecks']) for flavor in ('standard','low')}
    matched=[]
    for rule in rules['changeRules']:
        hits=[name for name in changed if matches_path(name,rule['paths'])]
        if not hits:continue
        matched.append({'rule':rule['id'],'paths':hits})
        for flavor in rule['flavors']:selected[flavor].update(rule['deviceChecks'])
    return {'schema':1,'contractSha256':digest(contract),'baselineReceipt':provenance,'baselineSha256':hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest(),
            'changed':changed,'rules':matched,'required':{k:sorted(v) for k,v in selected.items()}}


def validate(proof, selection):
    if not isinstance(proof,dict) or proof.get('acceptance')!=selection:
        raise ValueError('DEVICE_ACCEPTANCE_PLAN_MISMATCH')
    for flavor,checks in selection['required'].items():
        tested=proof.get('flavors',{}).get(flavor,{})
        behaviors=tested.get('behaviors',{})
        for check in checks:
            row=behaviors.get(check)
            if not isinstance(row,dict) or row.get('result')!='PASS' \
                    or not isinstance(row.get('evidence'),str) or not row['evidence'].strip():
                raise ValueError('DEVICE_ACCEPTANCE_MISSING:'+flavor+':'+check)
