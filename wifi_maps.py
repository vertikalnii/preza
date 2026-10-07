# -*- coding: utf-8 -*-
"""Карты покрытия Wi-Fi поверх плана этажа (лист 14 АР), метрическая система."""
import json, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

walls = json.load(open('out/walls_m.json'))
res = json.load(open('out/wifi_res.json'))
z = np.load('out/wifi_field.npz')
pts, rid, b24, b5 = z['pts'], z['rid'].astype(int), z['b24'], z['b5']
AP = {k: tuple(v) for k, v in res['AP'].items()}
names = {k: v['name'] for k, v in res['summary'].items()}

cmap = LinearSegmentedColormap.from_list('wifi',
    ['#d7191c', '#fdae61', '#ffffbf', '#a6d96a', '#1a9641'])
bounds = [-95, -85, -78, -70, -60, -30]

def draw(ax, field, title):
    # стены в метрах
    for x0, y0, x1, y1 in walls:
        ax.plot([x0, x1], [y0, y1], color='#333333', lw=0.4, alpha=0.55, solid_capstyle='round')
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=field, cmap=cmap, vmin=-90, vmax=-30,
                   s=16, marker='s')
    for name, (px, py) in AP.items():
        ax.plot(px, py, marker='o', ms=11, mfc='white', mec='#0b3d91', mew=2.2, zorder=5)
        ax.annotate(name, (px, py), textcoords='offset points', xytext=(0, 9),
                    ha='center', fontsize=7.5, fontweight='bold', color='#0b3d91', zorder=6)
    # подписи помещений
    for r in res['summary']:
        s = res['summary'][r]
        pass
    ax.set_xlim(-1.5, 31.5); ax.set_ylim(-1.5, 28.5)
    ax.invert_yaxis()
    ax.set_aspect('equal'); ax.axis('off')
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label('RSSI, дБм', fontsize=9)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)

# центры помещений для подписей — из calib_v2 centers_m
cm = {int(k): v for k, v in json.load(open('out/calib_v2.json'))['centers_m'].items()}

fig, ax = plt.subplots(figsize=(11, 8.6), dpi=150)
draw(ax, b24, 'План этажа (лист 14 АР) — покрытие Wi-Fi 2.4 ГГц (Eltex WEP-2AC Smart ×11)\nРабочие помещения: 100% площади ≥ −70 дБм · все помещения: 96,6%')
for r, (cx, cy) in cm.items():
    ax.text(cx, cy, f"{r}", fontsize=8, ha='center', va='center', color='black',
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.75))
fig.tight_layout(); fig.savefig('out/wifi_map_24.png'); plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 8.6), dpi=150)
draw(ax, b5, 'Покрытие Wi-Fi 5 ГГц (тот же проект, затухание в ЖБ-стенах +20 дБ/стену)\nСквозь 1 стену уверенный приём сохраняется; техпомещения — только 2.4 ГГц')
for r, (cx, cy) in cm.items():
    ax.text(cx, cy, f"{r}", fontsize=8, ha='center', va='center', color='black',
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.75))
fig.tight_layout(); fig.savefig('out/wifi_map_5.png'); plt.close(fig)
print('maps saved')
