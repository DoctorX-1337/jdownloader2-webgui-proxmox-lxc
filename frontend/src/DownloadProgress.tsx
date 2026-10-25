import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import './download-progress.css';

export type ProgressState='running'|'paused'|'finished'|'queued'|'error'|'extracting';
type Watch={notify:(visible:boolean)=>void;intersecting:boolean};
const watches=new Map<Element,Watch>();
let observer:IntersectionObserver|undefined;

function watchVisibility(node:Element,notify:(visible:boolean)=>void){
 if(typeof IntersectionObserver==='undefined'){notify(!document.hidden);return()=>{};}
 if(!observer){
  observer=new IntersectionObserver(entries=>{for(const entry of entries){const watch=watches.get(entry.target);if(watch){watch.intersecting=entry.isIntersecting;watch.notify(entry.isIntersecting&&!document.hidden);}}},{threshold:0.01});
  document.addEventListener('visibilitychange',()=>{for(const watch of watches.values())watch.notify(watch.intersecting&&!document.hidden);});
 }
 watches.set(node,{notify,intersecting:false});observer.observe(node);
 return()=>{observer?.unobserve(node);watches.delete(node);};
}

export const DownloadProgress=React.memo(function DownloadProgress({value,state,speed=0,label,compact=false,stale=false}:{value:number|null;state:ProgressState;speed?:number;label:string;compact?:boolean;stale?:boolean}){
 const root=useRef<HTMLDivElement>(null),previous=useRef(value);
 const [visible,setVisible]=useState(false);
 const safe=value===null?null:Math.max(0,Math.min(100,Number.isFinite(value)?value:0));
 const reset=safe!==null&&previous.current!==null&&safe<previous.current;
 useLayoutEffect(()=>{previous.current=safe;},[safe]);
 const active=!compact&&!stale&&state==='running'&&speed>0&&safe!==null&&safe>0&&safe<100;
 useEffect(()=>{const node=root.current;if(!node||!active){setVisible(false);return;}return watchVisibility(node,setVisible);},[active]);
 const formatted=safe===null?'–':safe.toLocaleString('de-DE',{maximumFractionDigits:1})+' %';
 return <div ref={root} className={`download-progress ${compact?'compact':''} ${safe===null?'unknown':''} ${reset?'reset':''}`} data-state={state} data-moving={active&&visible?'true':'false'}>
  <div className="download-progress-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={safe===null?undefined:Math.round(safe*10)/10} aria-valuetext={safe===null?'Gesamtgröße wird ermittelt':formatted}>
   <div className="download-progress-fill" style={{width:(safe??0)+'%'}}>{active&&<><span className="download-progress-edge" aria-hidden="true"/><span className="download-progress-particles" aria-hidden="true"><i/><i/><i/></span></>}</div>
  </div>
  {!compact&&<strong className="download-progress-value">{formatted}</strong>}
 </div>;
});
