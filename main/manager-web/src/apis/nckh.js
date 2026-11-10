import {getServiceUrl} from './api';
export async function nckhRequest(path,method='GET',body){
    const saved=JSON.parse(localStorage.getItem('token')||'{}');
    if(!saved.token)throw new Error('Bạn cần đăng nhập lại.');
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),185000);
    try{
        const response=await fetch(getServiceUrl()+path,{method,signal:controller.signal,headers:{'Content-Type':'application/json','Accept-Language':'vi-VN',Authorization:'Bearer '+saved.token},body:body===undefined?undefined:JSON.stringify(body)});
        const result=await response.json();
        if(!response.ok || (result.code!==0 && result.code!=='success'))throw new Error(result.msg||'Yêu cầu thất bại.');
        return result.data;
    }finally{clearTimeout(timer);}
}
