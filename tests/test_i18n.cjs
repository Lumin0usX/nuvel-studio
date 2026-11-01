// SPDX-License-Identifier: GPL-3.0-only
// Copyright © 2026 Lumin0usX

// Run with: node tests/test_i18n.cjs. No browser or third-party test dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'ui/i18n.js'), 'utf8');
const catalog = JSON.parse(source.match(/\/\* CATALOG_START \*\/([\s\S]*?)\/\* CATALOG_END \*\//)[1]);
const updateCatalog = JSON.parse(source.match(/\/\* UPDATE_CATALOG_START \*\/([\s\S]*?)\/\* UPDATE_CATALOG_END \*\//)[1]);
for (const [key, values] of Object.entries(updateCatalog)) {
  catalog.th[key] = values[0]; catalog.en[key] = key; catalog.ja[key] = values[1]; catalog['zh-CN'][key] = values[2];
}
const context = {window: {}};
vm.createContext(context); vm.runInContext(source, context);
const i18n = context.window.StudioI18n;
const modes = i18n.translatedValues({video:'วิดีโอ'});
const expected = {en:['Settings','Video','Saved 3 images'], th:['การตั้งค่า','วิดีโอ','บันทึกแล้ว 3 ภาพ'], ja:['設定','動画','3 枚を保存しました'], 'zh-CN':['设置','视频','已保存 3 张图片']};
for (const language of i18n.languages) {
  assert.equal(i18n.setLanguage(language), true);
  assert.equal(i18n.t('Settings'), expected[language][0]);
  assert.equal(modes.video, expected[language][1]);
  assert.equal(i18n.t('Saved {count} images',{count:3}), expected[language][2]);
  assert.equal(i18n.backend('บันทึกแล้ว 3 ภาพ'), expected[language][2]);
  assert.equal(i18n.backend('ERROR: ExampleClip title [123].mp4'), 'ERROR: ExampleClip title [123].mp4');
  assert.deepEqual(Object.keys(catalog[language]).sort(), Object.keys(catalog.th).sort());
  for (const [key,value] of Object.entries(catalog[language])) {
    assert.ok(value, language + ': empty ' + key);
    if (language !== 'th') assert.ok(!/[\u0e00-\u0e7f]/.test(value), language + ': Thai copy leaked into ' + key);
    assert.ok(!value.includes('???'), 'Broken encoding in ' + key);
    assert.deepEqual(value.match(/\{\w+\}/g)?.sort() || [], key.match(/\{\w+\}/g)?.sort() || []);
  }
}
assert.equal(i18n.setLanguage('unknown'), false);
assert.equal(i18n.language, 'zh-CN');
i18n.setLanguage('en');
assert.equal(i18n.backend('ไม่เกิน 1080p'), 'Up to 1080p');
assert.equal(i18n.backend('ด้านยาวไม่เกิน 2048px'), 'Long edge up to 2048px');
assert.equal(i18n.backend('ภาพจาก example.com (4 ภาพ)'), 'Images from example.com (4 images)');
assert.equal(i18n.backend('ดาวน์โหลดไม่สำเร็จ\n\nรายละเอียด: ERROR: original diagnostic'), 'Download failed\n\nDetails: ERROR: original diagnostic');
assert.equal(i18n.t('อ่านตัวอย่างไม่สำเร็จ · คุณยังลองดาวน์โหลดได้\n'), 'Preview unavailable · You can still try downloading\n');
i18n.setLanguage('th');
assert.equal(i18n.backend('Could not connect to the app'),'เชื่อมต่อกับแอปไม่สำเร็จ');
// Every Thai literal used by the frontend must have an authored translation.
const app = fs.readFileSync(path.join(root, 'ui/studio.js'),'utf8');
for (const match of app.matchAll(/(['"])(?:\\.|(?!\1).)*?\1/g)) {
  if (!/[\u0e00-\u0e7f]/.test(match[0])) continue;
  const message = match[0].slice(1,-1).replace(/\\n/g,'\n');
  assert.ok(Object.hasOwn(catalog.th,message), 'Missing UI translation: '+message);
}
console.log('i18n passed: four locales, complete catalogs, live values, interpolation, diagnostics and source-copy coverage');
