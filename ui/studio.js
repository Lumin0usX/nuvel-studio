'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1);
const settings = {folder:'', cookies:'none', cookie_path:''};
let ready = false, busy = false, activeFolder = '', lastPhase = '', lastPlatforms = '', lastHistory = '', toastTimer;
async function api(method, ...args) {
  if (window.pywebview?.api) return window.pywebview.api[method](...args);
  if (token && location.protocol.startsWith('http')) {
    const response = await fetch('/api/' + method, {method:'POST', headers:{'Content-Type':'application/json','X-Studio-Token':token}, body:JSON.stringify(args)});
    if (!response.ok) throw new Error('เชื่อมต่อกับแอปไม่สำเร็จ');
    return response.json();
  }
  throw new Error('เปิดผ่าน start.bat หรือ start_macos.command เพื่อเริ่มดาวน์โหลด');
}
function toast(text) {clearTimeout(toastTimer); $('toast').textContent=text; $('toast').hidden=false; toastTimer=setTimeout(()=>$('toast').hidden=true,4200);}
function showError(text) {$('form-error').textContent=text; $('form-error').hidden=!text;}
function showPage(page) {
  $('home-page').hidden=page!=='home'; $('history-page').hidden=page!=='history';
  $('page-name').textContent=page==='home'?'ดาวน์โหลด':'กิจกรรมล่าสุด';
  document.querySelectorAll('[data-page]').forEach(el=>el.classList.toggle('selected',el.dataset.page===page));
}
document.querySelectorAll('[data-page]').forEach(el=>el.addEventListener('click',()=>showPage(el.dataset.page)));
function mode() {return document.querySelector('input[name="mode"]:checked').value;}
function setBusy(value) {
  busy=value;
  document.querySelectorAll('#download-form input, #download-form button').forEach(el=>el.disabled=value);
  $('settings-nav').disabled=value; $('cancel').hidden=!value;
  $('download').querySelector('span').textContent=value?'กำลังจัดการคลิปของคุณ…':mode()==='video'?'ดาวน์โหลดวิดีโอ':'ดาวน์โหลดเสียง';
}
document.querySelectorAll('input[name="mode"]').forEach(el=>el.addEventListener('change',()=>setBusy(busy)));
$('url').addEventListener('input',()=>{
  showError('');
  try {const url=new URL($('url').value.trim()); $('url-hint').textContent=['https:','http:'].includes(url.protocol)?url.hostname:'ใช้ลิงก์ที่ขึ้นต้นด้วย https://';}
  catch {$('url-hint').textContent=$('url').value?'วางลิงก์แบบเต็มที่ขึ้นต้นด้วย https://':'YouTube, TikTok, Instagram และอีกหลายแพลตฟอร์ม';}
});
$('paste').addEventListener('click',async()=>{
  try {$('url').value=(await navigator.clipboard.readText()).trim(); $('url').dispatchEvent(new Event('input')); $('url').focus();}
  catch {$('url').focus(); toast('กด ⌘V บน Mac หรือ Ctrl+V บน Windows เพื่อวางลิงก์');}
});
$('download-form').addEventListener('submit',async event=>{
  event.preventDefault(); if(busy)return;
  showError('');
  if(!$('url').value.trim()){showError('วางลิงก์คลิปที่ต้องการดาวน์โหลดก่อน');$('url').focus();return;}
  setBusy(true);
  try {const result=await api('start_download',{url:$('url').value.trim(),mode:mode(),...settings});
    if(result.error){showError(result.error);setBusy(false);} else {showPage('home');await poll();}}
  catch(error){showError(error.message);setBusy(false);}
});
function updateFolder(){const path=settings.folder.replace(/[\\/]+$/,'');$('folder-label').textContent=path.split(/[\\/]/).pop()||path||'เลือกโฟลเดอร์';$('folder-label').title=settings.folder;}
function openSettings(){if(busy){toast('รอให้งานปัจจุบันเสร็จก่อนเปลี่ยนการตั้งค่า');return;}$('folder-path').value=settings.folder;$('cookies').value=settings.cookies;$('cookie-path').value=settings.cookie_path;$('cookie-file-row').hidden=settings.cookies!=='file';$('settings-dialog').showModal();}
['advanced','settings-nav','change-folder'].forEach(id=>$(id).addEventListener('click',openSettings));
$('help').addEventListener('click',()=>$('help-dialog').showModal());
$('cookies').addEventListener('change',()=>$('cookie-file-row').hidden=$('cookies').value!=='file');
$('browse-folder').addEventListener('click',async()=>{try{const result=await api('choose_folder');if(result.path)$('folder-path').value=result.path;if(result.error)toast(result.error);}catch(e){toast(e.message);}});
$('browse-cookie').addEventListener('click',async()=>{try{const result=await api('choose_cookies');if(result.path)$('cookie-path').value=result.path;if(result.error)toast(result.error);}catch(e){toast(e.message);}});
$('save-settings').addEventListener('click',()=>{
  if(!$('folder-path').value.trim()){toast('ใส่โฟลเดอร์ปลายทางก่อน');$('folder-path').focus();return;}
  Object.assign(settings,{folder:$('folder-path').value.trim(),cookies:$('cookies').value,cookie_path:$('cookie-path').value.trim()});
  updateFolder();$('settings-dialog').close();toast('บันทึกการตั้งค่าแล้ว');
});
async function openFolder(path){try{const result=await api('open_folder',path);if(result.error)toast(result.error);}catch(e){toast(e.message);}}
$('open-folder').addEventListener('click',()=>openFolder(activeFolder||settings.folder));
$('cancel').addEventListener('click',async()=>{try{await api('cancel_download');await poll();}catch(e){toast(e.message);}});
function renderPlatforms(platforms) {
  if(!platforms.length)return;
  const key=platforms.map(p=>p.name+p.status).join();if(key===lastPlatforms)return;lastPlatforms=key;
  const supported=platforms.filter(p=>p.status==='supported').length;
  $('support-number').textContent=supported.toString().padStart(2,'0');
  $('support-summary').textContent=`มีตัวรองรับ ${supported} จาก ${platforms.length} แพลตฟอร์ม`;
  $('platforms').replaceChildren();
  const labels={supported:'มีตัวรองรับ',broken:'ตัวรองรับมีปัญหา',missing:'ยังไม่พบตัวรองรับ',unknown:'กำลังตรวจสอบ'};
  for(const platform of platforms){
    const button=document.createElement('button');button.className='platform '+platform.status;
    button.title=platform.name+' · '+labels[platform.status];button.setAttribute('aria-label',button.title);
    const img=document.createElement('img');img.src=platform.icon;img.alt=platform.name;
    const dot=document.createElement('span');dot.className='status-dot';button.append(img,dot);
    button.addEventListener('click',()=>{document.querySelectorAll('.platform').forEach(el=>el.classList.remove('chosen'));button.classList.add('chosen');$('platform-detail').textContent=button.title;});
    $('platforms').append(button);
  }
}
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href','#'+name);svg.append(use);return svg;}
function renderHistory(history){
  const key=JSON.stringify(history);if(lastHistory===key)return;lastHistory=key;
  $('history-count').textContent=String(history.length);$('history-list').replaceChildren();
  if(!history.length){const empty=document.createElement('div');empty.className='empty-history glass';empty.append(icon('clock'));const heading=document.createElement('h3');heading.textContent='คอลเลกชันของคุณ เริ่มได้ทุกเมื่อ';const hint=document.createElement('p');hint.textContent='คลิปที่ดาวน์โหลดสำเร็จจะแสดงที่นี่';const button=document.createElement('button');button.className='soft-button';button.textContent='ดาวน์โหลดคลิปแรก';button.onclick=()=>{showPage('home');$('url').focus();};empty.append(heading,hint,button);$('history-list').append(empty);return;}
  for(const item of history){const row=document.createElement('div');row.className='activity glass done';const mark=document.createElement('div');mark.className='activity-icon';mark.append(icon(item.mode==='video'?'play':'music'));const body=document.createElement('div');body.className='activity-main';const title=document.createElement('strong');title.textContent=item.title;const details=document.createElement('p');details.textContent=`${item.mode==='video'?'MP4':'MP3'} · ${item.time} · บันทึกแล้ว`;body.append(title,details);const open=document.createElement('button');open.className='round-button';open.title='เปิดโฟลเดอร์';open.append(icon('folder'));open.onclick=()=>openFolder(item.folder);row.append(mark,body,open);$('history-list').append(row);}
}
function render(state){
  if(!ready){settings.folder=state.folder;updateFolder();ready=true;}
  renderPlatforms(state.platforms);renderHistory(state.history);
  const working=['connecting','downloading','processing','cancelling'].includes(state.phase);setBusy(working);
  $('activity').className='activity glass '+state.phase;
  if(state.phase!=='idle'){
    $('job-title').textContent=state.title||'คลิปของคุณ';$('job-detail').textContent=state.phase==='error'?state.error:state.detail;
    activeFolder=state.folder;
  }
  $('job-percent').textContent=state.phase==='downloading'?Math.round(state.percent)+'%':state.phase==='done'?'เสร็จแล้ว':'';
  $('progress-track').hidden=!working&&state.phase!=='done';
  $('progress-track').classList.toggle('indeterminate',['connecting','processing','cancelling'].includes(state.phase));
  $('progress-fill').style.width=(state.phase==='done'?100:state.percent)+'%';
  $('job-meta').textContent=[state.speed,state.eta?'เหลือประมาณ '+state.eta+' นาที':''].filter(Boolean).join('  ·  ');
  $('cancel').disabled=state.phase==='cancelling';$('cancel').textContent=state.phase==='cancelling'?'กำลังหยุด…':'หยุดงาน';
  if(state.phase==='done'&&lastPhase!=='done')toast('เก็บคลิปเรียบร้อยแล้ว');
  lastPhase=state.phase;
}
let polling=false;
async function poll(){if(polling)return;polling=true;try{render(await api('snapshot'));}catch(e){if(ready){$('job-detail').textContent='การเชื่อมต่อหยุดลง เปิดแอปใหม่เพื่อตรวจสอบ';setBusy(false);}}finally{polling=false;}}
function connect(){poll();setInterval(poll,650);}
window.addEventListener('pywebviewready',connect,{once:true});
if(token)connect();
renderHistory([]);
const seed=$('platform-seed');
if(seed){renderPlatforms(JSON.parse(seed.textContent));$('support-number').textContent='—';$('support-summary').textContent='กำลังตรวจสอบตัวรองรับ…';}
window.studioReady=true;
// Static preview is deliberately read-only: it never claims a download is running.
if(!token)setTimeout(()=>{if(!window.pywebview?.api&&!ready){$('support-summary').textContent='เปิดจากแอปเพื่อดูสถานะจริง';$('platform-detail').textContent='หน้าตัวอย่าง · ยังไม่เชื่อมต่อระบบดาวน์โหลด';}},2000);
