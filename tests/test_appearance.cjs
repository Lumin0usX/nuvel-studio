// Exercise the real appearance bootstrap and cancellation, independently of download code.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../ui/appearance.js'), 'utf8');
function boot(saved, reduced = false, blocked = false) {
  let listener;
  const media = {matches: reduced, addEventListener: (_, callback) => {listener = callback;}};
  const root = {dataset: {}};
  const context = {window: {matchMedia: () => media}, document: {documentElement: root},
    localStorage: {getItem: () => {if (blocked) throw new Error('Blocked storage'); return saved;}}};
  vm.runInNewContext(source, context);
  return {ui: context.window.StudioAppearance, root,
    osChange: value => {media.matches = value; listener();}};
}
function animatedElement() {
  const calls = [], effects = [];
  return {calls, effects, hidden: false, animate: (frames, options) => {
    calls.push({frames, options});
    const effect = {cancelled: false, finished: new Promise(() => {}), cancel() {this.cancelled = true;}};
    effects.push(effect); return effect;
  }};
}
for (const saved of [null, '{}', 'bad json', '{"visualStyle":"unknown"}']) {
  const app = boot(saved);
  assert.equal(app.root.dataset.visualStyle, 'obsidian');
  assert.equal(app.ui.motionEnabled, true);
}
assert.equal(boot(null, false, true).root.dataset.visualStyle, 'obsidian');
const saved = boot('{"visualStyle":"glass","reducedMotion":true}');
assert.equal(saved.root.dataset.visualStyle, 'glass'); assert.equal(saved.ui.motionEnabled, false);
const app = boot('{"visualStyle":"glass"}');
const element = animatedElement();
app.ui.enter(element); app.ui.enter(element);
assert.equal(element.calls.length, 2); assert.equal(element.effects[0].cancelled, true);
assert.equal(element.effects[1].cancelled, false);
app.ui.set({visualStyle: 'glass', reducedMotion: true});
assert.equal(element.effects[1].cancelled, true); assert.equal(app.root.dataset.motion, 'off');
app.ui.enter(element); assert.equal(element.calls.length, 2);
app.ui.set({visualStyle: 'obsidian', reducedMotion: false});
app.ui.enter(element, 'dialog'); assert.equal(element.calls.length, 3);
app.osChange(true); assert.equal(element.effects[2].cancelled, true);
assert.equal(app.ui.motionEnabled, false);
app.ui.set({visualStyle: 'glass', reducedMotion: false});
assert.equal(app.ui.motionEnabled, false); // OS Reduce Motion has precedence.
app.osChange(false); assert.equal(app.ui.motionEnabled, true);
app.ui.set({visualStyle: 'glass', reducedMotion: true}); app.osChange(true); app.osChange(false);
assert.equal(app.ui.motionEnabled, false); // Manual Off survives OS changes.
app.ui.set({visualStyle: 'invalid'}); assert.equal(app.root.dataset.visualStyle, 'obsidian');
const hidden = animatedElement(); hidden.hidden = true;
app.ui.enter(hidden); assert.equal(hidden.calls.length, 0);
app.ui.enter({hidden: false}); // Older engines without WAAPI remain functional.
console.log('Appearance passed: original default, glass cache, live motion toggle, interruption and system Reduce Motion precedence');
