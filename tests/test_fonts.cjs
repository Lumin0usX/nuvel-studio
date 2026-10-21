// Exercise the real font bootstrap, language isolation, and font-loading failure handling.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = ['font-catalog.js', 'fonts.js'].map(file => fs.readFileSync(path.join(__dirname, '../ui', file), 'utf8')).join('\n');
function boot(saved, load = async () => [{status: 'loaded'}], blocked = false) {
  const properties = {}, calls = [];
  const context = {
    window: {},
    document: {
      documentElement: {style: {setProperty: (key, value) => {properties[key] = value;}}},
      fonts: {load: (...args) => {calls.push(args); return load(...args);}}
    },
    localStorage: {getItem: () => {if (blocked) throw new Error('Storage blocked'); return saved;}}
  };
  vm.runInNewContext(source, context);
  return {fonts: context.window.StudioFonts, properties, calls};
}
(async () => {
  const app = boot(null);
  for (const [language, count] of Object.entries({en: 5, th: 5, ja: 3, 'zh-CN': 3})) {
    assert.equal(app.fonts.catalog[language].fonts.length, count);
  }
  assert.match(app.properties['--font'], /^"Studio-notosansthai"/);
  for (const cached of ['invalid JSON', '{}', '{"fonts":{"th":"lato"}}'])
    assert.match(boot(cached).properties['--font'], /^"Studio-notosansthai"/);
  assert.match(boot(null, undefined, true).properties['--font'], /^"Studio-notosansthai"/);
  const cached = boot('{"language":"ja","fonts":{"ja":"mplus1p","en":"lato","th":"prompt","zh-CN":"zcoolxiaowei"}}');
  assert.match(cached.properties['--font'], /^"Studio-mplus1p", "Studio-lato", "Studio-prompt", "Studio-zcoolxiaowei"/);
  cached.fonts.apply('en', {en: 'montserrat', th: 'kanit'});
  assert.match(cached.properties['--font'], /^"Studio-montserrat", "Studio-kanit"/);
  for (const [language, group] of Object.entries(app.fonts.catalog)) {
    for (const font of group.fonts) await app.fonts.load(language, font.id);
  }
  assert.equal(app.calls.length, 32);
  assert.ok(app.calls.every(([query, text]) => /^(400|600) 16px "Studio-/.test(query) && text.length));
  await assert.rejects(() => app.fonts.load('th', 'lato'), /Unknown font/);
  await assert.rejects(() => boot(null, async () => []).fonts.load('en', 'inter'), /Font unavailable/);
  await assert.rejects(() => boot(null, async () => [{status: 'error'}]).fonts.load('en', 'inter'), /Font unavailable/);
  await assert.rejects(() => boot(null, async () => {throw new Error('Missing file');}).fonts.load('en', 'inter'), /Missing file/);
  console.log('Fonts passed: 5/5/3/3 choices, offline bootstrap, per-language selection, storage recovery and real font-load failure handling');
})().catch(error => {console.error(error); process.exitCode = 1;});
