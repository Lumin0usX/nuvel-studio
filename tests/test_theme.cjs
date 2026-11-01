// SPDX-License-Identifier: GPL-3.0-only
// Copyright © 2026 Lumin0usX

// Test actual theme initialization and OS change events, without a browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../ui/theme.js'), 'utf8');
function boot(saved, darkSystem = false, blockedStorage = false) {
  let listener;
  const media = {matches: darkSystem, addEventListener: (event, callback) => {listener = callback;}};
  const root = {dataset: {}};
  const meta = {};
  const context = {
    window: {matchMedia: () => media},
    document: {documentElement: root, querySelector: selector => ({setAttribute: (attribute, value) => {meta[selector] = value;}})},
    localStorage: {getItem: () => {if (blockedStorage) throw new Error('Storage blocked'); return saved;}}
  };
  vm.runInNewContext(source, context);
  return {theme: context.window.StudioTheme, root, meta, osChange: dark => {media.matches = dark; listener();}};
}
// A light OS must never silently change the application's Dark default.
for (const saved of [null, '{}', 'invalid JSON', '{"theme":"unknown"}']) {
  const app = boot(saved, false);
  assert.equal(app.theme.mode, 'dark'); assert.equal(app.root.dataset.theme, 'dark');
}
assert.equal(boot(null, false, true).root.dataset.theme, 'dark');
const light = boot('{"theme":"light"}', true);
assert.equal(light.root.dataset.theme, 'light');
light.osChange(false); light.osChange(true);
assert.equal(light.root.dataset.theme, 'light');
assert.equal(light.meta['meta[name="color-scheme"]'], 'light');
assert.equal(light.meta['meta[name="theme-color"]'], '#f2f3f6');
const system = boot('{"theme":"system"}', false);
assert.equal(system.root.dataset.theme, 'light');
system.osChange(true); assert.equal(system.root.dataset.theme, 'dark');
system.theme.set('dark'); system.osChange(false);
assert.equal(system.root.dataset.theme, 'dark');
system.theme.set('light'); assert.equal(system.root.dataset.theme, 'light');
system.theme.set('invalid'); assert.equal(system.theme.mode, 'dark');
console.log('Theme passed: Dark default, cached preference, blocked storage, live system changes and explicit overrides');
