# -*- coding: utf-8 -*-
"""Финальные карты Wi-Fi: тепловые поля 2.4/5 ГГц с изолиниями зон качества,
обрезка строго по зданию 30x27 м, чистая схема размещения (слайд 5)."""
import json, numpy as np
from scipy.ndimage import gaussian_filter
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
plt.rcParams['font.family'] = 'DejaVu Sans'

BX0, BY0, BX1, BY1 = 0., 0., 30., 27.
S24 = np.load('/tmp/S24.npy'); S5 = np.load('/tmp/S5.npy'); Rid = np.load('/tmp/Rid.npy')
NY, NX = S24.shape
xs_m = np.linspace(0.325, 29.675, NX); ys_m = np.linspace(0.075, 25.825, NY)
GX, GY = np.meshgrid(xs_m, ys_m)
RES = xs_m[1] - xs_m[0]
IN = ~np.isnan(S24)

d = json.load(open('out/wifi_res.json'))
APs = {k: tuple(v) for k, v in d['AP'].items()}
summ = d['summary']
names = {int(k): v['name'] for k, v in summ.items()}
cal = json.load(open('out/calib_v2.json'))
centers = {int(k): tuple(v) for k, v in cal['centers_m'].items()}
walls = json.load(open('/tmp/walls_in.json'))

def room_polys():
    polys = []
    for r in [str(i) for i in range(1, 19)]:
        M = (Rid == r) & IN
        if M.sum() < 8: continue
        Ms = gaussian_filter(M.astype(float), sigma=1.2) > 0.5
        cs = plt.contour(GX, GY, Ms.astype(float), levels=[0.5])
        for seg in cs.allsegs[0]:
            if len(seg) >= 6: polys.append((r, seg))
        plt.close(cs.axes.figure)
    return polys

cmap24 = LinearSegmentedColormap.from_list('w', ['#5a0000', '#a50f15', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#66bd63', '#1a7e37', '#00441b'])
cmap5 = LinearSegmentedColormap.from_list('5', ['#1a0340', '#4b03a1', '#8063e7', '#c2a5f1', '#e8d4ff', '#ffd9a0', '#ffa64d', '#f16913', '#b30000'])

def draw_walls(ax, lw=0.7, alpha=0.55):
    for x0, y0, x1, y1 in walls:
        ax.plot([x0, x1], [y0, y1], color='#37474f', lw=lw, alpha=alpha, solid_capstyle='round', zorder=3)

def draw_numbers(ax):
    for n, (cx, cy) in centers.items():
        if 1 <= n <= 18 and names.get(n):
            ax.text(cx, cy, str(n), ha='center', va='center', fontsize=10.5, fontweight='bold', color='white', zorder=5,
                    bbox=dict(boxstyle='circle,pad=0.2', fc='#263238', ec='white', lw=1.0, alpha=0.92))

def draw_aps(ax, r=0.85):
    for name, (x, y) in APs.items():
        ax.add_patch(plt.Circle((x, y), r, fc='#00e676', ec='#0d1b12', lw=1.6, zorder=7, alpha=0.97))
        ax.plot(x, y, marker='+', ms=8, mew=2, color='#0d1b12', zorder=8)
        ax.annotate(name, (x, y), xytext=(0, 12), textcoords='offset points', ha='center', fontsize=7.5,
                    fontweight='bold', zorder=8, bbox=dict(boxstyle='round,pad=0.22', fc='#fffde7', ec='#33691e', lw=0.8))

def scalebar(ax):
    ax.plot([1.0, 11.0], [26.6, 26.6], color='black', lw=3, zorder=6)
    for xx in (1, 6, 11): ax.plot([xx, xx], [26.45, 26.75], color='black', lw=2, zorder=6)
    ax.text(6.0, 26.95, 'масштаб 10 м', ha='center', fontsize=8.5, fontweight='bold', zorder=6)

def hatch_bad(ax, S, thr):
    bad = IN & (S < thr)
    ax.contourf(GX, GY, bad.astype(float), levels=[0.5, 1.5], colors=['none'], hatches=['///'], zorder=2, alpha=0.5)

# ================= MAP 2.4 =================
fig, ax = plt.subplots(figsize=(12.4, 11.2), dpi=170)
M = np.ma.masked_where(~IN, S24)
im = ax.imshow(M, extent=[xs_m[0]-RES/2, xs_m[-1]+RES/2, ys_m[-1]+RES/2, ys_m[0]-RES/2],
               cmap=cmap24, vmin=-75, vmax=-35, origin='upper', interpolation='bilinear', zorder=1)
hatch_bad(ax, S24, -70)
draw_walls(ax, 0.6, 0.45)
cs = ax.contour(GX, GY, S24, levels=[-70, -67, -60], colors=['#ffcccb', '#ffe082', '#ffffff'],
                linewidths=[1.6, 1.3, 1.6], linestyles=['-', '--', '-'], zorder=4)
ax.clabel(cs, fmt={-70: '−70 дБм · минимум', -67: '−67 · хорошо', -60: '−60 · отлично'}, fontsize=7.5, inline=True)
for r, seg in room_polys():
    ax.fill(seg[:, 0], seg[:, 1], facecolor='none', edgecolor='#ffffff', lw=1.0, alpha=0.35, zorder=2)
ax.add_patch(plt.Rectangle((BX0, BY0), BX1-BX0, BY1-BY0, fill=False, ec='black', lw=3.4, zorder=6))
draw_numbers(ax); draw_aps(ax); scalebar(ax)
ax.set_xlim(-0.6, 30.6); ax.set_ylim(27.5, -0.5); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('Зоны покрытия Wi-Fi — 2,4 ГГц (Eltex WEP-2AC Smart ×11)\nплощадь с уровнем ≥ −70 дБм: 96,6% всей площади этажа (100% рабочих помещений)',
             fontsize=15, fontweight='bold', pad=10)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label('RSSI, дБм', fontsize=10)
for yv, lab in [(-40, 'отлично'), (-60, 'хорошо'), (-67, 'норма'), (-72, 'слабый')]:
    f = (yv + 75) / 40
    cb.ax.annotate(lab, xy=(1.0, f), xycoords='axes fraction', xytext=(6, 0), textcoords='offset points',
                   fontsize=8, va='center', annotation_clip=False)
ax.legend(handles=[plt.Line2D([], [], color='white', ls='-', lw=1.6, label='изолиния −60 дБм (отлично)'),
                   plt.Line2D([], [], color='#ffe082', ls='--', lw=1.4, label='изолиния −67 дБм (хорошо)'),
                   plt.Line2D([], [], color='#ffcccb', ls='-', lw=1.6, label='изолиния −70 дБм (минимум)'),
                   matplotlib.patches.Patch(facecolor='none', edgecolor='white', hatch='///', label='зоны вне нормы (< −70 дБм)')],
          loc='lower left', fontsize=8, framealpha=0.85, ncol=2)
fig.savefig('out/wifi_map_24.png', bbox_inches='tight', facecolor='white', pad_inches=0.15); plt.close(fig)

# ================= MAP 5 =================
fig, ax = plt.subplots(figsize=(12.4, 11.2), dpi=170)
M = np.ma.masked_where(~IN, S5)
im = ax.imshow(M, extent=[xs_m[0]-RES/2, xs_m[-1]+RES/2, ys_m[-1]+RES/2, ys_m[0]-RES/2],
               cmap=cmap5, vmin=-95, vmax=-35, origin='upper', interpolation='bilinear', zorder=1)
hatch_bad(ax, S5, -70)
draw_walls(ax, 0.6, 0.45)
cs = ax.contour(GX, GY, S5, levels=[-70, -67, -60], colors=['#ffb3a7', '#ffe082', '#ffffff'],
                linewidths=[1.6, 1.3, 1.6], linestyles=['-', '--', '-'], zorder=4)
ax.clabel(cs, fmt={-70: '−70', -67: '−67', -60: '−60'}, fontsize=7.5, inline=True)
ax.add_patch(plt.Rectangle((BX0, BY0), BX1-BX0, BY1-BY0, fill=False, ec='black', lw=3.4, zorder=6))
draw_numbers(ax); draw_aps(ax); scalebar(ax)
ax.set_xlim(-0.6, 30.6); ax.set_ylim(27.5, -0.5); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('Зоны покрытия Wi-Fi — 5 ГГц (Eltex WEP-2AC Smart ×11)\nплощадь с уровнем ≥ −70 дБм: 86,2% всей площади (96,5% рабочих); сквозь ЖБ-стены сигнал затухает на ~20 дБ',
             fontsize=15, fontweight='bold', pad=10)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label('RSSI, дБм', fontsize=10)
ax.legend(handles=[plt.Line2D([], [], color='white', ls='-', lw=1.6, label='изолиния −60 дБм'),
                   plt.Line2D([], [], color='#ffe082', ls='--', lw=1.4, label='изолиния −67 дБм'),
                   plt.Line2D([], [], color='#ffb3a7', ls='-', lw=1.6, label='изолиния −70 дБм'),
                   matplotlib.patches.Patch(facecolor='none', edgecolor='white', hatch='///', label='вне нормы (< −70 дБм): тех. помещения, санузлы')],
          loc='lower left', fontsize=8, framealpha=0.85)
fig.savefig('out/wifi_map_5.png', bbox_inches='tight', facecolor='white', pad_inches=0.15); plt.close(fig)

# ================= SLIDE 5 SCHEMATIC =================
fig, ax = plt.subplots(figsize=(12.0, 10.8), dpi=170)
ax.add_patch(plt.Rectangle((BX0, BY0), BX1-BX0, BY1-BY0, fc='#eef2f6', ec='#102a43', lw=3.6, zorder=1))
draw_walls(ax, 0.9, 0.8)
for name, (x, y) in APs.items():
    ax.add_patch(plt.Circle((x, y), 7.5, fc='#4caf50', ec='#2e7d32', lw=0.8, alpha=0.10, zorder=2, ls=':'))
for n, (cx, cy) in centers.items():
    if 1 <= n <= 18 and names.get(n):
        ax.text(cx, cy-0.75, str(n), ha='center', va='center', fontsize=12, fontweight='bold', color='#102a43', zorder=5)
        ax.text(cx, cy+0.55, names[n][:30], ha='center', va='center', fontsize=6.4, color='#51607a', zorder=5)
draw_aps(ax, r=0.95)
scalebar(ax)
ax.set_xlim(-0.6, 30.6); ax.set_ylim(27.5, -0.5); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart — план этажа 30×27 м (лист 14 АР)',
             fontsize=15, fontweight='bold', pad=10)
fig.savefig('out/wifi_layout.png', bbox_inches='tight', facecolor='white', pad_inches=0.15); plt.close(fig)
print('maps done')
