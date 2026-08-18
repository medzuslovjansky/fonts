import '@interslavic/slovosbor-serif/index.css';

// DOM Elements
const canvas = document.getElementById('specimen-text') as HTMLElement;
const weightSlider = document.getElementById('weight-slider') as HTMLInputElement;
const weightVal = document.getElementById('weight-val') as HTMLElement;
const sizeSlider = document.getElementById('size-slider') as HTMLInputElement;
const sizeVal = document.getElementById('size-val') as HTMLElement;
const leadingSlider = document.getElementById('leading-slider') as HTMLInputElement;
const leadingVal = document.getElementById('leading-val') as HTMLElement;
const trackingSlider = document.getElementById('tracking-slider') as HTMLInputElement;
const trackingVal = document.getElementById('tracking-val') as HTMLElement;

const toggleItalic = document.getElementById('toggle-italic') as HTMLInputElement;
const featCalt = document.getElementById('feat-calt') as HTMLInputElement;
const featSs10 = document.getElementById('feat-ss10') as HTMLInputElement;
const featSs09 = document.getElementById('feat-ss09') as HTMLInputElement;
const featSs07 = document.getElementById('feat-ss07') as HTMLInputElement;
const featSalt = document.getElementById('feat-salt') as HTMLInputElement;
const langSelect = document.getElementById('lang-select') as HTMLSelectElement;
const cssSnippet = document.getElementById('css-snippet') as HTMLElement;

interface PresetConfig {
  text: string;
  lang: string;
  italic?: boolean;
  calt?: boolean;
  ss10?: boolean;
  ss09?: boolean;
  ss07?: boolean;
  salt?: boolean;
}

const presets: Record<string, PresetConfig> = {
  'isv-std': {
    text: 'Každa ščestliva ryba fugu uměje graciozno padati v hladnu vodu.\nЧи јест ли грєх мыслити, же западне цифры сут бољ, воњ и шок?',
    lang: 'isv',
    calt: true,
  },
  'isv-etym': {
    text: 'Ćuđi děvėc už nese dȯžď i gręź. Či bųde li vśako zlo, smŕťny sȯn, i fataĺno pohlådańje?\nЋуђи дѣвьц уж несе дъждь и грѧзь. Чи бѫде ли всяко зло, смьртьны сън, и фатально похлӑданьѥ?',
    lang: 'isv',
    calt: true,
  },
  'yat-test': {
    text: 'ХЛѢБЪ Хлѣбъ СѢѬ Сѣѭ РѢШѪ Рѣшѫ... ѢДА Ѣда ...\nСѢЮ СВѢТЪ ВѢРА ВѢКЪ ѢХАТИ ѢСТИ\nсѣю свѣтъ вѣра вѣкъ ѣхати ѣсти (сѣмена, рѣка, лѣсъ)',
    lang: 'isv',
    calt: true,
  },
  'yus-test': {
    text: 'ѫ ѭ ѧ ѩ  —  ѫ́ ѧ́ ѭ́ ѩ́\nрѫка, пѫть, мѫжь, свѧты, пѧть, понѧти, имѧ, взѧти, сѫть',
    lang: 'isv',
    ss10: true,
    calt: true,
  },
  'locl-bg': {
    text: 'Българскиятъ езикъ притежава уникаленъ рѫкописенъ характеръ на буквитѣ. Ах, чудна българска земьо, покланям се пред теб!',
    lang: 'bg',
    calt: true,
  },
  'locl-sr': {
    text: 'Боже, џентлмени осећају физичко гађење од прљавих шољица! Фини чика Љубомир згужва џак у жутој фиоци.',
    lang: 'sr',
    italic: true,
    calt: true,
  },
  'locl-mk': {
    text: 'Желката Љуба музицира на харфа читајќи го Његош, а песот Ѓоше се џари во ѕвезди.',
    lang: 'mk',
    italic: true,
    calt: true,
  },
  'locl-uk': {
    text: 'Фабрикуймо гіпотези: шеф чекає звіт щодо з’їздів юристів у п’ятницю. Жебракують філософи при ґанку церкви в Галичі.',
    lang: 'uk',
    calt: true,
  },
  'locl-be': {
    text: 'У чашчы паўднёвых лясоў ёрзаў спрытны барсук з хітраватай мысай. Чалавек з гонарам глядзіць у будучыню праз прызму вякоў.',
    lang: 'be',
    calt: true,
  },
  'locl-ru': {
    text: 'Съѣшь-же ещё этихъ мягкихъ французскихъ булокъ, да выпѣй ѳракійскаго чаю.',
    lang: 'ru',
    calt: true,
  },
  'locl-pl': {
    text: 'Pchnąć w tę łódź jeża lub ośm skrzyń fig. Stróż pchnął kość w głąb żytniej fuzji.',
    lang: 'pl',
    calt: true,
  },
  'locl-cs': {
    text: 'Příliš žluťoučký kůň úpěl ďábelské ódy. Kŕdeľ šťastných ďatľov učí pri ústí Váhu mláďa žrať čerstvé smrekové ihličie.',
    lang: 'cs',
    calt: true,
  },
};

function updateSpecimen() {
  const weight = weightSlider.value;
  const size = sizeSlider.value;
  const leading = leadingSlider.value;
  const tracking = trackingSlider.value;
  const isItalic = toggleItalic.checked;
  const lang = langSelect.value;

  weightVal.textContent = weight;
  sizeVal.textContent = `${size}px`;
  leadingVal.textContent = leading;
  trackingVal.textContent = `${tracking}em`;

  canvas.style.fontWeight = weight;
  canvas.style.fontSize = `${size}px`;
  canvas.style.lineHeight = leading;
  canvas.style.letterSpacing = `${tracking}em`;
  canvas.style.fontStyle = isItalic ? 'italic' : 'normal';
  canvas.lang = lang;

  // OpenType features
  const features: string[] = [];
  features.push(`"calt" ${featCalt.checked ? 1 : 0}`);
  if (featSs10.checked) features.push('"ss10" 1');
  if (featSs09.checked) features.push('"ss09" 1');
  if (featSs07.checked) features.push('"ss07" 1');
  if (featSalt.checked) features.push('"salt" 1');

  const featureString = features.join(', ');
  canvas.style.fontFeatureSettings = featureString;

  // Update CSS snippet
  cssSnippet.textContent = `.custom-text {
  font-family: 'Slovosbor Serif', Georgia, serif;
  font-weight: ${weight};
  font-style: ${isItalic ? 'italic' : 'normal'};
  font-size: ${size}px;
  line-height: ${leading};
  letter-spacing: ${tracking}em;
  font-feature-settings: ${featureString};
}`;
}

// Event Listeners
[weightSlider, sizeSlider, leadingSlider, trackingSlider].forEach((el) =>
  el.addEventListener('input', updateSpecimen)
);

[toggleItalic, featCalt, featSs10, featSs09, featSs07, featSalt].forEach((el) =>
  el.addEventListener('change', updateSpecimen)
);

langSelect.addEventListener('change', updateSpecimen);

// Presets Click Handlers
document.querySelectorAll<HTMLButtonElement>('.preset-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.preset-chip').forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');

    const key = chip.dataset.text || 'isv-std';
    const config = presets[key];

    if (config) {
      canvas.innerText = config.text;

      // Update and synchronize controls
      langSelect.value = config.lang;
      toggleItalic.checked = Boolean(config.italic);
      featCalt.checked = config.calt !== undefined ? config.calt : true;
      featSs10.checked = Boolean(config.ss10);
      featSs09.checked = Boolean(config.ss09);
      featSs07.checked = Boolean(config.ss07);
      featSalt.checked = Boolean(config.salt);

      updateSpecimen();
    }
  });
});

updateSpecimen();
