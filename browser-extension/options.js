const server=document.querySelector('#server'),token=document.querySelector('#token'),status=document.querySelector('#status'),form=document.querySelector('form');
chrome.storage.local.get({server:'http://jdownloader2',token:''},values=>{server.value=values.server;token.value=values.token;});

function requestPortalAccess(origin) {
  return new Promise((resolve,reject) => {
    chrome.permissions.request({origins:[origin+'/*']}, granted => {
      const error=chrome.runtime.lastError;
      if(error) reject(new Error(error.message));
      else resolve(granted);
    });
  });
}

form.addEventListener('submit',event=>{
  event.preventDefault();
  status.textContent='Berechtigung und Verbindung werden geprüft …';
  let origin;
  try {
    const url=new URL(server.value);
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw new Error();
    origin=url.origin;
  } catch {
    status.textContent='Bitte eine gültige Portal-Adresse eingeben.';
    return;
  }
  // Must be called directly from this click so Firefox can show its permission prompt.
  requestPortalAccess(origin).then(granted=>{
    if(!granted)throw new Error('Firefox benötigt Zugriff auf diese Portal-Adresse.');
    return fetch(origin+'/api/extension/status',{method:'POST',headers:{'Content-Type':'application/json','X-Extension-Token':token.value},body:'{}',targetAddressSpace:'local'});
  }).then(async response=>{
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.detail||'Verbindung fehlgeschlagen.');
    chrome.storage.local.set({server:origin,token:token.value},()=>{status.textContent='Gespeichert. Die Erweiterung ist bereit.';});
  }).catch(error=>{status.textContent=error.message==='NetworkError when attempting to fetch resource.'?'Portal nicht erreichbar. Bitte Erweiterung 1.0.2 neu laden und die Portal-Adresse prüfen.':(error.message||'Verbindung fehlgeschlagen.');});
});
