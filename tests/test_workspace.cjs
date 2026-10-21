// Activity must earn its column; polling and empty state changes use the shipped renderer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../ui/studio.js'), 'utf8');
function element() {
  const classes = new Set();
  return {children: [], classes,
    classList: {toggle: (key, value) => value ? classes.add(key) : classes.delete(key)},
    replaceChildren() {this.children = [];}, append(child) {this.children.push(child);}};
}
const workspace = element(), elements = {};
for (const id of ['recent-section','recent-list','downloads-list','history-search','history-filter']) elements[id] = element();
elements['history-search'].value = ''; elements['history-filter'].value = 'all';
const context = vm.createContext({snapshot: {phase: 'idle', history: []}, lastLists: '', lastRequest: null,
  document: {activeElement: null, querySelector: selector => {assert.equal(selector,'.workspace'); return workspace;}},
  $: id => elements[id], t: value => value, renderHistory: () => {},
  node: (tag, className, text) => ({tag, className, text}),
  emptyState: () => ({kind: 'empty'}), transferRow: (item, current) => ({item, current})});
const start = source.indexOf('function renderLists('), end = source.indexOf('\nfunction renderHistory()', start);
assert.ok(start >= 0 && end > start);
vm.runInContext(source.slice(start,end), context);
const render = () => vm.runInContext('renderLists(true)', context);
render();
assert.equal(workspace.classes.has('has-activity'),false);
assert.equal(elements['recent-section'].classes.has('is-empty'),true);
assert.equal(elements['recent-list'].children.length,1);
assert.equal(elements['recent-list'].children[0].tag,'p');
context.snapshot = {phase:'downloading', history:[], title:'Current job'}; render();
assert.equal(workspace.classes.has('has-activity'),true);
assert.equal(elements['recent-section'].classes.has('is-empty'),false);
assert.equal(elements['recent-list'].children[0].current,true);
context.snapshot = {phase:'idle',history:[{id:'real-entry',title:'Saved file'}]}; render();
assert.equal(workspace.classes.has('has-activity'),true);
assert.equal(elements['recent-list'].children[0].item.id,'real-entry');
context.snapshot = {phase:'idle',history:[]}; render();
assert.equal(workspace.classes.has('has-activity'),false);
assert.equal(elements['recent-section'].classes.has('is-empty'),true);
console.log('Workspace passed: compact empty state, real job/history expansion and collapse after records are removed');
