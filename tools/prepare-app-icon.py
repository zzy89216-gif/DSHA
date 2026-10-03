#!/usr/bin/env python3
"""用一张方形照片生成启动图标：自适应图标前景（图像放在 72dp 安全区内）+ 背景色 + 各密度 PNG。

背景色取照片四边的平均色，使自适应图标的遮罩区域与照片无缝衔接。
用法：python3 tools/prepare-app-icon.py 照片.jpg
"""
from pathlib import Path
import argparse
from PIL import Image, ImageOps, ImageDraw

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
res = Path(__file__).resolve().parents[1] / 'app/src/main/res'
im = ImageOps.exif_transpose(Image.open(args.source)).convert('RGB')
w, h = im.size; s = min(w, h)
im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
px = im.load()
edge = [px[x, y] for x in range(0, s, 8) for y in (0, s - 1)] + [px[x, y] for y in range(0, s, 8) for x in (0, s - 1)]
bg = tuple(sum(c[i] for c in edge) // len(edge) for i in range(3))
# 108dp 画布按 4 倍（432px）输出；图像占中间 72dp（288px），四周 18dp 留给遮罩。
fg = Image.new('RGB', (432, 432), bg); fg.paste(im.resize((288, 288), Image.Resampling.LANCZOS), (72, 72))
fg.save(res / 'drawable-nodpi/launcher_foreground_v2.png', optimize=True)
(res / 'values/launcher_icon.xml').write_text('<resources><color name="launcher_background">#%02X%02X%02X</color></resources>\n' % bg)
for density, n in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    base = im.resize((n, n), Image.Resampling.LANCZOS)
    for name in ('ic_launcher.png', 'ic_launcher_v2.png'): base.save(res / f'mipmap-{density}/{name}', optimize=True)
    mask = Image.new('L', (n * 4, n * 4), 0); ImageDraw.Draw(mask).ellipse((0, 0, n * 4 - 1, n * 4 - 1), fill=255)
    round_icon = Image.new('RGBA', (n, n), (0, 0, 0, 0)); round_icon.paste(base, (0, 0), mask.resize((n, n), Image.Resampling.LANCZOS))
    round_icon.save(res / f'mipmap-{density}/ic_launcher_round_v2.png', optimize=True)
print('已生成自适应图标前景、背景色与 5 种密度图标；更换图标时请递增资源名后缀（v2 → v3）以刷新桌面缓存。')
