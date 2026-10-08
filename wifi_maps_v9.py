# -*- coding: utf-8 -*-
"""Карты Wi-Fi v9: СПЛОШНЫЕ зоны покрытия (тепловая карта RSSI) поверх плана этажа.
Источник — поле wifi_field.npz (44884 точки с шагом 0,5 м внутри помещений),
значения переносятся на плотную сетку 0,05 м диффузией ВНУТРИ каждого помещения
(за стены не «течёт»), поэтому зоны обрезаются строго по границам комнат.
Обрезка карты — точно по контуру здания 30x27 м, без лишних областей."""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.patches import Patch
from scipy.ndimage import distance_transform_edt, binary_closing

BASE = '/workspace/out/'
res = json.load(open(BASE + 'wifi_res.json'))
APs = res['AP']; rl = res['roomlab']
d = np.load(BASE + 'wifi_field.npz')
pts, rid, b24, b5 = d['pts'], d['rid'].astype(str), d['b24'], d['b5']

W, H, GX, GY = 30.0, 27.0, 601, 541
dx, dy = W/(GX-1), H/(GY-1)
gx, gy = np.linspace(0, W, GX), np.linspace(0, H, GY)
GXX, GYY = np.meshgrid(gx, gy)

ix = (pts[:,0]/dx).round().astype(int); iy = (pts[:,1]/dy).round().astype(int)
IDG = np.full((GY, GX), '', dtype='<U4'); IDG[iy, ix] = rid
inside = IDG != ''

# --- стены ---
walls = json.load(open(BASE + 'walls_m.json'))
WM = np.zeros((GY, GX), bool)
for x0, y0, x1, y1 in walls:
    L = max(abs(x1-x0), abs(y1-y0))
    if L < 0.3: continue
    n = int(L/0.05)+1
    for t in np.linspace(0, 1, n):
        ii = int((x0+(x1-x0)*t)/dx); jj = int((y0+(y1-y0)*t)/dy)
        if 0 <= ii < GX and 0 <= jj < GY: WM[jj, ii] = True
WM = binary_closing(WM, np.ones((3,3), bool))

def build_field(vals):
    Rf = np.full((GY, GX), np.nan)
    Rf[iy, ix] = vals
    nanm = np.isnan(Rf) & inside & ~WM
    while nanm.any():
        _, idx = distance_transform_edt(nanm, return_indices=True)
        upd = np.where(~nanm & inside, Rf, np.nan)[tuple(idx)]
        newly = nanm & np.isfinite(upd)
        if not newly.any(): break
        Rf[newly] = upd[newly]
        nanm = np.isnan(Rf) & inside & ~WM
    nanm = np.isnan(Rf) & inside
    if nanm.any():
        _, idx = distance_transform_edt(nanm, return_indices=True)
        Rf[nanm] = Rf[idx[0][nanm], idx[1][nanm]]
    Rf[~inside] = np.nan
    return Rf

F24 = build_field(b24); F5 = build_field(b5)
np.savez_compressed(BASE+'wifi_field_dense.npz', F24=F24, F5=F5)

# сверка со сводкой
sm = res['summary']; worst = max(
    (abs(np.nanmean(F24[IDG==k]) - sm[k]['avg24']), k) for k in sm if (IDG==k).sum() > 50)
print('сверка: макс расхождение %.1f дБ (пом %s)' % worst)

# --- единая шкала и цвета зон для обеих карт ---
BINS = [-np.inf, -85, -80, -70, -67, -60, -50, np.inf]
ZNAMES = ['нет покрытия (< −85)', 'пограничная −85…−80', 'слабая −80…−70',
          'минимум приёмности −70…−67', 'хорошо −67…−60', 'отлично −60…−50', 'превосходно > −50']
ZCOLS = ['#cfd8dc', '#ef9a9a', '#ff7043', '#ffc107', '#9ccc65', '#43a047', '#1b8a4c']
CMAP = LinearSegmentedColormap.from_list('rssi', ['#5c6b73','#cfd8dc','#ef9a9a','#ff7043',
      '#ffd54f','#aed581','#4caf50','#1b8a4c','#0d5c2f'])
NORM = BoundaryNorm(BINS, CMAP.N)

def draw_walls(ax):
    for x0, y0, x1, y1 in walls:
        L = max(abs(x1-x0), abs(y1-y0))
        if L < 0.4: continue
        ax.plot([x0,x1],[y0,y1], color='#3a4a5f', lw=1.0, solid_capstyle='butt', zorder=6)
    ax.add_patch(plt.Rectangle((0,0), W, H, fill=False, ec='#101720', lw=3.2, zorder=7))

def draw_map(F, fname, title, band):
    fig, ax = plt.subplots(figsize=(13.4, 11.0), dpi=150)
    ax.set_facecolor('#eef1f5')
    # сплошная тепловая карта зон покрытия
    im = ax.imshow(F, origin='lower', extent=[0,W,0,H], cmap=CMAP, norm=NORM,
                   interpolation='bilinear', zorder=1)
    # границы зон: изолинии порогов
    Cf = np.nan_to_num(F, nan=-200)
    cs = ax.contour(GXX, GYY, Cf, levels=[-85,-80,-70,-67,-60,-50],
                    colors='white', linewidths=1.1, zorder=4)
    ax.clabel(cs, fmt={-70:'−70', -67:'−67', -60:'−60'}, fontsize=7, inline_spacing=4)
    # затемнение зон ниже −70 (нет уверенного приёма) + жирный контур границы зоны −70
    low = (Cf < -70) & inside
    ov = np.ma.masked_where(~low, np.ones_like(low, dtype=float))
    from matplotlib.colors import ListedColormap as _LC
    ax.imshow(ov, origin='lower', extent=[0,W,0,H], cmap=_LC(['#455a64']),
              alpha=0.28, interpolation='nearest', zorder=5)
    ax.contour(GXX, GYY, Cf, levels=[-70], colors=['#263238'], linewidths=2.0, zorder=5)
    draw_walls(ax)
    # номера помещений
    for s in set(rid):
        m = IDG == s
        if m.sum() < 200: continue
        cx, cy = GXX[m].mean(), GYY[m].mean()
        ax.text(cx, cy, str(rl.get(s,'?')), ha='center', va='center', fontsize=10,
                fontweight='bold', color='#101720', zorder=9,
                bbox=dict(boxstyle='circle,pad=0.24', fc='white', ec='#101720', lw=1.0, alpha=.92))
    # AP
    for name, (x, y) in APs.items():
        ax.plot(x, y, marker='o', ms=11, mfc='#ffd400', mec='#101720', mew=1.6, zorder=10)
        ax.annotate(name, (x,y), xytext=(7,7), textcoords='offset points', fontsize=8,
                    fontweight='bold', color='#101720', zorder=11,
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#101720', alpha=.95))
    # легенда зон
    handles = [Patch(facecolor=c, edgecolor='#777', label=n) for c,n in zip(ZCOLS, ZNAMES)]
    leg = ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.002,1.0),
                    fontsize=9.5, title='Зоны уровня сигнала · '+band, title_fontsize=10.5)
    leg.get_title().set_fontweight('bold')
    # масштаб
    ax.plot([1,6],[H-0.8,H-0.8], color='#101720', lw=3, solid_capstyle='butt', zorder=10)
    ax.text(3.5, H-0.4, '5 м', ha='center', fontsize=9, fontweight='bold', zorder=10)
    ax.set_xlim(-0.4, W+0.4); ax.set_ylim(-0.4, H+0.4)   # обрезка строго по зданию
    ax.set_aspect('equal'); ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5))
    ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=15, fontweight='bold', pad=12)
    fig.text(0.46, 0.015, 'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · '
             'железобетонные стены 200 мм с базальтовым наполнением: затухание 12 дБ @2,4 ГГц / 20 дБ @5 ГГц · '
             'цвет = уровень сигнала RSSI, белая линия = граница зоны',
             ha='center', fontsize=8.5, color='#555')
    fig.tight_layout(rect=[0, 0.035, 0.985, 1])
    fig.savefig(BASE+fname, facecolor='white')
    plt.close(fig)
    print('saved', fname)

draw_map(F24, 'wifi_map_24.png',
         'Зоны покрытия Wi-Fi · 2,4 ГГц — сплошное покрытие всех рабочих зон', '2,4 ГГц')
draw_map(F5, 'wifi_map_5.png',
         'Зоны покрытия Wi-Fi · 5 ГГц — приоритетный трафик внутри помещений', '5 ГГц')

# схема размещения v9 — та же геометрия, мягкая подложка вместо пустоты
fig, ax = plt.subplots(figsize=(13.4, 11.0), dpi=150)
ax.set_facecolor('#f7f9fb')
ids = sorted(set(rid), key=lambda s: int(rl.get(s, 0)))
past = ['#dbe7f4','#fdf1d7','#e2f3dd','#fbe3e3','#ece2f8','#dff2f4','#f7ecd9','#e8eef4',
        '#f3e7d3','#e0f0ea','#f4e0ee','#dfe7f2','#fdf7d9','#e6f3da','#fadfdf','#e3ecf8',
        '#efe7da','#dcecf1']
col = {s: past[i % len(past)] for i, s in enumerate(ids)}
CG = np.full((GY, GX), np.nan)
for i, s in enumerate(ids): CG[IDG == s] = i
from matplotlib.colors import ListedColormap
ax.imshow(CG, origin='lower', extent=[0,W,0,H], cmap=ListedColormap([col[s] for s in ids]),
          interpolation='nearest', zorder=0)
draw_walls(ax)
for s in ids:
    m = IDG == s
    if m.sum() < 200: continue
    cx, cy = GXX[m].mean(), GYY[m].mean()
    ax.text(cx, cy, str(rl[s]), ha='center', va='center', fontsize=11, fontweight='bold',
            color='#101720', zorder=8,
            bbox=dict(boxstyle='circle,pad=0.26', fc='white', ec='#101720', lw=1.1, alpha=.95))
for name, (x, y) in APs.items():
    ax.plot(x, y, marker='o', ms=14, mfc='#d62728', mec='#101720', mew=1.8, zorder=9)
    ax.annotate(name, (x,y), xytext=(8,8), textcoords='offset points', fontsize=8.5,
                fontweight='bold', color='#101720', zorder=10,
                bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='#101720', alpha=.95))
ax.set_xlim(-0.4, W+0.4); ax.set_ylim(-0.4, H+0.4); ax.set_aspect('equal')
ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
ax.grid(color='#d7dde5', lw=0.5, zorder=0)
ax.plot([1,6],[H-0.8,H-0.8], color='#101720', lw=3, zorder=9)
ax.text(3.5, H-0.4, '5 м', ha='center', fontsize=9, fontweight='bold', zorder=9)
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart (11 шт.)',
             fontsize=15, fontweight='bold', pad=12)
fig.text(0.5, 0.015, 'Монтаж на потолок h≈3,5–4,0 м · PoE 802.3af · координаты от юго-западного угла '
         'здания · контур 30×27 м по листу 14 АР', ha='center', fontsize=8.5, color='#555')
fig.tight_layout()
fig.savefig(BASE+'wifi_layout.png', facecolor='white')
plt.close(fig)
print('saved wifi_layout.png')

tot = np.isfinite(F24).sum(); tot5 = np.isfinite(F5).sum()
print('2.4: >=-70 %.1f%% | >=-67 %.1f%%' % (((F24>=-70).sum()/tot)*100, ((F24>=-67).sum()/tot)*100))
print('5:   >=-70 %.1f%% | >=-67 %.1f%%' % (((F5>=-70).sum()/tot5)*100, ((F5>=-67).sum()/tot5)*100))
