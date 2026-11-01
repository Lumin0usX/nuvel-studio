// SPDX-License-Identifier: GPL-3.0-only
// Copyright © 2026 Lumin0usX

// Run the shipped renderer/poller: catalog deltas must preserve source/engine data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../ui/studio.js'), 'utf8');
const nodes = {'connection-label': {}, 'dock-status': {}};
const calls = [], catalogs = [];
let response, fail = false;
const context = vm.createContext({
  ready: true, polling: false, connected: false, catalogRevision: null,
  snapshot: {phase: 'idle', history: []}, lastPhase: 'idle',
  imageEngine: {available: false, modules: []}, engineVersion: '', appUpdate: {},
  activePhases: new Set(['downloading', 'processing']),
  $: id => nodes[id], t: value => value, toast() {},
  api: async (...args) => {calls.push(args); if (fail) throw new Error('disconnected'); return response;},
  renderPlatforms: value => catalogs.push(value),
  renderEngineVersion() {}, renderAppUpdate() {}, renderFontSettings() {},
  updateButtons() {}, renderLists() {}, renderDock() {}
});
const renderStart = source.indexOf('function render(state)');
const renderEnd = source.indexOf('\nfunction renderEngineVersion()', renderStart);
const pollStart = source.indexOf('async function poll()');
const pollEnd = source.indexOf('\nfunction connect()', pollStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart && pollStart >= 0 && pollEnd > pollStart);
vm.runInContext(source.slice(renderStart, renderEnd) + '\n' + source.slice(pollStart, pollEnd), context);
const poll = () => vm.runInContext('poll()', context);
(async () => {
  // A scan may still be running on the first request.
  response = {phase: 'idle', history: [], platforms: [], catalog_revision: 'scanning', version: ''};
  await poll(); assert.deepEqual(calls.at(-1), ['snapshot', null]);
  response = {phase: 'idle', history: [], platforms: [{name: 'Real source'}],
    image_engine: {available: true, modules: ['fixture']}, version: 'engine-version', catalog_revision: 'complete'};
  await poll(); assert.deepEqual(calls.at(-1), ['snapshot', 'scanning']);
  assert.equal(catalogs.at(-1)[0].name, 'Real source');
  response = {phase: 'downloading', history: [], percent: 42, catalog_revision: 'complete'};
  await poll(); assert.deepEqual(calls.at(-1), ['snapshot', 'complete']);
  assert.equal(catalogs.length, 2);
  assert.equal(context.snapshot.percent, 42);
  assert.equal(context.engineVersion, 'engine-version');
  assert.equal(context.imageEngine.available, true);
  assert.equal(Object.hasOwn(context.snapshot, 'catalog_revision'), false);
  fail = true; await poll(); assert.equal(context.connected, false);
  fail = false; response = {phase: 'idle', history: [], catalog_revision: 'new-session',
    platforms: [{name: 'Refreshed source'}], version: 'new-engine'};
  await poll(); assert.deepEqual(calls.at(-1), ['snapshot', null]);
  assert.equal(context.connected, true); assert.equal(context.catalogRevision, 'new-session');
  assert.equal(catalogs.at(-1)[0].name, 'Refreshed source');
  // A response from a server without revision support remains usable.
  response = {phase: 'idle', history: [], platforms: [], version: 'legacy-engine'};
  await poll(); assert.equal(context.catalogRevision, null);
  assert.equal(context.engineVersion, 'legacy-engine');
  console.log('Snapshot polling passed: async scan, compact progress, retained catalog, reconnect and legacy response');
})().catch(error => {console.error(error); process.exitCode = 1;});
