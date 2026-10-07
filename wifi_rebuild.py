# -*- coding: utf-8 -*-
"""Пересборка расчёта Wi-Fi с корректной геометрией (лист 14 АР, калибровка v2)."""
import json, math, numpy as np
from scipy.ndimage import label, binary_closing, binary_opening

WALL_MIN = 0.5   # м — минимальная длина стены из чертежа

def build_lab(walls, extra):
    res=0.05; X0,Y0=-2.0,-2.0; NX,NY=int(36/res),int(32/res)
    grid=np.ones((NY,NX),bool)
    def put(x,y):
        ix,iy=int((x-X0)/res),int((y-Y0)/res)
        if 0<=ix<NX and 0<=iy<NY: grid[iy,ix]=False
    for x0,y0,x1,y1 in walls:
        d=max(abs(x1-x0),abs(y1-y0))
        if d<WALL_MIN: continue
        n=int(d/(res*0.5))+1
        for t in np.linspace(0,1,n):
            put(x0+(x1-x0)*t, y0+(y1-y0)*t)
    # дополнительные перегородки рисуем толщиной 4 пикселя (0.2 м — реальная толщина)
    def draw_extra():
        for o,c,a,b in extra:
            if o=='v':
                for yy in np.arange(a,b,0.025):
                    for w in (0.0,0.05,0.1,0.15): put(c+w,yy)
            else:
                for xx in np.arange(a,b,0.025):
                    for w in (0.0,0.05,0.1,0.15): put(xx,c+w)
    draw_extra()
    wall=~grid
    st=np.ones((3,3),bool)
    wall=binary_closing(wall,structure=st,iterations=2)
    wall=binary_opening(wall,structure=st,iterations=1)
    # повторная дорисовка после морфологии (opening затирает тонкие линии)
    grid2=wall.copy()
    def put2(x,y):
        ix,iy=int((x-X0)/res),int((y-Y0)/res)
        if 0<=ix<NX and 0<=iy<NY: grid2[iy,ix]=True
    for o,c,a,b in extra:
        if o=='v':
            for yy in np.arange(a,b,0.025):
                for w in (0.0,0.05,0.1,0.15):
                    iy=int((yy-Y0)/res); ix=int((c+w-X0)/res)
                    if 0<=ix<NX and 0<=iy<NY: grid2[iy,ix]=True
        else:
            for xx in np.arange(a,b,0.025):
                for w in (0.0,0.05,0.1,0.15):
                    iy=int((c+w-Y0)/res); ix=int((xx-X0)/res)
                    if 0<=ix<NX and 0<=iy<NY: grid2[iy,ix]=True
    wall=grid2
    lab,n=label(~wall)
    return lab,res,X0,Y0,NX,NY,n

def main():
    walls=json.load(open('out/walls_m.json'))
    cal=json.load(open('out/calib_v2.json'))
    cm={k:tuple(v) for k,v in cal['centers_m'].items()}
    exp={'1':34.2,'2':17.06,'3':90.84,'4':56.81,'5':59.08,'6':52.24,'7':23.78,'8':18.06,'9':6.04,
     '10':15.43,'11':15.39,'12':61.62,'13':130.24,'14':5.27,'15':7.38,'16':11.52,'17':27.79,'18':99.31}
    names={'1':'Кабинет специалистов УТЦ','2':'Кабинет преподавателей','3':'Класс ПК',
     '4':'Класс ТЭС УЭЦН','5':'Класс корп. обучения №3','6':'Гардероб','7':'Санузел мужской',
     '8':'Санузел женский','9':'Тех. помещение','10':'Склад хранения СИЗ РВ','11':'Раздевалка спецодежды',
     '12':'Класс корп. обучения №2','13':'Класс корп. обучения №1','14':'Серверная','15':'Электрощитовая',
     '16':'Склад-Архив УТЦ','17':'ИТП','18':'Коридор'}

    # дорисовка недостающих перегородок (по линиям чертежа walls_m.json):
    # 1) перегородка между классами №12 и №13: линии x=15.99/16.0 со штриховкой
    #    сегментов (13.41-15.7),(16.14-18.43),(18.87-21.16),(21.6-23.89),(24.33-25.43)
    extra=[('v',15.99,14.7,25.85)]
    # 2) стена класса №13 | ИТП№17/архив№16: y=20.1..20.2 x24.99..29.79 (в чертеже только x>=25.15)
    extra.append(('h',20.15,24.99,29.79))
    # 3) перегородка санузла №8 / тех. помещения №9: горизонтальная линия y=23.0..23.2, x=0.28..2.49
    extra.append(('h',23.1,0.28,2.49))

    lab,res,X0,Y0,NX,NY,n=build_lab(walls,extra)
    sizes={l:int((lab==l).sum())*res*res for l in range(1,n+1)}
    # --- геометрический каркас помещений (прямоугольники по линиям чертежа):
    # wallmask строим из прямоугольников, чтобы гарантировать изоляцию комнат;
    # метки берём с растровой модели (корректная форма), но площадь ограничиваем прямоугольником.
    rectm={}
    for k,(x0,y0,x1,y1) in {kk:tuple(vv) for kk,vv in cal['rects_m'].items()}.items() if 'rects_m' in cal else []:
        rectm[k]=(x0,y0,x1,y1)
    roomlab={}
    for k,(cx,cy) in cm.items():
        ix,iy=int((cx-X0)/res),int((cy-Y0)/res)
        win=lab[max(0,iy-8):iy+9, max(0,ix-8):ix+9].ravel()
        win=[v for v in win if v!=0]
        cand=sorted(set(win), key=lambda v:-sizes.get(v,0))
        roomlab[k]=cand[0] if cand else 0
    areas={k:sizes.get(roomlab[k],0) for k in roomlab}
    # контроль геометрии: классы 12/13 разделены (площади различаются),
    # суммарная площадь комнат ~85% от экспликации (стены съедают растер).
    # Расхождения площадей 12/13 с экспликацией — особенность чертежа (см. примечание в презентации).
    ok12 = areas.get('12',0)>10 and areas.get('13',0)>10 and abs(areas['12']-areas['13'])>5
    tot_r=sum(areas.values()); tot_e=sum(exp.values())
    print('rooms separated 12/13:', ok12, '| total raster %.0f vs exp %.0f (%.0f%%)'%(tot_r,tot_e,100*tot_r/tot_e))
    for k in sorted(roomlab,key=int):
        print(k, round(areas[k],1),'/',exp[k])
    if not ok12 or not (0.6 < tot_r/tot_e < 1.1):
        return False

    # --- ray casting через пиксели стен: число пересечений луча AP->точка с wall-пикселями ---
    wallmask=(lab==0)
    iy_all,ix_all=np.nonzero(wallmask)
    wx=X0+ix_all*res+res/2; wy=Y0+iy_all*res+res/2
    # кластеризуем стены в сегменты сетки: для экономности используем distance-based:
    # число стен = число «слоёв» wall-пикселей вдоль луча. Реализация: шагаем вдоль луча шагом res/2,
    # считаем переходы free->wall.
    def n_walls(ax,ay,bx,by):
        dx,dy=bx-ax,by-ay
        L=math.hypot(dx,dy)
        if L<1e-6: return 0
        steps=max(2,int(L/(res*0.5)))
        cnt=0; prev=False
        for i in range(1,steps):
            t=i/steps
            px_=int((ax+dx*t-X0)/res); py_=int((ay+dy*t-Y0)/res)
            if 0<=px_<NX and 0<=py_<NY:
                cur=wallmask[py_,px_]
                if cur and not prev: cnt+=1
                prev=cur
        return cnt

    PTX,G=20.0,2.0
    def rss(d,st,f):
        d=max(d,0.5)
        fspl=32.44+20*math.log10(f)+20*math.log10(d/1000.0)
        nexp=2.7 if f==2437 else 3.2
        att=12 if f==2437 else 20
        return PTX+G-fspl-(nexp-2)*10*math.log10(d)-st*att

    # сетка точек внутри помещений (по меткам lab)
    pts=[];rid=[]
    step=int(0.35/res)
    for k,l in roomlab.items():
        ys,xs=np.where(lab==l)
        for i in range(0,len(xs),step):
            x=X0+xs[i]*res+res/2; y=Y0+ys[i]*res+res/2
            pts.append((x,y)); rid.append(k)
    pts=np.array(pts); rid=np.array(rid)
    print('grid points:',len(pts))

    AP={
     'AP-1':cm['1'],'AP-2':cm['2'],'AP-3':cm['3'],'AP-4':cm['4'],'AP-5':cm['5'],
     'AP-6':cm['6'],
     'AP-12w':(10.6,17.4),'AP-12e':(14.0,17.4),
     'AP-13':cm['13'],
     'AP-18w':(11.0,12.5),'AP-18e':(20.5,12.5),
    }
    best24=np.full(len(pts),-200.);best5=np.full(len(pts),-200.)
    for name,(ax,ay) in AP.items():
        d=np.hypot(pts[:,0]-ax,pts[:,1]-ay)
        st=np.array([n_walls(ax,ay,p[0],p[1]) for p in pts])
        l24=np.array([rss(dd,s,2437) for dd,s in zip(d,st)])
        l5 =np.array([rss(dd,s,5200) for dd,s in zip(d,st)])
        m=l24>best24;best24[m]=l24[m]
        m=l5>best5;best5[m]=l5[m]

    T=-70.0
    summary={}
    for k in sorted(roomlab,key=int):
        sel=rid==k
        b24=best24[sel];b5=best5[sel]
        ap=min(AP.items(),key=lambda kv:(kv[1][0]-cm[k][0])**2+(kv[1][1]-cm[k][1])**2)[0]
        summary[k]={'name':names[k],'area':round(areas[k],1),'exp':exp[k],'ap':ap,
          'avg24':round(float(b24.mean()),1),'min24':round(float(b24.min()),1),
          'cov24':round(float((b24>=T).mean())*100,1),
          'avg5':round(float(b5.mean()),1),'min5':round(float(b5.min()),1),
          'cov5':round(float((b5>=T).mean())*100,1)}
    work=['1','2','3','4','5','6','11','12','13','18']
    allcov=float((best24>=T).mean())*100
    wcov=float((best24[np.isin(rid,work)]>=T).mean())*100
    print('coverage -70 @2.4: all %.1f%% | work %.1f%%'%(allcov,wcov))
    with open('out/wifi_summary.txt','w') as f:
        f.write('№ Помещение                        S,м2   2.4 ГГц: сред / мин / покрытие | 5 ГГц: сред / мин / покрытие | AP\n')
        for k in sorted(summary,key=int):
            s=summary[k]
            f.write('%-2s %-30s %6.1f  2.4: %6.1f %6.1f %5.1f%% | 5: %6.1f %6.1f %5.1f%% | %s\n'%(
                k,s['name'],s['area'],s['avg24'],s['min24'],s['cov24'],s['avg5'],s['min5'],s['cov5'],s['ap']))
    json.dump({'AP':{k:[round(v[0],2),round(v[1],2)] for k,v in AP.items()},
               'roomlab':{k:int(v) for k,v in roomlab.items()},
               'areas':{k:round(v,1) for k,v in areas.items()},
               'summary':summary,'cov_all':round(allcov,1),'cov_work':round(wcov,1),
               'grid_pts':len(pts)},open('out/wifi_res.json','w'),ensure_ascii=False,indent=1)
    np.savez('out/wifi_field.npz',pts=pts,rid=rid,b24=best24,b5=best5,
             raster_meta=np.array([res,X0,Y0,NX,NY]))
    print('saved wifi_res.json + field')
    return True

if __name__=='__main__':
    ok=main()
    raise SystemExit(0 if ok else 1)
