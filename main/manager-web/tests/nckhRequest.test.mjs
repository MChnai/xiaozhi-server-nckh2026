import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
vi.mock('../src/apis/api',()=>({getServiceUrl:()=>'/xiaozhi'}));
import {nckhRequest} from '../src/apis/nckh';
beforeEach(()=>localStorage.setItem('token',JSON.stringify({token:'user-jwt'})));
afterEach(()=>vi.unstubAllGlobals());
describe('Workbench HTTP requests',()=>{
 it('requires login',async()=>{localStorage.clear();await expect(nckhRequest('/nckh/lab/a/config')).rejects.toThrow('đăng nhập');});
 it('uses user JWT and never server secret',async()=>{
 const mock=vi.fn().mockResolvedValue({ok:true,json:async()=>({code:0,data:{ready:true}})});vi.stubGlobal('fetch',mock);
 expect(await nckhRequest('/nckh/lab/a/probe','POST',{kind:'tts'})).toEqual({ready:true});expect(mock.mock.calls[0][0]).toBe('/xiaozhi/nckh/lab/a/probe');expect(mock.mock.calls[0][1].headers.Authorization).toBe('Bearer user-jwt');
 });
 it('does not retry reminder creation',async()=>{const mock=vi.fn().mockRejectedValue(new Error('network'));vi.stubGlobal('fetch',mock);await expect(nckhRequest('/nckh/reminders/mac','POST',{content:'hi'})).rejects.toThrow('network');expect(mock).toHaveBeenCalledTimes(1);});
 it('surfaces application failure on HTTP 200',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({code:500,msg:'Chưa kết nối thiết bị'})}));await expect(nckhRequest('/nckh/lab/a/probe','POST',{})).rejects.toThrow('Chưa kết nối');});
});
