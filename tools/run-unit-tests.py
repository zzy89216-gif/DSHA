#!/usr/bin/env python3
"""不经 Gradle 直接编译并跑纯逻辑单测（javac/kotlinc + JUnitCore）。

为什么需要它：AGP 9.1.1 硬性要求 build-tools >= 36.0.0，而 Google 仓库的 Linux
build-tools 只有 x86_64（`repository2-3.xml` 里 build-tools 只有 `_linux.zip`，
无 aarch64 变体）。aarch64 主机上 `processStandardDebugResources` 会卡在
"AAPT2 ... Daemon startup failed"，整个 `:app:testStandardDebugUnitTest` 连带跑不了。

但 `app/src/test/` 下的测试本来就不碰 Android 运行时（AGENTS.md：`util/` 下的类
不得 import Android API），所以完全可以用 `javac` / `kotlinc` + `JUnitCore` 直接跑，
绕开 aapt2 / d8 / 打包这一整条链。本脚本就是那条路，用来验证纯逻辑改动。

跑法：
    python3 tools/run-unit-tests.py
    DSHA_ONLY=QueryTest,ShellQuoteTest python3 tools/run-unit-tests.py   # 只跑几个

不做的事：不跑仪器测试（androidTest 需要真实设备）、不替代 CI 上的完整
Gradle 构建。它的定位是「本机没有可运行的 aapt2 时，仍然能验证改动」。

Kotlin 混编（主语言迁移后）：
    仓库里出现 `.kt` 时，走和 Gradle 一样的两遍编译 ——
      1) kotlinc 读全部 .kt **和** .java，其中 .java 只用来解析符号；
      2) javac 把 kotlinc 的输出放进 classpath，编译 .java。
    一个 .kt 都没有时自动退回纯 javac 路径，行为与迁移前一致。

本机拿不到资源产物时怎么编：
    R 和 BuildConfig 正常从 Gradle 产物里取（R.jar / R.txt / generated BuildConfig）；
    aapt2 跑不了时这些产物不存在，于是退化成**桩**：R 只包含源码里真正引用到的
    资源名，BuildConfig 按 app/build.gradle 的声明生成。桩只保证类型能对上，
    不保证资源 id 的真实数值 —— 纯逻辑单测本来也不该依赖那个。

类路径从哪来：
    tools/classpath.init.gradle 让 Gradle 只做依赖解析（配置阶段在 aarch64 上是好的），
    把 `standardDebugCompileClasspath` 导成 app/build/dsha-classpath/classpath.txt。
    清单不存在时本脚本会自动跑一次那次 Gradle 调用。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'

# 本机 kotlinc 必须与 **AGP 内置的 Kotlin** 同版本。
# AGP 9 起 Kotlin 是内置的（不再应用 org.jetbrains.kotlin.android），编译器版本跟着 AGP 走：
# AGP 9.1.1 → Kotlin 2.2.10。想升级就一起改，依据是 AGP 的 pom：
#   caches/modules-2/files-2.1/com.android.tools.build/gradle/<AGP 版本>/gradle-<AGP 版本>.pom
# 里的 org.jetbrains.kotlin:kotlin-gradle-plugin。
# 为什么较真：编译器版本决定语言特性能不能用，本机与 CI 不一致会出现
# 「本机编得过、CI 编不过」这种最难查的差异。
EXPECTED_KOTLIN = '2.2.10'

# 本机验证链覆盖的源码集：standard flavor + debug 变体（与迁移前保持一致）。
MAIN_ROOTS = ['src/main/java', 'src/standard/java', 'src/debug/java']
TEST_ROOT = 'src/test/java'


def die(msg: str) -> None:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def ensure_utf8_locale() -> None:
    """必须在任何 JVM 启动之前，且判据是「当前 locale 真是 UTF-8」。

    坑一：LANG 为空时 JVM 的 sun.jnu.encoding 落到 ANSI_X3.4-1968，工作区路径里的
    中文目录名会被替换成 '?'，javac 报一堆莫名其妙的 cannot find symbol —— 从错误
    信息完全看不出是编码问题。

    坑二（真踩过）：不能只看「有没有设 locale 变量就跳过」。本机 LC_CTYPE=POSIX 是
    设着的，按那个判据会直接返回，UTF-8 从没生效。所以这里查 locale charmap 的实际值。
    """
    def is_utf8() -> bool:
        try:
            r = subprocess.run(['locale', 'charmap'], capture_output=True, text=True, timeout=15)
            return 'utf' in r.stdout.lower()
        except Exception:
            return any('utf' in os.environ.get(v, '').lower()
                       for v in ('LC_ALL', 'LC_CTYPE', 'LANG'))

    if is_utf8():
        return
    try:
        avail = subprocess.run(['locale', '-a'], capture_output=True,
                               text=True, timeout=15).stdout.lower()
    except Exception:
        avail = ''
    for cand in ('C.utf8', 'C.UTF-8', 'en_US.utf8', 'en_US.UTF-8'):
        if cand.lower() in avail:
            os.environ['LANG'] = cand
            os.environ['LC_CTYPE'] = cand
            os.environ.pop('LC_ALL', None)
            return
    die('当前环境没有 UTF-8 locale，JVM 无法处理工作区路径里的非 ASCII 目录名；'
        '先装一个，例如 locale-gen en_US.UTF-8')


def gradle_user_home() -> Path:
    for cand in (os.environ.get('GRADLE_USER_HOME'), '/opt/toolchains/gradle-user-home',
                 str(Path.home() / '.gradle')):
        if cand and Path(cand).is_dir():
            return Path(cand)
    die('找不到 Gradle 缓存目录，设 GRADLE_USER_HOME 指过去')


def android_jar() -> Path:
    roots = [os.environ.get('ANDROID_SDK_ROOT'), os.environ.get('ANDROID_HOME'),
             '/opt/android-sdk', '/usr/lib/android-sdk']
    for r in roots:
        if not r:
            continue
        for p in sorted(Path(r).glob('platforms/android-3*'), reverse=True):
            jar = p / 'android.jar'
            if jar.is_file():
                return jar
    die('找不到 android.jar，设 ANDROID_SDK_ROOT 或装 platforms;android-37')


def kotlin_compiler() -> str:
    for cand in (os.environ.get('KOTLINC'), '/opt/kotlin/kotlinc/bin/kotlinc'):
        if cand and Path(cand).is_file():
            return cand
    found = shutil.which('kotlinc')
    if found:
        return found
    die('源码里有 .kt，但找不到 kotlinc。装一个 Kotlin 编译器，或设 KOTLINC=/path/to/kotlinc')


def verify_kotlin_version() -> str:
    """本机 kotlinc 与 AGP 内置 Kotlin 必须一致；不一致直接失败而不是悄悄跑。"""
    r = subprocess.run([kotlin_compiler(), '-version'], capture_output=True, text=True)
    m = re.search(r'kotlinc-jvm\s+([0-9][^\s(]*)', r.stdout + r.stderr)
    version = m.group(1) if m else ''
    if version != EXPECTED_KOTLIN and not os.environ.get('DSHA_ANY_KOTLIN'):
        die(f'本机 kotlinc 是 {version or "未知版本"}，但 AGP 内置的 Kotlin 是 {EXPECTED_KOTLIN}。\n'
            f'      两者不一致时，本机编得过、CI 编不过的差异几乎无法排查。\n'
            f'      装 v{EXPECTED_KOTLIN}（https://github.com/JetBrains/kotlin/releases），'
            f'或设 DSHA_ANY_KOTLIN=1 明确跳过这条检查。')
    return version


def kotlin_stdlib() -> str:
    """跑测试时必须在 classpath 上，否则 NoClassDefFoundError: kotlin/jvm/internal/Intrinsics。

    用编译器自带的那个（而不是依赖里传递进来的旧版本），保证与刚编出来的字节码同辈。
    """
    kc = Path(kotlin_compiler()).resolve()
    lib = kc.parents[1] / 'lib'
    jar = lib / 'kotlin-stdlib.jar'
    if not jar.is_file():
        die(f'找不到 {jar}（应该在 kotlinc 同级的 lib/ 下）')
    return str(jar)


def classpath_dump_file() -> Path:
    return APP / 'build/dsha-classpath/classpath.txt'


def resolve_classpath() -> list:
    """优先读 Gradle 导出的精确类路径，没有就现场导一次。

    为什么不沿用「扫 Gradle 缓存里所有 jar」（迁移前的做法）：那样会把 AGP 自己的
    插件依赖也算进去 —— 几十 MB，而且里面不少类的版本和 app 真实编译期看到的不一致，
    慢且容易冒出莫名其妙的符号冲突。tools/classpath.init.gradle 让 Gradle 自己解析
    `standardDebugCompileClasspath`，拿到的才是和真实构建同一份清单。
    """
    dump = classpath_dump_file()
    if not dump.is_file():
        print('==> 还没有类路径清单，先用 Gradle 导一次（配置阶段，约 1-2 分钟）')
        r = subprocess.run(
            ['bash', str(ROOT / 'build.sh'), '-I', str(ROOT / 'tools/classpath.init.gradle'),
             ':app:dshaDumpCompileClasspath'],
            cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode != 0 or not dump.is_file():
            sys.stderr.write((r.stdout or '')[-3000:])
            sys.stderr.write((r.stderr or '')[-3000:])
            die('导出类路径失败。手工复现：bash build.sh -I tools/classpath.init.gradle '
                ':app:dshaDumpCompileClasspath')
    entries = [line.strip() for line in dump.read_text(encoding='utf-8').splitlines()]
    entries = [e for e in entries if e and not e.startswith('#')]
    # 清单里会带上「本工程自己的 class 输出」（Gradle 的惰性产物，本机根本没生成）。
    # 那个位置由本脚本自己编译出来的 main_out 顶上，直接丢掉。
    own = str(APP.resolve())
    kept, dropped_own = [], 0
    for e in entries:
        if e.startswith(own):
            dropped_own += 1
            continue
        kept.append(e)
    if dropped_own:
        print(f'NOTE: 类路径清单里有 {dropped_own} 个本工程自身产物条目，已忽略')
    if not kept:
        die(f'类路径清单是空的：{dump}')
    missing = [e for e in kept if not Path(e).exists()]
    if missing:
        for e in missing[:5]:
            print(f'  缺失：{e}', file=sys.stderr)
        die(f'类路径里有 {len(missing)} 个文件不存在（缓存被清过？）。删掉 {dump} 后重跑')
    return kept


def find_jar(gh: Path, *needles: str) -> Path:
    for needle in needles:
        hits = [p for p in gh.glob(f'caches/modules-2/files-2.1/**/{needle}*.jar')
                if p.is_file() and 'sources' not in p.name and 'javadoc' not in p.name]
        if hits:
            return sorted(hits)[0]
    die(f'Gradle 缓存里找不到 {" 或 ".join(needles)}，先跑一次 Gradle 让它下载依赖')


R_REF = re.compile(r'\bR\.([a-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)')


def _write_r_java(src: Path, by_type: dict) -> None:
    src.parent.mkdir(parents=True, exist_ok=True)
    body = ['package com.deepseekharness.app;', '', 'public final class R {']
    for typ, items in sorted(by_type.items()):
        body.append(f'  public static final class {typ} {{')
        for name, value in items:
            body.append(f'    public static final int {name} = {value};')
        body.append('  }')
    body.append('}')
    src.write_text('\n'.join(body) + '\n', encoding='utf-8')


def r_classpath_entry(gen: Path):
    """返回 (加到 classpath 的条目, 需要一起编译的源码)。

    优先用 Gradle 产出；没有就造桩。桩按源码里实际出现的 `R.<type>.<name>` 生成，
    这样引用面一定盖得住，也不会因为多造几千个字段把编译拖慢。
    """
    for p in sorted(APP.glob('build/intermediates/compile_r_class_jar/*/*/R.jar')):
        return [str(p)], []
    txt = next(iter(sorted(APP.glob('build/intermediates/compile_symbol_list/*/*/R.txt'))), None)
    if txt is not None:
        by_type: dict = {}
        for line in txt.read_text(encoding='utf-8').splitlines():
            parts = line.split()
            if len(parts) == 3:
                by_type.setdefault(parts[0], []).append((parts[1], parts[2]))
        src = gen / 'from-rtxt' / 'R.java'
        _write_r_java(src, by_type)
        return [], [str(src)]

    by_type = {}
    for root in MAIN_ROOTS:
        for pat in ('*.java', '*.kt'):
            for p in (APP / root).rglob(pat):
                text = p.read_text(encoding='utf-8', errors='replace')
                for m in R_REF.finditer(text):
                    by_type.setdefault(m.group(1), set()).add(m.group(2))
    if not by_type:
        die('源码里没有任何 R 引用，也没找到 Gradle 生成的 R —— 无法继续')
    # 值只要互不相同即可；给每个条目一个稳定的序号，方便对照报错。
    filled = {}
    counter = 0x7f010000
    for typ in sorted(by_type):
        filled[typ] = [(name, counter + i) for i, name in enumerate(sorted(by_type[typ]))]
        counter += len(filled[typ])
    src = gen / 'r-stub' / 'R.java'
    _write_r_java(src, filled)
    print(f'NOTE: 没有可用的资源产物，R 用了桩（{sum(len(v) for v in filled.values())} 个条目）')
    return [], [str(src)]


def build_config_entry(gen: Path):
    """BuildConfig 同理：优先 Gradle 产物，否则按 app/build.gradle 生成桩。"""
    hits = sorted(APP.glob('build/generated/source/buildConfig/**/**/BuildConfig.java'))
    if hits:
        return [], [str(p) for p in hits]

    text = (APP / 'build.gradle').read_text(encoding='utf-8')

    def pick(pattern: str, default: str) -> str:
        m = re.search(pattern, text)
        return m.group(1) if m else default

    app_id = pick(r'applicationId\s+"([^"]+)"', 'com.deepseekharness.app')
    version_code = pick(r'versionCode\s+(\d+)', '1')
    version_name = pick(r'versionName\s+"([^"]*)"', '0.0')
    src = gen / 'buildconfig' / 'BuildConfig.java'
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        'package com.deepseekharness.app;\n\n'
        '/** 本机编译桩：真实的 BuildConfig 由 AGP 生成。字段与 app/build.gradle 对齐。 */\n'
        'public final class BuildConfig {\n'
        '  public static final boolean DEBUG = true;\n'
        f'  public static final String APPLICATION_ID = "{app_id}";\n'
        '  public static final String BUILD_TYPE = "debug";\n'
        '  public static final String FLAVOR = "standard";\n'
        f'  public static final int VERSION_CODE = {version_code};\n'
        f'  public static final String VERSION_NAME = "{version_name}";\n'
        '  public static final boolean LOW_ANDROID = false;\n'
        '}\n', encoding='utf-8')
    print('NOTE: 没有 Gradle 生成的 BuildConfig，用了桩')
    return [], [str(src)]


def generated_sources(gen: Path):
    """构建期生成的源码与 classpath 条目。返回 (源码列表, classpath 条目)。"""
    sources, cp = [], []
    # UiMessages 是 prepare-ui-languages.py 的产物，缺了就现场生成。
    if not any(APP.glob('build/generated/uiLanguage/**/UiMessages.java')):
        script = ROOT / 'tools/prepare-ui-languages.py'
        r = subprocess.run([sys.executable, '-B', str(script), '--output',
                            str(APP / 'build/generated/uiLanguage')], capture_output=True, text=True)
        if r.returncode != 0:
            die(f'生成 UiMessages 失败：{r.stdout}{r.stderr}')
    sources += [str(p) for p in APP.glob('build/generated/uiLanguage/**/*.java')]
    # AIDL 产物：本机没有能跑的 aidl 时用人工等价产物（见 tools/aidl-stub/README.md）
    sources += [str(p) for p in (ROOT / 'tools/aidl-stub').rglob('*.java')]
    for entry in (r_classpath_entry(gen), build_config_entry(gen)):
        cp += entry[0]
        sources += entry[1]
    return sources, cp


def _javac(sources, out: Path, cp) -> None:
    """把 -cp 和源文件一起写进 argfile。

    为什么 -cp 不能走命令行：这个容器经 proot/proroot 转一层 exec，把 ~36 KB 的
    classpath 当作单个 argv 元素传过去会被截断，javac 只认到前一小段，于是报一堆
    「package androidx.lifecycle does not exist」—— 而 android.jar 里的类又都能解析，
    看起来像依赖没下全。实测：同样的变量，bash 走 shell 传参正常、Python 直接
    execve 必挂；把 -cp 挪进 argfile 后两边都稳定。这类静默截断最耗人。
    """
    if not sources:
        return
    out.mkdir(parents=True, exist_ok=True)
    argfile = out.parent / f'{out.name}-javac-args.txt'
    lines = ['-cp', os.pathsep.join(cp)] + list(sources)
    argfile.write_text('\n'.join(lines), encoding='utf-8')
    cmd = ['javac', '-nowarn', '-encoding', 'UTF-8', '-source', '17', '-target', '17',
           '-d', str(out), f'@{argfile}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # 只打 `error:` 行会漏掉紧跟其后的 `symbol:` / `location:`，而"找不到什么"
        # 恰恰是有用的那一半。按原始顺序整段打出来，截断到 60 行够定位了。
        merged = (r.stdout + r.stderr).splitlines()
        errs = [l for l in merged if 'error:' in l]
        for line in merged[:60]:
            print(line, file=sys.stderr)
        if len(merged) > 60:
            print(f'...（还有 {len(merged) - 60} 行）', file=sys.stderr)
        die(f'javac 失败（{len(errs)} 条 error）')


def _kotlinc(sources, out: Path, cp, label: str) -> None:
    """kotlinc 也走 argfile：Kotlin 编译器的参数同样经不起 proot 那层截断。"""
    out.mkdir(parents=True, exist_ok=True)
    argfile = out.parent / f'{out.name}-kotlinc-args.txt'
    lines = ['-nowarn', '-jvm-target', '17', '-d', str(out),
             '-classpath', os.pathsep.join(cp)] + list(sources)
    argfile.write_text('\n'.join(lines), encoding='utf-8')
    r = subprocess.run([kotlin_compiler(), f'@{argfile}'], capture_output=True, text=True)
    if r.returncode != 0:
        merged = (r.stdout + r.stderr).splitlines()
        errs = [l for l in merged if 'error:' in l]
        for line in merged[:60]:
            print(line, file=sys.stderr)
        if len(merged) > 60:
            print(f'...（还有 {len(merged) - 60} 行）', file=sys.stderr)
        die(f'{label} kotlinc 失败（{len(errs)} 条 error）')


def _test_sources():
    """测试树里的**全部**源文件，而不是只挑 `*Test`。

    坑（真踩过）：`backup/JvmBackupFileSystem.java` 这类测试辅助类不以 Test 结尾，
    只编译 `*Test.java` 会让它整个缺席，于是 78 个测试类一起报 cannot find symbol，
    而报错位置全在 `import` 之后的行上，看起来像主线代码没编出来。
    编译全树、只把 `*Test` 拿去跑，语义才对。
    """
    java = sorted(str(p) for p in (APP / TEST_ROOT).rglob('*.java'))
    kt = sorted(str(p) for p in (APP / TEST_ROOT).rglob('*.kt'))
    return java, kt


def main() -> int:
    ensure_utf8_locale()
    gh = gradle_user_home()
    aj = android_jar()
    junit = find_jar(gh, 'junit-4.13.2', 'junit-4.13', 'junit-4.12')
    hamcrest = find_jar(gh, 'hamcrest-core-1.3', 'hamcrest-core')

    work = Path(tempfile.mkdtemp(prefix='dsha-unjunit-'))
    gen = work / 'gen'

    cp = [str(aj), str(junit), str(hamcrest)] + resolve_classpath()

    gen_sources, gen_cp = generated_sources(gen)
    cp += gen_cp

    java_sources = [str(p) for root in MAIN_ROOTS for p in (APP / root).rglob('*.java')]
    kotlin_sources = [str(p) for root in MAIN_ROOTS for p in (APP / root).rglob('*.kt')]
    java_sources = sorted(set(java_sources + gen_sources))
    if not java_sources and not kotlin_sources:
        die('没找到任何源码')

    main_out = work / 'main'
    if kotlin_sources or any(Path(t).suffix == '.kt' for t in (APP / TEST_ROOT).rglob('*.kt')):
        print(f'==> kotlinc {verify_kotlin_version()}（与 AGP 内置版本一致性已校验）')
    if kotlin_sources:
        print(f'==> kotlinc 主源码：{len(kotlin_sources)} 个 .kt + {len(java_sources)} 个 .java')
        _kotlinc(kotlin_sources + java_sources, main_out, cp, '主源码')
        _javac(java_sources, main_out, [str(main_out)] + cp)
    else:
        _javac(java_sources, main_out, cp)

    test_java, test_kt = _test_sources()
    if not test_java and not test_kt:
        die('没找到测试源码')

    test_out = work / 'test'
    if test_kt:
        _kotlinc(test_kt + test_java, test_out, [str(main_out)] + cp, '测试')
        _javac(test_java, test_out, [str(test_out), str(main_out)] + cp)
    else:
        _javac(test_java, test_out, [str(main_out)] + cp)

    # 必须是全限定名：JUnitCore 按 FQN 加载，裸类名会全部 ClassNotFound。
    classes = sorted(str(p.relative_to(test_out).with_suffix('')).replace(os.sep, '.')
                     for p in test_out.rglob('*Test.class'))
    # DSHA_ONLY 只挑要**跑**的测试；编译仍然是整棵测试树（辅助类不能少）。
    only = [s for s in os.environ.get('DSHA_ONLY', '').split(',') if s]
    if only:
        classes = [c for c in classes if c.rsplit('.', 1)[-1] in only]
    if not classes:
        die(f'没有可跑的测试类（DSHA_ONLY={",".join(only)} 没匹配到任何 *Test）')
    runtime = [str(test_out), str(main_out)] + cp
    # 资源目录也要进 classpath：`PortableBackupCryptoTest` 靠
    # `getResourceAsStream("/backups/v5-aesgcm-vector.json")` 读测试夹具，
    # 少这一条就是一句无从下手的 assertNotNull 失败。
    for res in (APP / TEST_ROOT).parent / 'resources', APP / 'src/main/resources':
        if res.is_dir():
            runtime.append(str(res))
    if kotlin_sources or test_kt:
        runtime.append(kotlin_stdlib())
    run_cp = os.pathsep.join(runtime)
    lang = f'Java+Kotlin（{len(kotlin_sources)} 个 .kt）' if kotlin_sources else '纯 Java'
    print(f'==> {lang} 单测：{len(classes)} 个测试类，'
          f'{len(java_sources)} 个 .java，android.jar={aj.name}')
    # 和 javac 同理：run 的 classpath 也不能走 argv（会被 proot 那层截断）。
    run_argfile = work / 'junit-args.txt'
    run_argfile.write_text('\n'.join(['-cp', run_cp, 'org.junit.runner.JUnitCore'] + classes),
                           encoding='utf-8')
    r = subprocess.run(['java', f'@{run_argfile}'], capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    for line in tail[-25:]:
        print(line)
    shutil.rmtree(work, ignore_errors=True)
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
