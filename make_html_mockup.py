#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML-макет презентации Wi-Fi: 9 слайдов 16:9, карты покрытия как inline SVG."""
import json
import numpy as np

rm = json.load(open('out/rooms_final.json'))
res = json.load(open('out/wifi_res.json'))
AP = res['AP']; S = res['summary']
f = np.load('out/wifi_field.npz')
pts, b24, b5 = f['pts'], f['b24'], f['b5']
rows = json.load(open('out/html_rows.json'))

W, H = 30.0, 26.7

def col(v):
    if v >= -55: return '#1e8e3e'
    if v >= -65: return '#7cc24a'
    if v >= -70: return '#f4c430'
    if v >= -80: return '#ef8e3b'
    return '#d64541'

def heat_svg(field, step=0.3):
    xs = np.floor((pts[:, 0] + step / 2) / step) * step
    ys = np.floor((pts[:, 1] + step / 2) / step) * step
    seen = {}
    for i in range(len(pts)):
        k = (xs[i], ys[i])
        if k not in seen or field[i] > seen[k]:
            seen[k] = field[i]
    cw = step / W * 100; ch = step / H * 100
    cells = []
    for (x, y), v in seen.items():
        cx = x / W * 100; cy = y / H * 100
        cells.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>' % (cx, cy, cw * 1.15, ch * 1.15, col(v)))
    plan = ['<svg viewBox="-1.5 -1.5 103 %.1f" xmlns="http://www.w3.org/2000/svg">' % (H + 3)]
    plan.append('<rect x="0" y="0" width="100" height="%.2f" fill="#fafbfc"/>' % H)
    plan += cells
    for r in rm:
        x0 = r['x0'] / W * 100; y0 = r['y0'] / H * 100
        x1 = r['x1'] / W * 100; y1 = r['y1'] / H * 100
        plan.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#3b4a5a" stroke-width="0.3"/>' % (x0, y0, x1 - x0, y1 - y0))
        plan.append('<text x="%.2f" y="%.2f" font-size="1.9" font-weight="bold" fill="#22303f" text-anchor="middle">%d</text>' % ((x0 + x1) / 2, (y0 + y1) / 2 + 0.7, r['no']))
    for name, (x, y) in AP.items():
        cx = x / W * 100; cy = y / H * 100
        plan.append('<g><circle cx="%.2f" cy="%.2f" r="1.1" fill="#0b7bd6" stroke="#ffffff" stroke-width="0.3"/><circle cx="%.2f" cy="%.2f" r="0.4" fill="#fff"/></g>' % (cx, cy, cx, cy))
        plan.append('<text x="%.2f" y="%.2f" font-size="1.25" font-weight="bold" fill="#08477c" text-anchor="middle">%s</text>' % (cx, cy - 1.6, name))
    plan.append('<rect x="0" y="0" width="100" height="%.2f" fill="none" stroke="#1c2733" stroke-width="0.6"/>' % H)
    plan.append('</svg>')
    return ''.join(plan)

map24 = heat_svg(b24)
map5 = heat_svg(b5)

ap_notes = {
 "AP-1": ("Кабинет специалистов УТЦ №1", "Потолок, центр кабинета. Покрывает также серверную №14 через лёгкую перегородку."),
 "AP-2": ("Кабинет преподавателей №2", "Один AP на два помещения (№2 + серверная №14). RSSI в серверной −63 дБм — достаточно для мониторинга."),
 "AP-3": ("Класс ПК №3 (86,6 м²)", "Центр зала: гарантированные ≥−60 дБм во всех углах, до 40 одновременных клиентов."),
 "AP-4": ("Класс ТЭС УЭЦН №4", "Потолок над стендами; экранирование установок компенсировано запасом уровня."),
 "AP-5": ("Класс корп. обучения №3 (№5)", "Центр комнаты 5,6×12,1 м; сквозь ЖБ-стены в соседние классы не полагаться — у каждого свой AP."),
 "AP-6": ("Гардероб №6", "Покрывает входную группу и коридор западного крыла."),
 "AP-12w": ("Класс №12, западная половина", "Ширина зала 8,6 м требует двух AP; западная точка держит также склад СИЗ №10 и раздевалку №11."),
 "AP-12e": ("Класс №12, восточная половина", "Второй AP с тем же SSID, роуминг 802.11r; совместно с AP-3 формирует бесшовную зону северного блока."),
 "AP-13": ("Класс корп. обучения №1 (№13, 95,9 м²)", "Крупнейший зал этажа — один AP в геометрическом центре, углы ≥−45 дБм."),
 "AP-18w": ("Коридор №18, западная часть", "Обслуживает транзит и санузлы №7–8 на остаточном уровне (не нормируется)."),
 "AP-18e": ("Коридор №18, восточная часть", "Покрытие архива №16, ИТП №17, щитовой №15 (техпомещения — по остаточному принципу)."),
}
ap_cards = ''.join('<div class="card"><div class="cap">%s</div><div class="ct"><b>%s</b><br>%s</div></div>' % (k, v[0], v[1]) for k, v in ap_notes.items())

trs = ''
for r in rows:
    s24, s5 = r['st24'], r['st5']
    trs += ('<tr><td class="num">%s</td><td>%s</td><td>%.1f</td><td class="ap">%s</td>'
            '<td>%d</td><td>%d</td><td class="%s">%s</td>'
            '<td>%d</td><td>%d</td><td class="%s">%s</td></tr>') % (
        r['no'], r['name'], r['area'], r['ap'], r['avg24'], r['min24'], s24[0], s24[1],
        r['avg5'], r['min5'], s5[0], s5[1])

html = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проект Wi-Fi — Учебный центр (лист 14 АР)</title>
<style>
:root{--ink:#1c2733;--blue:#0b7bd6;--dark:#0e2233;--mut:#5a6b7d}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;color:var(--ink);background:#55606e}
.slide{width:min(1280px,96vw);aspect-ratio:16/9;background:#fff;margin:26px auto;border-radius:14px;
box-shadow:0 18px 50px rgba(0,0,0,.45);position:relative;overflow:hidden;display:flex;flex-direction:column}
.head{display:flex;align-items:center;gap:14px;padding:20px 42px 12px;border-bottom:4px solid var(--blue)}
.head .n{background:var(--blue);color:#fff;font-weight:700;border-radius:10px;width:46px;height:46px;display:flex;align-items:center;justify-content:center;font-size:22px;flex:none}
.head h2{font-size:clamp(18px,2.2vw,27px);color:var(--dark)}
.body{flex:1;padding:18px 42px 20px;display:flex;gap:26px;min-height:0}
.foot{padding:8px 42px;color:var(--mut);font-size:12px;display:flex;justify-content:space-between;border-top:1px solid #e3e8ee}
.title{background:linear-gradient(135deg,#0e2233 0%,#0b4f8f 55%,#0b7bd6 100%);color:#fff;justify-content:center;align-items:flex-start;padding:0 70px}
.title h1{font-size:clamp(26px,3.6vw,46px);line-height:1.15;margin-bottom:14px}
.title .sub{font-size:clamp(14px,1.6vw,20px);opacity:.9;margin-bottom:34px}
.kpis{display:flex;gap:16px;width:100%}
.kpi{flex:1;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:12px;padding:16px 18px;text-align:center}
.kpi b{display:block;font-size:clamp(20px,2.6vw,34px);color:#ffd257}
.kpi span{font-size:13px;opacity:.85}
.badge{display:inline-block;background:#ffd257;color:#0e2233;font-weight:700;border-radius:20px;padding:4px 14px;font-size:13px;margin-bottom:18px}
.mapwrap{flex:1.6;min-width:0;display:flex;align-items:center;justify-content:center;background:#eef2f6;border-radius:10px;padding:8px}
.mapwrap svg{width:100%;height:100%}
.side{flex:1;display:flex;flex-direction:column;gap:12px;justify-content:center}
.legend div{display:flex;align-items:center;gap:10px;font-size:clamp(12px,1.3vw,16px);margin:6px 0}
.sw{width:26px;height:14px;border-radius:3px;flex:none}
.note{background:#f2f7fc;border-left:5px solid var(--blue);border-radius:8px;padding:12px 16px;font-size:clamp(12px,1.3vw,15px);line-height:1.45}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;overflow:auto;flex:1;align-content:start}
.card{background:#f6f9fc;border:1px solid #dde6ef;border-radius:10px;padding:10px 12px;font-size:clamp(10px,1.05vw,13px);line-height:1.35}
.cap{display:inline-block;background:var(--blue);color:#fff;font-weight:700;border-radius:6px;padding:2px 9px;font-size:12px;margin-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:clamp(9px,1.05vw,13px)}
th{background:var(--dark);color:#fff;padding:7px 8px;text-align:left;font-weight:600}
td{padding:6px 8px;border-bottom:1px solid #e6ebf1}
tr:nth-child(even) td{background:#f5f8fb}
td.num{font-weight:700;color:var(--blue)}
td.ap{font-weight:600}
.ok{color:#1e8e3e;font-weight:700}.mid{color:#c98a00;font-weight:700}.bad{color:#d64541;font-weight:700}
ol.steps{list-style:none;counter-reset:s;flex:1;display:flex;flex-direction:column;justify-content:center;gap:14px}
ol.steps li{counter-increment:s;background:#f6f9fc;border-radius:10px;padding:14px 18px 14px 60px;position:relative;font-size:clamp(13px,1.4vw,17px);line-height:1.45}
ol.steps li:before{content:counter(s);position:absolute;left:14px;top:50%;transform:translateY(-50%);width:34px;height:34px;background:var(--blue);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;flex:1;align-content:center}
.gcard{background:#f6f9fc;border:1px solid #dde6ef;border-radius:12px;padding:16px 20px;font-size:clamp(12px,1.35vw,16px);line-height:1.5}
.gcard b.t{color:var(--blue);display:block;margin-bottom:6px;font-size:clamp(13px,1.5vw,18px)}
@media print{body{background:#fff}.slide{box-shadow:none;margin:0;page-break-after:always}}
</style></head><body>

<section class="slide title">
<div class="badge">Проектная документация · СОУТ / ССС</div>
<h1>Проект беспроводной сети<br>учебного центра</h1>
<div class="sub">Расчёт размещения точек доступа <b>Eltex WEP-2AC Smart</b> · План этажа, лист 14 (проект АР от 27.03.26)<br>Диапазоны 2,4 ГГц и 5 ГГц · Монолитный ЖБ-каркас с базальтовым наполнением</div>
<div class="kpis">
<div class="kpi"><b>11</b><span>точек доступа</span></div>
<div class="kpi"><b>100%</b><span>рабочих зон ≥ −70 дБм (2,4 ГГц)</span></div>
<div class="kpi"><b>96,6%</b><span>покрытия всей площади этажа</span></div>
<div class="kpi"><b>800,9 м²</b><span>площадь этажа (30×26,7 м)</span></div>
</div>
</section>

<section class="slide">
<div class="head"><div class="n">2</div><h2>Исходные данные и радиомодель</h2></div>
<div class="body"><ol class="steps">
<li><b>Здание:</b> учебный центр, этаж 30,0×26,7 м, 18 помещений (экспликация листа 14 АР). Перекрытия 300 мм, стены — монолитный железобетон с наполнением базальтовым волокном, армированный каркас.</li>
<li><b>Оборудование:</b> Eltex WEP-2AC Smart — Wi-Fi 6 (802.11ax), 2×2 MIMO, оба диапазона, PoE 802.3af, монтаж потолочный (высота ≈3,5–4,0 м).</li>
<li><b>Модель потерь:</b> RSS = Tx − FSPL(d) − (n−2)·10·lg d − ΣATTстен. n = 2,7 (2,4 ГГц) / 3,0 (5 ГГц); затухание ЖБ-стены с базальтом и арматурой: <b>12 дБ @2,4 ГГц / 20 дБ @5 ГГц</b>.</li>
<li><b>Критерии качества:</b> отлично ≥ −55 дБм · хорошо ≥ −65 дБм · проектный минимум ≥ −70 дБм (клиенты ноутбуки/смартфоны, edge-скорость ≥ MCS6).</li>
</ol></div>
<div class="foot"><span>27.03.26 АР · лист 14 «План этажа»</span><span>2 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">3</div><h2>Карта покрытия 2,4 ГГц — зоны уровня сигнала</h2></div>
<div class="body">
<div class="mapwrap">__MAP24__</div>
<div class="side">
<div class="legend">
<div><span class="sw" style="background:#1e8e3e"></span>≥ −55 дБм — отлично</div>
<div><span class="sw" style="background:#7cc24a"></span>−55…−65 — хорошо</div>
<div><span class="sw" style="background:#f4c430"></span>−65…−70 — приемлемо (проектный порог)</div>
<div><span class="sw" style="background:#ef8e3b"></span>−70…−80 — слабо (вне нормы)</div>
<div><span class="sw" style="background:#d64541"></span>&lt; −80 дБм — нет покрытия</div>
</div>
<div class="note"><b>Результат:</b> 100% рабочих помещений ≥ −70 дБм. Красные зоны — только глубина мокрых техпомещений (санузлы №7–8, тех. помещение №9), нормирование Wi-Fi там не требуется.</div>
</div></div>
<div class="foot"><span>Сетка расчёта 0,3 м · сквозное затухание через ЖБ-стены учтено</span><span>3 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">4</div><h2>Карта покрытия 5 ГГц — зоны уровня сигнала</h2></div>
<div class="body">
<div class="mapwrap">__MAP5__</div>
<div class="side">
<div class="legend">
<div><span class="sw" style="background:#1e8e3e"></span>≥ −55 дБм — приоритетный трафик</div>
<div><span class="sw" style="background:#7cc24a"></span>−55…−65 — стабильно</div>
<div><span class="sw" style="background:#f4c430"></span>−65…−70 — приемлемо</div>
<div><span class="sw" style="background:#ef8e3b"></span>−70…−80 — за стеной (ЖБ +20 дБ)</div>
<div><span class="sw" style="background:#d64541"></span>&lt; −80 дБм — недоступно</div>
</div>
<div class="note"><b>Вывод:</b> 5 ГГц уверенно работает внутри каждого помещения со своим AP. Сквозь ЖБ-стены сигнал падает на ~20 дБ — роуминг между комнатами держать на 2,4 ГГц, 5 ГГц — основной трафик внутри класса.</div>
</div></div>
<div class="foot"><span>DFS-каналы 52–144, ширина 80 МГц в классах, 40 МГц в коридоре</span><span>4 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">5</div><h2>Размещение точек доступа — комментарий по каждой</h2></div>
<div class="body"><div class="cards">__APCARDS__</div></div>
<div class="foot"><span>Все AP — потолок, PoE от коммутатора в серверной №14 · SSID единый, 802.11k/v/r</span><span>5 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">6</div><h2>Уровни сигнала по помещениям</h2></div>
<div class="body" style="flex-direction:column">
<table><thead><tr><th>№</th><th>Помещение</th><th>S, м²</th><th>AP</th><th>2,4 ГГц avg</th><th>min</th><th>≥−70</th><th>5 ГГц avg</th><th>min</th><th>≥−70</th></tr></thead>
<tbody>__TABLE__</tbody></table></div>
<div class="foot"><span>✔ норма выполнена · ~ частичное (техпомещения) · ✘ вне нормы (нормирование не требуется)</span><span>6 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">7</div><h2>Рекомендации по монтажу</h2></div>
<div class="body"><div class="grid2">
<div class="gcard"><b class="t">Высота и место установки</b>Потолочный монтаж на 3,5–4,0 м, в стороне от металлических лотков и светильников (экранирование арматурой ЖБ-перекрытия снижает уровень на 3–6 дБ). Не размещать AP за вентиляционными шахтами и в запотолочных нишах.</div>
<div class="gcard"><b class="t">Питание и трассы</b>PoE 802.3af от коммутатора в серверной №14 (все кабели ≤90 м витой пары Cat5e/6). Для AP-12w/e и AP-18w/e — отдельная группа UPS: коридор и большие классы критичны для бесшовности.</div>
<div class="gcard"><b class="t">Каналы и мощность</b>2,4 ГГц: каналы 1/6/11, чередование по соседним AP, мощность 15–17 дБм (автонастройка Eltex NMS). 5 ГГц: DFS-каналы, 80 МГц в классах №3/12/13, 40 МГц в остальных; minimum RSSI −70 дБм для принудительного роуминга.</div>
<div class="gcard"><b class="t">Проверка после монтажа</b>Валидационный опход анализатором (inSSIDer/EkspertWiFi) по точкам контроля на карте: ожидаемое соответствие расчётным зонам ±5 дБ. При расхождении &gt;8 дБ — ревизия расположения AP или добавление точки в техзону №9–10.</div>
</div></div>
<div class="foot"><span>Eltex WEP-2AC Smart · управление через контроллер Eltex NMS / CAPWAP</span><span>7 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">8</div><h2>Ведомость оборудования</h2></div>
<div class="body"><div class="grid2" style="grid-template-columns:1.2fr 1fr">
<div class="gcard"><b class="t">Основное</b>
Точка доступа Eltex WEP-2AC Smart — <b>11 шт.</b><br>Коммутатор PoE 24 порта (NVS-24P-150 или аналог) — 1 шт.<br>Кабель UTP Cat6 — ≈450 м (средняя трасса 40 м × 11)<br>Розетки/патч-панели, органайзеры — комплект<br>Креёж потолочный (нашивки на шину) — 11 компл.</div>
<div class="gcard"><b class="t">Ограничения проекта</b>
• Расчёт детерминистический, без инструментального обследования — при монтаже возможен перенос AP ±2 м;<br>
• Санузлы №7–8, техпомещение №9, щитовая №15, ИТП №17 — покрытие по остаточному принципу (задача датчиков, не пользователей);<br>
• При увеличении плотности клиентов в классе №12 (&gt;60 устройств) — предусмотреть резерв под 3-ю AP.</div>
</div></div>
<div class="foot"><span>Стоимость и трудозатраты — по локальной смете подрядчика</span><span>8 / 9</span></div>
</section>

<section class="slide">
<div class="head"><div class="n">9</div><h2>Итоги</h2></div>
<div class="body"><ol class="steps">
<li><b>11 точек Eltex WEP-2AC Smart</b> обеспечивают проектное покрытие ≥ −70 дБм на 100% рабочих помещений и 96,6% общей площади этажа (2,4 ГГц).</li>
<li><b>Железобетон с базальтовым наполнением</b> — главный фактор: сквозь стену 5 ГГц теряет ~20 дБ, поэтому схема «AP в каждом помещении», а не «один AP на блок».</li>
<li><b>Большие залы</b> №3, №12, №13 покрыты с запасом; зал №12 (8,6 м ширины) — двумя AP для гарантии edge-скорости.</li>
<li><b>Бесшовность</b>: единый SSID, 802.11k/v/r, minimum RSSI −70 — мобильные клиенты переключаются в коридоре без разрывов сессий.</li>
</ol></div>
<div class="foot"><span>Отчётные материалы: wifi_map_24/5.svg · wifi_res.json · wifi_summary.txt · make_html_mockup.py</span><span>9 / 9</span></div>
</section>

</body></html>"""

html = html.replace('__MAP24__', map24).replace('__MAP5__', map5).replace('__APCARDS__', ap_cards).replace('__TABLE__', trs)
open('wifi_presentation.html', 'w', encoding='utf-8').write(html)
print('written', len(html), 'bytes')
