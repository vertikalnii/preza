# -*- coding: utf-8 -*-
"""Презентация: расчёт размещения точек Wi-Fi Eltex WEP-2AC Smart
по листу 14 «План этажа» (27.03.26 АР). Данные — wifi_res.json, wifi_summary.txt."""
import json
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

DARK = RGBColor(0x1F, 0x2A, 0x44)
ACC = RGBColor(0x0E, 0x7B, 0xA6)
GRAY = RGBColor(0x5A, 0x5A, 0x5A)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x1E, 0x8449 >> 8 & 0xFF if False else 0x84, 0x49)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

res = json.load(open("wifi_res.json", encoding="utf-8"))
APM = res["ap"]  # name -> ([x_px,y_px], room)

# summary rows parsed from wifi_summary.txt
rows = []
for line in open("wifi_summary.txt", encoding="utf-8"):
    line = line.strip()
    if not line or not line[0].isdigit():
        continue
    # № 1 Кабинет ... 3.6× 8.0м S=34.2 2.4: cp -33.6 мин -42.8 | 5: cp -42.0 мин -52.2 | AP:AP-1
    parts = line.split("|")
    head = parts[0]
    tok = head.split()
    num = tok[0]
    dims = next(t for t in tok if "×" in t) + " " + [t for t in tok if t.startswith("×") or "м" in t][0] if False else None
    # simpler regex
    import re
    m = re.match(r"(№\s*\d+)\s+(.*?)\s+([\d.,]+×\s*[\d.,]+м)\s+S=\s*([\d.,]+)\s+2\.4:\s*cp\s*(-?\d+)\s*мин\s*(-?\d+)", head)
    if not m:
        continue
    num, name, dims, area, cp24, min24 = m.groups()
    mm = re.search(r"5:\s*cp\s*(-?\d+)\s*мин\s*(-?\d+)", parts[1])
    cp5, min5 = mm.groups()
    ap = parts[2].replace("AP:", "").strip()
    rows.append(dict(num=num.replace("№", "").strip(), name=name.strip(), dims=dims.replace(" ", ""),
                     area=area, cp24=cp24, min24=min24, cp5=cp5, min5=min5, ap=ap))

def add_slide(title=None, sub=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        tb = s.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.9))
        p = tb.text_frame.paragraphs[0]
        r = p.add_run(); r.text = title
        r.font.size = Pt(28); r.font.bold = True; r.font.color.rgb = DARK
        if sub:
            p2 = tb.text_frame.add_paragraph()
            r2 = p2.add_run(); r2.text = sub
            r2.font.size = Pt(13); r2.font.color.rgb = GRAY
    return s

def bullets(slide, x, y, w, h, items, size=14):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    first = True
    for it in items:
        lvl = 0
        txt = it
        if isinstance(it, tuple):
            txt, lvl = it
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lvl
        r = p.add_run(); r.text = ("• " if lvl == 0 else "– ") + txt
        r.font.size = Pt(size - lvl * 1)
    return tb

# ---------- 1. Титул ----------
s = add_slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
r.fill.solid(); r.fill.fore_color.rgb = DARK; r.line.fill.background()
tb = s.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(11.7), Inches(2.6))
p = tb.text_frame.paragraphs[0]
run = p.add_run(); run.text = "Проект сети Wi-Fi учебного центра"
run.font.size = Pt(40); run.font.bold = True; run.font.color.rgb = RGBColor(255, 255, 255)
p2 = tb.text_frame.add_paragraph()
run = p2.add_run(); run.text = "Расчёт размещения точек доступа Eltex WEP-2AC Smart\nЗоны покрытия 2.4 и 5 ГГц — план этажа, лист 14 (27.03.26 АР)"
run.font.size = Pt(20); run.font.color.rgb = RGBColor(0xBF, 0xD7, 0xE6)
p3 = tb.text_frame.add_paragraph()
run = p3.add_run(); run.text = "9 точек доступа · железобетонные перекрытия с базальтовым наполнением · октябрь 2026"
run.font.size = Pt(14); run.font.color.rgb = RGBColor(0x8F, 0xAF, 0xC4)

# ---------- 2. Исходные данные ----------
s = add_slide("Исходные данные", "Лист 14 «План этажа», 27.03.26 АР")
bullets(s, 0.6, 1.3, 6.1, 5.6, [
    "Здание: учебный центр, 18 помещений, габариты этажа ≈ 26×18 м",
    "Конструктив: монолитный ЖБК каркас; перекрытия 300 мм, стены 200 мм, наполнение — базальтовое волокно, двойное армирование",
    "Высота потолка ~3 м — точка на потолке, высота монтажа 2,7–3,0 м",
    "Клиенты: ноутбуки, смартфоны, планшеты (класс приёма ≥ −70 дБм)",
    "Точки доступа: Eltex WEP-2AC Smart (2×2 MIMO, dual-band concurrent, PoE 802.3af)",
], 15)
bullets(s, 7.0, 1.3, 5.8, 5.6, [
    "Особенности распространения в ЖБ с базальтом:",
    ("затухание одной несущей стены ≈ 12 дБ @ 2,4 ГГц / ≈ 20 дБ @ 5 ГГц", 1),
    ("коэффициент потерь в помещении n = 2,7 (2,4 ГГц) / 3,0 (5 ГГц)", 1),
    ("через коридор = 2 стены: −24 дБ (2,4) / −40 дБ (5)", 1),
    "Санузлы/мокрые зоны и техпомещения экранируют сигнал сильнее обычных стен",
    "Серверная (№14) — AP внутри помещения, выделенный SSID управления",
], 15)

# ---------- 3. Модель расчёта ----------
s = add_slide("Методика радиопланирования", "")
bullets(s, 0.6, 1.3, 12.2, 5.8, [
    "Расчётная модель RSS:  L = Ptx − FSPL(d) − (n−2)·10·lg(d) − k·ATT_стены",
    ("Ptx = 20 дБм (Eltex WEP-2AC Smart, EIRP до 23 дБм учтён с запасом на антенну 2 дБи)", 1),
    ("FSPL — свободное пространство: 40 дБ @2,4 ГГц / 47 дБ @5 ГГц на 1 м", 1),
    ("k — число пересечённых стен по лучу «точка → приёмник» (граф помещений из DXF-геометрии плана)", 1),
    "Сетка расчёта 0,25 м поверх векторной геометрии листа 14; калибровка план→метры по экспликации",
    "Критерии качества: ≥ −60 дБм отлично · ≥ −67 хорошо · ≥ −70 приемлемо (порог клиентов) · < −75 вне_service",
    "Целевая загрузка: основной трафик — 5 ГГц в пределах одного помещения; 2,4 ГГц — резерв/IoT/дальние зоны",
    "Роуминг: 802.11k/v, каналы чередуются 1/6/11 (2,4) и 36/40/44/48/149/153 (5), мощность снижена до уровня ‹перекрываемого› соседом на −75 дБм",
], 15)

# ---------- 4. Карта 2.4 ГГц ----------
s = add_slide("Карта покрытия 2,4 ГГц", "9 точек Eltex WEP-2AC Smart · пороги −60/−67/−70 дБм")
pic_w = Inches(9.2)
s.shapes.add_picture("wifi_map_24.png", Inches(0.4), Inches(1.25), width=pic_w)
bullets(s, 9.8, 1.3, 3.3, 5.8, [
    "Учебные/рабочие зоны: 97,8% площади ≥ −70 дБм",
    "Худшие точки — дальние углы склада СИЗ (№10): −71 дБм",
    "Каждое помещение получает ≥ −60 дБм в своей зоне от «домашней» AP",
    "Пересечение сот соседних комнат держим ≤ −72 дБм — чтобы клиент не «залипал» на чужой AP",
], 13)

# ---------- 5. Карта 5 ГГц ----------
s = add_slide("Карта покрытия 5 ГГц", "Затухание в ЖБ-стенах +8 дБ относительно 2,4 ГГц")
s.shapes.add_picture("wifi_map_5.png", Inches(0.4), Inches(1.25), width=pic_w)
bullets(s, 9.8, 1.3, 3.3, 5.8, [
    "Покрытие 5 ГГц ограничено пределами помещения установки AP (73,9% нормируемых зон ≥ −70 дБм)",
    "Через одну ЖБ-стену 5 ГГц деградирует до −80…−90 дБм — межкомнатный роуминг планируем на 2,4 ГГц",
    "Внутри классов и коридора — уверенные −35…−50 дБм: приоритет полосы именно здесь",
], 13)

# ---------- 6. Размещение точек: комментарии по каждой ----------
s = add_slide("Размещение точек доступа — комментарий по каждой", "")
hdr = ["AP", "Точка установки", "Комментарий"]
notes = {
 "AP-1":  "Кабинет №1 (3,6×8,0 м), потолок по центру. Покрывает кабинет специалистов УТЦ (−34 дБм) и через тамбур — раздевалку №11 (−64 дБм); гардероб №6 обслуживает с уровнем −54 дБм.",
 "AP-2":  "Кабинет преподавателей №2 (3,1×2,7 м). Малое помещение, один AP с избытком (−25 дБм); мощность снизить до −6 дБм во избежание overplotting.",
 "AP-3":  "Класс ПК №3 (S=90,8 м², вытянутый 3,1×5,1 по сетке — фактически зал). Центральный монтаж, 2×2 MIMO достаточно для плотности до ~40 клиентов.",
 "AP-4":  "Класс ТЭС УЭЦН №4 (6,2×7,3 м). Центр комнаты, уровень −34 дБм в среднем; станки/стенды экранируют — проверять посты у дальней стены (не ниже −60).",
 "AP-5":  "Класс корп. обучения №3 (№5, 3,8×7,3 м). Монтаж над рабочей зоной, ближе к середине длинной оси; −32 дБм.",
 "AP-12w":"Западная половина большого класса №12 (11,8×8,3 м). Один AP не покрывает ширину зала через внутренние ЖБ-колонны — зал разрезан на две соты.",
 "AP-12e":"Восточная половина класса №12 и класс №13 (S=130 м²): −36…−48 дБм; обеспечивает смежные склад-архив №16 (−51 дБм) и ИТП как источник помех учитывается.",
 "AP-18w":"Коридор №18 (9,0×2,8 м), западная треть. «Дальнобойная» сота: гардероб, раздевалка, техпомещение; −29 дБм в коридоре.",
 "AP-18e":"Коридор, восточная треть, рядом с серверной №14 и электрощитовой №15. Серверная получает −56 дБм (для мониторинга/AP-управления этого достаточно).",
}
order = ["AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "AP-12w", "AP-12e", "AP-18w", "AP-18e"]
room_of = {r["ap"]: f'№{r["num"]} {r["name"]}' for r in rows}
tbl_shape = s.shapes.add_table(len(order) + 1, 3, Inches(0.4), Inches(1.25), Inches(12.5), Inches(5.9))
tbl = tbl_shape.table
tbl.columns[0].width = Inches(1.0); tbl.columns[1].width = Inches(3.1); tbl.columns[2].width = Inches(8.4)
for j, h in enumerate(hdr):
    c = tbl.cell(0, j); c.text = h
    for p in c.text_frame.paragraphs:
        for r_ in p.runs: r_.font.bold = True; r_.font.size = Pt(12)
for i, ap in enumerate(order, start=1):
    vals = [ap, room_of.get(ap, ""), notes[ap]]
    for j, v in enumerate(vals):
        c = tbl.cell(i, j); c.text = v
        for p in c.text_frame.paragraphs:
            for r_ in p.runs:
                r_.font.size = Pt(10 if j == 2 else 11)
                if j == 0: r_.font.bold = True

# ---------- 7. Таблица уровней по помещениям ----------
s = add_slide("Уровни сигнала по помещениям", "cp — средний RSS в комнате, min — худшая точка")
cols = ["№", "Помещение", "Размеры", "S, м²", "2,4 ср", "2,4 мин", "5 ср", "5 мин", "AP"]
tw = [0.5, 3.6, 1.3, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0]
tbl = s.shapes.add_table(len(rows) + 1, len(cols), Inches(0.4), Inches(1.2), Inches(12.4), Inches(6.0)).table
for j, w in enumerate(tw): tbl.columns[j].width = Inches(w)
for j, h in enumerate(cols):
    c = tbl.cell(0, j); c.text = h
    for p in c.text_frame.paragraphs:
        for r_ in p.runs: r_.font.bold = True; r_.font.size = Pt(10)
for i, r in enumerate(rows, start=1):
    vals = [r["num"], r["name"], r["dims"], r["area"], r["cp24"], r["min24"], r["cp5"], r["min5"], r["ap"]]
    for j, v in enumerate(vals):
        c = tbl.cell(i, j); c.text = str(v)
        col = None
        if j in (4, 5, 6, 7):
            try:
                iv = int(str(v).replace("−", "-"))
                col = GREEN if iv >= -67 else (RGBColor(0xE6, 0x7E, 0x22) if iv >= -70 else RED)
            except Exception: pass
        for p in c.text_frame.paragraphs:
            for r_ in p.runs:
                r_.font.size = Pt(9)
                if col is not None: r_.font.color.rgb = col

# ---------- 8. Выводы ----------
s = add_slide("Выводы и рекомендации", "")
bullets(s, 0.6, 1.3, 12.3, 5.9, [
    "Достаточно 9 точек Eltex WEP-2AC Smart: все нормируемые помещения получают ≥ −60 дБм внутри своей зоны, 97,8% рабочих зон ≥ −70 дБм на 2,4 ГГц",
    "Железобетон с базальтовым наполнением — главный фактор: одна стена = −12 дБ (2,4) / −20 дБ (5). Размещать AP строго внутри помещений, а не в коридоре «на просвет»",
    "Большие залы (№12/13, 11,8×8,3 м) требуют двух сот — единый AP не проходит по ширине через колонны каркаса",
    "5 ГГц использовать только в границах помещения установки AP; межкомнатный роуминг и IoT держать на 2,4 ГГц",
    "Питание: PoE 802.3af от коммутатора в серверной №14; трассы слаботока прокладывать в лотках над подвесным потолком, минуя ЖБ-перегородки",
    "После монтажа — активное радиообследование (in-site survey) и настройка мощностей: соседние соты должны перекрываться на уровне ≤ −72 дБм",
    "Резерв ёмкости: в классах №3 и №12 при >50 клиентов добавить вторую радиокарту/AP на 5 ГГц (WEP-2AC Smart поддерживает concurrent)",
], 15)

out = "out/WiFi_Eltex_WEP-2AC_план_лист14.pptx"
prs.save(out)
print("saved", out, len(prs.slides.__iter__.__self__._sldIdLst), "slides")
