#!/usr/bin/env python3
"""tools/make-update-feed.py 的单测：输出必须满足 UpdatePolicy.Release.valid() 的全部条件。"""
import importlib.util, os, re, tempfile, unittest
spec = importlib.util.spec_from_file_location('feed', os.path.join(os.path.dirname(__file__), 'make-update-feed.py'))
feed = importlib.util.module_from_spec(spec); spec.loader.exec_module(feed)
BADGING = ("package: name='zzy.dsha.Kotlin' versionCode='152' versionName='0.1.7-rc2-zzy.4' platformBuildVersionName='16'\n"
           "minSdkVersion:'30'\ntargetSdkVersion:'37'\nnative-code: 'arm64-v8a'\n")

def valid(r, a):  # 与 UpdatePolicy.Release.valid() 一一对应
    https = lambda u: u.startswith('https://') and '#' not in u and '@' not in u.split('/')[2]
    return (r['versionCode'] > 0 and 23 <= a['minSdk'] <= 100 and r['version'] and r['channel'] in ('stable', 'preview')
            and a['flavor'] in ('standard', 'low') and a['abi'] == 'arm64-v8a' and https(a['url']) and https(r['pageUrl'])
            and re.fullmatch('[0-9a-f]{64}', a['sha256']) and 0 < a['bytes'] <= 1 << 30)

class FeedTest(unittest.TestCase):
    def setUp(self):
        self.apk = tempfile.NamedTemporaryFile(delete=False, suffix='.apk'); self.apk.write(b'apk' * 100); self.apk.close()
    def tearDown(self): os.unlink(self.apk.name)
    def build(self, **kw):
        args = dict(apk=self.apk.name, badging=BADGING, repo='o/r', tag='v0.1.7-rc2-zzy.4', asset='a.apk', expect_package='zzy.dsha.Kotlin')
        args.update(kw); return feed.build(**args)
    def test_valid_release(self):
        f = self.build(); r = f['releases'][0]; a = r['artifacts'][0]
        self.assertEqual(f['schemaVersion'], 1); self.assertTrue(valid(r, a))
        self.assertEqual((r['versionCode'], r['version'], a['bytes']), (152, '0.1.7-rc2-zzy.4', 300))
        self.assertEqual(a['url'], 'https://github.com/o/r/releases/download/v0.1.7-rc2-zzy.4/a.apk')
        self.assertEqual(r['pageUrl'], 'https://github.com/o/r/releases/tag/v0.1.7-rc2-zzy.4')
    def test_rejects_wrong_package(self):
        with self.assertRaises(ValueError): self.build(expect_package='com.dsh.client')
    def test_rejects_tag_mismatch(self):
        with self.assertRaises(ValueError): self.build(tag='v0.1.7-rc2-zzy.5')
    def test_rejects_bad_tag(self):
        with self.assertRaises(ValueError): self.build(tag='latest')
    def test_rejects_missing_arm64(self):
        with self.assertRaises(ValueError): self.build(badging=BADGING.replace("'arm64-v8a'", "'x86_64'"))
    def test_notes_summary_skips_headings(self):
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf8') as f: f.write('# 标题\n\n- 第一条\n## 小节\n- 第二条\n')
        try: self.assertEqual(feed.notes_summary(f.name), '- 第一条\n- 第二条')
        finally: os.unlink(f.name)

if __name__ == '__main__': unittest.main()
