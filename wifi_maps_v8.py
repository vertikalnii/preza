# -*- coding: utf-8 -*-
"""Карты Wi-Fi v8: сплошные зоны покрытия. RSSI считается аналитически в каждой
ячейке сетки 0,05 м внутри помещений; обрезка — строго по помещениям (вне здания чисто)."""
import json, math, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from scipy.ndimage import distance_transform_edt, binary_closing

BASE='/workspace/out/'
res=json.load(open(BASE+'wifi_res.json'))
d=np.load(BASE+'wifi_field.npz')
pts,rid=d['pts'],d['rid'].astype(str)
rl=res['roomlab']            # raster-id -> номер на плане

W,H,GX,GY=30.0,27.0,601,541
dx=W/(GX-1); dy=H/(GY-1)
gx=np.linspace(0,W,GX); gy=np.linspace(0,H,GY)
GXX,GYY=np.meshgrid(gx,gy)

ix=(pts[:,0]/dx).round().astype(int); iy=(pts[:,1]/dy).round().astype(int)
IDG=np.full((GY,GX),'',dtype='<U4'); IDG[iy,ix]=rid
inside=IDG!=''

# --- ТОЧНОЕ поле из результата расчёта wifi_rebuild: NN-перенос значений AP-выбора
# на плотную сетку 0,05 м; за стенами значения не распространяются (диффузия только
# внутри каждого помещения) => зоны обрезаются строго по помещениям, без «течений».
from scipy.ndimage import distance_transform_edt, binary_closing
ys,xs=np.nonzero(inside)

def build_field(vals):
    Rf=np.full((GY,GX),np.nan)
    Rf[iy,ix]=vals
    # маска помещений для изолированной диффузии: стены = WM
    walls=json.load(open(BASE+'walls_m.json'))
    WM=np.zeros((GY,GX),bool)
    def put(x,y):
        ii=int(x/dx); jj=int(y/dy)
        if 0<=ii<GX and 0<=jj<GY: WM[jj,ii]=True
    for x0,y0,x1,y1 in walls:
        L=max(abs(x1-x0),abs(y1-y0))
        if L<0.3: continue
        n=int(L/0.05)+1
        for t in np.linspace(0,1,n): put(x0+(x1-x0)*t, y0+(y1-y0)*t)
    for o,c,a,b in [('v',15.99,14.7,25.85),('h',20.15,24.99,29.79),('h',23.1,0.28,2.49)]:
        if o=='v':
            for yy in np.arange(a,b,0.05):
                for w in (0.0,0.05,0.1,0.15): put(c+w,yy)
        else:
            for xx in np.arange(a,b,0.05):
                for w in (0.0,0.05,0.1,0.15): put(xx,c+w)
    WM=binary_closing(WM,np.ones((3,3),bool))
    # диффузия NaN-значений только через НЕ-стеновые ячейки того же помещения
    nanm=np.isnan(Rf)&inside&~WM
    while nanm.any():
        _,idx=distance_transform_edt(nanm,return_indices=True)
        src_ok=~nanm&inside
        # источник должен быть в том же помещении ИЛИ рядом (через двери) — берём ближайший заполненный сосед
        upd=np.where(src_ok,Rf,np.nan)[tuple(idx)]
        newly=nanm&np.isfinite(upd)
        if not newly.any(): break
        Rf[newly]=upd[newly]
        nanm=np.isnan(Rf)&inside&~WM
    # то, что осталось NaN (собственно стены/двери) — средним соседа этого помещения
    nanm=np.isnan(Rf)&inside
    if nanm.any():
        _,idx=distance_transform_edt(nanm,return_indices=True)
        Rf[nanm]=Rf[idx[0][nanm],idx[1][nanm]]
    Rf[~inside]=np.nan
    return Rf

F24=build_field(d['b24'])
F5=build_field(d['b5'])
walls=json.load(open(BASE+'walls_m.json'))

# сверка со средней таблицей summary (rid в точках расчёта = номер на плане)
sm=res['summary']
chk=[]
for plannr in sm:
    m=IDG==str(plannr)
    v=F24[m]; v=v[np.isfinite(v)]
    if v.size>50: chk.append((abs(float(v.mean())-sm[plannr]['avg24']),plannr))
print('сверка со средней таблицей: макс расхождение %.1f дБ (пом. %s)'%max(chk))

BINS=[-np.inf,-85,-80,-70,-67,-60,-50,np.inf]
CATNAMES=['нет покрытия (< −85 дБм)','пограничная (−85…−80)','слабая (−80…−70)',
          'минимум приёмности (−70…−67)','хорошо (−67…−60)','отлично (−60…−50)','превосходно (> −50)']
COLS=['#cfd8dc','#ef9a9a','#ff7043','#ffc107','#9ccc65','#43a047','#1b8a4c']
CMAPC=ListedColormap(COLS)

def cats(F):
    C=np.full(F.shape,np.nan)
    for i,(lo,hi) in enumerate(zip(BINS[:-1],BINS[1:])):
        C[(F>=lo)&(F<hi)]=i
    return C

def draw_walls(ax):
    for x0,y0,x1,y1 in walls:
        L=max(abs(x1-x0),abs(y1-y0))
        if L<0.4: continue
        ax.plot([x0,x1],[y0,y1],color='#3a4a5f',lw=1.0,solid_capstyle='butt',zorder=4)
    wx0=min(min(w[0],w[2]) for w in walls); wx1=max(max(w[0],w[2]) for w in walls)
    wy0=min(min(w[1],w[3]) for w in walls); wy1=max(max(w[1],w[3]) for w in walls)
    ax.add_patch(plt.Rectangle((wx0,wy0),wx1-wx0,wy1-wy0,fill=False,ec='#101720',lw=3.4,zorder=5))

def draw_map(F,fname,title,band):
    fig,ax=plt.subplots(figsize=(14.6,11.0),dpi=150)
    ax.set_facecolor('#eef1f5')
    C=cats(F)
    ax.imshow(C,origin='lower',extent=[0,W,0,H],cmap=CMAPC,vmin=-0.5,vmax=len(COLS)-0.5,
              interpolation='nearest',alpha=0.93,zorder=1)
    Cf=np.nan_to_num(C,nan=-1)
    ax.contour(GXX,GYY,Cf,levels=np.arange(len(COLS))+0.5,colors='white',linewidths=1.0,zorder=3)
    draw_walls(ax)
    for s in set(rid):
        m=IDG==s
        if m.sum()<200: continue
        cx,cy=GXX[m].mean(),GYY[m].mean()
        ax.text(cx,cy,str(rl.get(s,'?')),ha='center',va='center',fontsize=10,fontweight='bold',
                color='#101720',zorder=7,bbox=dict(boxstyle='circle,pad=0.24',fc='white',
                ec='#101720',lw=1.0,alpha=.92))
    for name,(x,y) in res['AP'].items():
        ax.plot(x,y,marker='o',ms=11,mfc='#ffd400',mec='#101720',mew=1.6,zorder=8)
        ax.annotate(name,(x,y),xytext=(7,7),textcoords='offset points',fontsize=8,
                    fontweight='bold',color='#101720',zorder=9,
                    bbox=dict(boxstyle='round,pad=0.2',fc='white',ec='#101720',alpha=.95))
    handles=[Patch(facecolor=c,edgecolor='#777',label=n) for c,n in zip(COLS,CATNAMES)]
    leg=ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(1.002,1.0),fontsize=9.5,
                  title='Зоны уровня сигнала · '+band,title_fontsize=10.5)
    leg.get_title().set_fontweight('bold')
    ax.plot([1,6],[H-0.8,H-0.8],color='#101720',lw=3,solid_capstyle='butt',zorder=9)
    ax.text(3.5,H-0.4,'5 м',ha='center',fontsize=9,fontweight='bold',zorder=9)
    ax.set_xlim(-0.5,W+0.5); ax.set_ylim(-0.5,H+0.5); ax.set_aspect('equal')
    ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
    ax.set_title(title,fontsize=15,fontweight='bold',pad=12)
    fig.text(0.47,0.015,'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · железобетонные '
             'стены 200 мм с базальтовым наполнением: затухание 12 дБ @2,4 ГГц / 20 дБ @5 ГГц · порог −70 дБм',
             ha='center',fontsize=8.5,color='#555')
    fig.tight_layout(rect=[0,0.035,0.985,1])
    fig.savefig(BASE+fname,facecolor='white')
    plt.close(fig)
    print('saved',fname)

draw_map(F24,'wifi_map_24.png','Зоны покрытия Wi-Fi · 2,4 ГГц — основной диапазон (сплошное покрытие рабочих зон)','2,4 ГГц')
draw_map(F5,'wifi_map_5.png','Зоны покрытия Wi-Fi · 5 ГГц — приоритетный трафик (сквозь ЖБ стены −20 дБ/стену)','5 ГГц')

# схема размещения v8 — та же геометрия без heatmap
fig,ax=plt.subplots(figsize=(14.6,11.0),dpi=150)
ax.set_facecolor('#f7f9fb')
ids=sorted(set(rid),key=lambda s:int(rl.get(s,0)))
past=['#dbe7f4','#fdf1d7','#e2f3dd','#fbe3e3','#ece2f8','#dff2f4','#f7ecd9','#e8eef4','#f3e7d3','#e0f0ea','#f4e0ee','#dfe7f2','#fdf7d9','#e6f3da','#fadfdf','#e3ecf8','#efe7da','#dcecf1']
col={s:past[i%len(past)] for i,s in enumerate(ids)}
CG=np.full((GY,GX),np.nan)
for i,s in enumerate(ids): CG[IDG==s]=i
ax.imshow(CG,origin='lower',extent=[0,W,0,H],cmap=ListedColormap([col[s] for s in ids]),
          interpolation='nearest',zorder=0)
draw_walls(ax)
for s in ids:
    m=IDG==s
    if m.sum()<200: continue
    cx,cy=GXX[m].mean(),GYY[m].mean()
    ax.text(cx,cy,str(rl[s]),ha='center',va='center',fontsize=11,fontweight='bold',color='#101720',
            zorder=6,bbox=dict(boxstyle='circle,pad=0.26',fc='white',ec='#101720',lw=1.1,alpha=.95))
for name,(x,y) in res['AP'].items():
    ax.plot(x,y,marker='o',ms=14,mfc='#d62728',mec='#101720',mew=1.8,zorder=7)
    ax.annotate(name,(x,y),xytext=(8,8),textcoords='offset points',fontsize=8.5,fontweight='bold',
                color='#101720',zorder=8,bbox=dict(boxstyle='round,pad=0.22',fc='white',ec='#101720',alpha=.95))
ax.set_xlim(-0.5,W+0.5); ax.set_ylim(-0.5,H+0.5); ax.set_aspect('equal')
ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
ax.grid(color='#d7dde5',lw=0.5,zorder=0)
ax.plot([1,6],[H-0.8,H-0.8],color='#101720',lw=3,zorder=8)
ax.text(3.5,H-0.4,'5 м',ha='center',fontsize=9,fontweight='bold',zorder=8)
ax.set_title('Схема размещения точек доступа Eltex WEP-2AC Smart (11 шт.)',fontsize=15,fontweight='bold',pad=12)
fig.text(0.5,0.015,'Монтаж на потолок h≈3,5–4,0 м · PoE 802.3af · координаты от юго-западного угла здания · контур 30×27 м по листу 14 АР',
         ha='center',fontsize=8.5,color='#555')
fig.tight_layout()
fig.savefig(BASE+'wifi_layout.png',facecolor='white')
plt.close(fig)
print('saved wifi_layout.png')

tot=np.isfinite(F24).sum()
print('2.4: >=-70 %.1f%% | >=-67 %.1f%%'%(((F24>=-70).sum()/tot)*100,((F24>=-67).sum()/tot)*100))
tot5=np.isfinite(F5).sum()
print('5:   >=-70 %.1f%% | >=-67 %.1f%%'%(((F5>=-70).sum()/tot5)*100,((F5>=-67).sum()/tot5)*100))
