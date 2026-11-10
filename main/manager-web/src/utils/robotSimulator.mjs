// Virtual hardware only: no physical GPIO operations.
const string=values=>({type:'string',enum:values});
const integer=(minimum,maximum)=>({type:'integer',minimum,maximum});
const tool=(name,description,properties)=>({name,description:'[MÔ PHỎNG] '+description,inputSchema:{type:'object',properties,required:Object.keys(properties),additionalProperties:false}});
export const robotTools=[
 tool('self.led.set_mode','Đặt đèn mắt',{led:string(['left','right','both']),mode:string(['off','on','blink_slow','blink_fast','breathe'])}),
 tool('self.robot.move','Di chuyển bánh xe tối đa 2 giây',{direction:string(['forward','backward','left','right','stop']),duration_ms:integer(0,2000)}),
 tool('self.robot.set_servo','Đặt góc servo',{part:string(['neck','arm_left','arm_right']),angle:integer(0,180)}),
 tool('self.robot.get_distance','Đọc khoảng cách giả lập (cm)',{}),
 tool('self.robot.wave_hand','Vẫy tay',{which:string(['left','right','both']),times:integer(1,10)})
];
export function simulateTool(name,args,distance=100){
 const definition=robotTools.find(t=>t.name===name);if(!definition)throw new Error('Công cụ không được mô phỏng');
 const properties=definition.inputSchema.properties;
 if(!args || typeof args!=='object' || Array.isArray(args))throw new Error('Tham số phải là object');
 for(const key of Object.keys(args))if(!properties[key])throw new Error('Tham số không được hỗ trợ: '+key);
 for(const [key,spec]of Object.entries(properties)){const value=args[key];if(spec.enum && !spec.enum.includes(value))throw new Error('Giá trị không hợp lệ: '+key);if(spec.type==='integer' && (!Number.isInteger(value)||value<spec.minimum||value>spec.maximum))throw new Error('Giá trị ngoài giới hạn: '+key);}
 return {simulated:true,tool:name,arguments:args,...(name==='self.robot.get_distance'?{distance_cm:distance}:{success:true})};
}
export function mcpReply(payload,distance=100){
 if(payload.id===undefined || !payload.method)return null;
 try{
  let result;
  if(payload.method==='initialize')result={protocolVersion:'2024-11-05',capabilities:{tools:{}},serverInfo:{name:'RobotVietSimulator',version:'3.0.0'}};
  else if(payload.method==='tools/list')result={tools:robotTools};
  else if(payload.method==='tools/call')result={content:[{type:'text',text:JSON.stringify(simulateTool(payload.params.name,payload.params.arguments||{},distance))}],isError:false};
  else return {jsonrpc:'2.0',id:payload.id,error:{code:-32601,message:'Phương thức không được hỗ trợ'}};
  return {jsonrpc:'2.0',id:payload.id,result};
 }catch(e){return {jsonrpc:'2.0',id:payload.id,error:{code:-32602,message:e.message}};}
}
export function pcmToWav(chunks,sampleRate=16000){
 const length=chunks.reduce((n,c)=>n+c.length,0),buffer=new ArrayBuffer(44+length*2),view=new DataView(buffer);
 const str=(offset,s)=>{for(let i=0;i<s.length;i++)view.setUint8(offset+i,s.charCodeAt(i));};
 str(0,'RIFF');view.setUint32(4,36+length*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,sampleRate,true);view.setUint32(28,sampleRate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,length*2,true);
 let offset=44;for(const chunk of chunks)for(const value of chunk){const s=Math.max(-1,Math.min(1,value));view.setInt16(offset,s<0?s*32768:s*32767,true);offset+=2;}
 return new Blob([buffer],{type:'audio/wav'});
}
