#!/usr/bin/env python3
"""
Проверка Slovosbor Serif: всё ли на месте после сборки или чужого экспорта.

Запуск:  python3 verify_slovosbor.py SlovosborSerif-VF.ttf SlovosborSerif-Italic-VF.ttf

Печатает PASS или список того, что отвалилось. Прогоняйте на любом файле,
который вернётся из FontCreator, — правки живут в GSUB/GPOS и молча теряются
при экспорте из старого проекта.
"""
import subprocess, sys
from fontTools.ttLib import TTFont

FAMILY = "Slovosbor Serif"


def shape(path, text, lang="ru", features=None):
    cmd = ["hb-shape", "--no-positions", "--no-clusters",
           "--script=Cyrl", "--language=" + lang]
    if features:
        cmd.append("--features=" + features)
    try:
        r = subprocess.run(cmd + [path, text], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("Error: 'hb-shape' (harfbuzz) not found. Install with: brew install harfbuzz (macOS) or apt-get install libharfbuzz-bin (Linux)")
    return r.stdout.strip().strip("[]")


LOW = "абвгдежзийклмнопрстуфхцчшщъыьэюя"
UP = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def locale_diff(path, lang):
    return [c for c in LOW + UP if shape(path, c) != shape(path, c, lang)]


def check(path, italic):
    style = "Italic" if italic else "Regular"
    font = TTFont(path)
    name, os2 = font["name"], font["OS/2"]
    bad = []

    def want(cond, msg):
        if not cond:
            bad.append(msg)

    # имя и связка Regular ↔ Italic
    want(name.getDebugName(1) == FAMILY, f"name[1] = {name.getDebugName(1)!r}, ждали {FAMILY!r}")
    want(name.getDebugName(16) == FAMILY, "name[16] потерян — курсив не свяжется с прямым")
    want(name.getDebugName(2) == style, f"name[2] = {name.getDebugName(2)!r}, ждали {style!r}")
    want(name.getDebugName(7) is None, "вернулся чужой товарный знак в name[7]")
    want(os2.achVendID.strip() == "SLVS", f"achVendID = {os2.achVendID!r}")

    # метрики
    want(bool(os2.fsSelection & (1 << 7)), "флаг USE_TYPO_METRICS сброшен")
    want(font["hhea"].ascent == os2.sTypoAscender and
         font["hhea"].descent == os2.sTypoDescender,
         "hhea и typo разошлись — интерлиньяж поедет между приложениями")

    # языковые системы
    scripts = {s.ScriptTag: s.Script for s in font["GSUB"].table.ScriptList.ScriptRecord}
    want("cyrl" in scripts, "нет кириллического скрипта в GSUB")
    if "cyrl" in scripts:
        tags = {r.LangSysTag.strip() for r in scripts["cyrl"].LangSysRecord}
        for t in ("BGR", "CSL", "SRB", "MKD"):
            want(t in tags, f"не зарегистрирован cyrl/{t}")

    # фичи
    feats = {f.FeatureTag for f in font["GSUB"].table.FeatureList.FeatureRecord}
    for t in ("locl", "salt", "aalt", "ss09", "ss10"):
        want(t in feats, f"пропала фича {t}")
    if not italic:
        want("calt" in feats, "пропала calt — ять в прописных не уйдёт в асцендер")

    # aalt должен быть полным, а не огрызком
    alts = {}
    g = font["GSUB"].table
    for fr in g.FeatureList.FeatureRecord:
        if fr.FeatureTag == "aalt":
            for li in fr.Feature.LookupListIndex:
                for st in g.LookupList.Lookup[li].SubTable:
                    alts.update(getattr(st, "alternates", {}))
    want(len(alts) > 60, f"aalt похудел до {len(alts)} букв — палитра глифов опустеет")

    # якоря верхних меток
    marks = None
    for lk in font["GPOS"].table.LookupList.Lookup:
        if lk.LookupType == 4:
            for st in lk.SubTable:
                if "acutecomb" in st.MarkCoverage.glyphs:
                    marks = st
    want(marks is not None, "не найден лукап верхних меток")
    if marks:
        cmap = font.getBestCmap()
        cov = set(marks.BaseCoverage.glyphs)
        for cp, ch in ((0x044D, "э"), (0x044E, "ю"), (0x044F, "я"), (0x0454, "є"),
                       (0x0463, "ѣ"), (0x046B, "ѫ"), (0x0467, "ѧ"),
                       (0x0469, "ѩ"), (0x046D, "ѭ")):
            want(cmap.get(cp) in cov, f"у {ch} пропал якорь — акут уедет на край")
        bg_yu = "yucyrl.loclBGR" if not italic else "u044E.loclBGR"
        want(bg_yu in cov, f"у болгарского ю ({bg_yu}) пропал якорь")
        want(len(cov) > 240, f"якорей всего {len(cov)} — часть альтернатив потеряла разметку")

    # локали: сербское и македонское прямое обязано совпасть с русским
    if not italic:
        for lang in ("sr", "mk"):
            d = locale_diff(path, lang)
            want(not d, f"{lang} в прямом отличается от русского: {' '.join(d)}")
    else:
        for lang in ("sr", "mk"):
            d = locale_diff(path, lang)
            want(sorted(d) == list("гдпт"), f"{lang} в курсиве даёт {' '.join(d)}, ждали г д п т")
    want(len(locale_diff(path, "bg")) >= 13, "болгарский набор похудел")

    # ять по схеме заказчика
    if not italic:
        want(shape(path, "ѣ") == "u0463", "прямой ять по умолчанию сменился")
        want(shape(path, "СѢЮ").split("|")[1] == "Yatcyrl.alt01",
             "ять в прописных не уходит в асцендер")
    else:
        want(shape(path, "ѣ") == "yatcyrl.alt01", "курсивный ять по умолчанию сменился")
    want(shape(path, "ѣ", "bg", "salt").endswith("alt02"), "salt-ять в болгарице не сработал")
    want(shape(path, "ѣ", "ru", "salt") == shape(path, "ѣ"), "salt трогает ять вне болгарицы")

    # юсы
    want(shape(path, "ѫ", "bg") == "u046B", "болгарский юс снова рукописный")
    want(shape(path, "ѫ", "ru", "ss10") == "yusbigcyrl.alt01", "ss10 не даёт рукописный юс")
    want(shape(path, "ѫ", "bg", "salt") == "yusbigcyrlalt1", "круглый юс в salt не сработал")

    print(f"\n=== {style}: {path}")
    if bad:
        for b in bad:
            print("  ✗", b)
    else:
        print("  ✓ PASS — все правки на месте")
    return not bad


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ok = check(sys.argv[1], False) & check(sys.argv[2], True)
    print()
    sys.exit(0 if ok else 1)
