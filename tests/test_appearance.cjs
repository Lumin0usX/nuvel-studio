// SPDX-License-Identifier: GPL-3.0-only
// Copyright © 2026 Lumin0usX

// Exercise the real appearance bootstrap and cancellation, independently of download code.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../ui/appearance.js'), 'utf8');
function boot(saved, reduced = false, blocked = false, glassSupported = true, transparencyReduced = false) {
  let listener;
  const media = {matches: reduced, addEventListener: (_, callback) => {listener = callback;}};
  const properties = {};
  const transparency = {matches: transparencyReduced};
  const root = {dataset: {}, style: {setProperty: (name, value) => {properties[name] = value;}}};
  const context = {window: {matchMedia: query => query.includes('transparency') ? transparency : media,
    CSS: {supports: () => glassSupported}}, document: {documentElement: root},
    localStorage: {getItem: () => {if (blocked) throw new Error('Blocked storage'); return saved;}}};
  vm.runInNewContext(source, context);
  return {ui: context.window.StudioAppearance, root, properties,
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
for (const opacity of [0, 1, 35, 72, 99, 100]) {
  const restored = boot(JSON.stringify({visualStyle: 'glass', glassOpacity: opacity}));
  assert.equal(restored.properties['--glass-opacity'], String(opacity / 100));
  restored.ui.set({visualStyle: 'obsidian', glassOpacity: opacity});
  assert.equal(restored.properties['--glass-opacity'], String(opacity / 100));
  restored.osChange(true); restored.osChange(false);
  assert.equal(restored.properties['--glass-opacity'], String(opacity / 100));
}
for (const opacity of [null, false, '35', -1, 101, 3.5, 'url(https://example.com)']) {
  const restored = boot(JSON.stringify({glassOpacity: opacity}));
  assert.equal(restored.properties['--glass-opacity'], '0.72');
}
assert.equal(boot(null, false, true).properties['--glass-opacity'], '0.72');
assert.equal(boot(null, false, false, false).ui.glassSupported, false);
assert.equal(boot(null, false, false, true, true).ui.transparencyReduced, true);
console.log('Appearance passed: style cache, live motion toggle, cancellation, glass opacity bounds/cache and OS accessibility preferences');
