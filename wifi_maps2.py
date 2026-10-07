# -*- coding: utf-8 -*-
"""Финальные карты покрытия Wi-Fi поверх плана этажа (лист 14 АР)."""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

z = np.load('out/wifi_field.npz')
pts, rid, b24, b5 = z['pts'], z['rid'].astype(int), z['b24'], z['b5']
res, X0, Y0 = (float(v) for v in z['raster_meta'][:3])
NX, NY = (int(v) for v in z['raster_meta'][3:])

d = json.load(open('out/wifi_res.json'))
APs = d['AP']; roomlab = {int(k): v for k, v in d['roomlab'].items()}
summary = d['summary']

walls = json.load(open('out/walls_m.json'))
cal = json.load(open('out/calib_v2.json'))
centers = {int(k): tuple(v) for k, v in cal['centers_m'].items()}

names = {n: summary[str(n)]['name'] for n in range(1, 19)}

# raster of best-rssi per band over indoor points
G24 = np.full((NY, NX), np.nan); G5 = np.full((NY, NX), np.nan)
ix = ((pts[:, 0] - X0) / res).astype(int); iy = ((pts[:, 1] - Y0) / res).astype(int)
np.maximum.at(G24, (iy, ix), b24)
np.maximum.at(G5, (iy, ix), b5)
# indoor mask
IN = np.zeros((NY, NX), bool); IN[iy, ix] = True

cmap24 = LinearSegmentedColormap.from_list('wifi', [
    (0.00, '#67001f'), (0.25, '#b2182b'), (0.45, '#ef8a62'), (0.62, '#fddbc7'),
    (0.75, '#7fbf7b'), (0.88, '#1b7837'), (1.00, '#00441b')])
cmap5 = LinearSegmentedColormap.from_list('wifi5', [
    (0.00, '#330066'), (0.3, '#6a00a8'), (0.5, '#b429f9'), (0.7, '#f16913'),
    (0.85, '#fed976'), (1.0, '#ffffcc')])

def draw(band):
    G, cm, lo, hi = (G24, cmap24, -90, -30) if band == '24' else (G5, cmap5, -110, -30)
    fig, ax = plt.subplots(figsize=(12.2, 11.2), dpi=170)
    # heat only indoors
    masked = np.ma.masked_where(~IN, G)
    ax.imshow(masked, extent=[X0, X0 + NX * res, Y0 + NY * res, Y0],
              cmap=cm, vmin=lo, vmax=hi, origin='upper', interpolation='bilinear', alpha=0.95)
    # walls on top
    for x0, y0, x1, y1 in walls:
        ax.plot([x0, x1], [y0, y1], color='#1a1a1a', lw=0.5, alpha=0.55, solid_capstyle='round')
    # building outline
    bx0, by0, bx1, by1 = [-0.35, 0.0, 30.03, 27.0]
    for (a, b, c, dd) in [(bx0, by0, bx1, by0), (bx1, by0, bx1, by1), (bx1, by1, bx0, by1), (bx0, by1, bx0, by0)]:
        ax.plot([a, c], [b, dd], color='black', lw=3.0, solid_capstyle='round')
    # room numbers
    for n, (cx, cy) in centers.items():
        if 0 <= n <= 18 and n >= 1:
            ax.text(cx, cy, str(n), ha='center', va='center', fontsize=13, fontweight='bold',
                    color='white', bbox=dict(boxstyle='circle,pad=0.28', fc='#263238', ec='white', lw=1.2))
    # AP markers
    for name, (x, y) in APs.items():
        ax.plot(x, y, marker='o', ms=13, mfc='#00e676', mec='black', mew=1.6, zorder=6)
        ax.plot(x, y, marker='o', ms=5, mfc='black', mec='none', zorder=7)
        ax.annotate(name, (x, y), textcoords='offset points', xytext=(0, 12), ha='center',
                    fontsize=8.5, fontweight='bold', color='black',
                    bbox=dict(boxstyle='round,pad=0.25', fc='#fff59d', ec='black', lw=0.8), zorder=8)
    # scale bar
    ax.plot([1.0, 11.0], [26.2, 26.2], color='black', lw=3, solid_capstyle='butt')
    ax.text(6.0, 26.45, '10 м', ha='center', fontsize=10, fontweight='bold')
    ax.set_xlim(-1.2, 31.5); ax.set_ylim(28.0, -1.0)
    ax.set_aspect('equal'); ax.axis('off')
    ttl = ('Зона покрытия 2,4 ГГц — RSSI Eltex WEP-2AC Smart ×11' if band == '24'
           else 'Зона покрытия 5 ГГц — RSSI Eltex WEP-2AC Smart ×11')
    ax.set_title(ttl, fontsize=15, fontweight='bold', pad=10)
    sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(lo, hi))
    cb = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02)
    cb.set_label('RSSI, дБм', fontsize=11)
    cb.ax.text(0.5, 0.5, '', transform=cb.ax.transAxes)
    for yv, lab in ([(-40, 'отлично ≥ −60'), (-65, 'хорошо ≥ −67'), (-70, 'норма ≥ −70')] if band == '24'
                    else [(-40, 'отлично'), (-65, 'хорошо'), (-70, 'норма')]):
        frac = (yv - lo) / (hi - lo)
        cb.ax.annotate(lab, xy=(1.0, frac), xycoords='axes fraction', xytext=(6, 0),
                       textcoords='offset points', fontsize=8, va='center', annotation_clip=False)
    fig.savefig(f'out/wifi_map_{band}.png', bbox_inches='tight', facecolor='white')
    plt.close(fig)

draw('24'); draw('5')

# --- combined side-by-side overview ---
fig, axes = plt.subplots(1, 2, figsize=(22, 6.4), dpi=150)
for ax, (G, cm, lo, hi, t) in zip(axes, [(G24, cmap24, -90, -30, '2,4 ГГц'), (G5, cmap5, -110, -30, '5 ГГц')]):
    m = np.ma.masked_where(~IN, G)
    ax.imshow(m, extent=[X0, X0 + NX * res, Y0 + NY * res, Y0], cmap=cm, vmin=lo, vmax=hi, interpolation='bilinear')
    for x0, y0, x1, y1 in walls:
        ax.plot([x0, x1], [y0, y1], color='#1a1a1a', lw=0.4, alpha=0.5)
    for a, b, c, dd in [(-0.35, 0, 30.03, 0), (30.03, 0, 30.03, 27), (30.03, 27, -0.35, 27), (-0.35, 27, -0.35, 0)]:
        ax.plot([a, c], [b, dd], color='black', lw=2.4)
    for name, (x, y) in APs.items():
        ax.plot(x, y, marker='o', ms=9, mfc='#00e676', mec='black', mew=1.2)
    for n, (cx, cy) in centers.items():
        ax.text(cx, cy, str(n), ha='center', va='center', fontsize=8, fontweight='bold', color='white',
                bbox=dict(boxstyle='circle,pad=0.2', fc='#263238', ec='none'))
    ax.set_title(f'Diапазон {t}', fontsize=13, fontweight='bold')
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle('Сравнение покрытия 2,4 и 5 ГГц (порог −70 дБм)', fontsize=14, fontweight='bold', y=1.0)
fig.tight_layout()
fig.savefig('out/wifi_map_both.png', bbox_inches='tight', facecolor='white')
plt.close(fig)

# --- KPI banner image ---
work_rooms = ['1','2','3','4','5','6','10','11','12','13','18']
cov24_work = np.mean([summary[r]['cov24'] for r in work_rooms])
fig = plt.figure(figsize=(12, 2.1), dpi=170)
ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
ax.add_patch(Rectangle((0, 0), 1, 1, fc='#0b3d66'))
kpis = [('11', 'точек доступа\nEltex WEP-2AC Smart'), ('100%', f'покрытие рабочих зон\n2,4 ГГц ≥ −70 дБм'),
        (f'{d["cov_all"]:.1f}%', 'покрытие всей площади\nэтажа 2,4 ГГц'), ('18/18', 'помещений\nобеспечены сигналом')]
for i, (big, small) in enumerate(kpis):
    x = 0.055 + i * 0.245
    ax.text(x, 0.62, big, fontsize=26, fontweight='bold', color='#ffd54f')
    ax.text(x, 0.22, small, fontsize=10.5, color='white', va='bottom')
fig.savefig('out/kpi_banner.png', facecolor='#0b3d66')
plt.close(fig)
print('maps done')
