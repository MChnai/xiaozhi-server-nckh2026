<template>
 <div class="lab-page"><HeaderBar />
  <main class="lab-main">
   <h1>Kiểm thử server Robot Việt</h1>
   <p>Thiết bị ảo thử giao thức WebSocket/MCP. Thao tác LED, motor và servo bên dưới chỉ được mô phỏng.</p>
   <el-alert title="Hội thoại và công cụ dịch có thể tính phí khi bật DeepSeek. Demo trả lời cố định, không tự chọn công cụ." type="info" :closable="false" />
   <div class="toolbar">
    <el-select v-model="agentId" placeholder="Chọn trợ lý" @change="selectAgent" :disabled="busy || connected || connecting"><el-option v-for="a in agents" :key="a.id" :label="a.agentName" :value="a.id" /></el-select>
    <el-button @click="connect" :disabled="!agentId || connected || connecting || busy">Kết nối thiết bị ảo</el-button>
    <el-button @click="disconnect" :disabled="!connected">Ngắt kết nối</el-button>
    <el-tag :type="connected?'success':'info'">{{ connected?'Đã kết nối':connecting?'Đang kết nối':'Chưa kết nối' }}</el-tag>
   </div>
   <div class="status-card"><strong>Robot Việt v3</strong>
    <el-button @click="refreshStatus" :disabled="!agentId || busy" size="small">Kiểm tra cấu hình</el-button>
    <p v-if="runtime">Chế độ: <b>{{ runtime.mode === 'demo' ? 'Demo — không gọi DeepSeek' : 'DeepSeek — có thể tính phí API' }}</b>.
     Voice: {{ runtime.ready ? 'sẵn sàng' : 'chưa sẵn sàng' }}.
     Khóa DeepSeek: {{ runtime.deepseek_configured ? 'đã cấu hình' : 'chưa có' }}.
     Khóa thời tiết: {{ runtime.weather_configured ? 'đã cấu hình' : 'chưa có' }}.</p>
   </div>
   <p v-if="summary">Model đang lưu: {{ summary }}</p>
   <p v-if="virtual">MAC thiết bị ảo: {{ virtual.device_id }}. Có thể xóa thiết bị này tại Quản lý thiết bị.</p>
   <el-alert v-if="error" :title="error" type="error" @close="error=''" />
   <el-tabs v-model="tab">
    <el-tab-pane label="Hội thoại" name="chat">
     <p>Gửi văn bản qua WebSocket; nhận phản hồi và âm thanh Opus từ server. Dùng tab ASR để thử tệp thu âm.</p>
     <el-input v-model="message" placeholder="Nhập câu hỏi hoặc yêu cầu" maxlength="2000" @keyup.enter.native="sendChat" />
     <el-button @click="sendChat" :disabled="!connected || busy">Gửi hội thoại</el-button><el-button @click="abort" :disabled="!connected">Ngắt lời</el-button>
     <p>{{ reply }}</p><p>Đã nhận {{ packets }} gói âm thanh trong lượt gần nhất.</p>
    </el-tab-pane>
    <el-tab-pane label="ASR / TTS" name="audio">
     <h3>Đọc tiếng Việt</h3><el-input v-model="ttsText" type="textarea" maxlength="2000" />
     <el-button @click="testTts" :loading="busy" :disabled="!agentId">Tạo giọng nói theo cấu hình trợ lý</el-button>
     <h3>Nhận dạng tệp thu âm</h3><p>Chọn WAV, MP3 hoặc M4A, tối đa 8 MB; nhận dạng 30 giây đầu. Không cần API DeepSeek.</p>
     <el-button @click="startRecording" :disabled="recording || busy">Thu bằng micro (tối đa 30 giây)</el-button>
     <el-button @click="stopRecording" :disabled="!recording">Dừng thu</el-button>
     <span v-if="recording">Đang thu âm…</span>
     <p>Micro cần mở trang bằng localhost hoặc HTTPS. Khi dùng IP LAN qua HTTP, bạn vẫn có thể tải tệp thu âm.</p>
     <p v-if="audioFile">Tệp đang chọn: {{ audioFile.name || 'bản thu micro' }} ({{ Math.round(audioFile.size/1024) }} KB)</p>
     <input type="file" accept="audio/*" @change="chooseAudio" /><el-button @click="testAsr" :loading="busy" :disabled="!audioFile || !agentId">Nhận dạng tiếng Việt</el-button>
     <p>{{ transcript }}</p><el-button v-if="transcript" @click="message=transcript;tab='chat'">Dùng văn bản này để trò chuyện</el-button>
    </el-tab-pane>
    <el-tab-pane label="Plugin" name="plugins">
     <p>Thử trực tiếp để phân biệt lỗi nguồn dữ liệu với lỗi LLM chọn công cụ. Plugin dịch dùng DeepSeek thật.</p>
     <el-select v-model="plugin" @change="resetPlugin"><el-option v-for="p in pluginOptions" :key="p.name" :label="p.label" :value="p.name" /></el-select>
     <el-input type="textarea" v-model="pluginArgs" :rows="4" /><el-button @click="testPlugin" :loading="busy" :disabled="!agentId">Chạy plugin</el-button><pre>{{ pluginResult }}</pre>
    </el-tab-pane>
    <el-tab-pane label="MCP mô phỏng" name="mcp">
     <p>Kết nối thiết bị ảo trước. Khoảng cách giả lập: <el-input-number v-model="distance" :min="0" :max="500" /> cm.</p>
     <el-button @click="testMcp('self.robot.get_distance',{})" :disabled="!connected || busy">Đọc khoảng cách</el-button>
     <el-button @click="testMcp('self.led.set_mode',{led:'both',mode:'blink_slow'})" :disabled="!connected || busy">Nháy mắt</el-button>
     <el-button @click="testMcp('self.robot.wave_hand',{which:'both',times:2})" :disabled="!connected || busy">Vẫy tay</el-button>
     <el-button @click="testMcp('self.robot.set_servo',{part:'neck',angle:90})" :disabled="!connected || busy">Đặt cổ 90°</el-button>
     <el-button @click="testMcp('self.robot.move',{direction:'forward',duration_ms:500})" :disabled="!connected || busy">Di chuyển ảo 0,5 giây</el-button><pre>{{ mcpResult }}</pre>
    </el-tab-pane>
    <el-tab-pane label="Nhắc nhở" name="reminders">
     <p>Thiết bị phải online và rảnh để phát lời nhắc; thiết bị ảo phát qua trang này.</p>
     <el-select v-model="reminderDevice" placeholder="Chọn thiết bị" @change="loadReminders"><el-option v-for="d in devices" :key="d.macAddress" :label="(d.alias || d.board || 'Thiết bị')+' — '+d.macAddress" :value="d.macAddress" /></el-select>
     <el-button @click="loadReminders" :disabled="!reminderDevice || busy">Tải lại</el-button>
     <el-input v-model="reminderText" placeholder="Nội dung nhắc" maxlength="500" /><el-date-picker v-model="reminderDate" type="datetime" placeholder="Giờ theo múi giờ máy tính" />
     <el-select v-model="repeat"><el-option label="Một lần" value="none" /><el-option label="Hằng ngày" value="daily" /><el-option label="Hằng tuần" value="weekly" /></el-select>
     <el-button @click="addReminder" :disabled="!reminderDevice || busy">Lưu lời nhắc</el-button><el-button @click="reminderDate=new Date(Date.now()+60000)" :disabled="busy">Đặt sau 1 phút</el-button>
     <el-table :data="reminders"><el-table-column prop="content" label="Nội dung" /><el-table-column label="Thời gian Việt Nam"><template slot-scope="scope">{{ vnTime(scope.row.due_at) }}</template></el-table-column><el-table-column label="Lặp"><template slot-scope="scope">{{ ({none:'Một lần',daily:'Hằng ngày',weekly:'Hằng tuần'})[scope.row.repeat_type] || scope.row.repeat_type }}</template></el-table-column><el-table-column label="Trạng thái"><template slot-scope="scope">{{ ({pending:'Đang chờ',sending:'Đang phát',queued:'Đã gửi âm thanh',cancelled:'Đã hủy'})[scope.row.status] || scope.row.status }}</template></el-table-column><el-table-column label="Thao tác"><template slot-scope="scope"><el-button v-if="['pending','sending'].includes(scope.row.status)" @click="cancelReminder(scope.row.id)" :disabled="busy">Hủy</el-button></template></el-table-column></el-table>
    </el-tab-pane>
   </el-tabs>
   <section v-if="audioUrl"><h3>Âm thanh kiểm thử</h3><audio ref="player" :src="audioUrl" controls /><a :href="audioUrl" :download="audioName">Tải âm thanh</a></section>
   <h3>Nhật ký kiểm thử</h3><el-button @click="logs=[]">Xóa nhật ký</el-button><pre class="logs">{{ logs.join('\n') }}</pre>
  </main>
 </div>
</template>
<script>
import HeaderBar from '@/components/HeaderBar.vue';
import {nckhRequest} from '@/apis/nckh';
import {mcpReply,pcmToWav} from '@/utils/robotSimulator.mjs';
const plugins=[
 {name:'get_news_from_vnexpress',label:'Tin VnExpress',args:{category:'moi-nhat',limit:3}},
 {name:'get_weather_vn',label:'Thời tiết',args:{city:'Da Lat,VN'}},
 {name:'get_gold_price',label:'Giá vàng',args:{type_code:'SJL1L10'}},
 {name:'get_lunar',label:'Âm lịch Việt Nam',args:{}},
 {name:'translate_text',label:'Dịch Việt–Anh / IPA (có phí API)',args:{text:'Xin chào, rất vui được gặp bạn.',direction:'vi-en'}},
 {name:'play_music',label:'Phát nhạc local (cần kết nối)',args:{song_name:'nhạc mẫu'}}
];
export default{
 components:{HeaderBar},
 data(){return {runtime:null,recording:false,agents:[],agentId:'',summary:'',busy:false,connecting:false,connected:false,virtual:null,error:'',tab:'chat',message:'',reply:'',packets:0,logs:[],distance:100,ttsText:'Xin chào, đây là Robot AI tiếng Việt.',audioFile:null,transcript:'',audioUrl:'',audioName:'robot-viet-test.wav',pluginOptions:plugins,plugin:plugins[0].name,pluginArgs:JSON.stringify(plugins[0].args,null,2),pluginResult:'',mcpResult:'',devices:[],reminderDevice:'',reminders:[],reminderText:'',reminderDate:null,repeat:'none'};},
 async mounted(){try{this.agents=await nckhRequest('/agent/list');if(this.agents.length){this.agentId=this.agents[0].id;await this.selectAgent();}}catch(e){this.error=e.message;}},
 beforeDestroy(){this.stopRecording();clearTimeout(this.recordTimer);this.disconnect();if(this.audioUrl)URL.revokeObjectURL(this.audioUrl);},
 methods:{
  log(s){this.logs.push(new Date().toLocaleTimeString('vi-VN')+' '+s);if(this.logs.length>300)this.logs.shift();},
  async guarded(action){if(this.busy)return;this.busy=true;this.error='';try{await action();}catch(e){this.error=e.name==='AbortError'?'Yêu cầu đã hết thời gian chờ.':e.message;this.log(this.error);}finally{this.busy=false;}},
  async selectAgent(){this.virtual=null;this.reminderDevice='';this.reminders=[];try{const s=await nckhRequest('/nckh/lab/'+this.agentId+'/config');this.summary=JSON.stringify(s.selected_module);await this.loadDevices();await this.refreshStatus();}catch(e){this.error=e.message;}},
  async loadDevices(){this.devices=await nckhRequest('/device/bind/'+this.agentId);},
  async connect(){await this.guarded(async()=>{
   this.virtual=await nckhRequest('/nckh/lab/'+this.agentId+'/device','POST',{});await this.loadDevices();this.reminderDevice=this.virtual.device_id;
   const {OpusDecoder}=await import('opus-decoder');this.decoder=new OpusDecoder({sampleRate:16000});await this.decoder.ready;
   this.audioChain=Promise.resolve();this.chunks=[];
   const u=new URL(this.virtual.websocket_url,window.location.href);u.searchParams.set('device-id',this.virtual.device_id);u.searchParams.set('client-id',this.virtual.client_id);u.searchParams.set('authorization','Bearer '+this.virtual.token);
   const socket=new WebSocket(u.toString());this.ws=socket;this.connecting=true;socket.binaryType='arraybuffer';this.connectTimer=setTimeout(()=>{if(this.ws===socket && this.connecting){this.error='WebSocket chưa mở sau 15 giây. Kiểm tra IP và cổng 8000.';this.disconnect();}},15000);
   socket.onopen=()=>{if(this.ws!==socket)return;clearTimeout(this.connectTimer);this.connecting=false;this.connected=true;this.ws.send(JSON.stringify({type:'hello',version:1,transport:'websocket',features:{mcp:true},audio_params:{format:'opus',sample_rate:16000,channels:1,frame_duration:60}}));this.log('Đã kết nối WebSocket với thiết bị ảo.');};
   socket.onmessage=event=>{if(this.ws===socket)this.onMessage(event);};
   socket.onclose=()=>{if(this.ws!==socket)return;clearTimeout(this.connectTimer);this.ws=null;this.connecting=false;this.connected=false;if(this.decoder){this.decoder.free();this.decoder=null;}this.log('WebSocket đã đóng. Kết nối lại để lấy token mới.');};
   socket.onerror=()=>{if(this.ws!==socket)return;this.error='Không kết nối được WebSocket. Kiểm tra IP, cổng 8000, firewall và TLS nếu dùng HTTPS.';};
  });},
  disconnect(){clearTimeout(this.connectTimer);if(this.ws){const socket=this.ws;this.ws=null;socket.close();}this.connecting=false;this.connected=false;if(this.decoder){this.decoder.free();this.decoder=null;}},
  onMessage(event){
   if(event.data instanceof ArrayBuffer){const bytes=new Uint8Array(event.data);this.packets++;this.audioChain=this.audioChain.then(()=>{if(!this.decoder)return;const d=this.decoder.decodeFrame(bytes);if(d.channelData[0] && this.chunks.reduce((n,c)=>n+c.length,0)<1600000)this.chunks.push(d.channelData[0].slice());}).catch(()=>this.log('Không giải mã được một gói Opus.'));return;}
   let m;try{m=JSON.parse(event.data);}catch(e){this.log(String(event.data));return;}
   if(m.type==='mcp'){const payload=mcpReply(m.payload,this.distance);if(m.payload.method==='tools/call')this.log('MCP mô phỏng: '+m.payload.params.name);if(payload && this.ws && this.ws.readyState===1)this.ws.send(JSON.stringify({type:'mcp',payload}));}
   else if(m.type==='tts'){if(m.state==='start'){this.chunks=[];this.packets=0;this.reply='';}if(m.text)this.reply+=(this.reply?' ':'')+m.text;if(m.state==='stop')this.audioChain.then(()=>{if(this.chunks.length)this.setAudio(pcmToWav(this.chunks),true);this.log('Đã kết thúc lượt âm thanh.');});}
   else if(m.type==='stt')this.log('ASR/STT: '+m.text);else if(m.type==='hello')this.log('Đã nhận hello từ server.');
  },
  sendChat(){if(!this.connected || !this.message.trim())return;this.log('Bạn: '+this.message);this.ws.send(JSON.stringify({type:'listen',state:'detect',text:this.message.trim()}));this.message='';},
  abort(){if(this.ws && this.connected)this.ws.send(JSON.stringify({type:'abort',reason:'user'}));},
  setAudio(blob,autoplay=false){this.audioName=blob.type==='audio/mpeg'?'robot-viet-test.mp3':'robot-viet-test.wav';if(this.audioUrl)URL.revokeObjectURL(this.audioUrl);this.audioUrl=URL.createObjectURL(blob);if(autoplay)this.$nextTick(()=>{this.$refs.player.play().catch(()=>this.log('Nhấn nút phát trên trình nghe để nghe âm thanh.'));});},
  async probe(body){return nckhRequest('/nckh/lab/'+this.agentId+'/probe','POST',body);},
  async testTts(){await this.guarded(async()=>{const r=await this.probe({kind:'tts',text:this.ttsText});const bytes=Uint8Array.from(atob(r.audio_base64),c=>c.charCodeAt(0));this.setAudio(new Blob([bytes],{type:r.mime}));this.log('TTS đạt: '+r.bytes+' byte âm thanh.');});},
  async refreshStatus(){try{this.runtime=await this.probe({kind:'status'});}catch(e){this.error=e.message;}},
  async startRecording(){
   try{
    if(!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia)throw new Error('Trình duyệt chỉ cho thu micro qua localhost hoặc HTTPS. Mở http://localhost:8002 trên máy server hoặc chọn tệp ghi âm.');
    this.mediaStream=await navigator.mediaDevices.getUserMedia({audio:true});
    if(!window.MediaRecorder){this.mediaStream.getTracks().forEach(t=>t.stop());throw new Error('Trình duyệt chưa hỗ trợ ghi âm. Hãy chọn tệp âm thanh.');}
    const mime=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
    const chunks=[];const recorder=new MediaRecorder(this.mediaStream,mime?{mimeType:mime}:{});this.recorder=recorder;
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onstop=()=>{clearTimeout(this.recordTimer);this.mediaStream.getTracks().forEach(t=>t.stop());this.recording=false;if(chunks.length){this.audioFile=new Blob(chunks,{type:recorder.mimeType});this.log('Đã thu micro. Nhấn Nhận dạng tiếng Việt để chạy PhoWhisper.');}};
    recorder.onerror=()=>{this.error='Thu âm thất bại. Hãy chọn một tệp thu âm.';this.stopRecording();};
    recorder.start();this.recording=true;this.recordTimer=setTimeout(()=>this.stopRecording(),30000);
   }catch(e){this.error=e.message;this.recording=false;}
  },
  stopRecording(){clearTimeout(this.recordTimer);if(this.recorder && this.recorder.state!=='inactive')this.recorder.stop();},
  chooseAudio(event){this.audioFile=event.target.files[0]||null;},
  async testAsr(){await this.guarded(async()=>{if(this.audioFile.size>8000000)throw new Error('Tệp phải nhỏ hơn 8 MB.');const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(this.audioFile);});const r=await this.probe({kind:'asr',audio_base64:base64});this.transcript=r.text;this.log(r.text?'Đã nhận dạng âm thanh.':'ASR không tìm được lời nói.');});},
  resetPlugin(){this.pluginArgs=JSON.stringify(plugins.find(p=>p.name===this.plugin).args,null,2);},
  async testPlugin(){await this.guarded(async()=>{const r=await this.probe({kind:'plugin',name:this.plugin,arguments:JSON.parse(this.pluginArgs)});this.pluginResult=JSON.stringify(r,null,2);});},
  async testMcp(name,args){await this.guarded(async()=>{this.mcpResult=JSON.stringify(await this.probe({kind:'mcp',name,arguments:args}),null,2);});},
  vnTime(s){return s?new Date(s).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'';},
  async loadReminders(){if(!this.reminderDevice)return;try{this.reminders=await nckhRequest('/nckh/reminders/'+encodeURIComponent(this.reminderDevice));}catch(e){this.error=e.message;}},
  async addReminder(){await this.guarded(async()=>{if(!this.reminderDate)throw new Error('Chọn thời điểm cần nhắc.');await nckhRequest('/nckh/reminders/'+encodeURIComponent(this.reminderDevice),'POST',{content:this.reminderText,due_at:this.reminderDate.toISOString(),repeat_type:this.repeat});await this.loadReminders();this.log('Đã lưu lời nhắc. Giữ thiết bị ảo online để nghe.');});},
  async cancelReminder(id){await this.guarded(async()=>{await nckhRequest('/nckh/reminders/'+encodeURIComponent(this.reminderDevice)+'/'+id,'DELETE');await this.loadReminders();});}
 }
};
</script>
<style scoped>
.lab-page{background:#f0f5ff;min-height:100vh;color:#263c5b}.lab-main{max-width:1180px;margin:auto;padding:24px}.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:20px 0}h1{font-size:28px}h3{margin-top:24px}.el-input,.el-textarea{margin:12px 0}.el-button{margin-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px;border-radius:10px;max-height:420px;overflow:auto}audio{display:block;margin:12px 0;width:100%}a{color:#3658cf}.el-tabs{background:white;padding:20px;border-radius:12px}.logs{background:#17233a;color:#dce8ff}.el-alert{margin:12px 0}
</style>
