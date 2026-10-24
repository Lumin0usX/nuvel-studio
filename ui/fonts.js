/* Fonts are bundled, scoped to this app, and remembered per interface language. */
(() => {
  'use strict';
  const catalog = window.StudioFontCatalog;
  const languages = Object.keys(catalog);
  function clean(values) {
    const result = {};
    for (const language of languages) {
      const value = values?.[language];
      result[language] = catalog[language].fonts.some(font => font.id === value) ? value : catalog[language].default;
    }
    return result;
  }
  function stack(language, selections) {
    const locale = languages.includes(language) ? language : 'th';
    const choices = clean(selections);
    const order = [...new Set([locale, 'en', 'th', ...(locale === 'ja' ? ['ja','zh-CN'] : ['zh-CN','ja'])])];
    return order.map(key => '"Studio-' + choices[key] + '"').join(', ') + ', system-ui, sans-serif';
  }
  function apply(language, selections) {
    document.documentElement.style.setProperty('--font', stack(language, selections));
  }
  async function load(language, id) {
    const group = catalog[language];
    if (!group || !group.fonts.some(font => font.id === id)) throw new Error('Unknown font.');
    const results = await Promise.all([400, 600].map(weight =>
      document.fonts.load(weight + ' 16px "Studio-' + id + '"', group.sample)));
    if (results.some(faces => !faces.length || faces.some(face => face.status !== 'loaded')))
      throw new Error('Font unavailable.');
  }
  let cached = {};
  try { cached = JSON.parse(localStorage.getItem('nuvel-obsidian-preferences-v1') || '{}') || {}; }
  catch { /* Ordinary system fallbacks remain available when storage is blocked. */ }
  window.StudioFonts = Object.freeze({catalog, clean, stack, apply, load});
  apply(cached.language || 'th', clean(cached.fonts));
})();
