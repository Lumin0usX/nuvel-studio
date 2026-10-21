// Exercise the shipped filter: compact discovery must never limit search results.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../ui/studio.js'), 'utf8');
const start = source.indexOf('function filterPlatforms()');
const end = source.indexOf("\n$('platform-search').addEventListener", start);
assert.ok(start >= 0 && end > start, 'Platform filter must remain independently testable');
const classes = new Set();
const entries = Array.from({length: 50}, (_, index) => ({dataset: {search: index === 22 ? 'pinterest pinterest.com' : 'source-' + index}, hidden: false}));
const elements = {
  'platform-search': {value: ''},
  platforms: {children: entries, classList: {toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name)}},
  'expand-platforms': {setAttribute(name, value) {this[name] = value;}},
  'support-summary': {}, 'platform-empty': {}
};
const context = vm.createContext({$: id => elements[id], sourcesExpanded: false, knownPlatforms: entries,
  t: (key, values) => key.replace('{count}', values?.count)});
vm.runInContext(source.slice(start, end), context);
const update = () => vm.runInContext('filterPlatforms()', context);
const visible = () => entries.filter(entry => !entry.hidden);
update(); assert.equal(visible().length, 8); assert.equal(elements['expand-platforms']['aria-expanded'], 'false');
elements['platform-search'].value = '  PINTEREST  '; update();
assert.equal(visible().length, 1); assert.equal(visible()[0], entries[22]);
assert.equal(elements['expand-platforms'].hidden, true);
elements['platform-search'].value = 'no match'; update(); assert.equal(elements['platform-empty'].hidden, false);
elements['platform-search'].value = ''; update(); assert.equal(visible().length, 8);
vm.runInContext('sourcesExpanded = true', context); update();
assert.equal(visible().length, 50); assert.equal(classes.has('expanded'), true);
assert.equal(elements['expand-platforms'].textContent, 'Show fewer');
vm.runInContext('sourcesExpanded = false', context); update();
assert.equal(visible().length, 8); assert.equal(classes.has('expanded'), false);
context.knownPlatforms = entries.slice(0, 5); update(); assert.equal(elements['expand-platforms'].hidden, true);
console.log('Platform directory passed: compact eight, search across all sources, empty results and reversible expansion');
