#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Планирование размещения Wi-Fi точек доступа по плану БЖ (стр. 14 "27.03.26 АР.pdf").

Метод:
  1. Помещения извлечены из векторов чертежа, откалиброваны по размерным цепям
     (здание 30.0 x 27.0 м, стены 0.2-0.4 м).
  2. Строится модель стен (объединённые линии границ помещений).
  3. Граф трассировки лучей: узлы — сетка 0.5 м внутри помещений + центры комнат;
     рёбра — прямые участки, пересекающие <=1 стену (проход через дверь/перегородку).
  4. Для каждой пары (AP-кандидат, помещение) ищется минимальное число стен на пути
     (Dijkstra с лексикографским весом: сначала стены, затем длина).
  5. Attenuation: L = 22 log10(d) + 5.5 + sum(walls*W), W=[3 дБ коридорная перегородка,
     10 дБ капитальная стена] — выбор типа стены по длине пересечения (короткая = дверь? 
     упрощённо: все стены 8 дБ, наружные 12 дБ). RSSI = Tx(20 дБм) + G(2) - L.
  6. Покрытие: целевой порог -67 дБм. Жадный set cover с штрафом за избыточное число AP.
"""
import json, math, heapq
from collections import defaultdict

ROOMS = json.load(open('out/rooms.json'))
PX0,PX1,PY0,PY1 = 148.0,1215.5,158.0,956.2
BW,BH = 30.0,27.0
SX=BW/(PX1-PX0); SY=BH/(PY1-PY0)
def rect(r): return ((r['x0']-PX0)*SX,(r['y0']-PY0)*SY,(r['x1']-PX0)*SX,(r['y1']-PY0)*SY)

RX={int(k):rect(v) for k,v in ROOMS.items()}
EXP={int(k):float(v['exp']) for k,v in ROOMS.items()}
NAME={int(k):v['name'] for k,v in ROOMS.items()}

# ---------- walls ----------
segs=[]
for r in ROOMS.values():
    x0,y0,x1,y1 = rect(r)
    segs.append(('h',y0,x0,x1)); segs.append(('h',y1,x0,x1))
    segs.append(('v',x0,y0,y1)); segs.append(('v',x1,y0,y1))

def build(orient, tol=0.4, gap=0.3, minlen=0.7):
    lines={}
    for o,c,a,b in segs:
        if o!=orient: continue
        placed=False
        for k in list(lines):
            if abs(k-c)<=tol: lines[k].append((a,b)); placed=True; break
        if not placed: lines[c]=[(a,b)]
    out=[]
    for c,ivs in lines.items():
        ivs.sort(); cur=list(ivs[0])
        for a,b in ivs[1:]:
            if a<=cur[1]+gap: cur[1]=max(cur[1],b)
            else: out.append((c,cur[0],cur[1])); cur=[a,b]
        out.append((c,cur[0],cur[1]))
    return [(o,c,a,b) for c,a,b in out if b-a>=minlen]

WL = build('h') + build('v')
NW=len(WL)

def crossed(ax,ay,bx,by):
    """indices of walls strictly crossed by open segment"""
    res=[]; dx=bx-ax; dy=by-ay
    for idx,(o,c,a,b) in enumerate(WL):
        if o=='h':
            if abs(dy)<1e-9: continue
            t=(c-ay)/dy
            if 0<t<1 and a+0.02<=ax+t*dx<=b-0.02: res.append(idx)
        else:
            if abs(dx)<1e-9: continue
            t=(c-ax)/dx
            if 0<t<1 and a+0.02<=ay+t*dy<=b-0.02: res.append(idx)
    return res

def room_of(x,y):
    for k,(x0,y0,x1,y1) in RX.items():
        if x0+0.03<x<x1-0.03 and y0+0.03<y<y1-0.03: return k
    return None

# ---------- ray graph nodes: grid 0.5 m inside rooms ----------
NODES=[]; COORD=[]; RNODE=defaultdict(list)
y=0.25
while y<BH-0.1:
    x=0.25
    while x<BW-0.1:
        k=room_of(x,y)
        if k is not None:
            RNODE[k].append(len(NODES)); NODES.append((x,y)); COORD.append((x,y,k))
        x+=0.5
    y+=0.5
N=len(NODES)
print(f'nodes: {N}, walls: {NW}')

# ---------- edges via Dijkstra per source room-grid? Too many sources.
# Instead: precompute wall-crossing between nearby nodes lazily during multi-source search.
# For efficiency: run one Dijkstra per *AP candidate set evaluation* is too slow.
# Better approach: compute minimal-wall distance field from each candidate AP once.
# Candidate AP positions: node subset (every 1 m grid + centers). Evaluate all candidates -> too heavy.
# Use two-stage: coarse candidate grid 1.0m (~350 points), per-candidate BFS on wall-hops graph built
# with edges limited to crossings<=1 within same/adjacent rooms.

CAND=[]
y=0.75
while y<BH-0.1:
    x=0.75
    while x<BW-0.1:
        k=room_of(x,y)
        if k is not None: CAND.append((x,y,k))
        x+=1.0
    y+=1.0
# add room centers as candidates too
for k,(x0,y0,x1,y1) in RX.items():
    CAND.append(((x0+x1)/2,(y0+y1)/2,k))
NC=len(CAND)
print('candidates:', NC)

# Build global hop-graph over ALL nodes+candidates with edges crossing <=1 wall,
# using spatial bucketing to limit pair checks.
ALLP = COORD + [(cx,cy,ck) for cx,cy,ck in CAND]
NA=len(ALLP)
BUCKET=4.0
buckets=defaultdict(list)
for i,(x,y,k) in enumerate(ALLP):
    buckets[(int(x//BUCKET),int(y//BUCKET))].append(i)

# In-room complete connectivity would be O(n^2) huge; instead connect grid neighbors + LOS jumps.
# Strategy: edges = pairs whose segment crosses <=1 wall AND both in same room or adjacent rooms.
# To keep it tractable: same-room edges only between nodes within 12 m and clear LOS; cross-room
# edges only between nodes near shared boundary (<3 m). Approximation acceptable for planning.
edges=defaultdict(list)
same_pairs=0
for key,idxs in buckets.items():
    bx,by=key
    neigh=[]
    for dx_ in (-1,0,1):
        for dy_ in (-1,0,1):
            neigh += buckets.get((bx+dx_,by+dy_),[])
    for i in idxs:
        xi,yi,ki=ALLP[i]
        for j in neigh:
            if j<=i: continue
            xj,yj,kj=ALLP[j]
            if ki==kj:
                d=math.hypot(xi-xj,yi-yj)
                if d>12.5: continue
                cr=crossed(xi,yi,xj,yj)
                if len(cr)==0:
                    edges[i].append((j,len(cr),d)); edges[j].append((i,len(cr),d))
            else:
                d=math.hypot(xi-xj,yi-yj)
                if d>4.5: continue
                cr=crossed(xi,yi,xj,yj)
                if len(cr)==1:
                    # classify wall attenuation: exterior if along building border
                    edges[i].append((j,1,d)); edges[j].append((i,1,d))
print('edge build done, avg deg %.1f'%(sum(len(v) for v in edges.values())/NA))

# ---------- coverage model ----------
TX=20.0; G=2.0
ATT_WALL=8.0; ATT_EXT=12.0; PL_LOSS=lambda d: 22*math.log10(max(d,0.5))+5.5
TARGET=-67.0

# For each candidate AP, which nodes does it cover (RSSI>=TARGET)?
# Path loss uses graph shortest path (walls, then distance).
def dijkstra(src):
    W=[(math.inf,math.inf)]*NA; W[src]=(0,0.0); prev=[None]*NA
    pq=[(0,0.0,src)]; W[src]=(0,0.0)
    while pq:
        w,d,u=heapq.heappop(pq)
        if (w,d)>W[u]: continue
        for v,nwc,dd in edges[u]:
            nw2=w+nwc; nd=d+dd
            if (nw2,nd)<W[v]:
                W[v]=(nw2,nd); prev[v]=u; heapq.heappush(pq,(nw2,nd,v))
    return W,prev

def rssi_for(src):
    W,prev=dijkstra(src)
    cov=set()
    detail=defaultdict(int)
    for i in range(N):
        x,y,k=ALLP[i]
        w,d=W[i]
        if w==math.inf: continue
        L=PL_LOSS(d)+w*ATT_WALL
        if TX+G-L>=TARGET:
            cov.add(i); detail[k]+=1
    return cov,detail

# ---------- greedy set cover with penalty ----------
node_need=set(range(N))
room_total=defaultdict(int)
for i in range(N): room_total[ALLP[i][2]]+=1

chosen=[]; covered=set()
scores=[]
# precompute coverage for all candidates (heavy but OK ~400 dijkstras)
print('computing coverage...')
COV=[]
for ci in range(NC):
    cov,det=rssi_for(ci+N)   # candidate nodes appended after N
    COV.append((cov,det))
    if ci%50==0: print(ci,end=' ',flush=True)
print()

def uncovered_frac(cov):
    return len(node_need-covered)

remaining=set(range(NC))
while True:
    best=None; best_key=None
    for ci in remaining:
        gain=len(COV[ci][0]-covered)
        if gain<=0: continue
        # prefer high gain, low cost
        key=(-gain)
        if best is None or key<best_key:
            best=ci; best_key=key
    if best is None: break
    chosen.append(best); covered|=COV[best][0]; remaining.discard(best)
    print(f"pick AP {best}: +{len(COV[best][0])} nodes, total {len(covered)}/{N}")
    if len(covered)>=N: break

uncov=N-len(covered)
print('\n=== RESULT ===')
print(f'AP count: {len(chosen)}, covered {len(covered)}/{N} ({100*len(covered)/N:.1f}%), uncovered {uncov}')
per_room=defaultdict(lambda:[0,0])
for i in range(N):
    k=ALLP[i][2]
    per_room[k][1]+=1
    if i in covered: per_room[k][0]+=1
for k in sorted(per_room):
    c,t=per_room[k]
    print(f'  room {k:>2} {NAME[k][:30]:<30} {c/t*100:5.1f}%  (S={EXP[k]} m2)')
json.dump({'chosen':[list(CAND[c]) for c in chosen]}, open('out/ap_result.json','w'), ensure_ascii=False)
