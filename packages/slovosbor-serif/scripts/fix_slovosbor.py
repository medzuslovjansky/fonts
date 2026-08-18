#!/usr/bin/env python3
"""
Slovosbor Serif — пересборка кириллической проводки и техпаспорта.

Вход:  IBMPlexSerifVar33-VF.ttf, IBMPlexSerifVarItalicVar33-VF.ttf
Выход: SlovosborSerif-VF.ttf,    SlovosborSerif-Italic-VF.ttf

Запуск:  python3 fix_slovosbor.py <roman.ttf> <italic.ttf> [outdir]
"""
import sys, os
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from anchors import add_missing_anchors

FAMILY   = "Slovosbor Serif"
PSFAMILY = "SlovosborSerif"
DESIGNER = "S.-V. Sofienczuk-Wojczyszyn"
VENDOR   = "SLVS"
VERSION  = "Version 2.000"
REVISION = 2.0

# ── мелкие помощники по GSUB ────────────────────────────────────────────────

def cyrl_script(gsub):
    for sr in gsub.ScriptList.ScriptRecord:
        if sr.ScriptTag == "cyrl":
            return sr.Script
    raise KeyError("нет cyrl")

def langsys(script, tag):
    if tag == "dflt":
        return script.DefaultLangSys
    for r in script.LangSysRecord:
        if r.LangSysTag.strip() == tag:
            return r.LangSys
    return None

def feature_index(gsub, script, langtag, featuretag):
    ls = langsys(script, langtag)
    for i in ls.FeatureIndex:
        if gsub.FeatureList.FeatureRecord[i].FeatureTag == featuretag:
            return i
    return None

def new_single_lookup(gsub, mapping):
    """SingleSubst lookup из словаря {база: альтернат}; вернуть его индекс."""
    st = ot.SingleSubst()
    st.mapping = dict(mapping)
    lk = ot.Lookup()
    lk.LookupType, lk.LookupFlag = 1, 0
    lk.SubTable = [st]
    lk.SubTableCount = 1
    gsub.LookupList.Lookup.append(lk)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    return len(gsub.LookupList.Lookup) - 1

def add_ss_feature(font, gsub, tag, ui_name, lookup_indices):
    """Новый стилистический набор с человеческим именем; вернуть его индекс."""
    name_id = font["name"].addName(ui_name)
    params = ot.FeatureParamsStylisticSet()
    params.Version, params.UINameID = 0, name_id
    feat = ot.Feature()
    feat.FeatureParams = params
    feat.LookupListIndex = list(lookup_indices)
    feat.LookupCount = len(feat.LookupListIndex)
    rec = ot.FeatureRecord()
    rec.FeatureTag, rec.Feature = tag, feat
    gsub.FeatureList.FeatureRecord.append(rec)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    idx = len(gsub.FeatureList.FeatureRecord) - 1
    # зарегистрировать во всех script/langsys, иначе набор невидим
    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None and idx not in ls.FeatureIndex:
                ls.FeatureIndex.append(idx)
                ls.FeatureCount = len(ls.FeatureIndex)
    return idx

def sort_feature_list(gsub):
    """FeatureRecord'ы обязаны идти по алфавиту; пересобрать и перенумеровать."""
    recs = gsub.FeatureList.FeatureRecord
    order = sorted(range(len(recs)), key=lambda i: (recs[i].FeatureTag, i))
    remap = {old: new for new, old in enumerate(order)}
    gsub.FeatureList.FeatureRecord = [recs[i] for i in order]
    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex = sorted(remap[i] for i in ls.FeatureIndex)
                ls.FeatureCount = len(ls.FeatureIndex)

def add_langsys(script, tag, feature_indices):
    """Скопировать набор фич под новый языковой тег; LangSysRecord'ы — по алфавиту."""
    tag4 = (tag + "    ")[:4]
    for r in script.LangSysRecord:
        if r.LangSysTag == tag4:
            return r.LangSys
    ls = ot.LangSys()
    ls.LookupOrder = None
    ls.ReqFeatureIndex = 0xFFFF
    ls.FeatureIndex = sorted(feature_indices)
    ls.FeatureCount = len(ls.FeatureIndex)
    rec = ot.LangSysRecord()
    rec.LangSysTag, rec.LangSys = tag4, ls
    script.LangSysRecord.append(rec)
    script.LangSysRecord.sort(key=lambda r: r.LangSysTag)
    script.LangSysCount = len(script.LangSysRecord)
    return ls

def add_ligature(gsub, lookup_index, first, components, lig_glyph):
    st = gsub.LookupList.Lookup[lookup_index].SubTable[0]
    lig = ot.Ligature()
    lig.Component, lig.LigGlyph = list(components), lig_glyph
    lig.CompCount = len(lig.Component) + 1
    st.ligatures.setdefault(first, [])
    # длинные последовательности должны идти раньше коротких
    st.ligatures[first].append(lig)
    st.ligatures[first].sort(key=lambda l: -len(l.Component))

def close_acute_gaps(font, gsub, log):
    """Композит с акутом нарисован, а правила «acute + база» нет — дописать."""
    cmap = font.getBestCmap()
    glyphs = set(font.getGlyphOrder())
    lk = None                                  # лукап, где живут правила «acute + …»
    for i, l in enumerate(gsub.LookupList.Lookup):
        if l.LookupType == 4 and any("acute" in st.ligatures for st in l.SubTable):
            lk = i
            break
    if lk is None:
        return
    wanted = [(0x046B, "yusbigacutecyrl"),       # ѫ́
              (0x0454, "ieukrainianacutecyrl"),  # є́
              (0x0438, "iacutecyrl"),            # и́
              (0x0443, "uacutecyrl")]            # у́
    added = []
    for cp, comp in wanted:
        base = cmap.get(cp)
        if not base or comp not in glyphs:
            continue
        if liga_lookup_with(gsub, "acute", base) is None:
            add_ligature(gsub, lk, "acute", [base], comp)
            added.append(chr(cp) + "́")
    if added:
        log.append(f"liga: закрыты дыры с акутом — {' '.join(added)}")


def clone_feature_for_lang(gsub, script, langtag, tag, extra_lookups):
    """Отдельная запись фичи для одного языка: те же лукапы плюс добавочные."""
    base_idx = feature_index(gsub, script, "dflt", tag)
    if base_idx is None:
        return None
    src = gsub.FeatureList.FeatureRecord[base_idx].Feature
    feat = ot.Feature()
    feat.FeatureParams = src.FeatureParams
    feat.LookupListIndex = list(src.LookupListIndex) + list(extra_lookups)
    feat.LookupCount = len(feat.LookupListIndex)
    rec = ot.FeatureRecord()
    rec.FeatureTag, rec.Feature = tag, feat
    gsub.FeatureList.FeatureRecord.append(rec)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    new_idx = len(gsub.FeatureList.FeatureRecord) - 1
    ls = langsys(script, langtag)
    ls.FeatureIndex = [i for i in ls.FeatureIndex if i != base_idx] + [new_idx]
    ls.FeatureCount = len(ls.FeatureIndex)
    return new_idx


def set_cyrl_salt(font, gsub, mapping, log):
    """Переопределить salt для кириллицы. Латинский salt — отдельная запись,
    его не трогаем."""
    cyrl = cyrl_script(gsub)
    idx = feature_index(gsub, cyrl, "dflt", "salt")
    if idx is None:
        log.append("salt: кириллическая запись не найдена")
        return
    mapping = {k: v for k, v in mapping.items()
               if k and v and k in font.getGlyphOrder() and v in font.getGlyphOrder()}
    feat = gsub.FeatureList.FeatureRecord[idx].Feature
    feat.LookupListIndex = [new_single_lookup(gsub, mapping)]
    feat.LookupCount = 1
    log.append(f"salt для кириллицы переопределён: {len(mapping)} подстановок "
               "(болгарский набор убран — он и так приезжает через locl)")


def set_italic_yat_default(font, gsub, log):
    """По умолчанию курсивный ять — форма 2. Старая база остаётся доступна."""
    new_default = "yatcyrl.alt01"
    if new_default not in font.getGlyphOrder():
        return None
    old = None
    for table in font["cmap"].tables:
        if 0x0463 in table.cmap:
            old = old or table.cmap[0x0463]
            table.cmap[0x0463] = new_default
    for table in font["cmap"].tables:
        if 0x0464 in table.cmap:
            pass
    log.append(f"курсив: ять по умолчанию {old} → {new_default}; "
               f"прежняя форма осталась в ss09 и aalt")
    return old


def _coverage(font, names):
    cov = ot.Coverage()
    gid = {n: i for i, n in enumerate(font.getGlyphOrder())}
    cov.glyphs = sorted((n for n in names if n in gid), key=lambda n: gid[n])
    return cov


def uppercase_yat(font, gsub, log):
    """Внутри прописных ять уходит в асцендер: перекладина по капслайну,
    палочка выше неё. Глиф нарисован, правила не было."""
    cmap = font.getBestCmap()
    base, alt = cmap.get(0x0462), "Yatcyrl.alt01"
    if not base or alt not in font.getGlyphOrder():
        log.append("calt: в этом начертании нет высокой формы прописного ятя — пропущено")
        return
    ups = [n for cp, n in cmap.items()
           if chr(cp).isupper() and (0x0400 <= cp < 0x0530 or 0x41 <= cp <= 0x5A)]
    sub_lk = new_single_lookup(gsub, {base: alt})
    lookups = []
    for back, ahead in ((ups, None), (None, ups)):
        st = ot.ChainContextSubst()
        st.Format = 3
        st.BacktrackGlyphCount = 1 if back else 0
        st.BacktrackCoverage = [_coverage(font, back)] if back else []
        st.InputGlyphCount = 1
        st.InputCoverage = [_coverage(font, [base])]
        st.LookAheadGlyphCount = 1 if ahead else 0
        st.LookAheadCoverage = [_coverage(font, ahead)] if ahead else []
        rec = ot.SubstLookupRecord()
        rec.SequenceIndex, rec.LookupListIndex = 0, sub_lk
        st.SubstCount, st.SubstLookupRecord = 1, [rec]
        lk = ot.Lookup()
        lk.LookupType, lk.LookupFlag = 6, 0
        lk.SubTable, lk.SubTableCount = [st], 1
        gsub.LookupList.Lookup.append(lk)
        gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
        lookups.append(len(gsub.LookupList.Lookup) - 1)

    feat = ot.Feature()
    feat.FeatureParams = None
    feat.LookupListIndex = lookups
    feat.LookupCount = len(lookups)
    rec = ot.FeatureRecord()
    rec.FeatureTag, rec.Feature = "calt", feat
    gsub.FeatureList.FeatureRecord.append(rec)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    idx = len(gsub.FeatureList.FeatureRecord) - 1
    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None and idx not in ls.FeatureIndex:
                ls.FeatureIndex.append(idx)
                ls.FeatureCount = len(ls.FeatureIndex)
    log.append("calt: внутри прописных ять уходит в асцендер (трюк дизайнера восстановлен)")


def rebuild_aalt(font, gsub, log):
    """aalt обязан перечислять ВСЕ альтернаты каждой буквы — им живёт
    палитра глифов в InDesign и Illustrator. Сейчас там три позиции."""
    feats = gsub.FeatureList.FeatureRecord
    alts = {}

    def collect(mapping_items):
        for base, alt in mapping_items:
            if base == alt:
                continue
            alts.setdefault(base, [])
            if alt not in alts[base]:
                alts[base].append(alt)

    for fr in feats:
        if fr.FeatureTag == "aalt":
            continue
        for li in fr.Feature.LookupListIndex:
            lk = gsub.LookupList.Lookup[li]
            for st in lk.SubTable:
                if lk.LookupType == 1:
                    collect(st.mapping.items())
                elif lk.LookupType == 3:
                    for b, al in st.alternates.items():
                        collect((b, a) for a in al)

    before = 0
    for fr in feats:
        if fr.FeatureTag != "aalt":
            continue
        for li in fr.Feature.LookupListIndex:
            for st in gsub.LookupList.Lookup[li].SubTable:
                if getattr(st, "mapping", None):
                    before = max(before, len(st.mapping))
                    collect(st.mapping.items())
                elif getattr(st, "alternates", None):
                    before = max(before, len(st.alternates))
                    for b, al in st.alternates.items():
                        collect((b, a) for a in al)

    if not alts:
        return
    sub = ot.AlternateSubst()
    sub.alternates = {b: list(a) for b, a in alts.items()}
    lk = ot.Lookup()
    lk.LookupType, lk.LookupFlag = 3, 0
    lk.SubTable, lk.SubTableCount = [sub], 1
    gsub.LookupList.Lookup.append(lk)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    idx = len(gsub.LookupList.Lookup) - 1

    for fr in feats:
        if fr.FeatureTag == "aalt":
            fr.Feature.LookupListIndex = [idx]
            fr.Feature.LookupCount = 1
    total = sum(len(v) for v in alts.values())
    log.append(f"aalt пересобран: {len(alts)} букв, {total} альтернат "
               f"(было {before}) — палитра глифов теперь показывает всё")

def liga_lookup_with(gsub, first, component):
    for i, lk in enumerate(gsub.LookupList.Lookup):
        if lk.LookupType != 4:
            continue
        for st in lk.SubTable:
            for f, ligs in st.ligatures.items():
                if f == first and any(l.Component == [component] for l in ligs):
                    return i
    return None

# ── общие правки: имя, метрики, экземпляры ─────────────────────────────────

def set_name(font, nid, value):
    recs = [r for r in font["name"].names if r.nameID == nid]
    if recs:
        for r in recs:
            font["name"].setName(value, nid, r.platformID, r.platEncID, r.langID)
    else:
        font["name"].setName(value, nid, 3, 1, 0x409)

def rebrand(font, italic, log):
    style = "Italic" if italic else "Regular"
    set_name(font, 1,  FAMILY)
    set_name(font, 2,  style)
    set_name(font, 16, FAMILY)
    set_name(font, 17, style)
    set_name(font, 4,  FAMILY + (" Italic" if italic else ""))
    set_name(font, 6,  f"{PSFAMILY}-{style}")
    set_name(font, 3,  f"{FAMILY} {style}:{VERSION}")
    set_name(font, 5,  VERSION)
    set_name(font, 25, PSFAMILY + ("Italic" if italic else "Roman"))
    set_name(font, 0,  "Copyright 2020 IBM Corp. All rights reserved. "
                       f"Modifications copyright 2026 {DESIGNER}.")
    set_name(font, 8,  DESIGNER)
    set_name(font, 9,  f"{DESIGNER}; Mike Abbink, Paul van der Laan, Pieter van Rosmalen")
    set_name(font, 10, "Extensively revised derivative of IBM Plex Serif by Bold Monday.")
    font["name"].removeNames(7)          # чужой товарный знак
    font["OS/2"].achVendID = VENDOR
    font["head"].fontRevision = REVISION
    log.append(f"имя семейства → {FAMILY} {style}; name[7] удалён; vendor → {VENDOR}")

def fix_metrics(font, log):
    os2, hhea = font["OS/2"], font["hhea"]
    asc, desc, gap = os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap
    hhea.ascent, hhea.descent, hhea.lineGap = asc, desc, gap
    os2.fsSelection |= 1 << 7            # USE_TYPO_METRICS
    log.append(f"метрики выровнены {asc}/{desc}/{gap}, USE_TYPO_METRICS включён "
               f"→ {(asc - desc + gap) / font['head'].unitsPerEm:.2f}em везде")

def round_instances(font, log):
    n = 0
    for inst in font["fvar"].instances:
        for ax, v in list(inst.coordinates.items()):
            if abs(v - round(v)) > 1e-9:
                inst.coordinates[ax] = float(round(v))
                n += 1
    if n:
        log.append(f"округлено координат экземпляров: {n}")

# ── правки конкретно кириллицы ─────────────────────────────────────────────

def fix_roman(font, log):
    gsub = font["GSUB"].table
    cyrl = cyrl_script(gsub)
    cmap = font.getBestCmap()

    # 1. сербский прямой = русский прямой: убрать SRB-лукап из locl
    srb_locl = feature_index(gsub, cyrl, "SRB", "locl")
    shared = feature_index(gsub, cyrl, "dflt", "locl")
    shared_lookups = set(gsub.FeatureList.FeatureRecord[shared].Feature.LookupListIndex)
    feat = gsub.FeatureList.FeatureRecord[srb_locl].Feature
    dropped = [i for i in feat.LookupListIndex if i not in shared_lookups]
    feat.LookupListIndex = [i for i in feat.LookupListIndex if i in shared_lookups]
    feat.LookupCount = len(feat.LookupListIndex)
    log.append(f"locl SRB: убраны болгарские подстановки (лукапы {dropped}); "
               "сербский прямой теперь совпадает с русским")

    # 2. недостающая лига: акут над болгарским ю
    lk = liga_lookup_with(gsub, "acute", "yerucyrl.alt01")
    if lk is not None and liga_lookup_with(gsub, "acute", "yucyrl.loclBGR") is None:
        add_ligature(gsub, lk, "acute", ["yucyrl.loclBGR"], "juacutecyrl.alt01")
        log.append("liga: добавлено acute + болгарское ю → ю́ (было потеряно)")

    # 3. ss07 меняет У, но забывает акцентированные У
    ss07 = feature_index(gsub, cyrl, "dflt", "ss07")
    u_base = cmap.get(0x0423)                       # У — за ней тянутся остальные
    st = None
    for li in gsub.FeatureList.FeatureRecord[ss07].Feature.LookupListIndex:
        lk = gsub.LookupList.Lookup[li]
        if lk.LookupType != 1:
            continue
        for sub in lk.SubTable:
            if u_base in sub.mapping:
                st = sub
    if st is None:
        raise RuntimeError("в ss07 не найден SingleSubst с У")
    follow = {0x040E: "Ushortcyrl.alt01", 0x04EE: "Umacroncyrl.alt01",
              0x04F0: "Udieresiscyrl.alt01", 0x04F2: "Udoubleacutecyrlalt01"}
    added = []
    for cp, alt in follow.items():
        base = cmap.get(cp)
        if base and alt in font.getGlyphOrder() and base not in st.mapping:
            st.mapping[base] = alt
            added.append(chr(cp))
    if added:
        log.append(f"ss07: акцентированные У подтянуты за базовой ({' '.join(added)})")

    # 4. осиротевшие формы — в стилистические наборы
    g = lambda cp: cmap.get(cp)
    ss09 = {g(0x0431): "bcyrl.alt01",   g(0x0434): "dcyrl.alt01",
            g(0x044B): "yerucyrl.alt01", g(0x0463): "yatcyrl.alt02",
            g(0x046B): "yusbigcyrlalt1",
            # композиты с акутом — набор обязан переключать и их,
            # иначе liga отработает раньше и вернёт базовую форму
            "yeruacutecyrl":   "yeruacutecyrl.alt01",
            "yatacutecyrl":    "yatacutecyrl.alt02",
            "yusbigacutecyrl": "yusbigcyrlacutealt1"}
    ss09 = {k: v for k, v in ss09.items() if k and v in font.getGlyphOrder()}
    add_ss_feature(font, gsub, "ss09", "Alternate Cyrillic letterforms",
                   [new_single_lookup(gsub, ss09)])
    log.append(f"ss09 «Alternate Cyrillic letterforms»: {len(ss09)} подстановок "
               "(сербские г и т убраны по решению заказчика)")

    # 5. македонский = сербский (в прямом оба равны русскому)
    srb_feats = langsys(cyrl, "SRB").FeatureIndex
    add_langsys(cyrl, "MKD", srb_feats)
    log.append("зарегистрирован cyrl/MKD (в прямом = русский, как и сербский)")

    # 5a. рукописные юсы убрать из автоматической болгарицы — они нестандартны
    bgr_i = feature_index(gsub, cyrl, "BGR", "locl")
    shared_lk = set(gsub.FeatureList.FeatureRecord[
        feature_index(gsub, cyrl, "dflt", "locl")].Feature.LookupListIndex)
    removed_yus = []
    for li in gsub.FeatureList.FeatureRecord[bgr_i].Feature.LookupListIndex:
        if li in shared_lk:
            continue
        for stt in gsub.LookupList.Lookup[li].SubTable:
            for b in list(getattr(stt, "mapping", {})):
                if "yus" in stt.mapping[b]:
                    removed_yus.append(b)
                    del stt.mapping[b]
    if removed_yus:
        log.append(f"locl BGR: рукописные юсы убраны ({len(removed_yus)}) — "
                   "болгарский юс снова стандартный, рукописный живёт в ss10")

    # 6. сербское и македонское прямое = русское прямое, включая б
    # 7. salt: общая часть для всех, ять — только в болгарице
    set_cyrl_salt(font, gsub, {
        g(0x046B):          "yusbigcyrlalt1",
        "yusbigacutecyrl":  "yusbigcyrlacutealt1",
    }, log)
    # в болгарице locl уже дал форму 2 — salt подхватывает именно её
    yat_lk = new_single_lookup(gsub, {"yatcyrl.alt01": "yatcyrl.alt02",
                                      "yatacutecyrl.alt01": "yatacutecyrl.alt02"})
    clone_feature_for_lang(gsub, cyrl, "BGR", "salt", [yat_lk])
    log.append("salt: ять срабатывает только в болгарской локали")

    # 8. рукописные юсы — нестандартные, поэтому отдельным набором
    ss10 = {g(0x046B): "yusbigcyrl.alt01",  g(0x046D): "yusiotifiedbigcyrl.alt01",
            g(0x0467): "yuslittlecyrl.alt01", g(0x0469): "yusiotifiedlittlecyrl.alt01",
            "yusbigacutecyrl": "yusbigacutecyrl.alt01",
            "yusiotifiedbigacutecyrl": "yusiotifiedbigacutecyrl.alt01",
            "yuslittleacutecyrl": "yuslittleacutecyrl.alt01",
            "yusiotifiedlittleacutecyrl": "yusiotifiedlittleacutecyrl.alt01"}
    ss10 = {k: v for k, v in ss10.items() if k and v in font.getGlyphOrder()}
    add_ss_feature(font, gsub, "ss10", "Handwritten yus forms",
                   [new_single_lookup(gsub, ss10)])
    log.append(f"ss10 «Handwritten yus forms»: {len(ss10)} подстановок")

def fix_italic(font, log):
    gsub = font["GSUB"].table
    cyrl = cyrl_script(gsub)
    cmap = font.getBestCmap()

    # 1. сербский курсив: оставить только г д п т
    srb_locl = feature_index(gsub, cyrl, "SRB", "locl")
    shared = set(gsub.FeatureList.FeatureRecord[
        feature_index(gsub, cyrl, "dflt", "locl")].Feature.LookupListIndex)
    own = [i for i in gsub.FeatureList.FeatureRecord[srb_locl].Feature.LookupListIndex
           if i not in shared]
    keep_cps = {0x0433, 0x0434, 0x043F, 0x0442}          # г д п т
    keep_glyphs = {cmap[c] for c in keep_cps if c in cmap}
    removed = []
    for li in own:
        for st in gsub.LookupList.Lookup[li].SubTable:
            for base in list(st.mapping):
                if base not in keep_glyphs:
                    removed.append(base)
                    del st.mapping[base]
    log.append(f"locl SRB курсив: убрано {len(removed)} болгарских подстановок, "
               "оставлены только г д п т")

    # 2. осиротевшие формы — в ss09
    g = lambda cp: cmap.get(cp)
    ss09 = {g(0x0442): "tecyrl.alt02", g(0x0448): "shacyrl.alt02",
            "yatcyrl.alt01": "u0463",
            "yatacutecyrl.alt01": "yatacutecyrl"}
    ss09 = {k: v for k, v in ss09.items() if k and v in font.getGlyphOrder()}
    add_ss_feature(font, gsub, "ss09", "Alternate Cyrillic letterforms",
                   [new_single_lookup(gsub, ss09)])
    log.append(f"ss09 «Alternate Cyrillic letterforms»: {len(ss09)} подстановки "
               "(в т.ч. ш с подчёркиванием)")

    # 3. македонский = сербский один-в-один
    srb_feats = langsys(cyrl, "SRB").FeatureIndex
    add_langsys(cyrl, "MKD", srb_feats)
    log.append("зарегистрирован cyrl/MKD = сербский набор (г д п т)")

    # 3a. рукописные юсы — вон из автоматической болгарицы, они нестандартны
    bgr_i = feature_index(gsub, cyrl, "BGR", "locl")
    shared_lk = set(gsub.FeatureList.FeatureRecord[
        feature_index(gsub, cyrl, "dflt", "locl")].Feature.LookupListIndex)
    removed_yus = []
    for li in gsub.FeatureList.FeatureRecord[bgr_i].Feature.LookupListIndex:
        if li in shared_lk:
            continue
        for stt in gsub.LookupList.Lookup[li].SubTable:
            for b in list(getattr(stt, "mapping", {})):
                if "yus" in stt.mapping[b]:
                    removed_yus.append(b)
                    del stt.mapping[b]
    if removed_yus:
        log.append(f"locl BGR курсив: рукописные юсы убраны ({len(removed_yus)})")

    # 4. ять: по умолчанию форма 2, в болгарице форма 3, в salt форма 3
    old_yat = set_italic_yat_default(font, gsub, log)
    bgr = feature_index(gsub, cyrl, "BGR", "locl")
    shared_l = set(gsub.FeatureList.FeatureRecord[
        feature_index(gsub, cyrl, "dflt", "locl")].Feature.LookupListIndex)
    for li in gsub.FeatureList.FeatureRecord[bgr].Feature.LookupListIndex:
        if li in shared_l:
            continue
        gsub.LookupList.Lookup[li].SubTable[0].mapping["yatcyrl.alt01"] = "yatcyrl.alt02"
    log.append("locl BGR курсив: ять → форма 3")

    set_cyrl_salt(font, gsub, {
        g(0x0442):          "tecyrl.alt02",
        g(0x0448):          "shacyrl.alt02",
        g(0x046B):          "yusbigcyrlalt1",
        "yusbigacutecyrl":  "yusbigcyrlacutealt1",
    }, log)
    yat_lk = new_single_lookup(gsub, {"yatcyrl.alt01": "yatcyrl.alt02",
                                      "yatacutecyrl.alt01": "yatacutecyrl.alt02"})
    clone_feature_for_lang(gsub, cyrl, "BGR", "salt", [yat_lk])
    log.append("salt: ять срабатывает только в болгарской локали")

    ss10 = {g(0x046B): "yusbigcyrl.alt01",  g(0x046D): "yusiotifiedbigcyrl.alt01",
            g(0x0467): "yuslittlecyrl.alt01", g(0x0469): "yusiotifiedlittlecyrl.alt01",
            "yusbigacutecyrl": "yusbigacutecyrl.alt01",
            "yusiotifiedbigacutecyrl": "yusiotifiedbigacutecyrl.alt01",
            "yuslittleacutecyrl": "yuslittleacutecyrl.alt01",
            "yusiotifiedlittleacutecyrl": "yusiotifiedlittleacutecyrl.alt01"}
    ss10 = {k: v for k, v in ss10.items() if k and v in font.getGlyphOrder()}
    add_ss_feature(font, gsub, "ss10", "Handwritten yus forms",
                   [new_single_lookup(gsub, ss10)])
    log.append(f"ss10 «Handwritten yus forms»: {len(ss10)} подстановок")

# ── главная ────────────────────────────────────────────────────────────────

def build(path, italic, outdir):
    font = TTFont(path, recalcTimestamp=False)  # сборка должна быть побайтово воспроизводимой
    log = []
    (fix_italic if italic else fix_roman)(font, log)
    close_acute_gaps(font, font["GSUB"].table, log)
    uppercase_yat(font, font["GSUB"].table, log)
    rebuild_aalt(font, font["GSUB"].table, log)
    add_missing_anchors(font, log, italic, path)
    sort_feature_list(font["GSUB"].table)
    rebrand(font, italic, log)
    fix_metrics(font, log)
    round_instances(font, log)
    out = os.path.join(outdir, f"{PSFAMILY}{'-Italic' if italic else ''}-VF.ttf")
    font.save(out)
    print(f"\n=== {'КУРСИВ' if italic else 'ПРЯМОЕ'} → {os.path.basename(out)}")
    for line in log:
        print("  •", line)
    return out

if __name__ == "__main__":
    roman, italic = sys.argv[1], sys.argv[2]
    outdir = sys.argv[3] if len(sys.argv) > 3 else "."
    os.makedirs(outdir, exist_ok=True)
    build(roman, False, outdir)
    build(italic, True, outdir)
