'use strict';

const {t, backend: translateBackend, translatedValues} = window.StudioI18n;
window.StudioI18n.capture(document.body);
const $ = id => document.getElementById(id);
const token = location.hash.slice(1);
const storageKey = 'nuvel-obsidian-preferences-v1';
const settings = {folder: '', cookies: 'none', cookie_path: ''};
const appearance = {sidebar: 'auto', reducedMotion: false, density: 'comfortable', language: 'th', theme: 'dark', visualStyle: 'obsidian', glassOpacity: 72, fonts: window.StudioFonts.clean()};
const qualities = {video: 'best', audio: 'best', image: 'best'};
const qualityChoices = {
  video: [['best','สูงสุดที่ต้นทางมี'],['4320','8K · ไม่เกิน 4320p'],['2160','4K · ไม่เกิน 2160p'],['1440','2K · ไม่เกิน 1440p'],['1080','Full HD · ไม่เกิน 1080p'],['720','HD · ไม่เกิน 720p'],['480','ไม่เกิน 480p'],['360','ไม่เกิน 360p']],
  audio: [['best','ต้นฉบับ · สูงสุดจากต้นทาง'],['320','MP3 · 320 kbps'],['256','MP3 · 256 kbps'],['192','MP3 · 192 kbps'],['128','MP3 · 128 kbps'],['96','MP3 · 96 kbps']],
  image: [['best','ต้นฉบับ · สูงสุดจากต้นทาง'],['4096','ด้านยาวไม่เกิน 4096px'],['2560','ด้านยาวไม่เกิน 2560px'],['2048','ด้านยาวไม่เกิน 2048px'],['1920','ด้านยาวไม่เกิน 1920px'],['1280','ด้านยาวไม่เกิน 1280px'],['1024','ด้านยาวไม่เกิน 1024px'],['640','ด้านยาวไม่เกิน 640px']]
};
const modeNames = translatedValues({video: 'วิดีโอ', audio: 'เสียง', image: 'ภาพ'});
const phaseNames = translatedValues({idle: 'พร้อมใช้งาน', connecting: 'กำลังวิเคราะห์', downloading: 'กำลังดาวน์โหลด', processing: 'กำลังเตรียมไฟล์', cancelling: 'กำลังหยุด', cancelled: 'ยกเลิกแล้ว', done: 'สำเร็จ', error: 'ไม่สำเร็จ'});
const activePhases = new Set(['connecting', 'downloading', 'processing', 'cancelling']);
let currentPage = 'overview', connected = false, ready = false, busy = false, submitting = false;
let settingsDirty = false;
let knownPlatforms = [], imageEngine = {available: false, modules: []};
let sourcesExpanded = false, platformMode = '';
let snapshot = {phase: 'idle', history: []}, lastPhase = 'idle', lastRequest = null;
let toastTimer, analyzeTimer, metadataSequence = 0;
let lastLists = '', lastPlatforms = '', polling = false, connecting = false;
let previewData = null, metadataState = {kind: 'empty'}, formError = '';
let engineVersion = '', preferenceSave = Promise.resolve();
let catalogRevision = null;
let appUpdate = {phase: 'idle', current: '', packaged: false};
let fontOptionLanguage = '';
const fontLoading = new Set(), fontStatus = {}, pendingFonts = {};

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS(svg.namespaceURI, 'use');
  use.setAttribute('href', '#' + name + '-icon');
  svg.append(use);
  return svg;
}
function action(label, iconName, handler) {
  const button = node('button', 'icon-button');
  button.type = 'button'; button.title = label; button.setAttribute('aria-label', label);
  button.append(icon(iconName)); button.addEventListener('click', handler);
  return button;
}
function toast(text) {
  clearTimeout(toastTimer); $('toast').textContent = translateBackend(text); $('toast').hidden = false;
  window.StudioAppearance.enter($('toast'), 'toast');
  toastTimer = setTimeout(() => $('toast').hidden = true, 4200);
}
async function api(method, ...args) {
  if (window.pywebview?.api) return window.pywebview.api[method](...args);
  if (token && location.protocol.startsWith('http')) {
    const response = await fetch('/api/' + method, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Studio-Token': token}, body: JSON.stringify(args)});
    if (!response.ok) throw new Error(t('เชื่อมต่อกับแอปไม่สำเร็จ'));
    return response.json();
  }
  throw new Error(t('เปิดผ่าน start.bat หรือ start_macos.command เพื่อใช้งาน'));
}
function mode() { return document.querySelector('input[name="mode"]:checked').value; }
function parseURL(value) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && url.hostname ? url : null; }
  catch { return null; }
}
function platformFor(url) {
  const host = url.hostname.toLowerCase();
  return knownPlatforms.find(p => (p.domains || []).some(domain => host === domain || host.endsWith('.' + domain)));
}
function showError(text) {
  formError = text;
  $('form-error').textContent = translateBackend(text); $('form-error').hidden = !text;
  const invalidURL = !!text && !parseURL($('url').value.trim());
  $('url').setAttribute('aria-invalid', String(invalidURL));
  document.querySelector('.url-field').classList.toggle('invalid', invalidURL);
}
function showPage(page, focus = false) {
  if (!['overview', 'downloads', 'history', 'settings'].includes(page)) return;
  const changed = currentPage !== page;
  currentPage = page;
  for (const name of ['overview', 'downloads', 'history', 'settings']) $(name + '-page').hidden = name !== page;
  document.querySelectorAll('[data-page]').forEach(button => {
    const selected = button.dataset.page === page;
    button.classList.toggle('selected', selected);
    if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  $('page-name').textContent = t({overview: 'Overview', downloads: 'Downloads', history: 'History', settings: 'Settings'}[page]);
  if (page === 'settings' && !settingsDirty) fillSettings();
  if (focus) { window.scrollTo({top: 0, behavior: 'instant'}); $('main').focus({preventScroll: true}); }
  window.StudioAppearance.syncSelections();
  if (changed) window.StudioAppearance.enter($(page + '-page'));
}
document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page, true)));
document.querySelector('.brand').addEventListener('click', event => {event.preventDefault(); showPage('overview', true); $('url').focus();});
document.querySelector('.skip-link').addEventListener('click', event => {event.preventDefault(); $('main').focus();});

// Persist only ordinary UI preferences; cookies and their paths stay in memory.
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
  if (typeof saved.folder === 'string') settings.folder = saved.folder;
  if (['auto','expanded','collapsed'].includes(saved.sidebar)) appearance.sidebar = saved.sidebar;
  if (typeof saved.reducedMotion === 'boolean') appearance.reducedMotion = saved.reducedMotion;
  if (['comfortable','compact'].includes(saved.density)) appearance.density = saved.density;
  if (window.StudioI18n.languages.includes(saved.language)) appearance.language = saved.language;
  if (window.StudioTheme.modes.includes(saved.theme)) appearance.theme = saved.theme;
  if (window.StudioAppearance.styles.includes(saved.visualStyle)) appearance.visualStyle = saved.visualStyle;
  appearance.glassOpacity = window.StudioAppearance.normalizeOpacity(saved.glassOpacity);
  appearance.fonts = window.StudioFonts.clean(saved.fonts);
} catch { /* Storage may be disabled by the embedded browser. */ }
window.StudioI18n.setLanguage(appearance.language);
window.StudioI18n.translateStatic();
function persistPreferences() {
  try { localStorage.setItem(storageKey, JSON.stringify({...appearance, folder: settings.folder})); return true; }
  catch { return false; }
}
async function saveDevicePreferences() {
  persistPreferences();
  if (!connected) return {error: t('ยังไม่เชื่อมต่อกับแอป · ใช้การตั้งค่าในรอบนี้')};
  const values = {...appearance, fonts: {...appearance.fonts}, folder: settings.folder};
  // Rapid language changes must reach the device store in selection order.
  preferenceSave = preferenceSave.catch(() => {}).then(() => api('save_preferences', values));
  return preferenceSave;
}
const narrowWindow = matchMedia('(max-width: 1023px)');
function applyAppearance() {
  window.StudioAppearance.set(appearance);
  window.StudioTheme.set(appearance.theme);
  window.StudioFonts.apply(appearance.language, appearance.fonts);
  const collapsed = appearance.sidebar === 'collapsed' || (appearance.sidebar === 'auto' && narrowWindow.matches);
  document.body.classList.toggle('sidebar-collapsed', collapsed);
  document.body.classList.toggle('density-compact', appearance.density === 'compact');
  const label = collapsed ? t('ขยายเมนู') : t('ย่อเมนู');
  $('collapse-sidebar').setAttribute('aria-label', label);
  $('collapse-sidebar').setAttribute('aria-expanded', String(!collapsed));
  $('collapse-sidebar').title = label;
  $('collapse-sidebar').querySelector('span').textContent = label;
  window.StudioAppearance.syncSelections();
  renderGlassOpacity();
}
narrowWindow.addEventListener('change', applyAppearance);
$('collapse-sidebar').addEventListener('click', async () => {
  appearance.sidebar = document.body.classList.contains('sidebar-collapsed') ? 'expanded' : 'collapsed';
  applyAppearance();
  try {const result = await saveDevicePreferences(); if (result.error) toast(result.error);} catch (error) {toast(error.message);}
});
applyAppearance();

function renderQuality() {
  const current = mode(), value = qualities[current];
  $('quality-label').textContent = {video:t('ความละเอียด'), audio:t('คุณภาพเสียง'), image:t('ขนาดภาพ')}[current];
  $('quality').replaceChildren();
  for (const [key, label] of qualityChoices[current]) {
    const option = node('option', '', t(label)); option.value = key; $('quality').append(option);
  }
  $('quality').value = value;
  $('output-format').textContent = current === 'video' ? 'MP4' : current === 'audio' ? (value === 'best' ? t('ต้นฉบับ') : 'MP3') : t('ต้นฉบับ');
  $('quality-hint').textContent = current === 'video' ? t('Source resolution is never upscaled.') :
    current === 'audio' ? (value === 'best' ? t('Keeps the best original audio format.') : t('Converts to MP3; source quality still applies.')) :
    value === 'best' ? t('Keeps the original image file.') : t('Resizes without enlarging smaller images.');
  $('image-hint').hidden = current !== 'image';
  renderPlatforms(knownPlatforms); updateButtons();
}
$('quality').addEventListener('change', () => {qualities[mode()] = $('quality').value; renderQuality();});
document.querySelectorAll('input[name="mode"]').forEach(input => input.addEventListener('change', () => {
  renderQuality(); resetMetadata(); if (parseURL($('url').value.trim())) scheduleAnalysis();
  window.StudioAppearance.syncSelections();
}));
function updateButtons() {
  const valid = !!parseURL($('url').value.trim());
  $('download').disabled = !connected || busy || submitting || !valid;
  $('download').querySelector('span').textContent = submitting ? t('กำลังเริ่ม…') : busy ? t('กำลังดาวน์โหลด…') : t('ดาวน์โหลด') + modeNames[mode()];
  $('analyze').disabled = !connected || !valid || $('analyze').dataset.loading === 'true';
  $('analyze').title = !valid ? t('Paste a valid link to analyze it.') : !connected ? t('ยังไม่เชื่อมต่อ') : '';
  $('download').title = !valid ? t('Paste a valid link to download.') : !connected ? t('ยังไม่เชื่อมต่อ') : '';
}
function updateSource() {
  const value = $('url').value.trim(), parsed = parseURL(value);
  $('clear-url').hidden = !value;
  if (parsed) { const platform = platformFor(parsed); $('url-hint').textContent = platform ? platform.name + ' · ' + parsed.hostname : parsed.hostname; }
  else $('url-hint').textContent = value ? t('ใช้ลิงก์แบบเต็ม เช่น https://…') : t('Paste a media link to get started.');
  updateButtons();
}
function resetMetadata() {
  clearTimeout(analyzeTimer); metadataSequence++;
  previewData = null; metadataState = {kind: 'empty'};
  $('media-preview').hidden = true; $('metadata-message').hidden = true;
  $('preview-thumbnail').hidden = true; $('preview-thumbnail').removeAttribute('src');
  $('analyze').dataset.loading = 'false'; $('analyze').textContent = t('ตรวจสอบลิงก์'); updateButtons();
}
function scheduleAnalysis() {
  clearTimeout(analyzeTimer);
  if (connected && parseURL($('url').value.trim())) analyzeTimer = setTimeout(analyzeURL, 900);
}
$('url').addEventListener('input', () => {showError(''); resetMetadata(); updateSource(); scheduleAnalysis();});
$('url').addEventListener('blur', () => {if ($('url').value.trim() && !parseURL($('url').value.trim())) showError(t('ใช้ลิงก์แบบเต็มที่ขึ้นต้นด้วย https://'));});
$('clear-url').addEventListener('click', () => {$('url').value = ''; showError(''); resetMetadata(); updateSource(); $('url').focus();});
$('paste').addEventListener('click', async () => {
  try { $('url').value = (await navigator.clipboard.readText()).trim(); $('url').dispatchEvent(new Event('input')); $('url').focus(); }
  catch { $('url').focus(); toast(t('กด Ctrl+V หรือ ⌘V เพื่อวางลิงก์จากคลิปบอร์ด')); }
});
function durationLabel(seconds) {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return '';
  const whole = Math.floor(seconds), minutes = Math.floor(whole / 60), remainder = String(whole % 60).padStart(2, '0');
  return minutes >= 60 ? Math.floor(minutes / 60) + ':' + String(minutes % 60).padStart(2, '0') + ':' + remainder : minutes + ':' + remainder;
}
async function analyzeURL() {
  clearTimeout(analyzeTimer);
  const url = $('url').value.trim();
  if (!parseURL(url) || !connected) return;
  const sequence = ++metadataSequence;
  $('analyze').dataset.loading = 'true'; $('analyze').textContent = t('กำลังอ่านข้อมูล…'); updateButtons();
  $('media-preview').hidden = true;
  metadataState = {kind: 'loading'}; renderMetadataStatus();
  try {
    const result = await api('analyze_url', {url, mode: mode(), cookies: settings.cookies, cookie_path: settings.cookie_path});
    if (sequence !== metadataSequence) return;
    if (result.error || result.unavailable) {
      metadataState = result.unavailable ? {kind: 'unavailable', detail: result.detail} : {kind: 'error', error: result.error};
      renderMetadataStatus();
      return;
    }
    previewData = {result, url}; metadataState = {kind: 'empty'};
    renderMetadataStatus(); renderPreview();
  } catch (error) {
    if (sequence === metadataSequence) {metadataState = {kind: 'error', error: error.message}; renderMetadataStatus();}
  } finally {
    if (sequence === metadataSequence) { $('analyze').dataset.loading = 'false'; $('analyze').textContent = t('ตรวจสอบอีกครั้ง'); updateButtons(); }
  }
}
function renderMetadataStatus() {
  $('metadata-message').hidden = metadataState.kind === 'empty';
  $('metadata-message').className = 'metadata-message' + (metadataState.kind === 'loading' ? ' loading' : '');
  $('metadata-message').textContent = metadataState.kind === 'loading' ? t('กำลังอ่านข้อมูลจากต้นทาง… คุณยังเลือกคุณภาพหรือเริ่มดาวน์โหลดได้') :
    metadataState.kind === 'error' ? t('อ่านตัวอย่างไม่สำเร็จ · คุณยังลองดาวน์โหลดได้\n') + translateBackend(metadataState.error) : translateBackend(metadataState.detail || '');
}
function renderPreview() {
  if (!previewData) return;
  const {result, url} = previewData;
  const newlyVisible = $('media-preview').hidden;
  $('media-preview').hidden = false;
  $('preview-title').textContent = result.title || t('ต้นทางไม่ได้ระบุชื่อสื่อ');
  $('preview-source').textContent = platformFor(parseURL(url))?.name || (result.source === 'Generic' ? parseURL(url).hostname : result.source);
  $('preview-detail').textContent = [durationLabel(result.duration), (result.resolutions || []).length ? t('สูงสุด ') + Math.max(...result.resolutions) + 'p' : ''].filter(Boolean).join(' · ');
  $('preview-formats').textContent = result.formats?.length ? t('รูปแบบจากต้นทาง: ') + result.formats.join(' / ').toUpperCase() : t('ต้นทางไม่ได้ระบุรายการรูปแบบ');
  const thumb = parseURL(result.thumbnail || '');
  if (thumb) {if ($('preview-thumbnail').src !== thumb.href) $('preview-thumbnail').src = thumb.href; $('preview-thumbnail').hidden = false;}
  else $('preview-thumbnail').hidden = true;
  if (newlyVisible) window.StudioAppearance.enter($('media-preview'));
}
$('analyze').addEventListener('click', analyzeURL);
$('preview-thumbnail').addEventListener('error', () => $('preview-thumbnail').hidden = true);

async function startDownload(request) {
  if (busy || submitting || !connected) return;
  showError(''); submitting = true; updateButtons();
  try {
    const result = await api('start_download', request);
    if (result.error) { showError(result.error); toast(result.error); }
    else { lastRequest = {...request}; await poll(); }
  } catch (error) { showError(error.message); toast(error.message); }
  finally { submitting = false; updateButtons(); }
}
$('download-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!parseURL($('url').value.trim())) {showError(t('วางลิงก์แบบเต็มที่ขึ้นต้นด้วย https://')); $('url').focus(); return;}
  startDownload({url: $('url').value.trim(), mode: mode(), quality: qualities[mode()], ...settings});
});
document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && currentPage === 'overview' && !document.querySelector('dialog[open]')) {
    event.preventDefault(); if (!$('download').disabled) $('download-form').requestSubmit();
  }
});
if (/Mac|iPhone|iPad/.test(navigator.platform)) $('submit-modifier').textContent = '⌘';
function updateFolder() {
  const path = settings.folder.replace(/[\\/]+$/, '');
  $('folder-label').textContent = path.split(/[\\/]/).pop() || path || t('เลือกโฟลเดอร์');
  $('folder-label').title = settings.folder;
}
async function openFolder(path) {
  try { const result = await api('open_folder', path); if (result.error) toast(result.error); }
  catch (error) { toast(error.message); }
}
async function cancelDownload() {
  try { const result = await api('cancel_download'); if (result.error) toast(result.error); await poll(); }
  catch (error) { toast(error.message); }
}
$('change-folder').addEventListener('click', async () => {
  try {
    const result = await api('choose_folder');
    if (result.path) { settings.folder = result.path; updateFolder(); const saved = await saveDevicePreferences(); if (saved.error) toast(saved.error); }
    else if (result.error) {showPage('settings', true); $('folder-path').focus(); toast(result.error);}
  } catch (error) { showPage('settings', true); $('folder-path').focus(); toast(error.message); }
});
$('advanced').addEventListener('click', () => {showPage('settings', true); $('cookies').focus();});
$('dock-open').addEventListener('click', () => showPage('downloads', true));
$('dock-cancel').addEventListener('click', cancelDownload);
$('help').addEventListener('click', () => { $('help-dialog').showModal(); window.StudioAppearance.enter($('help-dialog'), 'dialog'); });

function fillSettings() {
  $('folder-path').value = settings.folder; $('cookies').value = settings.cookies; $('cookie-path').value = settings.cookie_path;
  $('cookie-file-row').hidden = settings.cookies !== 'file';
  $('sidebar-preference').value = appearance.sidebar; $('animations').checked = !appearance.reducedMotion; $('density').value = appearance.density;
  $('language').value = appearance.language;
  $('theme').value = appearance.theme;
  $('visual-style').value = appearance.visualStyle;
  renderMotionStatus();
  renderFontSettings();
}
function renderMotionStatus() {
  const message = appearance.reducedMotion ? 'Animations are off.' :
    window.StudioAppearance.motionEnabled ? 'Animations are on.' : 'System Reduce Motion is active; animations are off.';
  $('motion-feedback').textContent = t(message);
}
function renderGlassOpacity() {
  const {glassSupported, transparencyReduced} = window.StudioAppearance;
  $('glass-opacity-row').hidden = appearance.visualStyle !== 'glass';
  const slider = $('glass-opacity');
  if (slider.value !== String(appearance.glassOpacity)) slider.value = String(appearance.glassOpacity);
  slider.disabled = !glassSupported || transparencyReduced;
  slider.style.setProperty('--glass-position', appearance.glassOpacity + '%');
  slider.setAttribute('aria-valuetext', t('{value}% opacity', {value: appearance.glassOpacity}));
  $('glass-opacity-value').textContent = appearance.glassOpacity + '%';
  $('reset-glass-opacity').disabled = slider.disabled || appearance.glassOpacity === 72;
  $('glass-opacity-feedback').textContent = transparencyReduced ? t('System Reduce Transparency is active; glass is opaque.') :
    !glassSupported ? t('Glass transparency is unavailable in this renderer.') : '';
}
window.matchMedia('(prefers-reduced-transparency: reduce)').addEventListener('change', renderGlassOpacity);
window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', renderMotionStatus);
function renderFontSettings() {
  const language = appearance.language, group = window.StudioFonts.catalog[language];
  const select = $('font-family');
  if (fontOptionLanguage !== language) {
    select.replaceChildren();
    for (const font of group.fonts) {
      const option = node('option', '', font.name); option.value = font.id; select.append(option);
    }
    fontOptionLanguage = language;
  }
  select.value = pendingFonts[language] || appearance.fonts[language];
  select.disabled = !ready || !connected || fontLoading.has(language);
  $('font-preview').textContent = group.sample;
  const messages = {idle:'Bundled fonts work offline.', loading:'Loading font…', saved:'Font saved.',
    error:'Could not load this font. Your previous font was kept.',
    unavailable:'Could not load the selected font. Restart the app and try again.',
    save_error:'Font changed, but could not save it on this device.'};
  const state = fontStatus[language] || 'idle';
  $('font-feedback').textContent = t(messages[state]);
  $('font-feedback').dataset.error = String(['error','unavailable','save_error'].includes(state));
}
async function checkActiveFont() {
  const language = appearance.language, id = appearance.fonts[language];
  if (fontLoading.has(language)) return;
  fontLoading.add(language); fontStatus[language] = 'loading'; renderFontSettings();
  try { await window.StudioFonts.load(language, id); fontStatus[language] = 'idle'; }
  catch { fontStatus[language] = 'unavailable'; }
  finally {fontLoading.delete(language); renderFontSettings();}
}
function applyLanguage() {
  window.StudioI18n.setLanguage(appearance.language);
  window.StudioI18n.translateStatic();
  lastLists = ''; lastPlatforms = '';
  renderQuality(); renderLists(true); renderDock(); applyAppearance(); updateFolder();
  showError(formError); renderMetadataStatus(); renderPreview();
  renderEngineVersion(); renderAppUpdate();
  $('page-name').textContent = t({overview:'Overview', downloads:'Downloads', history:'History', settings:'Settings'}[currentPage]);
  $('analyze').textContent = $('analyze').dataset.loading === 'true' ? t('กำลังอ่านข้อมูล…') : t('ตรวจสอบลิงก์');
  $('connection-label').textContent = connected ? t('Local workspace') : t('ยังไม่เชื่อมต่อ');
  $('language').value = appearance.language;
  renderMotionStatus();
  renderFontSettings(); checkActiveFont();
}
$('font-family').addEventListener('change', async () => {
  const language = appearance.language, id = $('font-family').value;
  if (fontLoading.has(language)) return;
  pendingFonts[language] = id; fontLoading.add(language); fontStatus[language] = 'loading'; renderFontSettings();
  let applied = false;
  try {
    await window.StudioFonts.load(language, id);
    appearance.fonts[language] = id;
    window.StudioFonts.apply(appearance.language, appearance.fonts);
    applied = true;
    const saved = await saveDevicePreferences();
    fontStatus[language] = saved.error ? 'save_error' : 'saved';
  } catch {fontStatus[language] = applied ? 'save_error' : 'error';}
  finally {delete pendingFonts[language]; fontLoading.delete(language); renderFontSettings();}
});
$('language').addEventListener('change', async () => {
  appearance.language = $('language').value; applyLanguage();
  try {
    const result = await saveDevicePreferences();
    $('settings-feedback').textContent = result.error ? translateBackend(result.error) : t('เปลี่ยนภาษาแล้ว');
    toast($('settings-feedback').textContent);
  } catch (error) {toast(error.message);}
});
$('theme').addEventListener('change', async () => {
  appearance.theme = $('theme').value;
  applyAppearance();
  try {
    const result = await saveDevicePreferences();
    $('settings-feedback').textContent = result.error ? translateBackend(result.error) : t('Theme saved.');
    toast($('settings-feedback').textContent);
  } catch (error) {toast(error.message);}
});
for (const id of ['visual-style', 'animations']) $(id).addEventListener('change', async () => {
  if (id === 'visual-style') appearance.visualStyle = $(id).value;
  else appearance.reducedMotion = !$(id).checked;
  applyAppearance(); renderMotionStatus();
  try {
    const result = await saveDevicePreferences();
    $('settings-feedback').textContent = result.error ? translateBackend(result.error) : t('Appearance saved.');
    if (result.error) toast(result.error);
  } catch (error) {toast(error.message);}
});
async function saveGlassOpacity() {
  try {
    const result = await saveDevicePreferences();
    $('settings-feedback').textContent = result.error ? translateBackend(result.error) : t('Appearance saved.');
    if (result.error) toast(result.error);
  } catch (error) {toast(error.message);}
}
$('glass-opacity').addEventListener('input', () => {
  appearance.glassOpacity = window.StudioAppearance.normalizeOpacity($('glass-opacity').valueAsNumber);
  window.StudioAppearance.set(appearance); renderGlassOpacity();
  persistPreferences();
});
$('glass-opacity').addEventListener('change', saveGlassOpacity);
$('reset-glass-opacity').addEventListener('click', () => {
  appearance.glassOpacity = 72;
  window.StudioAppearance.set(appearance); renderGlassOpacity();
  saveGlassOpacity();
});
$('cookies').addEventListener('change', () => $('cookie-file-row').hidden = $('cookies').value !== 'file');
$('settings-form').addEventListener('input', () => settingsDirty = true);
$('settings-form').addEventListener('change', () => settingsDirty = true);
$('browse-folder').addEventListener('click', async () => {
  try {const result = await api('choose_folder'); if (result.path) {$('folder-path').value = result.path; settingsDirty = true;} else if (result.error) toast(result.error);}
  catch (error) {toast(error.message);}
});
$('browse-cookie').addEventListener('click', async () => {
  try {const result = await api('choose_cookies'); if (result.path) {$('cookie-path').value = result.path; settingsDirty = true;} else if (result.error) toast(result.error);}
  catch (error) {toast(error.message);}
});
$('settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  const folder = $('folder-path').value.trim();
  if (!folder) {toast(t('ใส่โฟลเดอร์ปลายทางก่อน')); $('folder-path').focus(); return;}
  settings.folder = folder; settings.cookies = $('cookies').value; settings.cookie_path = $('cookie-path').value.trim();
  appearance.sidebar = $('sidebar-preference').value; appearance.reducedMotion = !$('animations').checked; appearance.density = $('density').value;
  applyAppearance(); updateFolder();
  $('save-settings').disabled = true;
  try {
    const saved = await saveDevicePreferences();
    if (!saved.error) settingsDirty = false;
    $('settings-feedback').textContent = saved.error ? t('บันทึกถาวรไม่สำเร็จ: ') + saved.error : t('บันทึกแล้ว · มีผลกับการดาวน์โหลดครั้งถัดไป');
    toast($('settings-feedback').textContent);
  } catch (error) {toast(error.message);}
  finally {$('save-settings').disabled = false;}
});

function renderPlatforms(platforms) {
  if (!platforms.length) return;
  knownPlatforms = platforms;
  const current = mode();
  const displayed = platforms.map(p => ({...p, status: p[current + '_status'] || p.status}));
  displayed.sort((a,b) => (a.status === 'supported' ? 0 : 1) - (b.status === 'supported' ? 0 : 1));
  const key = current + displayed.map(p => p.slug + p.status).join();
  if (key === lastPlatforms) return;
  lastPlatforms = key;
  if (platformMode !== current) $('platforms').scrollTop = 0;
  platformMode = current;
  $('support-mode-label').textContent = t('Supported in {mode} mode', {mode: modeNames[current]});
  const supported = displayed.filter(p => p.status === 'supported').length;
  $('support-number').textContent = t('{supported} of {total}', {supported, total: platforms.length});
  const supportDescription = t('{supported} of {total} sources support {mode}.', {supported, total: platforms.length, mode: modeNames[current]});
  $('support-number').setAttribute('aria-label', supportDescription);
  $('support-number').title = supportDescription;
  $('support-summary').textContent = t('สถานะจากตัวรองรับที่ติดตั้ง ไม่ใช่ผลทดสอบทุกลิงก์');
  $('platform-detail').textContent = t('เลือกแหล่งเพื่อดูรายละเอียด');
  $('platform-detail').hidden = true;
  $('image-support-note').hidden = current !== 'image';
  $('image-support-note').textContent = imageEngine.available ? t('ภาพจากโพสต์ใช้ gallery-dl · บางแหล่งต้องใช้บัญชี') : t('ภาพจากโพสต์ต้องติดตั้ง gallery-dl เพิ่ม · ลิงก์ไฟล์ภาพโดยตรงใช้ได้');
  const labels = {supported: t('มีตัวรองรับ'), unsupported: t('ไม่รองรับในโหมดนี้'), missing: current === 'image' ? t('ต้องติดตั้ง gallery-dl') : t('ยังไม่พบตัวรองรับ'), broken: t('ตัวรองรับมีปัญหา'), unknown: t('กำลังตรวจสอบ')};
  $('platforms').replaceChildren();
  for (const platform of displayed) {
    const button = node('button', 'platform ' + platform.status); button.type = 'button';
    button.dataset.platform = platform.slug;
    button.dataset.search = platform.name.toLowerCase() + ' ' + (platform.domains || []).join(' ');
    button.title = platform.name + ' · ' + labels[platform.status]; button.setAttribute('aria-label', button.title); button.setAttribute('aria-pressed', 'false');
    const img = node('img'); img.src = platform.icon; img.alt = ''; img.draggable = false;
    const name = node('span', 'platform-name', platform.name);
    const state = node('span', 'status-dot');
    if (platform.status === 'supported') state.append(icon('check'));
    button.append(img, name, state);
    button.addEventListener('click', () => {
      $('platforms').querySelectorAll('button').forEach(el => {el.classList.remove('chosen'); el.setAttribute('aria-pressed', 'false');});
      button.classList.add('chosen'); button.setAttribute('aria-pressed', 'true');
      $('platform-detail').textContent = button.title + (platform.status === 'supported' ? t(' · บางโพสต์อาจต้องใช้ cookies หรือบัญชี') : '');
      $('platform-detail').hidden = false;
    });
    $('platforms').append(button);
  }
  filterPlatforms(); updateSource();
}
function filterPlatforms() {
  const query = $('platform-search').value.trim().toLowerCase(); let visible = 0;
  const compact = !sourcesExpanded && !query;
  for (const button of $('platforms').children) {
    const matches = button.dataset.search.includes(query);
    button.hidden = !matches || (compact && visible >= 8);
    if (!button.hidden) visible++;
  }
  $('platforms').classList.toggle('expanded', sourcesExpanded || !!query);
  $('expand-platforms').textContent = sourcesExpanded ? t('Show fewer') : t('View all {count} sources', {count: knownPlatforms.length});
  $('expand-platforms').setAttribute('aria-expanded', String(sourcesExpanded));
  $('expand-platforms').hidden = !!query || knownPlatforms.length <= 8;
  $('support-summary').hidden = compact;
  $('platform-empty').hidden = visible > 0;
}
$('platform-search').addEventListener('input', () => {$('platforms').scrollTop = 0; filterPlatforms();});
$('expand-platforms').addEventListener('click', () => {sourcesExpanded = !sourcesExpanded; $('platforms').scrollTop = 0; filterPlatforms();});

function bytesLabel(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  const units = ['B','KB','MB','GB']; let index = 0;
  while (bytes >= 1024 && index < units.length - 1) {bytes /= 1024; index++;}
  return (index ? bytes.toFixed(1) : Math.round(bytes)) + ' ' + units[index];
}
function emptyState(title, detail, iconName, link = false) {
  const empty = node('div', 'empty-state'), body = node('div');
  empty.append(icon(iconName)); body.append(node('h3', '', title), node('p', '', detail));
  if (link) {const button = node('button', 'text-button', t('เริ่มจากลิงก์แรก')); button.addEventListener('click', () => {showPage('overview', true); $('url').focus();}); body.append(button);}
  empty.append(body); return empty;
}
function displayTitle(item) {
  // Only gallery-generated summaries are localized; real titles and filenames stay verbatim.
  return item.mode === 'image' && /^ภาพจาก \S+(?: \(\d+ ภาพ\))?$/.test(item.title || '') ? translateBackend(item.title) : item.title;
}
function transferRow(item, isCurrent = false, compact = false) {
  const phase = isCurrent ? item.phase : 'done';
  const row = node('article', 'transfer-row ' + phase), mark = node('div', 'transfer-icon');
  row.dataset.key = isCurrent ? 'current' : item.id || item.title;
  mark.append(icon(item.mode || 'video'));
  const body = node('div', 'transfer-body');
  const title = node('h3', 'transfer-title', displayTitle(item) || t('กำลังอ่านชื่อสื่อ…')); title.title = item.title || '';
  const details = [modeNames[item.mode], item.source, translateBackend(item.quality_label), item.time].filter(Boolean);
  body.append(title, node('p', 'transfer-detail', details.join(' · ')));
  if (isCurrent && activePhases.has(phase)) {
    const determinate = phase === 'downloading' && item.progress_known !== false;
    const progress = node('div', 'transfer-progress' + (determinate ? '' : ' indeterminate'));
    progress.setAttribute('role', 'progressbar'); progress.setAttribute('aria-label', t('ความคืบหน้าดาวน์โหลด'));
    progress.setAttribute('aria-valuemin', '0'); progress.setAttribute('aria-valuemax', '100');
    if (determinate) progress.setAttribute('aria-valuenow', String(Math.round(item.percent || 0)));
    const fill = node('div'); fill.style.width = Math.min(100, Math.max(0, item.percent || 0)) + '%'; progress.append(fill); body.append(progress);
    body.append(node('p', 'transfer-meta', [item.speed, item.eta ? t('เหลือ ') + item.eta : '', bytesLabel(item.total_bytes), item.image_count ? item.image_count + t(' ภาพ') : ''].filter(Boolean).join(' · ')));
  }
  if (isCurrent && phase === 'error' && !compact) body.append(node('p', 'transfer-error', translateBackend(item.error || item.detail)));
  if (isCurrent && ['processing','cancelled','cancelling'].includes(phase)) body.append(node('p', 'transfer-meta', translateBackend(item.detail || '')));
  const right = node('div', 'transfer-right');
  const status = node('span', 'transfer-status', phase === 'downloading' && item.progress_known !== false ? Math.round(item.percent || 0) + '%' : phaseNames[phase]);
  right.append(status);
  const actions = node('div', 'transfer-actions');
  if (isCurrent && activePhases.has(phase)) {
    const cancel = action(t('หยุดดาวน์โหลด'), 'close', cancelDownload); cancel.disabled = phase === 'cancelling'; actions.append(cancel);
  } else {
    if (isCurrent && ['error','cancelled'].includes(phase) && lastRequest) actions.append(action(t('ลองใหม่'), 'retry', () => startDownload({...lastRequest})));
    if (item.folder) actions.append(action(t('เปิดโฟลเดอร์'), 'folder', () => openFolder(item.folder)));
  }
  if (!isCurrent && !compact && item.id) actions.append(action(t('ลบเฉพาะประวัติ · ไม่ลบไฟล์'), 'trash', async () => {
    try {const result = await api('remove_history', item.id); if (result.error) toast(result.error); else {await poll(); toast(t('ลบประวัติแล้ว · ไฟล์จริงยังอยู่'));}}
    catch (error) {toast(error.message);}
  }));
  right.append(actions); row.append(mark, body, right); return row;
}
function renderLists(force = false) {
  const key = JSON.stringify([snapshot, $('history-search').value, $('history-filter').value, !!lastRequest]);
  if (!force && key === lastLists) return;
  lastLists = key;
  // Polling updates must not steal focus from cancel/retry/folder controls.
  const focused = document.activeElement;
  const focusList = focused?.closest('.transfer-list')?.id;
  const focusRow = focused?.closest('.transfer-row')?.dataset.key;
  const focusLabel = focused?.getAttribute('aria-label');
  const history = snapshot.history || [], hasCurrent = snapshot.phase !== 'idle';
  const hasActivity = hasCurrent || history.length > 0;
  document.querySelector('.workspace').classList.toggle('has-activity', hasActivity);
  $('recent-section').classList.toggle('is-empty', !hasActivity);
  const downloads = $('downloads-list'), recent = $('recent-list'); downloads.replaceChildren(); recent.replaceChildren();
  if (hasCurrent) {downloads.append(transferRow(snapshot, true)); recent.append(transferRow(snapshot, true, true));}
  // A successful current transfer is already represented by the first history entry.
  const older = hasCurrent && snapshot.phase === 'done' ? history.filter(item => item.id !== snapshot.history_id) : history;
  for (const item of older) downloads.append(transferRow(item, false, true));
  for (const item of (hasCurrent ? older.slice(0, 2) : history.slice(0, 3))) recent.append(transferRow(item, false, true));
  if (!downloads.children.length) downloads.append(emptyState(t('ยังไม่มีรายการดาวน์โหลด'), t('วางลิงก์ใน Overview เพื่อเริ่ม งานที่กำลังทำจะแสดงที่นี่'), 'download', true));
  if (!recent.children.length) recent.append(node('p', 'recent-empty', t('Your recent downloads will appear here.')));
  renderHistory();
  if (focusList && focusRow && focusLabel) {
    const row = [...$(focusList).children].find(element => element.dataset.key === focusRow);
    const button = row && [...row.querySelectorAll('button')].find(element => element.getAttribute('aria-label') === focusLabel);
    if (button && !button.disabled) button.focus({preventScroll: true});
  }
}
function renderHistory() {
  const query = $('history-search').value.trim().toLowerCase(), filter = $('history-filter').value;
  const history = snapshot.history || [];
  const items = history.filter(item => (filter === 'all' || item.mode === filter) && [item.title, displayTitle(item), item.source].join(' ').toLowerCase().includes(query));
  $('history-list').replaceChildren();
  for (const item of items) $('history-list').append(transferRow(item));
  if (!items.length) $('history-list').append(emptyState(history.length ? t('ไม่พบรายการที่ค้นหา') : t('ยังไม่มีประวัติ'), history.length ? t('ลองเปลี่ยนคำค้นหาหรือประเภทสื่อ') : t('ดาวน์โหลดสำเร็จแล้วจะปรากฏที่นี่ ประวัตินี้เก็บเฉพาะรอบการเปิดแอป'), 'history', !history.length));
}
$('history-search').addEventListener('input', renderHistory);
$('history-filter').addEventListener('change', renderHistory);
function renderDock() {
  $('transfer-dock').hidden = !busy;
  $('nav-active').hidden = !busy;
  $('dock-title').textContent = displayTitle(snapshot) || t('กำลังอ่านข้อมูล…');
  $('dock-status').textContent = [phaseNames[snapshot.phase], snapshot.speed, snapshot.eta ? t('เหลือ ') + snapshot.eta : ''].filter(Boolean).join(' · ');
  const known = snapshot.phase === 'downloading' && snapshot.progress_known !== false;
  $('dock-percent').textContent = known ? Math.round(snapshot.percent || 0) + '%' : '';
  $('dock-fill').style.width = known ? Math.min(100, snapshot.percent || 0) + '%' : '0%';
  $('dock-cancel').disabled = snapshot.phase === 'cancelling';
}
function render(state) {
  const notify = ready;
  const {platforms, image_engine, version, preferences, app_update, catalog_revision, ...job} = state;
  snapshot = job;
  if (!ready) {
    if (preferences && Object.keys(preferences).length) {
      Object.assign(appearance, {sidebar: preferences.sidebar, density: preferences.density, reducedMotion: preferences.reducedMotion, language: preferences.language || 'th', theme: preferences.theme || 'dark'});
      appearance.visualStyle = preferences.visualStyle || 'obsidian';
      appearance.glassOpacity = window.StudioAppearance.normalizeOpacity(preferences.glassOpacity);
      appearance.fonts = window.StudioFonts.clean(preferences.fonts);
      settings.folder = preferences.folder; applyAppearance();
    } else if (!settings.folder) settings.folder = state.folder;
    applyLanguage(); updateFolder(); ready = true;
    if (currentPage === 'settings' && !settingsDirty) fillSettings();
  }
  if (image_engine) imageEngine = image_engine;
  if (platforms) renderPlatforms(platforms);
  if (version !== undefined) engineVersion = version;
  renderEngineVersion();
  busy = activePhases.has(state.phase);
  if (app_update) appUpdate = app_update;
  renderAppUpdate();
  renderFontSettings();
  updateButtons(); renderLists(); renderDock();
  if (notify && state.phase === 'done' && lastPhase !== 'done') toast(t('ดาวน์โหลดสำเร็จ · บันทึกไฟล์แล้ว'));
  if (notify && state.phase === 'error' && lastPhase !== 'error') toast(t('ดาวน์โหลดไม่สำเร็จ · ดูรายละเอียดที่ Downloads'));
  lastPhase = state.phase;
  catalogRevision = typeof catalog_revision === 'string' ? catalog_revision : null;
}
function renderEngineVersion() {
  $('engine-version').textContent = engineVersion ? 'yt-dlp ' + engineVersion + ' · gallery-dl ' + (imageEngine.available ? t('พร้อมใช้งาน') : t('ยังไม่ติดตั้ง')) : t('กำลังตรวจสอบ…');
}
const updateMessages = {
  access_required: 'GitHub access is required. Add a token with read access to this private repository, or replace an expired token.',
  credential_error: 'Could not access the secure credential store. Unlock your Keychain or Windows account and try again.',
  no_release: 'No ready-to-use release has been published yet.',
  network_error: 'Could not reach GitHub. Check your connection and try again. Your app still works offline.',
  invalid_release: 'This release is incomplete or has an invalid update manifest. Your current app was kept.',
  invalid_package: 'The update did not pass verification. Your current app was kept. Check for updates and try again.',
  update_failed: 'The update could not be prepared. Check free disk space and your connection, then try again.',
  install_readonly: 'This app is in a read-only location. Move the full app to a folder you can write to and try again.',
  install_locked: 'Close other copies of NÜVEL Studio before installing the update.',
  source_build: 'This is a source launch. Build this version once to enable in-app installation. The existing folder updater still works.',
  unsupported_system: 'Ready-to-use updates support Windows x64 and macOS Apple Silicon.',
  update_busy: 'An app update is already in progress.',
  download_active: 'Wait for the active media download to finish before restarting to update.',
  native_required: 'Open the desktop app to install updates.',
  check_first: 'Check for updates first.',
  cancelled: 'Update download cancelled. Your current app was kept.'
};
function renderAppUpdate() {
  const phase = appUpdate.phase;
  const working = ['checking','downloading','verifying','installing'].includes(phase);
  $('app-version').textContent = 'NÜVEL Studio ' + (appUpdate.current || '—');
  const messages = {
    idle: 'Download verified releases without rebuilding.', checking: 'Checking GitHub releases…',
    up_to_date: 'You are using the latest version.', available: 'A new version is available.',
    downloading: 'Downloading update…', verifying: 'Verifying the package and testing the new app…',
    ready: 'Update ready. Your app will restart; downloaded media and preferences are preserved.',
    installing: 'Closing the app to install the update…', error: 'Update not completed.'
  };
  $('update-status').textContent = t(messages[phase] || messages.idle) +
    (appUpdate.latest && ['available','downloading','verifying','ready'].includes(phase) ? ' · v' + appUpdate.latest : '');
  $('update-error').textContent = appUpdate.error ? t(updateMessages[appUpdate.error] || updateMessages.update_failed) : '';
  $('update-error').hidden = !appUpdate.error;
  $('update-source-note').hidden = appUpdate.packaged || !appUpdate.current;
  $('update-session-note').hidden = !appUpdate.session_only;
  $('check-update').disabled = working || phase === 'ready' || !connected;
  $('download-update').hidden = phase !== 'available';
  $('download-update').disabled = !appUpdate.packaged;
  $('download-update').title = appUpdate.packaged ? '' : t(updateMessages.source_build);
  $('install-update').hidden = phase !== 'ready'; $('install-update').disabled = busy;
  $('install-update').title = busy ? t(updateMessages.download_active) : '';
  $('cancel-update').hidden = phase !== 'downloading';
  $('update-progress').hidden = !['downloading','verifying'].includes(phase);
  if (phase === 'verifying') $('update-progress').removeAttribute('value');
  else $('update-progress').value = appUpdate.percent || 0;
  for (const id of ['connect-updates','forget-update-token']) $(id).disabled = working || phase === 'ready';
  $('update-release').hidden = !appUpdate.notes;
  $('update-release-notes').textContent = appUpdate.notes || '';
  if (appUpdate.error === 'access_required') $('update-access').open = true;
}
async function updateAction(method, ...args) {
  try {
    const result = await api(method, ...args);
    if (result.error) toast(t(updateMessages[result.error] || updateMessages.update_failed));
    else await poll();
    return result;
  } catch { toast(t(updateMessages.network_error)); return {error: 'connection'}; }
}
$('check-update').addEventListener('click', () => updateAction('check_app_update'));
$('download-update').addEventListener('click', () => updateAction('download_app_update'));
$('cancel-update').addEventListener('click', () => updateAction('cancel_app_update'));
$('install-update').addEventListener('click', async () => {
  $('install-update').disabled = true;
  try {
    const result = await api('install_app_update');
    if (result.error) toast(t(updateMessages[result.error] || updateMessages.update_failed));
  } catch { /* The native bridge closes with the app during installation. */ }
});
$('connect-updates').addEventListener('click', async () => {
  const secret = $('update-token').value; $('update-token').value = '';
  if (!secret.trim()) { $('update-token').focus(); return; }
  const result = await updateAction('connect_updates', secret);
  if (!result.error) { $('update-access').open = false; await updateAction('check_app_update'); }
});
$('update-token').addEventListener('keydown', event => {
  if (event.key === 'Enter') {event.preventDefault(); $('connect-updates').click();}
});
$('forget-update-token').addEventListener('click', () => updateAction('connect_updates', '', true));
$('create-update-token').addEventListener('click', () => updateAction('open_update_access'));
async function poll() {
  if (polling) return;
  polling = true;
  try { const state = await api('snapshot', catalogRevision); connected = true; $('connection-label').textContent = t('Local workspace'); render(state); }
  catch {
    catalogRevision = null;
    connected = false; updateButtons(); $('connection-label').textContent = t('ขาดการเชื่อมต่อ');
    if (ready) $('dock-status').textContent = t('การเชื่อมต่อหยุดลง · เปิดแอปใหม่เพื่อตรวจสอบ');
  } finally {polling = false;}
}
function connect() {if (connecting) return; connecting = true; poll(); setInterval(poll, 700);}
window.addEventListener('pywebviewready', connect, {once: true});
if (token || window.pywebview?.api) connect();
renderQuality(); updateFolder(); renderLists(true);
const seed = $('platform-seed');
if (seed) {renderPlatforms(JSON.parse(seed.textContent)); $('support-number').textContent = '—'; $('support-summary').textContent = t('กำลังตรวจสอบตัวรองรับ…');}
showPage('overview');
window.StudioAppearance.mount();
window.studioReady = true;
if (!token) setTimeout(() => {
  if (!window.pywebview?.api && !ready) { $('connection-label').textContent = t('ยังไม่เชื่อมต่อ'); $('support-summary').textContent = t('เปิดจากแอปเพื่อดูสถานะจริง'); }
}, 2000);
