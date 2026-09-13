export class ApiError extends Error { constructor(public status:number,message:string){super(message);} }
let csrf='';
export function setCsrf(value:string){csrf=value;}
export async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
  const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json',...(method!=='GET'?{'X-CSRF-Token':csrf}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json().catch(()=>({detail:'Der Server ist momentan nicht erreichbar.'}));
  if(!response.ok)throw new ApiError(response.status,data.detail||'Die Anfrage ist fehlgeschlagen.');
  return data;
}
