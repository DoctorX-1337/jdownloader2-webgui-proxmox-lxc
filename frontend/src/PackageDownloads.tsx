import React,{useEffect,useMemo,useState} from 'react';
import {Activity,Check,ChevronDown,Clock,FileArchive,Folder,Info,Pause,Search,WifiOff} from 'lucide-react';
import './packages.css';
import {DownloadProgress,type ProgressState} from './DownloadProgress';
import {ExtractionStatus,type ExtractionInfo} from './ExtractionStatus';

export type DownloadPackage={uuid:string;name:string;bytesLoaded:number;bytesTotal:number;progress:number|null;speed:number;eta:number;fileCount:number;finishedCount:number;runningCount:number;unknownSizeCount:number;problemCount:number;finished:boolean;extraction?:ExtractionInfo|null;status:'running'|'queued'|'paused'|'finished'|'extracting'|'extraction_error'|'attention'};
export type PackageFile={uuid:string;packageUUID?:string;name:string;bytesLoaded?:number;bytesTotal?:number;finished?:boolean;running?:boolean;enabled?:boolean;extractionStatus?:string;status?:string};
const labels:Record<DownloadPackage['status'],string>={running:'Lädt herunter',queued:'In der Warteschlange',paused:'Pausiert',finished:'Abgeschlossen',extracting:'Wird entpackt',extraction_error:'Entpacken fehlgeschlagen',attention:'Aktion erforderlich'};
const order:Record<DownloadPackage['status'],number>={running:0,extracting:1,attention:2,extraction_error:2,queued:3,paused:4,finished:5};
function size(value=0){if(value<=0)return '0 B';const i=Math.min(4,Math.floor(Math.log(value)/Math.log(1024)));return `${(value/1024**i).toLocaleString('de-DE',{maximumFractionDigits:i?1:0})} ${['B','KB','MB','GB','TB'][i]}`;}
function time(seconds:number){const minutes=Math.ceil(seconds/60);return minutes>=60?`${Math.floor(minutes/60)} h ${minutes%60} min`:`${minutes} min`;}
function percent(value:number){return value.toLocaleString('de-DE',{maximumFractionDigits:1});}

export function PackageDownloads({packages,links,activeOnly,loading,stale,updated}:{packages:DownloadPackage[];links:PackageFile[];activeOnly:boolean;loading:boolean;stale:boolean;updated:number}){
 const [search,setSearch]=useState(''),[showAll,setShowAll]=useState(!activeOnly);
 useEffect(()=>setShowAll(!activeOnly),[activeOnly]);
 const filesByPackage=useMemo(()=>{const map=new Map<string,PackageFile[]>();for(const link of links){const id=link.packageUUID||'';const group=map.get(id)||[];group.push(link);map.set(id,group);}return map;},[links]);
 const active=packages.filter(p=>!p.finished||p.status==='extracting'||p.status==='extraction_error');
 const visible=(showAll?packages:active).filter(p=>p.name.toLowerCase().includes(search.toLowerCase())).slice().sort((a,b)=>order[a.status]-order[b.status]);
 const running=packages.filter(p=>p.status==='running').length;
 return <section className="card package-downloads" aria-label="Downloadpakete">
  <div className="package-heading"><div className="card-title"><Folder size={25}/><h2>Deine Downloadpakete <span>({packages.length})</span></h2></div><span className={`package-live ${stale?'stale':''}`}>{stale?<WifiOff size={13}/>:<span/>}{stale?'Letzter Stand':'Live · alle 3 s'}</span></div>
  <p className="muted package-intro">Der Gesamtfortschritt je Paket, inklusive aller fertigen Teil-Dateien. Ein DLC kann mehrere Pakete enthalten.</p>
  <div className="package-summary"><span><Activity size={15}/><strong>{running}</strong> laden</span><span><Clock size={15}/><strong>{active.length}</strong> offen</span><span><Check size={15}/><strong>{packages.filter(p=>p.status==='finished').length}</strong> fertig</span></div>
  <div className="package-toolbar"><div className="package-filter" role="group" aria-label="Pakete filtern"><button type="button" aria-pressed={!showAll} onClick={()=>setShowAll(false)}>Aktive Pakete <span>{active.length}</span></button><button type="button" aria-pressed={showAll} onClick={()=>setShowAll(true)}>Alle <span>{packages.length}</span></button></div><div className="search package-search"><Search size={16}/><input aria-label="Pakete durchsuchen" placeholder="Paket suchen …" value={search} onChange={e=>setSearch(e.target.value)}/></div></div>
  {stale&&<div className="package-stale" role="status"><WifiOff size={16}/><span>Die Verbindung wird wiederhergestellt. Angezeigt wird der letzte Stand{updated?' von '+new Date(updated).toLocaleTimeString('de-DE'):''}.</span></div>}
  {!visible.length?<div className="package-empty"><FileArchive size={30}/><strong>{loading?'Pakete werden geladen …':search?'Kein passendes Paket':packages.length?'Alle Pakete sind fertig':'Noch keine Downloadpakete'}</strong><p className="muted">{loading?'Einen Moment bitte.':search?'Versuche einen anderen Suchbegriff.':packages.length?'Unter „Alle“ siehst du die abgeschlossenen Pakete.':'Neue Links oder DLC-Dateien erscheinen hier automatisch.'}</p></div>:<div className="package-list">{visible.map(p=><PackageCard key={p.uuid} package={p} files={filesByPackage.get(p.uuid)||[]} stale={stale}/>)}</div>}
 </section>;
}

function PackageCard({package:p,files,stale}:{package:DownloadPackage;files:PackageFile[];stale:boolean}){
 const [open,setOpen]=useState(false);
 const done=p.status==='finished',attention=p.status==='attention'||p.status==='extraction_error';
 const progress=p.progress;
 return <article className={`package-card ${p.status}`} data-package-id={p.uuid}>
  <div className="package-card-heading"><span className="package-icon">{done?<Check size={23}/>:<FileArchive size={23}/>}</span><div className="package-title"><h3 title={p.name}>{p.name}</h3><span className={`package-status ${attention?'attention':''}`}>{p.status==='running'?<Activity size={12}/>:p.status==='paused'?<Pause size={12}/>:attention?<Info size={12}/>:done?<Check size={12}/>:null}{labels[p.status]}</span></div></div>
  <div className="package-meter"><DownloadProgress value={progress} state={p.finished?'finished':attention?'error':p.status as ProgressState} speed={p.speed} label={'Gesamtfortschritt: '+p.name} stale={stale}/></div>
  <div className="package-metrics"><span className="package-bytes">{size(p.bytesLoaded)} <span>/ {progress===null?'Gesamtgröße wird ermittelt':size(p.bytesTotal)}</span></span><span className="package-speed">{!stale&&p.speed>0?<><Activity size={13}/>{size(p.speed)}/s</>:null}</span></div>
  {p.extraction&&<ExtractionStatus info={p.extraction} stale={stale}/>}
  <div className="package-card-footer"><span><Check size={13}/>{p.finishedCount} / {p.fileCount} Dateien fertig</span>{!stale&&p.eta>0&&<span><Clock size={13}/>Noch ca. {time(p.eta)}</span>}<button type="button" aria-expanded={open} aria-controls={'package-files-'+p.uuid} onClick={()=>setOpen(!open)}>{open?'Dateien ausblenden':'Dateien ansehen'}<ChevronDown size={15} className={open?'expanded':''}/></button></div>
  {open&&<div className="package-files" id={'package-files-'+p.uuid}>{files.length?files.map(file=>{const value=file.finished?100:file.bytesTotal&&file.bytesTotal>0?Math.min(100,(file.bytesLoaded||0)/file.bytesTotal*100):null;return <div className="package-file" key={file.uuid}><div><span title={file.name}>{file.name}</span><small>{file.extractionStatus==='RUNNING'?'Wird entpackt':file.finished?'Fertig':file.running?'Lädt herunter':file.enabled===false?'Pausiert':'Wartend'}</small></div><DownloadProgress value={value} state={file.finished?'finished':file.enabled===false?'paused':file.running?'running':'queued'} label={'Fortschritt: '+file.name} compact/><small>{value===null?size(file.bytesLoaded):percent(value)+' %'}</small></div>;}):<p className="muted">Dateidetails werden beim nächsten Abruf aktualisiert.</p>}</div>}
 </article>;
}
