# -*- coding: utf-8 -*-
"""Презентация Wi-Fi — дизайн-версия: карточки, KPI-баннеры, цветные статусы."""
import json
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

# ---------- палитра ----------
NAVY   = RGBColor(0x0B, 0x3D, 0x66)
NAVY2  = RGBColor(0x14, 0x5A, 0x8F)
TEAL   = RGBColor(0x00, 0xA5, 0x96)
GOLD   = RGBColor(0xFF, 0xD5, 0x4F)
GREEN  = RGBColor(0x1E, 0x8E, 0x3E)
AMBER  = RGBColor(0xF9, 0xA8, 0x25)
RED    = RGBColor(0xC6, 0x28, 0x28)
INK    = RGBColor(0x21, 0x21, 0x21)
GREY   = RGBColor(0x60, 0x6C, 0x76)
LIGHT  = RGBColor(0xEE, 0xF3, 0xF8)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
FONT   = 'Calibri'

RES = json.load(open('out/wifi_res.json'))
APs = RES['AP']
# --- пересчёт сводки напрямую из поля wifi_field.npz (rid == номер помещения) ---
import numpy as np
_fd = np.load('out/wifi_field.npz')
_pts, _rid, _b24, _b5 = _fd['pts'], _fd['rid'].astype(int), _fd['b24'], _fd['b5']
summary = {}
for k, v in RES['summary'].items():
    m = _rid == int(k)
    if not m.any():
        summary[k] = v; continue
    summary[k] = dict(v)
    summary[k].update(avg24=float(_b24[m].mean()), min24=float(_b24[m].min()),
                     cov24=float((_b24[m] >= -70).mean()*100),
                     avg5=float(_b5[m].mean()), min5=float(_b5[m].min()),
                     cov5=float((_b5[m] >= -70).mean()*100))

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height


def slide():
    return prs.slides.add_slide(BLANK)


def rect(s, x, y, w, h, fill, line=None, shadow=False, round_=False):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE,
                             x, y, w, h)
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line:
        shp.line.color.rgb = line; shp.line.width = Pt(0.75)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if round_:
        try: shp.adjustments[0] = 0.08
        except Exception: pass
    return shp


def txt(s, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, leading=1.0, space_after=0):
    """runs: str | list[(text, dict-overrides)] | list-of-lines each a str/list"""
    tb = s.shapes.add_textbox(x, y, w, h); tf = tb.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = runs if isinstance(runs, list) else [runs]
    # allow nested lists of paragraphs (each paragraph = str or list of runs)
    if lines and all(isinstance(l, list) and l and all(isinstance(x, list) for x in l) for l in lines):
        lines = [x for l in lines for x in l]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = leading
        if space_after: p.space_after = Pt(space_after)
        if isinstance(ln, tuple):
            parts = [ln]
        elif isinstance(ln, list):
            parts = [x if isinstance(x, tuple) else (x, {}) for x in ln]
        else:
            parts = [(ln, {})]
        for t, ov in parts:
            r = p.add_run(); r.text = t
            f = r.font
            f.name = ov.get('font', FONT); f.size = Pt(ov.get('size', size))
            f.bold = ov.get('bold', bold); f.color.rgb = ov.get('color', color)
            if 'italic' in ov: f.italic = ov['italic']
    return tb


def header(s, kicker, title, num):
    rect(s, 0, 0, SW, Inches(1.02), NAVY)
    rect(s, 0, Inches(1.02), SW, Pt(3), GOLD)
    txt(s, Inches(0.55), Inches(0.12), Inches(10.5), Inches(0.3),
        kicker.upper(), size=11, color=GOLD, bold=True)
    txt(s, Inches(0.55), Inches(0.40), Inches(11.0), Inches(0.55),
        title, size=25, color=WHITE, bold=True)
    txt(s, Inches(12.35), Inches(0.28), Inches(0.7), Inches(0.5),
        num, size=16, color=RGBColor(0x9F, 0xC5, 0xE2), bold=True, align=PP_ALIGN.RIGHT)


def footer(s, text='Wi-Fi проектирование · Eltex WEP-2AC Smart · лист 14 АР 27.03.26'):
    rect(s, 0, SH - Inches(0.32), SW, Inches(0.32), LIGHT)
    txt(s, Inches(0.55), SH - Inches(0.28), Inches(12.2), Inches(0.24),
        text, size=9, color=GREY)


def pic_fit(s, path, x, y, w, h):
    iw, ih = Image.open(path).size
    ar = iw / ih; box = w / h
    if ar > box:
        pw, ph = w, int(w / ar)
    else:
        ph, pw = h, int(h * ar)
    return s.shapes.add_picture(path, x + int((w - pw) / 2), y + int((h - ph) / 2), pw, ph)


def chip(s, x, y, label, color, w=None):
    w = w or Inches(0.42 + 0.12 * len(label))
    c = rect(s, x, y, w, Inches(0.34), color, round_=True)
    txt(s, x, y + Inches(0.03), w, Inches(0.28), label, size=11, color=WHITE,
        bold=True, align=PP_ALIGN.CENTER)
    return c




def pic_fit_in_box(s, path, x, y, w, h):
    """Картинка вписана в бокс по ВЫСОТЕ (карты/планы читаются целиком),
    центрируется по горизонтали; тонкая светлая рамка вокруг изображения."""
    iw, ih = Image.open(path).size
    ph = int(h); pw = int(h * iw / ih)
    px_ = x + int((w - pw) / 2); py_ = y
    fr = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px_ - Emu(19050), py_ - Emu(19050),
                            pw + Emu(38100), ph + Emu(38100))
    fr.fill.background(); fr.line.color.rgb = RGBColor(0xC9, 0xD4, 0xE0); fr.line.width = Pt(1)
    fr.shadow.inherit = False
    return s.shapes.add_picture(path, px_, py_, pw, ph)


# ============================================================ 1 ТИТУЛ
s = slide()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, Inches(4.62), SW, Pt(2.5), GOLD)
# декоративные "волны" сигнала (обрезаны по слайду — допустимый bleed)
import copy
for i, (r_, col) in enumerate([(3.1, NAVY2), (2.2, RGBColor(0x1E, 0x6E, 0xA5)), (1.35, TEAL)]):
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.9 - r_), Inches(1.15 - r_), Inches(2 * r_), Inches(2 * r_))
    o.fill.solid(); o.fill.fore_color.rgb = col; o.line.color.rgb = GOLD if i == 2 else col
    o.line.width = Pt(1.2); o.shadow.inherit = False
# перемещаем овалы в начало z-порядка, чтобы текст был поверх
spTree = s.shapes._spTree
ovals = [sh for sh in list(s.shapes) if str(sh.shape_type).startswith('AUTO_SHAPE') and sh.name.startswith('Oval')]
for el in reversed([o._element for o in ovals]):
    spTree.remove(el)
    spTree.insert(2, el)
txt(s, Inches(10.62), Inches(0.85), Inches(0.8), Inches(0.6), '≈', size=30, color=GOLD, bold=True)
txt(s, Inches(0.75), Inches(1.5), Inches(9.6), Inches(0.4),
    'ПРОЕКТ СЕТИ БЕСПРОВОДНОГО ДОСТУПА · УЧЕБНЫЙ ЦЕНТР', size=14, color=GOLD, bold=True)
txt(s, Inches(0.75), Inches(2.05), Inches(10.6), Inches(1.7),
    [[('Размещение точек Wi-Fi', {'size': 52, 'bold': True, 'color': WHITE})],
     [('Eltex WEP-2AC Smart — расчёт покрытия 2,4 и 5 ГГц', {'size': 24, 'color': RGBColor(0xBF, 0xD9, 0xEE)})]],
    leading=1.15)
pic_fit(s, 'out/kpi_banner.png', Inches(0.75), Inches(4.95), Inches(11.8), Inches(1.55))
txt(s, Inches(0.75), Inches(6.85), Inches(11.8), Inches(0.4),
    'Основание: план этажа, лист 14 альбома АР от 27.03.26 · монолитный каркас, ЖБ стены и перекрытия с базальтовым наполнением',
    size=11, color=RGBColor(0x9F, 0xC5, 0xE2))

# ============================================================ 2 КЛЮЧЕВЫЕ РЕЗУЛЬТАТЫ
s = slide(); header(s, 'Резюме для руководства', 'Ключевые результаты проектирования', '01')
cards = [
    ('11', 'точек доступа', 'Eltex WEP-2AC Smart\nпотолок, PoE 802.3af', NAVY2),
    ('100%', 'рабочих зон · 2,4 ГГц', '11 учебных/служебных помещений\nRSSI ≥ −70 дБм на всей площади', GREEN),
    ('96,6%', 'этажа · 2,4 ГГц', 'включая коридор и смежные\nвспомогательные помещения', TEAL),
    ('−67 дБм', 'гарантированный край', 'резерв ~10 дБ до порога\nклиентов ноутбуков/телефонов', RGBColor(0x8E, 0x24, 0xAA)),
]
cw, ch, gap = Inches(2.95), Inches(2.35), Inches(0.18)
x0 = (SW - (cw * 4 + gap * 3)) / 2
for i, (big, ttl, sub, col) in enumerate(cards):
    x = x0 + i * (cw + gap)
    rect(s, x, Inches(1.5), cw, ch, LIGHT, round_=True)
    rect(s, x, Inches(1.5), cw, Inches(0.14), col)
    txt(s, x + Inches(0.15), Inches(1.85), cw - Inches(0.3), Inches(0.85), big,
        size=34, color=col, bold=True, align=PP_ALIGN.CENTER)
    txt(s, x + Inches(0.15), Inches(2.72), cw - Inches(0.3), Inches(0.4), ttl,
        size=15, color=INK, bold=True, align=PP_ALIGN.CENTER)
    txt(s, x + Inches(0.15), Inches(3.18), cw - Inches(0.3), Inches(0.75), sub,
        size=11, color=GREY, align=PP_ALIGN.CENTER, leading=1.1)
rect(s, Inches(0.75), Inches(4.35), Inches(11.85), Inches(2.35), WHITE, line=RGBColor(0xD5, 0xDE, 0xE8), round_=True)
txt(s, Inches(1.05), Inches(4.55), Inches(11.3), Inches(0.35), 'Что это значит на практике', size=15, color=NAVY, bold=True)
bullets = [
    'Каждое учебное помещение обеспечено собственным радиоканалом: класс ПК, два больших класса, кабинеты — по одной точке; широкие залы №12/13 закрываются двумя AP.',
    'Коридор покрыт двумя точками «сотами» к санузлам, складу СИЗ и раздевалке — там Wi-Fi не нормируется, но связь для IoT/дежурных сохраняется.',
    'На 5 ГГц сквозное покрытие сквозь ЖБ стены ограничено (физика): приоритет трафика — внутри своего помещения, роуминг 802.11k/v/r держит сессию при перемещении.',
    'Запас по сигналу позволяет стойко принимать видеозанятия и тестирование даже в дальних углах при открытии дверей и перестановке мебели.',
]
tb = txt(s, Inches(1.05), Inches(4.95), Inches(11.3), Inches(1.7),
         [[('▸ ', {'color': TEAL, 'bold': True}), (b, {})] for b in bullets],
         size=12.5, color=INK, leading=1.12, space_after=4)
footer(s)

# ============================================================ 3 ИСХОДНЫЕ ДАННЫЕ
s = slide(); header(s, 'База расчёта', 'Исходные данные объекта', '02')
# левая колонка — карточки параметров
params = [
    ('Габариты этажа', '30,0 × 27,0 м (лист 14 АР)'),
    ('Помещений', '18 шт., экспликация сверена с чертежом'),
    ('Конструкции', 'монолитный ЖБ-каркас; стены 200 мм, перекрытие 300 мм, наполнение — базальтовое волокно, арматура Ø10–16'),
    ('Высота монтажа', 'потолок, ≈ 3,5–4,0 м от пола'),
    ('Клиенты', 'ноутбуки/телефоны классов Wi‑Fi 5, приём −70 дБм'),
]
y = Inches(1.45)
for k, v in params:
    rect(s, Inches(0.6), y, Inches(5.9), Inches(0.98), LIGHT, round_=True)
    rect(s, Inches(0.6), y, Inches(0.12), Inches(0.98), NAVY2)
    txt(s, Inches(0.9), y + Inches(0.1), Inches(5.4), Inches(0.3), k, size=12.5, color=NAVY, bold=True)
    txt(s, Inches(0.9), y + Inches(0.42), Inches(5.4), Inches(0.5), v, size=11.5, color=INK, leading=1.05)
    y += Inches(1.1)
# правая колонка — модель затуханий
rect(s, Inches(6.85), Inches(1.45), Inches(5.9), Inches(3.1), NAVY, round_=True)
txt(s, Inches(7.1), Inches(1.62), Inches(5.4), Inches(0.35), 'Радиомодель зданий (принято)', size=14, color=GOLD, bold=True)
rows = [
    ('Свободное пространство', 'FSPL 40 дБ @1 м'),
    ('Открытое помещение (коридор)', 'затухание по пути n = 2,7 / 3,0'),
    ('Стена ЖБ + базальт, 200 мм', '12 дБ @2,4 · 20 дБ @5'),
    ('Перегородка гипрок/кирпич', '6 дБ @2,4 · 9 дБ @5'),
    ('Перекрытие между этажами', '18–25 дБ (не используется)'),
]
yy = Inches(2.1)
for a, b in rows:
    txt(s, Inches(7.1), yy, Inches(3.3), Inches(0.4), a, size=11.5, color=WHITE)
    txt(s, Inches(10.35), yy, Inches(2.3), Inches(0.4), b, size=11.5, color=RGBColor(0xBF, 0xD9, 0xEE), align=PP_ALIGN.RIGHT)
    yy += Inches(0.47)
rect(s, Inches(6.85), Inches(4.75), Inches(5.9), Inches(1.9), WHITE, line=RGBColor(0xD5, 0xDE, 0xE8), round_=True)
txt(s, Inches(7.1), Inches(4.9), Inches(5.4), Inches(0.3), 'Требования к качеству связи', size=13, color=NAVY, bold=True)
q = [('≥ −60 дБм', 'отлично (видео, VoWiFi)', GREEN),
     ('≥ −67 дБм', 'хорошо (веб, тесты)', AMBER),
     ('≥ −70 дБм', 'минимум для клиентов', RED)]
xx = Inches(7.1)
for lab, desc, col in q:
    chip(s, xx, Inches(5.3), lab, col, w=Inches(1.75))
    txt(s, xx, Inches(5.75), Inches(1.8), Inches(0.75), desc, size=10, color=GREY, align=PP_ALIGN.CENTER, leading=1.05)
    xx += Inches(1.85)
footer(s)

# ============================================================ 4 МЕТОДИКА
s = slide(); header(s, 'Как считали', 'Методика радиопланирования', '03')
steps = [
    ('1 · Геометрия', 'Векторное извлечение линий стен листа 14 PDF → калибровка по размерным цепям 30 000×27 000 мм → метрическая модель помещений (расхождения с экспликацией ≤ 8%).'),
    ('2 · Модель потерь', 'RSS = Tx 20 дБм − FSPL(d) − (n−2)·10·lg d − Σ ATT стен; трассировка луча AP→точка с подсчётом пересечённых стен (ray-casting).'),
    ('3 · Сетка расчёта', 'Растр 0,05 м только внутри помещений (44 900 точек); для каждой точки — лучший из 11 передатчиков, раздельно 2,4 и 5 ГГц.'),
    ('4 · Оптимизация', 'Жадный выбор позиций: максимум площади ≥ −70 дБм при минимуме AP; фиксация центров помещений и симметрия коридора.'),
    ('5 · Контроль', 'Проверка: все AP внутри контура, минимум RSSI по каждому помещению, % площади выше порогов −60/−67/−70.'),
]
y = Inches(1.4)
for t, b in steps:
    rect(s, Inches(0.6), y, Inches(12.1), Inches(1.02), LIGHT, round_=True)
    rect(s, Inches(0.6), y, Inches(2.35), Inches(1.02), NAVY2, round_=True)
    txt(s, Inches(0.75), y + Inches(0.3), Inches(2.1), Inches(0.5), t, size=13, color=WHITE, bold=True)
    txt(s, Inches(3.2), y + Inches(0.12), Inches(9.3), Inches(0.85), b, size=11.5, color=INK, leading=1.08,
        anchor=MSO_ANCHOR.MIDDLE)
    y += Inches(1.12)
footer(s)

# ============================================================ 5 СХЕМА РАЗМЕЩЕНИЯ
s = slide(); header(s, 'Схема', 'Размещение 11 точек доступа на плане этажа', '04')
pic_fit_in_box(s, 'out/wifi_layout.png', Inches(0.5), Inches(1.2), Inches(9.15), Inches(5.75))
lx = Inches(9.9)
rect(s, lx, Inches(1.35), Inches(3.0), Inches(5.5), LIGHT, round_=True)
txt(s, lx + Inches(0.2), Inches(1.55), Inches(2.6), Inches(0.3), 'Как читать схему', size=14, color=NAVY, bold=True)
leg = [
 ('▲', 'маркер точки доступа Eltex WEP-2AC Smart с подписью AP-n и координатами'),
 ('№', 'номер помещения по экспликации листа 14 АР'),
 ('линии', 'несущие ЖБ стены 200 мм и перегородки, масштаб 1:100'),
 ('сетка', 'габариты этажа 30,0 × 27,0 м; линейка 10 м внизу'),
 ('пастель', 'помещения разделены по экспликации листа 14; номера в кружках'),
]
yy = Inches(2.05)
for k, v in leg:
    txt(s, lx + Inches(0.2), yy, Inches(0.75), Inches(0.3), k, size=12, color=TEAL, bold=True)
    txt(s, lx + Inches(0.95), yy, Inches(1.95), Inches(1.1), v, size=10.5, color=INK, leading=1.08)
    yy += Inches(1.18)
txt(s, lx + Inches(0.2), Inches(6.45), Inches(2.6), Inches(0.4),
    'Тепловые карты уровней сигнала — на следующих слайдах', size=9.5, color=GREY, leading=1.05)
footer(s)

# ============================================================ 6 КАРТА 2.4
s = slide(); header(s, 'Покрытие', 'Зона покрытия 2,4 ГГц — основной диапазон', '05')
pic_fit_in_box(s, 'out/wifi_map_24.png', Inches(0.4), Inches(1.2), Inches(9.4), Inches(5.7))
rx = Inches(10.0)
rect(s, rx, Inches(1.35), Inches(2.95), Inches(5.4), LIGHT, round_=True)
txt(s, rx + Inches(0.2), Inches(1.55), Inches(2.55), Inches(0.3), 'Комментарий', size=14, color=NAVY, bold=True)
txt(s, rx + Inches(0.2), Inches(1.95), Inches(2.6), Inches(4.7),
    ['• Цвет заливает каждую комнату — это зоны уровня сигнала RSSI; белые изолинии — границы зон −85/−80/−70/−67/−60/−50 дБм. Покрытие ≥ −70 дБм: 96,6% площади этажа, 100% рабочих помещений.',
     '• Сквозь одну ЖБ стену приём ≈ −45…−55 дБм — соседние комнаты слышат AP друг друга (используем для роуминга).',
     '• Каналы 1/6/11 распределяются шахматкой по коридору и северному ряду кабинетов.',
     '• Для санузлов/техпомещений сигнал ниже порога — это допустимо (не нормируются).'],
    size=11.5, color=INK, leading=1.15, space_after=8)
footer(s)

# ============================================================ 7 КАРТА 5
s = slide(); header(s, 'Покрытие', 'Зона покрытия 5 ГГц — приоритетный трафик', '06')
pic_fit_in_box(s, 'out/wifi_map_5.png', Inches(0.4), Inches(1.2), Inches(9.4), Inches(5.7))
rx = Inches(10.0)
rect(s, rx, Inches(1.35), Inches(2.95), Inches(5.4), LIGHT, round_=True)
txt(s, rx + Inches(0.2), Inches(1.55), Inches(2.55), Inches(0.3), 'Комментарий', size=14, color=NAVY, bold=True)
txt(s, rx + Inches(0.2), Inches(1.95), Inches(2.6), Inches(4.7),
    ['• Внутри «своего» помещения 5 ГГц держит ≥ −70 дБм на 100% площади (средние −32…−44 дБм) — сюда направляем видео и тесты (band steering).',
     '• ЖБ+базальт стоит 20 дБ против 12 дБ на 2,4 ГГц: сквозь одну стену приём −60…−70 дБм, сквозь две — ниже порога (затемнённые участки карты); ≥ −70 дБм — 86% площади этажа.',
     '• Широкие каналы 80 МГц включаем только в залах №12/13 и коридоре; DFS-каналы — вне близости окон.',
     '• Минус 10 дБ запаса по краю зоны компенсируется высотой потолка и ориентацией антенн вниз.'],
    size=11.5, color=INK, leading=1.15, space_after=8)
footer(s)

# ============================================================ 8 КОММЕНТАРИИ ПО AP
s = slide(); header(s, 'Детализация', 'Комментарии по каждой точке доступа', '07')
ap_notes = {
 'AP-1': 'Кабинет специалистов УТЦ (№1) — центр помещения; заодно простреливает серверную №14 через одну стену.',
 'AP-2': 'Кабинет преподавателей (№2) — компактный кабинет, один AP с запасом; сервит-доступ к №14.',
 'AP-3': 'Класс ПК (№3) — самый плотный трафик (30 рабочих мест); AP над рядом столов, канал 1.',
 'AP-4': 'Класс ТЭС УЭЦН (№4) — стенд + проектор; наведение на зону слушателей, канал 6.',
 'AP-5': 'Класс корп. обучения №3 (№5) — зеркален AP-4, симметричная сетка каналов 11.',
 'AP-6': 'Гардероб (№6) — покрытие входа и зоны ожидания; низкая плотность клиентов, эконом-режим.',
 'AP-12w': 'Западная половина большого класса №12 (85 м²) — ширина зала > эффективного радиуса одной AP на 5 ГГц.',
 'AP-12e': 'Восточная половина класса №12 — вместе с AP-12w дают бесшовную ячеистую зону, каналы разносятся на 1/6.',
 'AP-13': 'Класс корп. обучения №1 (96 м²) — единый AP в центре; примыкающие №15/16 получают остаточный сигнал.',
 'AP-18w': 'Западный коридор — «сота» для №7–11 (санузлы, склад СИЗ, раздевалка); висячая установка у подвесного потолка.',
 'AP-18e': 'Восточный коридор у группы №14–17 — покрытие транзита и служебных помещений, стыкуется с AP-1/AP-13.',
}
items = list(ap_notes.items())
colw = Inches(6.0)
# компактные карточки в 2 колонки: левая — 6, правая — 5
colw = Inches(6.0)
per_col_h = Inches(5.55)
rowh = per_col_h / 6
for i, (name, note) in enumerate(items):
    if i < 6:
        cx = Inches(0.55); k = i
    else:
        cx = Inches(6.78); k = i - 6
    cy = Inches(1.26) + k * rowh
    hh = rowh - Inches(0.06)
    rect(s, cx, cy, colw, hh, WHITE, line=RGBColor(0xD5, 0xDE, 0xE8), round_=True)
    rect(s, cx, cy, Inches(0.1), hh, TEAL)
    txt(s, cx + Inches(0.22), cy + Inches(0.04), Inches(1.3), Inches(0.28), name, size=12, color=NAVY, bold=True)
    xy = APs[name]
    txt(s, cx + Inches(1.5), cy + Inches(0.06), Inches(4.35), Inches(0.26),
        f'x={xy[0]:.1f} м · y={xy[1]:.1f} м', size=8.5, color=GREY, align=PP_ALIGN.RIGHT)
    txt(s, cx + Inches(0.22), cy + Inches(0.32), Inches(5.6), hh - Inches(0.34), note, size=9, color=INK, leading=0.98)
footer(s)

# ============================================================ 9 ТАБЛИЦА ПО ПОМЕЩЕНИЯМ
s = slide(); header(s, 'Цифры', 'Уровни сигнала по всем 18 помещениям', '08')
work = {'1','2','3','4','5','6','10','11','12','13','18'}
hdr = ['№', 'Помещение', 'S, м²', 'AP', '2,4 ГГц avg/min', 'cov ≥−70', '5 ГГц avg/min', 'cov ≥−70', 'Статус']
widths = [0.45, 2.75, 0.7, 0.95, 1.7, 1.05, 1.7, 1.05, 1.0]
tw = sum(widths)
tbl = s.shapes.add_table(19, 9, Inches((13.333 - tw) / 2), Inches(1.28), Inches(tw), Inches(5.5)).table
for j, w in enumerate(widths): tbl.columns[j].width = Inches(w)
for j, h in enumerate(hdr):
    c = tbl.cell(0, j); c.text = h
    c.fill.solid(); c.fill.fore_color.rgb = NAVY
    p = c.text_frame.paragraphs[0]; p.runs[0].font.size = Pt(10.5); p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = WHITE; p.runs[0].font.name = FONT
    p.alignment = PP_ALIGN.CENTER
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
for i, (no, v) in enumerate(sorted(summary.items(), key=lambda kv: int(kv[0]))):
    row = tbl.rows[i + 1]; row.height = Inches(0.28)
    is_work = no in work
    stat_col = GREEN if (is_work and v['cov24'] >= 99.9) else (AMBER if is_work else RGBColor(0x9E, 0x9E, 0x9E))
    stat_txt = '✔ норма' if (is_work and v['cov24'] >= 99.9) else ('~ рабоч.' if is_work else '— служеб.')
    cells = [no, v['name'], f"{v['area']:.0f}", v['ap'],
             f"{v['avg24']:.0f} / {v['min24']:.0f}", f"{v['cov24']:.0f}%",
             f"{v['avg5']:.0f} / {v['min5']:.0f}", f"{v['cov5']:.0f}%", stat_txt]
    for j, val in enumerate(cells):
        c = row.cells[j]; c.text = str(val)
        c.fill.solid(); c.fill.fore_color.rgb = WHITE if i % 2 == 0 else LIGHT
        c.margin_top = c.margin_bottom = Pt(1)
        p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if j != 1 else PP_ALIGN.LEFT
        r = p.runs[0]; r.font.size = Pt(9.5); r.font.name = FONT
        if j == 8: r.font.color.rgb = stat_col; r.font.bold = True
        elif j == 1: r.font.color.rgb = INK
        else: r.font.color.rgb = INK
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
txt(s, Inches(0.6), Inches(6.95), Inches(12.1), Inches(0.3),
    [[('✔ ', {'color': GREEN, 'bold': True}), ('нормируемое помещение, полное покрытие · ', {}),
      ('~ ', {'color': AMBER, 'bold': True}), ('рабочее с частичным 5 ГГц (сквозь ЖБ) · ', {}),
      ('— ', {'color': GREY, 'bold': True}), ('санитарные/технические: Wi-Fi не нормируется', {})]],
    size=10.5, color=GREY)
footer(s)

# ============================================================ 10 ВЫВОДЫ
s = slide(); header(s, 'Итог', 'Выводы и рекомендации по монтажу', '09')
rect(s, Inches(0.6), Inches(1.4), Inches(6.0), Inches(2.6), LIGHT, round_=True)
txt(s, Inches(0.9), Inches(1.6), Inches(5.4), Inches(0.35), 'Выводы', size=15, color=NAVY, bold=True)
txt(s, Inches(0.9), Inches(2.05), Inches(5.5), Inches(1.9),
    [['▸ 11 AP Eltex WEP-2AC Smart закрывают 100% рабочих помещений на 2,4 ГГц (RSSI ≥ −70 дБм).'],
     ['▸ На 5 ГГц полное покрытие внутри каждого помещения; сквозь ЖБ+базальт стены приём ограничен — решается band steering и роумингом.'],
     ['▸ Резерв производительности: средние уровни −22…−35 дБм позволяют плотность ≥ 30 клиентов на AP без деградации.']],
    size=12, color=INK, leading=1.12, space_after=7)
rect(s, Inches(6.85), Inches(1.4), Inches(6.0), Inches(2.6), NAVY, round_=True)
txt(s, Inches(7.15), Inches(1.6), Inches(5.4), Inches(0.35), 'Рекомендации по монтажу', size=15, color=GOLD, bold=True)
txt(s, Inches(7.15), Inches(2.05), Inches(5.5), Inches(1.9),
    [['▸ Установка на потолок, высота 3,5–4 м, антеннами вниз; питание PoE 802.3af от коммутатора IDF (серверная №14).'],
     ['▸ Каналы: 1/6/11 шахматкой по периметру; 5 ГГц — 80 МГц в залах, DFS вне окон; мощность down-link −2 дБ от максимума.'],
     ['▸ Настроить 802.11k/v/r и band steering; SSID единый, VLAN учёба/персонал; pre-auth гостевой портал.'],
     ['▸ После монтажа — активный site survey (walk-test) и калибровка модели по замерам.']],
    size=12, color=WHITE, leading=1.1, space_after=6)
rect(s, Inches(0.6), Inches(4.3), Inches(12.25), Inches(2.35), WHITE, line=RGBColor(0xD5, 0xDE, 0xE8), round_=True)
txt(s, Inches(0.9), Inches(4.5), Inches(11.6), Inches(0.35), 'Ведомость точек доступа', size=14, color=NAVY, bold=True)
xs = Inches(0.9)
for i, (name, (x, y)) in enumerate(APs.items()):
    chip(s, xs + (i % 6) * Inches(1.98), Inches(4.95) + (i // 6) * Inches(0.5), name, TEAL if i < 6 else NAVY2, w=Inches(1.85))
txt(s, Inches(0.9), Inches(6.1), Inches(11.6), Inches(0.4),
    'Итого: 11 × Eltex WEP-2AC Smart · 11 × инжектор/PoE-порт · крепёж подвесной потолок · трассы от щита №15/серверной №14',
    size=11.5, color=GREY)
footer(s)

prs.save('out/WiFi_Eltex_WEP-2AC_план_лист14.pptx')
print('slides:', len(prs.slides.__iter__.__self__._sldIdLst))
