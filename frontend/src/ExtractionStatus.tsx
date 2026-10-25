import React from 'react';
import {Check,Clock,FileArchive,Info} from 'lucide-react';
import {DownloadProgress} from './DownloadProgress';

export type ExtractionInfo={state:'running'|'finished'|'queued'|'error';progress:number|null;bytesProcessed:number;bytesTotal:number;eta:number;label:string};
function size(value:number){if(!value)return '0 B';const index=Math.min(4,Math.floor(Math.log(value)/Math.log(1024)));return `${(value/1024**index).toLocaleString('de-DE',{maximumFractionDigits:1})} ${['B','KB','MB','GB','TB'][index]}`;}
function time(seconds:number){const minutes=Math.ceil(seconds/60);return minutes>=60?`${Math.floor(minutes/60)} h ${minutes%60} min`:`${minutes} min`;}

export function ExtractionStatus({info,stale=false}:{info:ExtractionInfo;stale?:boolean}){
 const done=info.state==='finished',error=info.state==='error';
 return <div className={'extraction-telemetry '+info.state} aria-label="Entpackfortschritt"><div className="extraction-heading"><span>{done?<Check size={15}/>:error?<Info size={15}/>:<FileArchive size={15}/>}<strong>{done?'Entpacken abgeschlossen':error?'Entpackfehler':info.state==='queued'?'Entpacken wartet':'Entpacken · aktuelles Archiv'}</strong></span><small>{info.label}</small></div>{!done&&<DownloadProgress value={info.progress} state={error?'error':'extracting'} label="Fortschritt beim Entpacken" stale={stale}/>}<div className="extraction-details">{info.bytesTotal>0&&<span>{size(info.bytesProcessed)} / {size(info.bytesTotal)} verarbeitet</span>}{info.state==='running'&&info.progress===null&&<span>JDownloader ermittelt den Entpackfortschritt.</span>}{!stale&&info.state==='running'&&info.eta>0&&<span><Clock size={12}/>Noch ca. {time(info.eta)}</span>}</div></div>;
}
