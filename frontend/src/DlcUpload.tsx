import React,{useEffect,useRef,useState} from 'react';
import {ArrowDownToLine,FileArchive,LoaderCircle,Upload} from 'lucide-react';
import {api} from './api';

const MB=1024*1024;
function size(bytes:number){return bytes<MB?`${Math.ceil(bytes/1024)} KB`:`${(bytes/MB).toLocaleString('de-DE',{maximumFractionDigits:1})} MB`;}
function readFile(file:File):Promise<string>{
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>resolve(String(reader.result).split(',')[1]);
  reader.onerror=()=>reject(new Error('Eine DLC-Datei konnte nicht gelesen werden. Bitte erneut auswählen.'));
  reader.onabort=()=>reject(new Error('Das Lesen der DLC-Datei wurde abgebrochen.'));
  reader.readAsDataURL(file);
 });
}

export function DlcUpload({disabled,onUploaded,onError}:{disabled:boolean;onUploaded:(message:string)=>void;onError:(error:unknown)=>void}){
 const input=useRef<HTMLInputElement>(null),dialog=useRef<HTMLDialogElement>(null);
 const [files,setFiles]=useState<File[]>([]),[sending,setSending]=useState(false),[error,setError]=useState('');
 const total=files.reduce((sum,file)=>sum+file.size,0);
 useEffect(()=>{if(files.length&&!dialog.current?.open)dialog.current?.showModal();},[files]);
 function cancel(){if(sending)return;dialog.current?.close();setFiles([]);setError('');}
 function select(event:React.ChangeEvent<HTMLInputElement>){
  const selected=Array.from(event.target.files||[]);
  event.target.value='';setError('');
  if(!selected.length)return;
  if(selected.length>20){setError('Bitte höchstens 20 DLC-Dateien gleichzeitig auswählen.');return;}
  if(selected.some(file=>!file.name.toLowerCase().endsWith('.dlc'))){setError('Bitte ausschließlich DLC-Dateien auswählen.');return;}
  if(selected.some(file=>!file.size||file.size>2*MB)){setError('Jede DLC-Datei muss zwischen 1 Byte und 2 MB groß sein.');return;}
  if(selected.reduce((sum,file)=>sum+file.size,0)>10*MB){setError('Die DLC-Dateien dürfen zusammen höchstens 10 MB groß sein.');return;}
  setFiles(selected);
 }
 async function submit(){
  if(sending||disabled||!files.length)return;
  setSending(true);setError('');
  try{
   const payload=await Promise.all(files.map(async file=>({name:file.name,content:await readFile(file)})));
   const result=await api<{message:string}>('/downloads/dlc','POST',{confirmed:true,files:payload});
   dialog.current?.close();setFiles([]);onUploaded(result.message);
  }catch(e){setError(e instanceof Error?e.message:'Die DLC-Dateien konnten nicht übergeben werden.');onError(e);}
  finally{setSending(false);}
 }
 return <div className="dlc-upload">
  <input ref={input} className="sr-only" type="file" accept=".dlc" multiple aria-label="DLC-Dateien auswählen" tabIndex={-1} onChange={select}/>
  <button type="button" className="button secondary" disabled={disabled||sending} onClick={()=>input.current?.click()}><Upload size={18}/> DLC-Dateien hochladen</button>
  <small className="muted">Mehrere Dateien möglich · bis 2 MB je Datei, insgesamt 10 MB</small>
  {error&&!files.length&&<div className="alert error" role="alert">{error}</div>}
  <dialog ref={dialog} className="card modal dlc-dialog" aria-labelledby="dlc-title" aria-describedby="dlc-description" onCancel={e=>{e.preventDefault();cancel();}}>
   <div className="card-title"><FileArchive/><h2 id="dlc-title">DLC-Upload bestätigen</h2></div>
   <p id="dlc-description" className="muted">Diese Dateien an JDownloader übergeben? Die enthaltenen Links werden entschlüsselt und nach deinen Einstellungen verarbeitet – einschließlich Downloadziel, Autostart und Entpacken.</p>
   <ul className="dlc-files">{files.map((file,index)=><li key={index}><FileArchive size={18}/><span>{file.name}</span><small>{size(file.size)}</small></li>)}</ul>
   <p className="muted">{files.length} {files.length===1?'Datei':'Dateien'} · {size(total)} gesamt</p>
   {error&&<div className="alert error" role="alert">{error}</div>}
   <div className="modal-actions"><button type="button" className="button secondary" disabled={sending} onClick={cancel} autoFocus>Abbrechen</button><button type="button" className="button primary" disabled={disabled||sending} onClick={submit}>{sending?<LoaderCircle className="spin" size={19}/>:<ArrowDownToLine size={19}/>} {sending?'Wird übergeben …':'Bestätigen & übergeben'}</button></div>
  </dialog>
 </div>;
}
