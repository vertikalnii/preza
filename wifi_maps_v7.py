# -*- coding: utf-8 -*-
"""Карты Wi-Fi v7: сплошные зоны покрытия (NN-классификация точек расчёта),
обрезка строго по помещениям, стены чертежа поверх, план 30x27 м."""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

BASE='/workspace/out/'
res=json.load(open(BASE+'wifi_res.json'))
d=np.load(BASE+'wifi_field.npz')
pts,rid,b24,b5=d['pts'],d['rid'].astype(str),d['b24'],d['b5']
rl=res['roomlab']

W,H,GX,GY=30.0,27.0,601,541
gx=np.linspace(0,W,GX); gy=np.linspace(0,H,GY)
GXX,GYY=np.meshgrid(gx,gy)
dx=(W/(GX-1)); dy=(H/(GY-1))

ix=((pts[:,0])/dx).round().astype(int)
iy=((pts[:,1])/dy).round().astype(int)

IDG=np.full((GY,GX),'',dtype='<U4')
IDG[iy,ix]=rid
R=np.full((GY,GX),-200.)
np.maximum.at(R,(iy,ix),b24)
R5=np.full((GY,GX),-200.)
np.maximum.at(R5,(iy,ix),b5)

def nearest(mask_src, val):
    """val с mask_src распространить на всю сетку NN-спуском"""
    V=val.copy(); M=~mask_src
    from scipy.ndimage import distance_transform_edt
    _,idx=distance_transform_edt(M,return_indices=True,return_distances=False)
    return V[tuple(idx)]

F24=nearest(IDG!='',np.where(R>-199,R,np.nan))
F5 =nearest(IDG!='',np.where(R5>-199,R5,np.nan))
# NaN внутри помещений (стены/двери) — тоже заполнить ближайшим значением этого помещения
def fill_inside(F):
    nanm=np.isnan(F)&(IDG!='')
    if nanm.any():
        from scipy.ndimage import distance_transform_edt
        _,idx=distance_transform_edt(nanm,return_indices=True)
        Fc=F.copy(); Fc[nanm]=F[idx[0][nanm],idx[1][nanm]]
        return Fc
    return F
F24=fill_inside(F24); F5=fill_inside(F5)
# ОБРЕЗКА: вне помещений — NaN
F24[IDG=='']=np.nan; F5[IDG=='']=np.nan

walls=json.load(open(BASE+'walls_m.json'))
def draw_walls(ax):
    for x0,y0,x1,y1 in walls:
        L=max(abs(x1-x0),abs(y1-y0))
        if L<0.4: continue
        ax.plot([x0,x1],[y0,y1],color='#3a4a5f',lw=1.0,solid_capstyle='butt',zorder=4)
    wx0=min(min(w[0],w[2]) for w in walls); wx1=max(max(w[0],w[2]) for w in walls)
    wy0=min(min(w[1],w[3]) for w in walls); wy1=max(max(w[1],w[3]) for w in walls)
    ax.add_patch(plt.Rectangle((wx0,wy0),wx1-wx0,wy1-wy0,fill=False,ec='#101720',lw=3.4,zorder=5))

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

def draw_map(F,fname,title,band):
    fig,ax=plt.subplots(figsize=(14.4,11.2),dpi=150)
    ax.set_facecolor('#eef1f5')
    C=cats(F)
    ax.imshow(C,origin='lower',extent=[0,W,0,H],cmap=CMAPC,vmin=-0.5,vmax=len(COLS)-0.5,
              interpolation='nearest',alpha=0.92,zorder=1)
    # границы зон — белые изолинии по классам
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
    ax.set_xlim(-0.5,W+0.5); ax.set_ylim(-0.5,H+0.5)
    ax.set_xticks(np.arange(0,W+1,5)); ax.set_yticks(np.arange(0,H+1,5)); ax.tick_params(labelsize=8)
    ax.set_aspect('equal')
    ax.set_title(title,fontsize=15,fontweight='bold',pad=12)
    fig.text(0.47,0.015,'УТЦ · лист 14 «План этажа» (27.03.26 АР) · Eltex WEP-2AC Smart ×11 · железобетонные '
             'стены 200 мм с базальтовым наполнением: затухание 12 дБ @2,4 ГГц / 20 дБ @5 ГГц · порог приёмности −70 дБм',
             ha='center',fontsize=8.5,color='#555')
    fig.tight_layout(rect=[0,0.035,0.985,1])
    fig.savefig(BASE+fname,facecolor='white')
    plt.close(fig)
    print('saved',fname)

draw_map(F24,'wifi_map_24.png','Зоны покрытия Wi-Fi · 2,4 ГГц — основной диапазон (сплошное покрытие рабочих зон)','2,4 ГГц')
draw_map(F5,'wifi_map_5.png','Зоны покрытия Wi-Fi · 5 ГГц — приоритетный трафик (сквозь ЖБ стены −20 дБ/стену)','5 ГГц')

# чистая схема размещения v7
fig,ax=plt.subplots(figsize=(14.4,11.2),dpi=150)
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
    nm=str(rl[s])
    ax.text(cx,cy,nm,ha='center',va='center',fontsize=11,fontweight='bold',color='#101720',zorder=6,
            bbox=dict(boxstyle='circle,pad=0.26',fc='white',ec='#101720',lw=1.1,alpha=.95))
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

# контроль: доли зон на картах (внутри помещений)
for F,nm in [(F24,'2.4'),(F5,'5')]:
    tot=np.isfinite(F).sum()
    ok=(F>=-70).sum()/tot*100
    print(f'{nm}: >=-70 {ok:.1f}% площади помещений')
