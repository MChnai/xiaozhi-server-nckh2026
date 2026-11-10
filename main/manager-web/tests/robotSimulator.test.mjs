import {describe,it,expect} from 'vitest';
import {robotTools,simulateTool,mcpReply,pcmToWav} from '../src/utils/robotSimulator.mjs';
describe('Robot Việt virtual hardware protocol',()=>{
 it('advertises exactly five firmware tool names',()=>expect(robotTools.map(t=>t.name)).toEqual(['self.led.set_mode','self.robot.move','self.robot.set_servo','self.robot.get_distance','self.robot.wave_hand']));
 it.each([
 ['self.robot.set_servo',{part:'neck',angle:181}],['self.robot.move',{direction:'forward',duration_ms:2001}],
 ['self.robot.wave_hand',{which:'left',times:0}],['self.led.set_mode',{led:'left',mode:'invalid'}],
 ['self.robot.get_distance',{hidden:true}],['self.robot.set_servo',{part:'neck',angle:1.5}]
 ])('rejects invalid arguments for %s',(name,args)=>expect(()=>simulateTool(name,args)).toThrow());
 it('returns clearly simulated distance',()=>expect(simulateTool('self.robot.get_distance',{},42)).toEqual({simulated:true,tool:'self.robot.get_distance',arguments:{},distance_cm:42}));
 it('preserves ids and ignores notifications and responses',()=>{
 expect(mcpReply({id:1,method:'initialize'}).id).toBe(1);expect(mcpReply({id:2,method:'tools/list'}).result.tools).toHaveLength(5);
 expect(mcpReply({method:'notifications/initialized'})).toBeNull();expect(mcpReply({id:3,result:{}})).toBeNull();
 });
 it('returns error for invalid servo',()=>expect(mcpReply({id:4,method:'tools/call',params:{name:'self.robot.set_servo',arguments:{part:'neck',angle:999}}}).error.code).toBe(-32602));
 it('encodes mono PCM16 WAV and clamps sample range',async()=>{
 const blob=pcmToWav([new Float32Array([-2,0,2])]);const bytes=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsArrayBuffer(blob);});
 const view=new DataView(bytes);expect(view.getUint32(24,true)).toBe(16000);expect(view.getUint32(40,true)).toBe(6);expect(view.getInt16(44,true)).toBe(-32768);expect(view.getInt16(48,true)).toBe(32767);
 });
});
