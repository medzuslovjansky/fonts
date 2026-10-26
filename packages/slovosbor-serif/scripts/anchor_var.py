"""Собственная вариация X-якоря по оси веса.

Донорские Device-таблицы описывают дрейф донора, а не цели, поэтому в Bold
акут уезжает. Здесь считается настоящий дрейф каждой буквы: где оптически
должен стоять акут при wght 100, 400 и 700, и разница пишется в GDEF VarStore
отдельной строкой.
"""
import copy
import math
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen

TRIANGLE_CPS = {0x0469, 0x046D}     # йотированные юсы — по просвету треугольника
# ъ ь Ъ Ь: верх краски — флажок и палочка, автоматика ставила акут над флажком.
# Ставим на ось мачты; в курсиве ось сносится по наклону до верха буквы
# (курсивный ъ выставлен вручную в anchors.py — гравис целит в ложбинку).
COUNTER_CPS = {0x044A, 0x044C, 0x042A, 0x042C}


def _contours(glyphset, name):
    rp = RecordingPen()
    glyphset[name].draw(rp)
    out, cur = [], []
    for op, args in rp.value:
        if op == "moveTo":
            if cur:
                out.append(cur)
            cur = [args[0]]
        elif op == "closePath":
            if cur:
                out.append(cur)
                cur = []
        else:
            cur.extend(p for p in args if isinstance(p, tuple))
    if cur:
        out.append(cur)
    return out


def _stem_x(glyphset, name, y, bounds):
    """Центр мачты: первая слева полоса краски на высоте середины просвета —
    там флажок ъ уже не достаёт, остаются только мачта и чаша."""
    start = None
    for x in range(int(bounds[0]), int(bounds[2]) + 1):
        pen = PointInsidePen(glyphset, (x, y))
        glyphset[name].draw(pen)
        if pen.getResult():
            start = x if start is None else start
        elif start is not None:
            return (start + x - 1) / 2
    return None


def optical_x(glyphset, name, cp, italic_angle=0.0):
    """Где оптически должен стоять акут: центр краски на самом верху,
    у йотированных юсов — центр просвета треугольника, у ъ ь — см. COUNTER_CPS."""
    cs = _contours(glyphset, name)
    if not cs:
        return None
    if cp in TRIANGLE_CPS and len(cs) > 1:
        small = min(cs, key=len)
        xs = [p[0] for p in small]
        return (min(xs) + max(xs)) / 2
    bp = BoundsPen(glyphset)
    glyphset[name].draw(bp)
    b = bp.bounds
    if b is None:
        return None
    if cp in COUNTER_CPS and len(cs) > 1:
        ys = [p[1] for p in min(cs, key=len)]
        cy = (min(ys) + max(ys)) / 2
        sx = _stem_x(glyphset, name, cy, b)
        if sx is None:
            return None
        return sx + math.tan(math.radians(-italic_angle)) * (b[3] - cy)
    height = b[3] - b[1]
    band = [p[0] for c in cs for p in c if p[1] >= b[3] - height * 0.12]
    if not band:
        return None
    return (min(band) + max(band)) / 2


def measure_drift(src_path, targets, overrides=None, weights=(100, 400, 700)):
    """targets — {имя глифа: codepoint или None}. Возвращает
    {имя глифа: (дельта при max, дельта при min)} — сдвиг формы к Regular."""
    overrides = overrides or {}
    vals = {}
    for w in weights:
        inst = instantiateVariableFont(TTFont(src_path), {"wght": w},
                                       inplace=False, updateFontNames=False)
        gs, angle = inst.getGlyphSet(), inst["post"].italicAngle
        for name, cp in targets.items():
            if name not in gs:
                continue
            x = optical_x(gs, name, cp, angle)
            if x is not None:
                vals.setdefault(name, {})[w] = x
    drift = {}
    for name, byw in vals.items():
        if len(byw) < 3:
            continue
        base = byw[400]
        drift[name] = (int(round(byw[700] - base)), int(round(byw[100] - base)))
    for name, cp in targets.items():
        if cp in overrides:
            drift[name] = overrides[cp]
    return drift


def _region_index(varstore, peak):
    for i, r in enumerate(varstore.VarRegionList.Region):
        ax = r.VarRegionAxis[0]
        if abs(ax.PeakCoord - peak) < 1e-6 and abs(ax.EndCoord - max(peak, 0.0)) < 1e-6 \
           and abs(ax.StartCoord - min(peak, 0.0)) < 1e-6:
            return i
    return None


def find_vardata(varstore):
    """VarData с парой регионов «вверх по весу» и «вниз». Вернуть (индекс, порядок)."""
    up, down = _region_index(varstore, 1.0), _region_index(varstore, -1.0)
    if up is None or down is None:
        return None, None
    for i, vd in enumerate(varstore.VarData):
        if list(vd.VarRegionIndex) == [up, down]:
            return i, (0, 1)
        if list(vd.VarRegionIndex) == [down, up]:
            return i, (1, 0)
    return None, None


def apply_x_variation(font, subtable, names, drift, donor_device, log):
    """Записать дельты в VarStore и повесить VariationIndex на X каждого якоря."""
    vs = getattr(font["GDEF"].table, "VarStore", None)
    if vs is None or donor_device is None:
        log.append("GDEF: VarStore недоступен — X-якоря остались статичными")
        return 0
    outer, order = find_vardata(vs)
    if outer is None:
        log.append("GDEF: не нашлось VarData с парой регионов веса — X статичны")
        return 0
    vd = vs.VarData[outer]
    cov = subtable.BaseCoverage.glyphs
    done = 0
    for name in names:
        if name not in drift or name not in cov:
            continue
        dmax, dmin = drift[name]
        if dmax == 0 and dmin == 0:
            continue
        row = [0, 0]
        row[order[0]], row[order[1]] = dmax, dmin
        vd.Item.append(row)
        inner = vd.ItemCount
        vd.ItemCount += 1
        dev = copy.deepcopy(donor_device)
        dev.DeltaFormat = 0x8000
        dev.StartSize, dev.EndSize = outer, inner
        subtable.BaseArray.BaseRecord[cov.index(name)].BaseAnchor[0].XDeviceTable = dev
        done += 1
    try:
        vd.calculateNumShorts()
    except Exception:
        pass
    if done:
        log.append(f"GDEF: X-якорям дана собственная вариация по весу — {done} шт. "
                   "(в Bold акут больше не уезжает)")
    return done
