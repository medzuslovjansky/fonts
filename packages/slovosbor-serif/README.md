# @interslavic/slovosbor-serif

[![Version](https://img.shields.io/npm/v/@interslavic/slovosbor-serif.svg)](https://www.npmjs.com/package/@interslavic/slovosbor-serif)
[![License: OFL-1.1](https://img.shields.io/badge/License-OFL--1.1-blue.svg)](license.txt)

**Slovosbor Serif** is an extensively revised, typographically enriched variable serif typeface commissioned and funded by [Yaroslav Serhieiev](https://github.com/noomorph), designed and expanded by [S.-V. Sofienczuk-Wojczyszyn](https://www.fiverr.com/sergevictor) (derived from IBM Plex Serif v5 by [Bold Monday](https://www.boldmonday.com/)). It is specifically tailored for **Interslavic**, modern Slavic languages (Russian, Ukrainian, Belarusian, Bulgarian, Serbian, Macedonian, Polish, Czech, Slovak, Croatian, Slovenian), and historical Cyrillic texts.

Packaged in the `@fontsource/*` standard structure with split WOFF2 subsets and OpenType layout features preserved.

---

## Quick Start

### Installation

```bash
npm install @interslavic/slovosbor-serif
# or
yarn add @interslavic/slovosbor-serif
```

### Usage in CSS / JS

Import the variable font across all subsets:

```js
// In your JS/TS entry point
import '@interslavic/slovosbor-serif';
// or
import '@interslavic/slovosbor-serif/variable.css';
```

Or in CSS:

```css
@import '@interslavic/slovosbor-serif';

body {
  font-family: 'Slovosbor Serif', Georgia, serif;
  font-weight: 400; /* Any weight between 100 and 700 */
  font-style: normal;
}
```

If you only need specific subsets:

```css
@import '@interslavic/slovosbor-serif/cyrillic.css';
@import '@interslavic/slovosbor-serif/latin.css';
@import '@interslavic/slovosbor-serif/greek.css';
@import '@interslavic/slovosbor-serif/pi.css';
```

### Direct HTML / CDN usage

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@interslavic/slovosbor-serif/index.css">
```

---

## Typography & OpenType Features

Slovosbor Serif features deep linguistic engineering across GPOS mark attachments and GSUB substitutions:

### 1. Combining Diacritics & GPOS Mark-to-Base
Combining accents (`U+0300–0304, U+0306–030C, U+0312, U+0315, U+031B, U+0323, U+0326–0328, U+032D–032E, U+0331`) and modifier spacing marks (`U+02BB–02BC, U+02C7, U+02D8–02D9, U+02DB, U+02DD`) are duplicated across all script subsets.
* Ensures **mark-attachment** never splits across `@font-face` boundaries.
* Stacking accents on Cyrillic vowels and historical letters (`ѣ́`, `ѫ́`, `ѧ́`, `є́`, `и́`, `у́`, `ю́`, `э́`, `я́`) sit precisely over the letter stem rather than drifting as loose ticks.

---

### 2. The Yat Letter (`ѣ` / `Ѣ`, U+0462, U+0463)

* **Automatic Uppercase Ascender Shift (`calt`)**: When an uppercase Yat appears in all-caps text (e.g. `СѢЮ`), the crossbar aligns with the cap-height while the vertical stem extends into the ascender zone (`Yatcyrl.alt01`).
* **Italic Default**: By default, Italic uses form 2 (`yatcyrl.alt01`). The historical standard form is accessible via `ss09` and `aalt`.
* **Bulgarian Locl / Salt**: In Bulgarian localization (`:lang(bg)` / `loclBGR`), Yat automatically renders in its authentic Bulgarian form (`yatcyrl.alt01` in upright, `yatcyrl.alt02` in italic); engaging `salt` inside Bulgarian further selects the alternative triangular/calligraphic shape (`yatcyrl.alt02`).

```html
<!-- Bulgarian Yat in Bulgarian context -->
<p lang="bg" style="font-feature-settings: 'salt' 1;">
  Българскиятъ езикъ ... буквитѣ
</p>
```

---

### 3. Yus Letters (`ѫ` `ѭ` `ѧ` `ѩ`, U+0467, U+0469, U+046B, U+046D)

* **Default**: Standard typographic historical Yus forms.
* **Handwritten Yus (`ss10`)**: Switches all Big and Little Yus forms (including iotated and accented forms) to calligraphic handwritten variants (`yusbigcyrl.alt01`, `yusiotifiedbigcyrl.alt01`, etc.).
* **Round Yus (`salt`)**: Activates round Yus variant.

```css
/* Activate calligraphic handwritten Yus forms */
.ancient-text {
  font-feature-settings: 'ss10' 1;
}
```

---

### 4. Cyrillic Localization (`locl`)

* **Bulgarian (`:lang(bg)` / `cyrl/BGR`)**: Authentic Bulgarian lowercase Cyrillic letterforms (13+ characters: в, г, д, ж, з, и, й, к, л, п, т, ц, ш, щ, ю).
* **Serbian & Macedonian (`:lang(sr)`, `:lang(mk)` / `cyrl/SRB`, `cyrl/MKD`)**:
  * **Upright (Roman)**: Matches standard pan-Slavic / Interslavic Cyrillic (without Bulgarian distortions).
  * **Italic**: Automatically engages Serbian italic glyphs for `г, д, п, т`.

```html
<!-- Automatically uses Serbian italic glyphs for г д п т -->
<p lang="sr" style="font-style: italic;">
  г д п т
</p>
```

---

### 5. Stylistic Sets Summary

| Feature | Name | Description |
|---|---|---|
| `calt` | Contextual Alternates | Automatically raises uppercase `Ѣ` stem in all-caps text |
| `locl` | Localized Forms | BGR (Bulgarian Cyrillic), SRB/MKD (Serbian italic `г,д,п,т`), CSL (Church Slavonic) |
| `ss07` | Alternate `У` | Alternate `У` with matching accented forms (`Ў`, `Ӯ`, `Ӱ`, `Ӳ`) |
| `ss09` | Alternate Cyrillic | Alternative forms for `б`, `д`, `ы`, `ш` with underline, etc. |
| `ss10` | Handwritten Yus | Calligraphic handwritten forms for `ѫ`, `ѭ`, `ѧ`, `ѩ` and their accented variants |
| `salt` | Stylistic Alternates | Round Yus, Bulgarian Yat, alternate `т`, `ш` |
| `aalt` | Access All Alternates | Full index of all 60+ letter alternate variants for glyph palettes |

---

## File Structure

* `index.css`, `variable.css` — imports all 6 subsets in normal and italic.
* `cyrillic.css` — Cyrillic-only subset.
* `latin.css` — Latin-1, Latin-2, Latin-3 subsets.
* `files/*.woff2` — optimized, pyftsubset-compiled WOFF2 webfonts.
* `raw/*.ttf` — full unsubsetted Variable TTFs (100–700 weight).

---

## License

* Font Software: [SIL Open Font License 1.1](license.txt)
* Original work: Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" (by Mike Abbink & [Bold Monday](https://www.boldmonday.com/)).
* Modifications: Copyright © 2026 [S.-V. Sofienczuk-Wojczyszyn](https://www.fiverr.com/sergevictor).
