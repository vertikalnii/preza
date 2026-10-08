# -*- coding: utf-8 -*-
"""Карты Wi-Fi v6: явные зоны покрытия (прозрачные цветовые слои по порогам),
обрезка поля строго по помещениям (без «лишних областей» вне здания),
стены чертежа как фон, план этажа 30x27 м."""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

BASE = '/workspace/out/'
res = json.load(open(BASE+'wifi_res.json'))
d = np.load(BASE+'wifi_field.npz')
pts, rid, b24, b5 = d['pts'], d['rid'].astype(str), d['b24'], d['b5']
rmeta = d['raster_meta']; rast_res, X0, Y0, NX, NY = [float(v) for v in rmeta]
NXi, NYi = int(NX), int(NY)

rl = res['roomlab']                       # raster-id -> номер на плане
lab2rid = {str(v): k for k, v in rl.items()}  # план № -> raster id

# --- растеризуем метки помещений и RSSI в общую сетку 0.1 м, область = здание ---
W, H = 30.0, 27.0
GX, GY = 301, 271
gx = np.linspace(0, W, GX); gy = np.linspace(0, H, GY)
GXX, GYY = np.meshgrid(gx, gy)

IDG = np.full((GY, GX), '', dtype='<U4')   # метка помещения (raster id) или ''
for s in set(rid):
    m = rid == s
    ix = ((pts[m,0]-0)/ (W/(GX-1))).round().astype(int)
    iy = ((pts[m,1])/ (H/(GY-1))).round().astype(int)
    ix = np.clip(ix, 0, GX-1); iy = np.clip(iy, 0, GY-1)
    IDG[iy, ix] = s

def field(vals):
    Z = np.full((GY, GX), np.nan)
    ix = ((pts[:,0])/(W/(GX-1))).round().astype(int)
    iy = ((pts[:,1])/(H/(GY-1))).round().astype(int)
    Z[iy, ix] = vals
    # диффузия только внутри помещений (IDG != '')
    inside = IDG != ''
    from scipy.signal import convolve2d
    for _ in range(120):
        nanm = np.isnan(Z) & inside
        if not nanm.any(): break
        Zs = np.where(np.isnan(Z), 0, Z); Cs = (~np.isnan(Z)).astype(float)
        k = np.array([[0,1,0],[1,4,1],[0,1,0]], float)/6.0
        num = convolve2d(Zs, k, mode='same'); den = convolve2d(Cs, k, mode='same')
        upd = np.where(den>0, num/np.maximum(den,1e-9), np.nan)
        Z = np.where(nanm & ~np.isnan(upd), upd, Z)
    # ОБРЕЗКА: значение только внутри помещений — никаких зон вне здания
    Z[~inside] = np.nan
    return Z

F24 = field(b24.copy()); F5 = field(b5.copy())

# --- фон: стены из чертежа (walls_m.json) ---
walls = json.load(open(BASE+'walls_m.json'))

def draw_walls(ax):
    for x0,y0,x1,y1 in walls:
        L = max(abs(x1-x0), abs(y1-y0))
        if L < 0.4: continue
        ax.plot([x0,x1],[y0,y1], color='#3a4a5f', lw=1.1, solid_capstyle='butt', zorder=3)
    # контур здания: extreme bbox стен
    wx0=min(min(w[0],w[2]) for w in walls); wx1=max(max(w[0],w[2]) for w in walls)
    wy0=min(min(w[1],w[3]) for w in walls); wy1=max(max(w[1],w[3]) for w in walls)
    ax.add_patch(plt.Rectangle((wx0,wy0), wx1-wx0, wy1-wy0, fill=False,
                 ec='#101720', lw=3.2, zorder=4))

# --- категории зон покрытия ---
BINS = [-np.inf, -85, -80, -70, -67, -60, -50, np.inf]
CATNAMES = ['нет покрытия (<−85)', 'крайняя (−85…−80)', 'слабая (−80…−70)',
            'минимум (−70…−67)', 'хорошо (−67…−60)', 'отлично (−60…−50)', 'превосходно (>−50)']
COLS = ['#cfd8dc', '#ef9a9a', '#ff7043', '#ffc107', '#9ccc65', '#43a047', '#1b8a4c']
CMAPC = ListedColormap(COLS)

def cat_field(F):
    C = np.full(F.shape, np.nan)
    for i,(lo,hi) in enumerate(zip(BINS[:-1], BINS[1:])):
        m = (F>=lo) & (F<hi)
        C[m] = i
    return C

def draw_map(F, band, fname, title):
    fig, ax = plt.subplots(figsize=(13.6, 11.4), dpi=170)
    # подложка «вне здания» — светлый нейтральный, чтобы было видно что обрезка чистая
    ax.set_facecolor('#f2f4f7')
    C = cat_field(F)
    im = ax.imshow(C, origin='lower', extent=[0,W,0,H], cmap=CMAPC,
                   vmin=-0.5, vmax=len(COLS)-0.5, interpolation='nearest', alpha=0.88, zorder=1)
    draw_walls(ax)
    # подписи помещений
    for s in set(rid):
        m = IDG == s
        if m.sum() < 60: continue
        cx, cy = GXX[m].mean(), GYY[m].mean()
        ax.text(cx, cy, str(rl.get(s,'?')), ha='center', va='center', fontsize=10.5,
                fontweight='bold', color='#101720', zorder=6,
                bbox=dict(boxstyle='circle,pad=0.26', fc='white', ec='#101720', lw=1.1, alpha=.92))
    # AP
    for name,(x,y) in res['AP'].items():
        ax.plot(x, y, marker='o', ms=12, mfc='#ffd400', mec='#101720', mew=1.7, zorder=7)
        ax.annotate(name, (x,y), xytext=(8,8), textcoords='offset points', fontsize=8.5,
                    fontweight='bold', color='#101720', zorder=8,
                    bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='#101720', alpha=.95))
    # границы зон — тонкие белые линии между категориями
    cs = ax.contour(np.arange(GX), np.arange(GY), np.nan_to_num(C, nan=-1),
                     levels=np.arange(len(COLS))+0.5, colors=['white']*len(COLS),
                     linewidths=[0.8]*len(COLS))
    ax.set_xlim(-0.6, W+0.6); ax.set_ylim(-0.6, H+0.6)
    ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5))
    ax.tick_params(labelsize=8)
    ax.grid(color='#d7dde5', lw=0.5, zorder=0)
    # легенда зон
    handles = [Patch(facecolor=c, edgecolor='#666', label=n) for c,n in zip(COLS, CATNAMES)]
    leg = ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.005, 1.0),
                    fontsize=9, title='Зона уровня сигнала', title_fontsize=10)
    leg.get_title().set_fontweight('bold')
    # масштабная линейка
    ax.plot([1,6],[H-0.8,H-0.8], color='#101720', lw=3, solid_capstyle='butt', zorder=8)
    ax.text(3.5,H-0.35,'5 м',ha='center',fontsize=9,fontweight='bold',zorder=8)
    ax.set_title(title, fontsize=15, fontweight='bold', pad=12)
    fig.text(0.5, 0.012, 'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · '
             'железобетонные стены 200 мм с базальтовым наполнением · затухание стены 12 дБ @2,4 ГГц / 20 дБ @5 ГГц',
             ha='center', fontsize=8.5, color='#555')
    fig.tight_layout(rect=[0,0.03,0.98,1])
    fig.savefig(BASE+fname, facecolor='white', bbox_inches=None)
    plt.close(fig)
    print('saved', fname)

draw_map(F24, '2,4 ГГц', 'wifi_map_24.png', 'Зоны покрытия Wi-Fi · 2,4 ГГц (802.11n) — сплошное покрытие рабочих помещений')
draw_map(F5,  '5 ГГц',  'wifi_map_5.png',  'Зоны покрытия Wi-Fi · 5 ГГц (802.11ac) — сквозь ЖБ стены сигнал снижается на ~8 дБ сильнее')

# --- чистая схема размещения v6: та же обрезка, без heatmap ---
fig, ax = plt.subplots(figsize=(13.6, 11.4), dpi=170)
ax.set_facecolor('#f7f9fb')
# мягкая заливка помещений пастельными тонами
past = ['#dbe7f4','#fdf1d7','#e2f3dd','#fbe3e3','#ece2f8','#dff2f4','#f7ecd9','#e6e6e6']
ids = sorted(set(rid), key=lambda s:int(rl.get(s,0)))
colmap = {}
for i,s in enumerate(ids): colmap[s]=past[i%len(past)]
CG = np.full((GY,GX), np.nan)
for i,s in enumerate(ids):
    m = IDG==s
    CG[m]=i
im = ax.imshow(CG, origin='lower', extent=[0,W,0,H],
               cmap=ListedColormap([colmap[s] for s in ids]), interpolation='nearest', zorder=0)
draw_walls(ax)
for s in ids:
    m = IDG==s
    if m.sum()<60: continue
    cx, cy = GXX[m].mean(), GYY[m].mean()
    ax.text(cx, cy, str(rl[s]), ha='center', va='center', fontsize=11, fontweight='bold',
            color='#101720', zorder=6,
            bbox=dict(boxstyle='circle,pad=0.26', fc='white', ec='#101720', lw=1.1, alpha=.95))
for name,(x,y) in res['AP'].items():
    ax.plot(x, y, marker='o', ms=15, mfc='#d62728', mec='#101720', mew=1.9, zorder=7)
    ax.annotate(name, (x,y), xytext=(9,9), textcoords='offset points', fontsize=9,
                fontweight='bold', color='#101720', zorder=8,
                bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#101720', alpha=.95))
ax.set_xlim(-0.6, W+0.6); ax.set_ylim(-0.6, H+0.6)
ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
ax.grid(color='#d7dde5', lw=0.5, zorder=0)
ax.plot([1,6],[H-0.8,H-0.8], color='#101720', lw=3, zorder=8)
ax.text(3.5,H-0.35,'5 м',ha='center',fontsize=9,fontweight='bold',zorder=8)
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart (11 шт.)', fontsize=15, fontweight='bold', pad=12)
fig.text(0.5, 0.012, 'Монтаж на потолок h≈3,5–4,0 м; питание PoE 802.3af; координаты от юго-западного угла здания; контур 30×27 м по листу 14 АР',
         ha='center', fontsize=8.5, color='#555')
fig.tight_layout()
fig.savefig(BASE+'wifi_layout.png', facecolor='white')
plt.close(fig)
print('saved wifi_layout.png')
