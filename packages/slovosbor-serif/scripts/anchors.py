"""Разметка якорей верхних меток.

Две задачи:
  1. Гласные, у которых якоря не было вовсе — акут падал на правый край.
  2. Альтернативные формы: у базовой буквы якорь есть, у её альтерната нет,
     поэтому в болгарской локали акут вообще не позиционировался.

X считается по оптике (центр краски на самом верху; у йотированных юсов —
по центру просвета треугольника), Y переносится от донора. Каждому якорю
даётся собственная вариация по оси веса, иначе в Bold акут уезжает.
"""
import copy
from fontTools.pens.boundsPen import BoundsPen
from anchor_var import measure_drift, apply_x_variation, optical_x

# гласные, которым нужен якорь для ударения
TARGET_CPS = [0x044D, 0x044E, 0x044F, 0x0454, 0x0463, 0x046B, 0x0467, 0x0469, 0x046D,
              0x042D, 0x042E, 0x042F, 0x0404, 0x0462, 0x046A]

# позиции, выправленные заказчиком по оттиску (X в юнитах шрифта)
OVERRIDE_X = {
    # круг 5: ять уехал на правое поле над перекладиной, я и є подвинуты влево
    False: {0x0463: 360, 0x0469: 531, 0x046D: 716, 0x042F: 404, 0x0467: 282,
            0x044F: 324, 0x0454: 334},
    True:  {0x0463: 419, 0x046B: 450, 0x0467: 369, 0x0469: 520,
            0x046D: 687, 0x042F: 453},
}

# Y переносится от донора, но у прямого ятя акут опущен вручную:
# он теперь стоит справа от палочки, а не над ней
OVERRIDE_Y = {False: {0x0463: 590}, True: {0x0463: 590}}

# у є оптический центр верха уползает влево с набором веса, а глазу нужно
# наоборот — держим X постоянным по всему весу
# Акут у ятя стоит справа от палочки, а её верх растёт с весом быстрее
# автоматической дельты. Дельты подобраны так, чтобы зазор до палочки
# держался 38 юнитов от Thin до Bold. Раздельно по начертаниям.
DRIFT_OVERRIDE = {
    False: {0x0454: (0, 0), 0x0463: (81, -49)},
    True:  {0x0454: (0, 0), 0x0463: (73, -69)},
}

# У болгарского ю верхние 12% краски — это высокая левая палка, поэтому
# автоматика ставила акут над ней. Глазу нужно над чашей и ниже.
ALT_OVERRIDE = {
    False: {"yucyrl.loclBGR": (536, 540)},
    True:  {"u044E.loclBGR":  (445, 540)},
}


def _bounds(glyphset, name):
    pen = BoundsPen(glyphset)
    glyphset[name].draw(pen)
    return pen.bounds


def above_mark_subtable(gpos):
    """MarkBasePos, отвечающий за верхние метки (тот, где acutecomb)."""
    for lk in gpos.LookupList.Lookup:
        if lk.LookupType != 4:
            continue
        for st in lk.SubTable:
            if "acutecomb" in st.MarkCoverage.glyphs:
                return st
    return None


def _alternate_pairs(gsub):
    """{альтернат: база} по таблице aalt."""
    out = {}
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag != "aalt":
            continue
        for li in fr.Feature.LookupListIndex:
            for sub in gsub.LookupList.Lookup[li].SubTable:
                for base, alts in getattr(sub, "alternates", {}).items():
                    for a in alts:
                        out.setdefault(a, base)
    return out


def _insert(subtable, have, gid, name, record):
    pos = 0
    while pos < len(have) and gid[have[pos]] < gid[name]:
        pos += 1
    have.insert(pos, name)
    subtable.BaseArray.BaseRecord.insert(pos, record)


def add_missing_anchors(font, log, italic=False, src_path=None):
    gpos = font["GPOS"].table
    st = above_mark_subtable(gpos)
    if st is None:
        log.append("GPOS: не найден лукап верхних меток — якоря не тронуты")
        return []

    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    gid = {n: i for i, n in enumerate(font.getGlyphOrder())}
    have = list(st.BaseCoverage.glyphs)
    have_set = set(have)
    rule_cp = {}                       # глиф → codepoint, по которому считать X

    # ── 1. гласные без якоря: донор — ближайшая по высоте размеченная буква ──
    donors = []
    for i, n in enumerate(have):
        a = st.BaseArray.BaseRecord[i].BaseAnchor[0]
        b = _bounds(gs, n)
        if a is not None and b is not None:
            donors.append((n, a, b))
    added_vowels = []
    for cp in TARGET_CPS:
        name = cmap.get(cp)
        if not name or name in have_set or not donors:
            continue
        tb = _bounds(gs, name)
        if tb is None:
            continue
        dn, da, db = min(donors, key=lambda d: (abs(d[2][3] - tb[3]),
                                                abs((d[2][2] - d[2][0]) - (tb[2] - tb[0]))))
        anchor = copy.deepcopy(da)
        ox = optical_x(gs, name, cp)
        anchor.XCoordinate = int(round(
            ox if ox is not None
            else da.XCoordinate + ((tb[0] + tb[2]) / 2 - (db[0] + db[2]) / 2)))
        anchor.YCoordinate = int(round(da.YCoordinate + (tb[3] - db[3])))
        if cp in OVERRIDE_X.get(bool(italic), {}):
            anchor.XCoordinate = OVERRIDE_X[bool(italic)][cp]
        if cp in OVERRIDE_Y.get(bool(italic), {}):
            anchor.YCoordinate = OVERRIDE_Y[bool(italic)][cp]
        rec = copy.deepcopy(st.BaseArray.BaseRecord[have.index(dn)])
        rec.BaseAnchor[0] = anchor
        _insert(st, have, gid, name, rec)
        have_set.add(name)
        rule_cp[name] = cp
        added_vowels.append(chr(cp))

    # ── 2. альтернаты: донор — их собственная база ──────────────────────────
    pairs = _alternate_pairs(font["GSUB"].table)
    added_alts = []
    for alt, base in sorted(pairs.items(), key=lambda kv: gid.get(kv[0], 0)):
        if alt in have_set or base not in have_set:
            continue
        ab, bb = _bounds(gs, alt), _bounds(gs, base)
        if ab is None or bb is None:
            continue
        bi = have.index(base)
        banchor = st.BaseArray.BaseRecord[bi].BaseAnchor[0]
        if banchor is None:          # база в покрытии, но якорь не задан
            continue
        cp = rule_cp.get(base)
        ax, bx = optical_x(gs, alt, cp), optical_x(gs, base, cp)
        anchor = copy.deepcopy(banchor)
        # сохраняем выверенное положение базы, добавляя разницу форм
        if ax is not None and bx is not None:
            anchor.XCoordinate = int(round(banchor.XCoordinate + (ax - bx)))
        anchor.YCoordinate = int(round(banchor.YCoordinate + (ab[3] - bb[3])))
        ov = ALT_OVERRIDE.get(bool(italic), {}).get(alt)
        if ov:
            anchor.XCoordinate, anchor.YCoordinate = ov
        anchor.XDeviceTable = None          # своя вариация появится ниже
        rec = copy.deepcopy(st.BaseArray.BaseRecord[bi])
        rec.BaseAnchor[0] = anchor
        _insert(st, have, gid, alt, rec)
        have_set.add(alt)
        if cp is not None:
            rule_cp[alt] = cp
        added_alts.append(alt)

    if not (added_vowels or added_alts):
        return []

    st.BaseCoverage.glyphs = have
    st.BaseArray.BaseCount = len(st.BaseArray.BaseRecord)

    gdef = font.get("GDEF")
    if gdef is not None and gdef.table.GlyphClassDef is not None:
        cls = gdef.table.GlyphClassDef.classDefs
        for n in [cmap[c] for c in TARGET_CPS if c in cmap] + added_alts:
            if cls.get(n, 1) != 1:
                cls[n] = 1

    # ── 3. собственная вариация X по весу ───────────────────────────────────
    if src_path:
        donor_dev = None
        for rec in st.BaseArray.BaseRecord:
            d = getattr(rec.BaseAnchor[0], "XDeviceTable", None)
            if d is not None and getattr(d, "DeltaFormat", 0) == 0x8000:
                donor_dev = d
                break
        targets = {cmap[c]: c for c in TARGET_CPS if c in cmap}
        targets.update({n: rule_cp.get(n) for n in added_alts})
        drift = measure_drift(src_path, targets, DRIFT_OVERRIDE.get(bool(italic), {}))
        for n in ALT_OVERRIDE.get(bool(italic), {}):
            drift[n] = (0, 0)          # выставлено вручную — не двигать по весу
        apply_x_variation(font, st, list(targets), drift, donor_dev, log)

    if added_vowels:
        log.append(f"GPOS: якоря гласным — {len(added_vowels)} ({' '.join(added_vowels)})")
    if added_alts:
        log.append(f"GPOS: якоря альтернативным формам — {len(added_alts)}; "
                   "среди них болгарское ю, где акут вообще не позиционировался")
    return added_vowels + added_alts
