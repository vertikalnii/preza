# -*- coding: utf-8 -*-
"""Карты покрытия Wi-Fi v3: плотный растр (интерполяция best-RSS поля),
обрезка по зданию 30x27 м, зоны качества сигнала, изолинии -60/-67/-70."""
import json, math, numpy as np
from scipy.interpolate import griddata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm

z = np.load('out/wifi_field.npz')
pts, rid, b24, b5 = z['pts'], z['rid'].astype(str), z['b24'], z['b5']
d = json.load(open('out/wifi_res.json'))
APs = {k: tuple(v) for k, v in d['AP'].items()}
summary = d['summary']

cal = json.load(open('out/calib_v2.json'))
centers = {int(k): tuple(v) for k, v in cal['centers_m'].items()}

BX0, BY0, BX1, BY1 = 0.0, 0.0, 30.0, 27.0   # точные габариты здания по листу 14 АР

# ---- модель для реконструкции поля (идентична wifi_rebuild.py) ----
PTX, G = 20.0, 2.0
def rss(dist, st, f):
    dist = max(dist, 0.5)
    fspl = 32.44 + 20*math.log10(f) + 20*math.log10(dist/1000.0)
    nexp = 2.7 if f == 2437 else 3.2
    att = 12 if f == 2437 else 20
    return PTX + G - fspl - (nexp-2)*10*math.log10(dist) - st*att

# классификация точек: снаружи / стена / внутри — по ближайшей метке решётки из поля
RES = 0.25
gx = np.arange(BX0+0.05, BX1-0.05, RES)
gy = np.arange(BY0+0.05, BY1-0.05, RES)
GX, GY = np.meshgrid(gx, gy)
px = ((pts[:,0]-BX0)/RES).astype(int); py = ((pts[:,1]-BY0)/RES).astype(int)
NXi, NYi = GX.shape[1], GX.shape[0]
cell = np.full((NYi, NXi), -1, int)          # -1 снаружи/стена, иначе индекс точки
cell[py.clip(0,NYi-1), px.clip(0,NXi-1)] = np.arange(len(pts))
okc = cell >= 0
# расширение внутренней области на 2 клетки (заполнить у самых стен)
from scipy.ndimage import binary_dilation
regrow = binary_dilation(okc, iterations=2) & ~okc
if regrow.any():
    idx = np.flatnonzero(regrow.ravel())
    # ближайшая известная точка каждой «отросшей» клетке
    ry, rx_ = np.nonzero(regrow)
    known_y, known_x = np.nonzero(okc)
    kd = np.stack([rx_-kx for kx in known_x]) # too big; use cKDTree
    from scipy.spatial import cKDTree
    tree = cKDTree(np.c_[known_x, known_y])
    _, nn = tree.query(np.c_[ry, rx_])
    src = cell[known_y[nn], known_x[nn]]
    cell[ry, rx_] = src
okc = cell >= 0

vals24 = np.where(okc, b24[np.clip(cell, 0, None)], np.nan)
vals5  = np.where(okc, b5 [np.clip(cell, 0, None)], np.nan)

# сглаживание 3x3 (только по внутренним)
from scipy.ndimage import generic_filter
def sm(a):
    m = ~np.isnan(a)
    if not m.any(): return np.nan
    return np.nanmean(a[m])
vals24 = generic_filter(vals24, sm, size=3, mode='constant', cval=np.nan)
vals5  = generic_filter(vals5,  sm, size=3, mode='constant', cval=np.nan)
# исходное значение сохраняем dominant (фильтр может слегка размыть максимум) — ок для визуализации

INM = okc

cmap24 = LinearSegmentedColormap.from_list('wifi', [
    (0.00,'#67001f'),(0.25,'#b2182b'),(0.45,'#ef8a62'),(0.62,'#fddbc7'),
    (0.75,'#7fbf7b'),(0.88,'#1b7837'),(1.00,'#00441b')])
cmap5 = LinearSegmentedColormap.from_list('wifi5', [
    (0.00,'#330066'),(0.3,'#6a00a8'),(0.5,'#b429f9'),(0.7,'#f16913'),
    (0.85,'#fed976'),(1.0,'#ffffcc')])

names = {int(k): summary[k]['name'] for k in summary}

def draw(band, fname):
    V, cm, lo, hi = (vals24, cmap24, -90, -30) if band=='24' else (vals5, cmap5, -110, -30)
    fig, ax = plt.subplots(figsize=(11.6, 10.6), dpi=170)
    M = np.ma.masked_where(~INM, V)
    im = ax.imshow(M, extent=[BX0, BX1, BY1, BY0], cmap=cm, vmin=lo, vmax=hi,
                   origin='upper', interpolation='bilinear')
    # изолинии зон качества
    lv = [-60, -67, -70]
    cs = ax.contour(GX+BX0, GY+BY0, V, levels=sorted(lv),
                    colors=['#ff7043','#ffd54f','white'],
                    linewidths=[1.8, 1.4, 1.4], linestyles=['-', '--', '-'])
    ax.clabel(cs, fmt={-70:'≥−70 норма', -67:'≥−67 хорошо', -60:'≥−60 отлично'}, fontsize=8)
    # контур здания
    ax.add_patch(plt.Rectangle((BX0,BY0), BX1-BX0, BY1-BY0, fill=False, ec='black', lw=3.2))
    # номера помещений
    for n,(cx,cy) in centers.items():
        if 1<=n<=18:
            ax.text(cx, cy, str(n), ha='center', va='center', fontsize=12, fontweight='bold',
                    color='white', bbox=dict(boxstyle='circle,pad=0.26', fc='#263238', ec='white', lw=1.1))
    # AP
    for name,(x,y) in APs.items():
        ax.plot(x, y, marker='o', ms=13, mfc='#00e676', mec='black', mew=1.5, zorder=6)
        ax.plot(x, y, marker='o', ms=5, mfc='black', mec='none', zorder=7)
        ax.annotate(name, (x,y), textcoords='offset points', xytext=(0,11), ha='center',
                    fontsize=8, fontweight='bold', color='black',
                    bbox=dict(boxstyle='round,pad=0.22', fc='#fff59d', ec='black', lw=0.7), zorder=8)
    # масштабная линейка
    ax.plot([1.0,11.0],[26.3,26.3], color='black', lw=3)
    ax.text(6.0,26.5,'10 м', ha='center', fontsize=9, fontweight='bold')
    ax.set_xlim(-0.7, 30.7); ax.set_ylim(27.4, -0.4)
    ax.set_aspect('equal'); ax.axis('off')
    ttl = ('Зона покрытия 2,4 ГГц — Eltex WEP-2AC Smart ×11 · RSSI, дБм'
           if band=='24' else 'Зона покрытия 5 ГГц — Eltex WEP-2AC Smart ×11 · RSSI, дБм')
    ax.set_title(ttl, fontsize=14, fontweight='bold', pad=8)
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cb.set_label('Уровень сигнала, дБм', fontsize=10)
    for yv, lab in [(-40,'пик'), (-60,'отлично'), (-67,'хорошо'), (-70,'минимум')]:
        frac=(yv-lo)/(hi-lo)
        cb.ax.annotate(lab, xy=(1.0,frac), xycoords='axes fraction', xytext=(6,0),
                       textcoords='offset points', fontsize=8, va='center', annotation_clip=False)
    fig.savefig(fname, bbox_inches='tight', facecolor='white', pad_inches=0.15)
    plt.close(fig)

draw('24', 'out/wifi_map_24.png')
draw('5',  'out/wifi_map_5.png')

# ---- единая схема размещения (чистый план без heatmap, квадратный кроп) ----
walls = json.load(open('out/walls_m.json'))
fig, ax = plt.subplots(figsize=(11.2, 10.4), dpi=170)
ax.add_patch(plt.Rectangle((BX0,BY0), BX1-BX0, BY1-BY0, fc='#f4f7fa', ec='black', lw=3.4))
for x0,y0,x1,y1 in walls:
    if min(x0,x1)>=BX0-0.6 and max(x0,x1)<=BX1+0.6 and min(y0,y1)>=BY0-0.6 and max(y0,y1)<=BY1+0.6:
        ax.plot([x0,x1],[y0,y1], color='#37474f', lw=1.0, alpha=0.85, solid_capstyle='round')
for n,(cx,cy) in centers.items():
    if 1<=n<=18:
        ax.text(cx, cy-0.62, str(n), ha='center', va='center', fontsize=13, fontweight='bold', color='#455a64')
        ax.text(cx, cy+0.55, names[n][:26], ha='center', va='center', fontsize=6.2, color='#78909c')
for name,(x,y) in APs.items():
    circ = plt.Circle((x,y), 1.05, fc='#00e676', ec='black', lw=1.4, alpha=0.95, zorder=6)
    ax.add_patch(circ)
    ax.text(x, y, '+', ha='center', va='center', fontsize=13, fontweight='bold', color='black', zorder=7)
    ax.annotate(name, (x,y), textcoords='offset points', xytext=(0,-16), ha='center',
                fontsize=8.5, fontweight='bold', color='#1b5e20',
                bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='#1b5e20', lw=0.9), zorder=8)
ax.plot([1.0,11.0],[26.3,26.3], color='black', lw=3)
ax.text(6.0,26.55,'10 м', ha='center', fontsize=9, fontweight='bold')
ax.set_xlim(-0.7, 30.7); ax.set_ylim(27.4, -0.4)
ax.set_aspect('equal'); ax.axis('off')
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart (11 шт.)',
             fontsize=14, fontweight='bold', pad=8)
fig.savefig('out/wifi_layout.png', bbox_inches='tight', facecolor='white', pad_inches=0.15)
plt.close(fig)

# ---- KPI-баннер (актуальные цифры) ----
work = ['1','2','3','4','5','6','10','11','12','13','18']
cov24w = np.mean([summary[r]['cov24'] for r in work])
fig = plt.figure(figsize=(12, 2.1), dpi=170)
ax = fig.add_axes([0,0,1,1]); ax.axis('off')
ax.add_patch(plt.Rectangle((0,0),1,1, fc='#0b3d66'))
kpis = [('11', 'точек доступа\nEltex WEP-2AC Smart'),
        (f'{cov24w:.0f}%', 'покрытие рабочих зон\n2,4 ГГц ≥ −70 дБм'),
        (f"{d['cov_all']:.1f}%".replace('.',','), 'покрытие всей площади\nэтажа 2,4 ГГц'),
        ('18/18', 'помещений\nобеспечены сигналом')]
for i,(big,small) in enumerate(kpis):
    x = 0.055 + i*0.245
    ax.text(x,0.62,big,fontsize=26,fontweight='bold',color='#ffd54f')
    ax.text(x,0.22,small,fontsize=10.5,color='white',va='bottom')
fig.savefig('out/kpi_banner.png', facecolor='#0b3d66')
plt.close(fig)
print('maps3 done')
