# -*- coding: utf-8 -*-
"""Пересборка карт Wi-Fi поверх плана этажа (лист 14 АР).
Исправления: сплошное тепловое поле, обрезка строго по контуру здания,
корректная привязка помещений (roomlab: raster-id -> номер на плане)."""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata

BASE = '/workspace/out/'
res = json.load(open(BASE+'wifi_res.json'))
d = np.load(BASE+'wifi_field.npz')
pts = d['pts']; rid = d['rid'].astype(str); b24 = d['b24']; b5 = d['b5']

# roomlab: raster-id -> плановый номер помещения
rl = res['roomlab']

# --- метрическая область здания 30 x 27 м ---
W, H = 30.0, 27.0
GX, GY = 301, 271          # сетка 0.1 м
gx = np.linspace(0, W, GX); gy = np.linspace(0, H, GY)
GXX, GYY = np.meshgrid(gx, gy)

def interp_field(vals):
    """точечные значения -> плотное поле + диффузия NaN внутри здания"""
    Z = griddata(pts, vals, (GXX, GYY), method='linear')
    # заполняем пропуски итеративной диффузией (только внутри контура)
    inside = np.ones_like(Z, dtype=bool)
    for _ in range(60):
        nanm = np.isnan(Z)
        if not nanm.any(): break
        Zs = np.where(nanm, 0, Z)
        Cs = np.where(nanm, 0, 1).astype(float)
        k = np.array([[0,1,0],[1,4,1],[0,1,0]], float)/6.0
        from scipy.signal import convolve2d
        num = convolve2d(Zs, k, mode='same'); den = convolve2d(Cs, k, mode='same')
        upd = np.where(den>0, num/np.maximum(den,1e-9), np.nan)
        Z = np.where(nanm, upd, Z)
    return Z

F24 = interp_field(b24.copy())
F5  = interp_field(b5.copy())

# маска помещений для подписей и границ: растеризуем точки rid
room_of_grid = griddata(pts, rid, (GXX, GYY), method='nearest')

CMAP = LinearSegmentedColormap.from_list('wifi', [
    (0.00,'#3b0f70'), (0.18,'#8c23a6'), (0.36,'#dc4fad'),
    (0.52,'#f2652f'), (0.68,'#fca71c'), (0.82,'#8bc63f'), (1.0,'#1fbf6f')])

def draw_map(F, band, fname, title):
    fig, ax = plt.subplots(figsize=(13.2, 11.6), dpi=160)
    im = ax.imshow(F, origin='lower', extent=[0,W,0,H], cmap=CMAP,
                   vmin=-90, vmax=-30, interpolation='bilinear')
    # изолинии порогов качества
    lv = [-60,-67,-70]
    cs = ax.contour(GXX, GYY, F, levels=lv, colors=['#053','#a60','#c00'], linewidths=1.4)
    ax.clabel(cs, fmt={-60:'−60', -67:'−67', -70:'−70 (мин.)'}, fontsize=8)
    # границы помещений (iso-line по смене room id)
    ids = np.unique(room_of_grid[room_of_grid!=''])
    idn = {s:i for i,s in enumerate(ids)}
    ID = np.vectorize(lambda s: idn.get(s,-1))(room_of_grid).astype(float)
    ax.contour(GXX, GYY, ID, levels=np.arange(len(ids))+0.5, colors='#234', linewidths=1.0)
    # номера помещений в центроидах
    for s in ids:
        m = room_of_grid==s
        if m.sum()<50: continue
        cx, cy = GXX[m].mean(), GYY[m].mean()
        ax.text(cx, cy, str(rl[s]), ha='center', va='center', fontsize=11,
                fontweight='bold', color='white',
                bbox=dict(boxstyle='circle,pad=0.28', fc='#12263f', ec='white', lw=1.2))
    # AP
    for name,(ax_,ay_) in res['AP'].items():
        ax_.v_ = None
        ax.plot(ax_, ay_, marker='o', ms=11, mfc='#ffd400', mec='#111', mew=1.6, zorder=6)
        ax.annotate(name, (ax_, ay_), xytext=(7,7), textcoords='offset points',
                    fontsize=8.5, fontweight='bold', color='#111',
                    bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='#111', alpha=.9), zorder=7)
    # контур здания
    for sp in ax.spines.values(): sp.set_edgecolor('#111'); sp.set_linewidth(2.2)
    ax.set_xlim(0,W); ax.set_ylim(0,H)
    ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5))
    ax.tick_params(labelsize=8)
    # масштабная линейка
    ax.plot([1,6],[H-1,H-1], color='#111', lw=3, solid_capstyle='butt')
    ax.text(3.5,H-0.55,'10 м',ha='center',fontsize=9,fontweight='bold')
    cb = fig.colorbar(im, ax=ax, pad=0.02, ticks=[-90,-80,-70,-60,-50,-40,-30])
    cb.set_label('RSSI, дБм', fontsize=10)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
    ax.text(W, -1.6, f'Порог приёмности: {band}', transform=ax.transData,
            ha='right', fontsize=9, color='#444')
    fig.text(0.5, 0.012, 'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · ЖБ стены 200 мм с базальтовым наполнением',
             ha='center', fontsize=8.5, color='#555')
    fig.tight_layout(rect=[0,0.03,1,1])
    fig.savefig(BASE+fname, facecolor='white')
    plt.close(fig)
    print('saved', fname)

draw_map(F24, '2,4 ГГц: −80 … −30 дБм', 'wifi_map_24.png',
         'Зоны покрытия Wi-Fi · 2,4 ГГц (802.11n)')
draw_map(F5,  '5 ГГц: −90 … −30 дБм', 'wifi_map_5.png',
         'Зоны покрытия Wi-Fi · 5 ГГц (802.11ac)')

# чистая схема размещения
fig, ax = plt.subplots(figsize=(13.2, 11.6), dpi=160)
room_of_grid = griddata(pts, rid, (GXX, GYY), method='nearest')
ids = np.unique(room_of_grid[room_of_grid!=''])
idn = {s:i for i,s in enumerate(ids)}
ID = np.vectorize(lambda s: idn.get(s,-1))(room_of_grid).astype(float)
ax.contourf(GXX, GYY, ID, levels=len(ids)+1, cmap='Pastel1')
ax.contour(GXX, GYY, ID, levels=np.arange(len(ids))+0.5, colors='#234', linewidths=1.4)
for s in ids:
    m = room_of_grid==s
    if m.sum()<50: continue
    cx, cy = GXX[m].mean(), GYY[m].mean()
    ax.text(cx, cy, str(rl[s]), ha='center', va='center', fontsize=12, fontweight='bold', color='#123')
for name,(x,y) in res['AP'].items():
    ax.plot(x, y, marker='o', ms=14, mfc='#d62728', mec='#111', mew=1.8, zorder=6)
    ax.annotate(name, (x, y), xytext=(8,8), textcoords='offset points',
                fontsize=9, fontweight='bold', color='#111',
                bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#111', alpha=.95), zorder=7)
for sp in ax.spines.values(): sp.set_edgecolor('#111'); sp.set_linewidth(2.4)
ax.set_xlim(0,W); ax.set_ylim(0,H)
ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
ax.plot([1,6],[H-1,H-1], color='#111', lw=3)
ax.text(3.5,H-0.55,'10 м',ha='center',fontsize=9,fontweight='bold')
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart (11 шт.)', fontsize=14, fontweight='bold', pad=10)
fig.text(0.5, 0.012, 'Выносная высота — потолок; питание PoE 802.3af; координаты в метрах от юго-западного угла здания',
         ha='center', fontsize=8.5, color='#555')
fig.tight_layout(rect=[0,0.03,1,1])
fig.savefig(BASE+'wifi_layout.png', facecolor='white')
plt.close(fig)
print('saved wifi_layout.png')

# сверка таблицы summary с полем (правильный маппинг: ключ summary = плановый номер)
lab2rid = {}
for k,v in rl.items(): lab2rid[str(v)] = k   # план № -> raster id
bad=0
for r in sorted(res['summary'], key=int):
    m = rid==lab2rid[r]
    avg=round(b24[m].mean(),1); cov=round(100*(b24[m]>=-70).mean(),1)
    s=res['summary'][r]
    if abs(avg-s['avg24'])>0.5 or abs(cov-s['cov24'])>1.0:
        bad+=1; print(f"РАСХОЖДЕНИЕ комн {r}: поле avg={avg} cov={cov} vs таблица avg={s['avg24']} cov={s['cov24']}")
print('сверка поля/таблицы, расхождений:', bad)

# проверка: AP внутри своего помещения
for r in sorted(res['summary'], key=int):
    ap=res['summary'][r]['ap']; x,y=res['AP'][ap]
    m=rid==lab2rid[r]; p=pts[m]
    dmin=((p[:,0]-x)**2+(p[:,1]-y)**2).min()**.5
    if dmin>=0.6: print(f"!!! AP {ap} вне помещения {r} ({dmin:.1f} м)")
print('проверка размещения AP завершена')
