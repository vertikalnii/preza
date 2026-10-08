# -*- coding: utf-8 -*-
"""Карты покрытия v4: сплошные тепловые зоны (интерполированное поле), обрезка по зданию, изолинии качества."""
import json, numpy as np
from scipy.ndimage import gaussian_filter, binary_closing
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.patches import Polygon as MplPoly
plt.rcParams['font.family']='DejaVu Sans'

ff=np.load("/tmp/field_final.npz")
F24,F5,RL,IN = ff["F24"],ff["F5"],ff["RL"].astype(int),ff["IN"]
x0,y0,step,W,H = [float(v) if i<3 else int(v) for i,v in enumerate(ff["meta"])]
GX = x0 + (np.arange(W)+0.5)*step
GY = y0 + (np.arange(H)+0.5)*step

walls=json.load(open("/tmp/walls_in.json"))
res=json.load(open("out/wifi_res.json")); summ=res["summary"]; APs={k:tuple(v) for k,v in res["AP"].items()}
cent=json.load(open("/tmp/centers_from_field.json"))["cent"]

# маска здания: замкнутый контур 30x27 с небольшим внутренним буфером наружу
def building_mask():
    m=np.zeros((H,W),bool)
    ix=(GX>=0)&(GX<=30); iy=(GY>=0)&(GY<=27)
    m[np.ix_(iy,ix)]=True
    return m
BM=building_mask()
Mshow = IN & BM
Mshow = binary_closing(Mshow, structure=np.ones((3,3)))

cmap24=LinearSegmentedColormap.from_list('w24',['#7f0000','#b32d1a','#e0652a','#f5a623','#ffd94d','#b8d94a','#5cb85c','#2e8b57'])
cmap5 =LinearSegmentedColormap.from_list('w5', ['#3b0764','#5b21b6','#7c3aed','#a78bfa','#c4b5fd','#f0abfc','#fb923c','#dc2626'])
B24=[-90,-80,-75,-70,-67,-60,-50,-40,-25]; L24=['<-80','−80…−75','−75…−70','−70…−67','−67…−60','−60…−50','−50…−40','>−40']
B5 =[ -90,-80,-75,-70,-67,-60,-50,-40,-25]
norm24=BoundaryNorm(B24,len(L24)); norm5=BoundaryNorm(B5,len(L24))

def base(ax):
    ax.set_xlim(-0.5,30.5); ax.set_ylim(27.5,-0.5); ax.set_aspect('equal'); ax.axis('off')
    # контур здания
    ax.add_patch(MplPoly([[0,0],[30,0],[30,27],[0,27]], closed=True, fill=False, ec='#102a43', lw=3.2, zorder=6))

def draw_walls(ax,lw=0.8,alpha=0.6):
    for wx0,wy0,wx1,wy1 in walls:
        ax.plot([wx0,wx1],[wy0,wy1],color='#37474f',lw=lw,alpha=alpha,zorder=4,solid_capstyle='round')

def draw_numbers(ax):
    for n,(cx,cy) in cent.items():
        if 1<=int(n)<=18:
            ax.text(cx,cy,str(n),ha='center',va='center',fontsize=10,fontweight='bold',color='white',zorder=8,
                    bbox=dict(boxstyle='circle,pad=0.18',fc='#263238',ec='white',lw=1.0,alpha=0.92))

def draw_aps(ax):
    for name,(x,y) in APs.items():
        ax.add_patch(plt.Circle((x,y),0.75,fc='#00e676',ec='#0d1b12',lw=1.6,zorder=9))
        ax.plot(x,y,marker='+',ms=7,mew=2,color='#0d1b12',zorder=10)
        ax.annotate(name,(x,y),xytext=(0,11),textcoords='offset points',ha='center',fontsize=7.5,fontweight='bold',zorder=10,
                    bbox=dict(boxstyle='round,pad=0.2',fc='#fffde7',ec='#33691e',lw=0.8))

def scalebar(ax):
    ax.plot([1,11],[26.55,26.55],color='#102a43',lw=3,zorder=9)
    for xx in (1,6,11): ax.plot([xx,xx],[26.4,26.7],color='#102a43',lw=2,zorder=9)
    ax.text(6,26.1,'масштаб 10 м',ha='center',fontsize=8,fontweight='bold',color='#102a43',zorder=9)

def legend(ax,title,norm,cmap,labels):
    from matplotlib.cm import ScalarMappable
    cb=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,pad=0.02,shrink=0.85,ticks=[(b+i+0.5)/len(labels) for i,b in enumerate(range(len(labels)))] if False else None)
    # дискретная легенда
    handles=[plt.Rectangle((0,0),1,1,fc=cmap(norm((B24[i]+B24[i+1])/2))) for i in range(len(labels))]
    leg=ax.legend(handles,labels,loc='lower left',bbox_to_anchor=(-0.02,-0.005),fontsize=7.2,title=title,framealpha=0.95,title_fontsize=8)
    leg.set_zorder(20)

def masked_field(S):
    A=np.ma.masked_where(~Mshow,S)
    A=gaussian_filter(np.where(Mshow,S,np.nanmean(S)),sigma=1.2)
    return np.ma.masked_where(~Mshow,A)

# ---- карта 2.4 ГГц ----
fig,ax=plt.subplots(figsize=(12.6,11.4),dpi=170)
A=masked_field(F24)
ax.imshow(A,extent=[GX[0]-step/2,GX[-1]+step/2,GY[-1]+step/2,GY[0]-step/2],origin='upper',cmap=cmap24,norm=norm24,zorder=1,interpolation='bilinear')
# изолинии зон качества
for thr,col in [(-70,'#102a43'),(-67,'#0d47a1'),(-60,'#1b5e20')]:
    cs=ax.contour(GX,GY,F24,levels=[thr],colors=[col],linewidths=[1.6],linestyles=['--'],zorder=5)
    for seg in cs.allsegs[0]:
        if len(seg)>8:
            x_,y_=seg[len(seg)//3]
            ax.text(x_,y_,f'{thr:g} дБм',fontsize=7,color=col,fontweight='bold',ha='center',va='bottom',zorder=6,
                    bbox=dict(boxstyle='round,pad=0.15',fc='white',ec=col,lw=0.6,alpha=0.9))
draw_walls(ax); base(ax); draw_numbers(ax); draw_aps(ax); scalebar(ax)
legend(ax,'RSSI 2,4 ГГц, дБм',norm24,cmap24,L24)
ax.set_title('Зоны покрытия Wi-Fi 2,4 ГГц — Eltex WEP-2AC Smart ×11',fontsize=13,fontweight='bold',color='#102a43',pad=10)
fig.savefig('out/wifi_map_24.png',bbox_inches='tight',facecolor='white',pad_inches=0.12); plt.close(fig)

# ---- карта 5 ГГц ----
fig,ax=plt.subplots(figsize=(12.6,11.4),dpi=170)
A=masked_field(F5)
ax.imshow(A,extent=[GX[0]-step/2,GX[-1]+step/2,GY[-1]+step/2,GY[0]-step/2],origin='upper',cmap=cmap5,norm=norm5,zorder=1,interpolation='bilinear')
for thr,lab,col in [(-70,'−70 дБм','#102a43'),(-67,'−67 дБм','#0d47a1'),(-60,'−60 дБм','#1b5e20')]:
    cs=ax.contour(GX,GY,F5,levels=[thr],colors=[col],linewidths=[1.4],linestyles=['--'],zorder=5)
draw_walls(ax); base(ax); draw_numbers(ax); draw_aps(ax); scalebar(ax)
legend(ax,'RSSI 5 ГГц, дБм',norm5,cmap5,L24)
ax.set_title('Зоны покрытия Wi-Fi 5 ГГц — Eltex WEP-2AC Smart ×11',fontsize=13,fontweight='bold',color='#102a43',pad=10)
fig.savefig('out/wifi_map_5.png',bbox_inches='tight',facecolor='white',pad_inches=0.12); plt.close(fig)

# ---- чистая схема размещения (слайд «Схема») ----
fig,ax=plt.subplots(figsize=(12.6,11.4),dpi=170)
ax.set_facecolor('#f5f7fa')
draw_walls(ax,lw=1.1,alpha=0.9)
base(ax)
# тонкая сетка 5 м
for gx in range(5,30,5): ax.plot([gx,gx],[0,27],color='#c9d4e0',lw=0.6,zorder=0)
for gy in range(5,27,5): ax.plot([0,30],[gy,gy],color='#c9d4e0',lw=0.6,zorder=0)
draw_numbers(ax); draw_aps(ax); scalebar(ax)
ax.set_title('Схема размещения точек доступа (11 AP) — план этажа, лист 14 АР',fontsize=13,fontweight='bold',color='#102a43',pad=10)
fig.savefig('out/wifi_layout.png',bbox_inches='tight',facecolor='white',pad_inches=0.12); plt.close(fig)
print("maps v4 done")
