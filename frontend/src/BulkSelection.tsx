import React,{useEffect,useRef,useState} from 'react';
import {LoaderCircle,Trash2} from 'lucide-react';
import './bulk-selection.css';

export function useListSelection(ids:string[]){
 const [selected,setSelected]=useState<Set<string>>(new Set());
 const available=new Set(ids);
 const current=Array.from(selected).filter(id=>available.has(id));
 const signature=ids.join(',');
 useEffect(()=>{const valid=new Set(ids);setSelected(old=>{const next=new Set(Array.from(old).filter(id=>valid.has(id)));return next.size===old.size?old:next;});},[signature]);
 return {ids:current,has:(id:string)=>selected.has(id),toggle:(id:string)=>setSelected(old=>{const next=new Set(old);if(next.has(id))next.delete(id);else next.add(id);return next;}),toggleAll:(visible:string[])=>setSelected(old=>{const next=new Set(old),all=visible.every(id=>next.has(id));for(const id of visible){if(all)next.delete(id);else next.add(id);}return next;}),clear:(idsToClear:string[])=>setSelected(old=>new Set(Array.from(old).filter(id=>!idsToClear.includes(id))))};
}
type Selection=ReturnType<typeof useListSelection>;

export function BulkSelection({selection,visibleIds,busy,scope,onRemove}:{selection:Selection;visibleIds:string[];busy:boolean;scope:'LinkGrabber'|'Downloads';onRemove:(ids:string[])=>Promise<boolean>}){
 const checkbox=useRef<HTMLInputElement>(null),dialog=useRef<HTMLDialogElement>(null);
 const [pending,setPending]=useState<string[]>([]),[working,setWorking]=useState(false),[error,setError]=useState('');
 const checked=visibleIds.length>0&&visibleIds.every(id=>selection.has(id));
 useEffect(()=>{if(checkbox.current)checkbox.current.indeterminate=!checked&&visibleIds.some(id=>selection.has(id));},[checked,visibleIds,selection.ids]);
 useEffect(()=>{if(pending.length&&!dialog.current?.open)dialog.current?.showModal();},[pending]);
 function close(){if(working)return;dialog.current?.close();setPending([]);setError('');}
 async function confirm(){
  if(working||!pending.length)return;setWorking(true);setError('');
  try{
   for(let index=0;index<pending.length;index+=2000){const batch=pending.slice(index,index+2000);if(!await onRemove(batch)){setPending(pending.slice(index));setError(index?'Ein Teil wurde entfernt. Die verbleibende Auswahl konnte nicht entfernt werden.':'Die Auswahl konnte nicht entfernt werden. Bitte erneut versuchen.');return;}selection.clear(batch);}
   dialog.current?.close();setPending([]);
  }finally{setWorking(false);}
 }
 return <><div className="bulk-selection" role="group" aria-label={scope+' Mehrfachauswahl'}><label><input ref={checkbox} type="checkbox" aria-label="Alle sichtbaren Einträge auswählen" checked={checked} disabled={busy||!visibleIds.length} onChange={()=>selection.toggleAll(visibleIds)}/><span>Alle auswählen</span></label><span className="bulk-count">{selection.ids.length} ausgewählt</span><button type="button" className="small-button danger" disabled={busy||!selection.ids.length} onClick={()=>{setError('');setPending([...selection.ids]);}}><Trash2 size={15}/>Auswahl entfernen</button></div><dialog ref={dialog} className="card modal bulk-dialog" aria-labelledby={'bulk-title-'+scope} onCancel={event=>{event.preventDefault();close();}}><h2 id={'bulk-title-'+scope}>{pending.length} {pending.length===1?'Eintrag':'Einträge'} entfernen?</h2><p className="muted">Die ausgewählten Einträge werden aus {scope==='LinkGrabber'?'dem LinkGrabber':'der Downloadliste'} entfernt.{scope==='Downloads'?' Ausgewählte laufende Downloads werden dadurch beendet.':''} Bereits gespeicherte Dateien auf dem NAS bleiben erhalten.</p><p className="muted">Es wird nur die bestätigte Auswahl entfernt. Neu hinzukommende Einträge werden nicht automatisch mit ausgewählt.</p>{error&&<div className="alert error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="button secondary" disabled={working} onClick={close} autoFocus>Abbrechen</button><button type="button" className="button danger" disabled={working||busy} onClick={confirm}>{working?<LoaderCircle className="spin" size={17}/>:<Trash2 size={17}/>} {working?'Wird entfernt …':'Auswahl endgültig entfernen'}</button></div></dialog></>;
}
