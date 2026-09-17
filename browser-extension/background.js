const DEFAULT_SERVER = 'http://jdownloader2';
const CNL_URLS = ['http://127.0.0.1:9666/flash/*', 'http://localhost:9666/flash/*'];
const seenRequests = new Set();

function settings() {
  return new Promise(resolve => chrome.storage.local.get({server: DEFAULT_SERVER, token: ''}, resolve));
}

function normalizedServer(value) {
  try {
    const url = new URL(value || DEFAULT_SERVER);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error();
    return url.origin;
  } catch { throw new Error('Portal-Adresse ist ungültig.'); }
}

function requestFields(details) {
  const result = {};
  const body = details.requestBody || {};
  if (body.formData) {
    for (const [key, values] of Object.entries(body.formData)) result[key] = values.length === 1 ? values[0] : values;
    return result;
  }
  if (body.raw) {
    const bytes=[];
    for (const part of body.raw) if (part.bytes) bytes.push(...new Uint8Array(part.bytes));
    const params=new URLSearchParams(new TextDecoder().decode(new Uint8Array(bytes)));
    for (const [key,value] of params) {
      if (key in result) result[key]=Array.isArray(result[key])?[...result[key],value]:[result[key],value];
      else result[key]=value;
    }
  }
  return result;
}

async function portal(path, body) {
  const saved = await settings();
  if (!saved.token) throw new Error('Erweiterungsschlüssel fehlt.');
  const response = await fetch(normalizedServer(saved.server) + '/api/extension/' + path, {
    method: 'POST', headers: {'Content-Type':'application/json','X-Extension-Token':saved.token}, body: JSON.stringify(body), targetAddressSpace:'local'
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Übergabe fehlgeschlagen.');
  return data;
}

function badge(text, color) {
  chrome.action.setBadgeBackgroundColor({color});
  chrome.action.setBadgeText({text});
  setTimeout(() => chrome.action.setBadgeText({text:''}), 5000);
}

chrome.webRequest.onBeforeRequest.addListener(details => {
  if (details.method !== 'POST' || seenRequests.has(details.requestId)) return;
  seenRequests.add(details.requestId);
  setTimeout(() => seenRequests.delete(details.requestId), 60000);
  const action = new URL(details.url).pathname.split('/').filter(Boolean).pop();
  if (!['add','addcrypted2'].includes(action)) return;
  portal('cnl', {action, fields:requestFields(details)}).then(() => badge('✓','#1ea84a')).catch(() => badge('!','#c53a3a'));
}, {urls:CNL_URLS}, ['requestBody']);

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({id:'jd-link',title:'Link an JDownloader 2 senden',contexts:['link']});
    chrome.contextMenus.create({id:'jd-selection',title:'Ausgewählte Links an JDownloader 2 senden',contexts:['selection']});
  });
});

chrome.contextMenus.onClicked.addListener(info => {
  const links = info.menuItemId === 'jd-link' ? info.linkUrl : info.selectionText;
  if (!links) return;
  portal('links',{links}).then(() => badge('✓','#1ea84a')).catch(() => badge('!','#c53a3a'));
});

chrome.action.onClicked.addListener(async () => {
  try { const saved=await settings(); if (!saved.token) return chrome.runtime.openOptionsPage(); chrome.tabs.create({url:normalizedServer(saved.server)}); }
  catch { chrome.runtime.openOptionsPage(); }
});
