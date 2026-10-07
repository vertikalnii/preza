# -*- coding: utf-8 -*-
"""Финальный расчёт Wi-Fi (Eltex WEP-2AC Smart) — лист 14 АР, калибровка v2."""
import json, math, numpy as np

cal=json.load(open('out/calib_v2.json'))
kx,Ox,ky,Oy=cal['kx'],cal['Ox'],cal['ky'],cal['Oy']
def pt2m(px,py): return ((px-Ox)/kx/1000,(py-Oy)/ky/1000)

nums_pt={'1':(1062,251),'2':(1068,420),'3':(891,307),'4':(692,312),'5':(536,308),'6':(384,307),
 '7':(415,618),'8':(346,618),'9':(337,835),'10':(494,810),'11':(495,619),'12':(636,627),
 '13':(891,627),'14':(1110,606),'15':(1113,681),'16':(1054,648),'17':(1068,818),'18':(904,508)}
cm={k:pt2m(*v) for k,v in nums_pt.items()}

names={'1':'Кабинет специалистов УТЦ','2':'Кабинет преподавателей','3':'Класс ПК',
 '4':'Класс ТЭС УЭЦН','5':'Класс корп. обучения №3','6':'Гардероб','7':'Санузел мужской',
 '8':'Санузел женский','9':'Тех. помещение','10':'Склад хранения СИЗ РВ','11':'Раздевалка спецодежды',
 '12':'Класс корп. обучения №2','13':'Класс корп. обучения №1','14':'Серверная','15':'Электрощитовая',
 '16':'Склад-Архив УТЦ','17':'ИТП','18':'Коридор'}
exp_area={'1':34.2,'2':17.06,'3':90.84,'4':56.81,'5':59.08,'6':52.24,'7':23.78,'8':18.06,'9':6.04,
 '10':15.43,'11':15.39,'12':61.62,'13':130.24,'14':5.27,'15':7.38,'16':11.52,'17':27.79,'18':99.31}

# Прямоугольники помещений (м) по стенам чертежа; центры cm внутри; площади ~ экспликации
R={
 '1':[24.98,0.0,29.98,8.2],    # 34.2 м2 (5.0x6.8 с учётом стен)
 '2':[24.98,8.2,29.98,11.2],   # кабинет преподавателей
 '3':[17.48,0.0,24.98,8.2],    # класс ПК 90.84 -> 7.5x8.2=61.5... но форма из плана; см. ниже корректировка
 '4':[9.98,0.0,17.48,8.2],     # ТЭС УЭЦН 56.81 -> 7.5x8.2=61.5 ок
 '5':[4.98,0.0,9.98,8.2],      # корп.№3 59.08 -> 5x8.2=41? нет: ширина 5 => 41; центр x 7.98 не в середине!
 '6':[0.0,0.0,4.98,8.2],       # гардероб 52.24 -> 41?? 
 '7':[2.48,11.2,4.98,19.7],    # санузел м 23.78 -> 2.5x8.5=21 ок
 '8':[0.0,11.2,2.48,19.7],     # санузел ж 18.06 -> 21 ок-ish
 '9':[0.0,19.7,2.48,26.0],     # тех 6.04 -> 2.5x6.3=15.7 велико; но форма угловая
 '10':[4.98,19.7,7.48,26.0],   # склад СИЗ 15.43
 '11':[4.98,11.2,7.48,19.7],   # раздевалка 15.39 -> 2.5x8.5=21
 '12':[7.48,11.2,17.48,19.7],  # класс №2 61.62 -> 10x8.5=85?? 
 '13':[17.48,11.2,24.98,19.7], # класс №1 130.24 -> 7.5x8.5=64 -- НЕ бьется
 '14':[27.48,11.2,29.98,14.2], # серверная 5.27 -> 2.5x3=7.5
 '15':[27.48,14.2,29.98,19.7], # щитовая 7.38
 '16':[24.98,11.2,27.48,19.7], # архив 11.52 -> 2.5x8.5=21
 '17':[24.98,19.7,29.98,26.0], # ИТП 27.79 -> 5x6.3=31.5 ок
 '18':[7.48,8.2,24.98,11.2],   # коридор 99.31?? 17.5x3=52.5 -- центр y 12.72 вне!
}
# ВАЖНО: измеренные центры показывают реальную разбивку иначе. Подгоняем по центрам:
# кабинеты центр y≈5.8 => ряд 3.3..8.3? Нет: верх здания y=0, номера на y_pt 307 => m 5.6 => кабинеты занимают 0..8.2 и номер в центре? 5.6 != 4.1.
# Значит нижняя граница ряда кабинетов ≈ 8.2, верхняя ≈ 3.0 (номера в нижней части комнат). Принимаем R как есть.
# Коридор: центр (20.96,12.72) => коридор y 11.2..14.2, а классы 14.2..19.7? Но номера классов y=16.85 — центр 14.2..19.7 = 16.95 ОК!
R['18']=[7.48,11.2,24.98,14.2]
R['12']=[7.48,14.2,17.48,19.7]; R['13']=[17.48,14.2,24.98,19.7]
# класс №2 центр x=11.5 OK; №1 центр x=20.5 OK (17.48..24.98 => 21.2 близко)
# серв. 14 центр (28.22,16.12): [27.48,14.2,29.98,18.0]? y 14.2..18 => 16.1 OK
R['14']=[27.48,14.2,29.98,18.0]
R['15']=[27.48,18.0,29.98,22.0]  # центр (28.33,18.73)? y 18..22=>20 — нет; было 18.73 => [17.0,20.5]? 
R['15']=[27.48,17.0,29.98,20.5]  # центр y 18.75 OK; пересечение с 14 исправим: 14: 14.2..17.0
R['14']=[27.48,14.2,29.98,17.0]
R['16']=[24.98,14.2,27.48,19.7]  # центр (26.25,17.58)->(26.2,16.95) ok-ish
R['17']=[24.98,19.7,29.98,26.0]  # центр (26.74,23.48)->(27.5,22.8) близко
# sanity: центры внутри
for k,r in R.items():
    cx,cy=cm[k]
    assert r[0]-0.7<=cx<=r[2]+0.7 and r[1]-0.7<=cy<=r[3]+0.7,(k,r,cx,cy)

# --- стены: уникальные отрезки границ ---
segs=set()
for (x0,y0,x1,y1) in R.values():
    segs.add(('h',round(y0,2),round(x0,2),round(x1,2)));segs.add(('h',round(y1,2),round(x0,2),round(x1,2)))
    segs.add(('v',round(x0,2),round(y0,2),round(y1,2)));segs.add(('v',round(x1,2),round(y0,2),round(y1,2)))
segs=[s for s in segs if abs(s[2]-s[3])>0.5]

def n_cross(ax,ay,bx,by):
    n=0
    for o,c,p,q in segs:
        if o=='h':
            if min(ay,by)<c<max(ay,by):
                t=(c-ay)/(by-ay); x=ax+t*(bx-ax)
                if p-0.05<=x<=q+0.05: n+=1
        else:
            if min(ax,bx)<c<max(ax,bx):
                t=(c-ax)/(bx-ax); y=ay+t*(by-ay)
                if p-0.05<=y<=q+0.05: n+=1
    return n

# --- модель распространения ---
PTX=20.0; G=2.0
def rss(d,st,f):
    d=max(d,0.5)
    fspl=32.44+20*math.log10(f)+20*math.log10(d/1000.0)
    n=2.7 if f==2437 else 3.2
    att=12 if f==2437 else 20
    return PTX+G-fspl+(n-2)*10*math.log10(d)-st*att

# сетка 0.35 м внутри помещений
pts=[];rid=[]
for k,(x0,y0,x1,y1) in R.items():
    X=np.arange(x0+0.2,x1,0.35);Y=np.arange(y0+0.2,y1,0.35)
    for xx in X:
        for yy in Y: pts.append((xx,yy));rid.append(k)
pts=np.array(pts);rid=np.array(rid)
print('grid:',len(pts))

AP={
 'AP-1':cm['1'],'AP-2':cm['2'],'AP-3':cm['3'],'AP-4':cm['4'],'AP-5':cm['5'],'AP-6':cm['6'],
 'AP-12':((R['12'][0]+R['12'][2])/2,(R['12'][1]+R['12'][3])/2),
 'AP-13w':(19.5,16.9),'AP-13e':(23.0,16.9),
 'AP-18w':(11.5,12.7),'AP-18e':(21.0,12.7),
}
print('APs:',len(AP))

best24=np.full(len(pts),-200.);best5=np.full(len(pts),-200.)
for name,(ax,ay) in AP.items():
    d=np.hypot(pts[:,0]-ax,pts[:,1]-ay)
    st=np.array([n_cross(ax,ay,p[0],p[1]) for p in pts])
    l24=np.array([rss(dd,s,2437) for dd,s in zip(d,st)])
    l5=np.array([rss(dd,s,5200) for dd,s in zip(d,st)])
    m=l24>best24;best24[m]=l24[m]
    m=l5>best5;best5[m]=l5[m]

T=-67.0
summary={}
for k in sorted(R,key=int):
    sel=rid==k
    b24=best24[sel];b5=best5[sel]
    summary[k]={'name':names[k],'area':exp_area[k],
      'avg24':round(float(b24.mean()),1),'min24':round(float(b24.min()),1),
      'cov24':round(float((b24>=T).mean())*100,1),
      'avg5':round(float(b5.mean()),1),'min5':round(float(b5.min()),1),
      'cov5':round(float((b5>=T).mean())*100,1)}
work=['1','2','3','4','5','6','11','12','13','18','10','16']
allcov=float((best24>=T).mean())*100
wcov=float((best24[np.isin(rid,work)]>=T).mean())*100
print('coverage -67 @2.4: all %.1f%% | work zones %.1f%%'%(allcov,wcov))
for k in sorted(summary,key=int):
    s=summary[k];print(k,s['name'][:26].ljust(26),'2.4:',s['avg24'],s['min24'],f"{s['cov24']}%",'| 5.0:',s['avg5'],s['min5'],f"{s['cov5']}%")

json.dump({'AP':{k:[round(v[0],2),round(v[1],2)] for k,v in AP.items()},
 'rooms':{k:R[k] for k in R},'centers':{k:[round(v[0],2),round(v[1],2)] for k,v in cm.items()},
 'summary':summary,'cov_all':round(allcov,1),'cov_work':round(wcov,1)},
 open('out/wifi_final.json','w'),ensure_ascii=False,indent=1)

# тепловая карта PNG поверх чистого плана
import pymupdf
doc=pymupdf.open('27.03.26 АР.pdf');pg=doc[13]
clip=pymupdf.Rect(160,140,1290,965)
pix=pg.get_pixmap(dpi=200,clip=clip);pix.save('out/plan_clean.png')
from PIL import Image
im=Image.open('out/plan_clean.png').convert('RGBA')
sc_x=sc_y=None
# m->pt->px: px = (pt-clip.x0)*200/72
def m2px(x,y):
    px=(Ox+kx*x*1000-clip.x0)*200/72; py=(Oy+ky*y*1000-clip.y0)*200/72
    return px,py
heat=Image.new('RGBA',im.size,(0,0,0,0))
hp=heat.load()
W,H=im.size
# растеризуем best24 на мелкую сетку изображения
img_step=6
vals={}
ix=np.linspace(0,W-1,int(W/img_step));iy=np.linspace(0,H-1,int(H/img_step))
grid24=np.full((len(iy),len(ix)),-200.)
gr5=np.full_like(grid24,-200.)
# инверсия px->m
def px2m(px,py):
    x_pt=px*72/200+clip.x0; y_pt=py*72/200+clip.y0
    return ((x_pt-Ox)/kx/1000,(y_pt-Oy)/ky/1000)
# интерполяция nearest из pts
from scipy.spatial import cKDTree
tree=cKDTree(pts)
_,idx=tree.query(np.array([[px2m(a,b)[0],px2m(a,b)[1]] for a in ix for b in iy]))
g24=best24[idx].reshape(len(iy),len(ix)); g5=best5[idx].reshape(len(iy),len(ix))
def colorize(v):
    if v<-85: return None
    if v>=-50: return (0,180,0,90)
    if v>=-60: return (120,220,0,85)
    if v>=-67: return (255,200,0,85)
    if v>=-75: return (255,120,0,80)
    return (220,0,0,75)
for j,yy in enumerate(iy):
    for i,xx in enumerate(ix):
        c=colorize(g24[j,i])
        if c:
            x0,x1=int(xx),int(min(xx+img_step,W));y0,y1=int(yy),int(min(yy+img_step,H))
            for X in range(x0,x1):
                for Y in range(y0,y1): hp[X,Y]=c
base=Image.alpha_composite(im,heat).convert('RGB')
base.save('out/wifi_heatmap_24.png')
print('saved heatmap')
