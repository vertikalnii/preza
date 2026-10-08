# -*- coding: utf-8 -*-
"""Карты Wi-Fi v10 — ЯРКИЕ зоны покрытия.
Исправления против v9:
  1) Насыщенная цветовая шкала (каждая зона уровня — свой выраженный цвет),
     вместо размытого градиента, который на печати выглядел серым.
  2) Отрисовка зон дискретно по классам RSSI (BoundaryNorm + nearest) — цвета чистые.
  3) Белая подложка вне помещений; зоны заливают ВСЮ площадь комнат.
  4) Обрезка строго по контуру здания 30x27 м (без лишних областей).
Источник поля: out/wifi_field.npz (44884 точки, шаг 0,5 м), диффузия внутри комнат.
"""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
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

# --- помещения: сплошная сетка по ПРЯМОУГОЛЬНИКАМ из wifi_field.npz ---
# Ключи IDG = id из rid (совпадают с ключами summary в wifi_res.json!)
recs = json.load(open(BASE + 'rooms_final.json'))
def room_rect(r):
    x0, x1 = sorted((r['x0'], r['x1'])); y0, y1 = sorted((r['y0'], r['y1']))
    return max(x0, 0.0), max(y0, 0.0), min(x1, W), min(y1, H)
IDG = np.full((GY, GX), '', dtype='<U4')
for r in recs:
    k = str(r['no']); x0, y0, x1, y1 = room_rect(r)
    a0, a1 = int(np.floor(x0/dx)), int(np.ceil(x1/dx))
    b0, b1 = int(np.floor(y0/dy)), int(np.ceil(y1/dy))
    IDG[max(b0,0):min(b1,GY)+1, max(a0,0):min(a1,GX)+1] = k
inside = IDG != ''
print('сплошная mask inside:', inside.sum(), 'клеток (%.0f м²)' % (inside.sum()*dx*dy))

ix = (pts[:, 0]/dx).round().astype(int); iy = (pts[:, 1]/dy).round().astype(int)

walls = json.load(open(BASE + 'walls_m.json'))
WM = np.zeros((GY, GX), bool)
for x0, y0, x1, y1 in walls:
    L = max(abs(x1-x0), abs(y1-y0))
    if L < 0.3:
        continue
    n = int(L/0.05)+1
    for t in np.linspace(0, 1, n):
        ii = int((x0+(x1-x0)*t)/dx); jj = int((y0+(y1-y0)*t)/dy)
        if 0 <= ii < GX and 0 <= jj < GY:
            WM[jj, ii] = True
WM = binary_closing(WM, np.ones((3, 3), bool))
# стены не должны «съедать» заливку: раздвинутая маска заливаемых клеток
PAD = np.ones((5, 5), bool)
from scipy.ndimage import binary_dilation
FILL = binary_dilation(inside & ~WM, PAD) & inside
print('fillable cells:', FILL.sum())

def build_field(vals):
    Rf = np.full((GY, GX), np.nan)
    Rf[iy, ix] = vals                      # семплы из расчётной сетки 0,5 м
    nanm = np.isnan(Rf) & FILL
    it = 0
    while nanm.any() and it < 60:
        _, idx = distance_transform_edt(nanm, return_indices=True)
        upd = np.where(~nanm, Rf, np.nan)[tuple(idx)]
        newly = nanm & np.isfinite(upd)
        if not newly.any():
            break
        Rf[newly] = upd[newly]
        nanm = np.isnan(Rf) & FILL
        it += 1
    # остаток (изолированные клетки у стен) — ближайший семпл того же помещения
    nanm = np.isnan(Rf) & inside
    if nanm.any():
        _, idx = distance_transform_edt(nanm, return_indices=True)
        Rf[nanm] = Rf[idx[0][nanm], idx[1][nanm]]
    Rf[~inside] = np.nan
    return Rf

F24 = build_field(b24); F5 = build_field(b5)
np.savez_compressed(BASE+'wifi_field_dense.npz', F24=F24, F5=F5)

# ---- ДИСКРЕТНЫЕ ЗОНЫ: яркие различимые цвета ----
BINS = [-np.inf, -85, -80, -70, -67, -60, np.inf]
ZNAMES = ['Нет связи   (< −85 дБм)',
          'Очень слабый   −85…−80',
          'Слабый   −80…−70',
          'Минимум приёмности   −70…−67',
          'Хороший сигнал   −67…−60',
          'Отличный сигнал   ≥ −60']
ZCOLS = ['#b0bec5',   # серый       — нет связи
         '#e57373',   # красный     — очень слабый
         '#ff9800',   # оранжевый   — слабый
         '#ffee58',   # жёлтый      — минимум приёмности
         '#66bb6a',   # зелёный     — хорошо
         '#1565c0']   # синий       — отлично
CMAP = ListedColormap(ZCOLS)
NORM = BoundaryNorm(BINS, CMAP.N)

def draw_walls(ax):
    for x0, y0, x1, y1 in walls:
        L = max(abs(x1-x0), abs(y1-y0))
        if L < 0.4:
            continue
        ax.plot([x0, x1], [y0, y1], color='#263238', lw=1.1, solid_capstyle='butt', zorder=6)
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, ec='#0d141c', lw=3.4, zorder=7))

def draw_map(F, fname, title, band):
    fig, ax = plt.subplots(figsize=(13.4, 11.0), dpi=150)
    ax.set_facecolor('#ffffff')
    cls = np.digitize(F, BINS[1:-1])          # 0..5
    cls = np.where(np.isfinite(F), cls, -1)
    rgba = np.full(cls.shape+(4,), np.nan)
    pal = [matplotlib.colors.to_rgba(c) for c in ZCOLS]
    for k in range(6):
        m = cls == k
        rgba[m] = pal[k]
    ax.imshow(rgba, origin='lower', extent=[0, W, 0, H], interpolation='nearest', zorder=1)
    # границы зон — изолинии порогов белыми линиями
    Cf = np.nan_to_num(F, nan=-200)
    cs = ax.contour(GXX, GYY, Cf, levels=[-85, -80, -70, -67, -60],
                    colors=['white']*5, linewidths=1.3, zorder=4)
    ax.clabel(cs, fmt={-70: '−70', -67: '−67', -60: '−60'}, fontsize=7.5,
              inline_spacing=4, colors='#37474f')
    # жирный контур границы уверенного приёма −70
    ax.contour(GXX, GYY, Cf, levels=[-70], colors=['#263238'], linewidths=2.2, zorder=5)
    draw_walls(ax)
    for s in sorted(set(rid), key=lambda z: int(rl.get(z, 0))):
        m = IDG == s
        if m.sum() < 200:
            continue
        cx, cy = GXX[m].mean(), GYY[m].mean()
        ax.text(cx, cy, str(rl.get(s, '?')), ha='center', va='center', fontsize=10,
                fontweight='bold', color='#101720', zorder=9,
                bbox=dict(boxstyle='circle,pad=0.24', fc='white', ec='#101720', lw=1.0, alpha=.95))
    for name, (x, y) in APs.items():
        ax.plot(x, y, marker='o', ms=11, mfc='#ffd400', mec='#101720', mew=1.6, zorder=10)
        ax.annotate(name, (x, y), xytext=(7, 7), textcoords='offset points', fontsize=8,
                    fontweight='bold', color='#101720', zorder=11,
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#101720', alpha=.95))
    handles = [Patch(facecolor=c, edgecolor='#616161', label=n) for c, n in zip(ZCOLS, ZNAMES)]
    leg = ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.002, 1.0),
                    fontsize=10, title='Зоны уровня сигнала · '+band, title_fontsize=11)
    leg.get_title().set_fontweight('bold')
    ax.plot([1, 6], [H-0.8, H-0.8], color='#101720', lw=3, solid_capstyle='butt', zorder=10)
    ax.text(3.5, H-0.4, '5 м', ha='center', fontsize=9, fontweight='bold', zorder=10)
    ax.set_xlim(-0.4, W+0.4); ax.set_ylim(-0.4, H+0.4)   # обрезка строго по зданию
    ax.set_aspect('equal'); ax.set_xticks(np.arange(0, W+1, 5)); ax.set_yticks(np.arange(0, H+1, 5))
    ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=15, fontweight='bold', pad=12)
    fig.text(0.46, 0.015, 'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · '
             'железобетонные стены 200 мм с базальтовым наполнением: затухание 12 дБ @2,4 ГГц / 20 дБ @5 ГГц · '
             'цвет заливки = зона RSSI, белая линия = граница зоны, тёмная линия −70 дБм = граница уверенного приёма',
             ha='center', fontsize=8.5, color='#555')
    fig.tight_layout(rect=[0, 0.035, 0.985, 1])
    fig.savefig(BASE+fname, facecolor='white')
    plt.close(fig)
    print('saved', fname)

draw_map(F24, 'wifi_map_24.png',
         'Зоны покрытия Wi-Fi · 2,4 ГГц — сплошное покрытие рабочих зон', '2,4 ГГц')
draw_map(F5, 'wifi_map_5.png',
         'Зоны покрытия Wi-Fi · 5 ГГц — приоритетный трафик внутри помещений', '5 ГГц')

tot = np.isfinite(F24).sum(); tot5 = np.isfinite(F5).sum()
print('2.4: >=-70 %.1f%% | >=-67 %.1f%%' % (((F24 >= -70).sum()/tot)*100, ((F24 >= -67).sum()/tot)*100))
print('5:   >=-70 %.1f%% | >=-67 %.1f%%' % (((F5 >= -70).sum()/tot5)*100, ((F5 >= -67).sum()/tot5)*100))
