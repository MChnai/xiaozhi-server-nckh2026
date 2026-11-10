package xiaozhi.modules.config.controller;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.time.format.DateTimeParseException;
import java.sql.Timestamp;
import java.util.*;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;

/** Authenticated server workbench; server/model secrets never leave this boundary. */
@RestController
@RequestMapping("/nckh")
@RequiresPermissions("sys:role:normal")
public class NckhLabController {
    private final AgentService agents;
    private final DeviceService devices;
    private final ConfigService configs;
    private final SysParamsService params;
    private final JdbcTemplate jdbc;
    private final HttpClient http=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    @Value("${nckh.voice-url:http://voice:8003}") private String voiceUrl;
    public NckhLabController(AgentService agents,DeviceService devices,ConfigService configs,SysParamsService params,JdbcTemplate jdbc){this.agents=agents;this.devices=devices;this.configs=configs;this.params=params;this.jdbc=jdbc;}
    private AgentEntity requireAgent(String id){
        if(!agents.checkAgentPermission(id,SecurityUser.getUserId()))throw new RenException(ErrorCode.NO_PERMISSION);
        return agents.getAgentById(id);
    }
    private DeviceEntity requireDevice(String mac){
        DeviceEntity d=devices.getDeviceByMacAddress(mac);
        if(d==null || !SecurityUser.getUserId().equals(d.getUserId()))throw new RenException(ErrorCode.NO_PERMISSION);
        requireAgent(d.getAgentId());return d;
    }
    private String virtualMac(String id)throws Exception{
        byte[] hash=MessageDigest.getInstance("SHA-256").digest((SecurityUser.getUserId()+":"+id).getBytes(StandardCharsets.UTF_8));
        StringBuilder mac=new StringBuilder("02");for(int i=0;i<5;i++)mac.append(String.format(":%02X",hash[i]&255));return mac.toString();
    }
    @PostMapping("/lab/{agentId}/device")
    public Result<Map<String,Object>> virtualDevice(@PathVariable String agentId)throws Exception{
        requireAgent(agentId);String mac=virtualMac(agentId);DeviceEntity d=devices.getDeviceByMacAddress(mac);
        if(d==null){DeviceManualAddDTO dto=new DeviceManualAddDTO();dto.setAgentId(agentId);dto.setMacAddress(mac);dto.setBoard("nckh-simulator");dto.setAppVersion("3.0.0");devices.manualAddDevice(SecurityUser.getUserId(),dto);}
        else if(!SecurityUser.getUserId().equals(d.getUserId()) || !agentId.equals(d.getAgentId()) || !"nckh-simulator".equals(d.getBoard()))throw new RenException(ErrorCode.NO_PERMISSION);
        String client=UUID.randomUUID().toString();String url=params.getValue("server.websocket",true);
        if(url==null || url.equals("null"))return new Result<Map<String,Object>>().error("Chưa cấu hình server.websocket");
        Map<String,Object> result=new LinkedHashMap<>();result.put("device_id",mac);result.put("client_id",client);result.put("websocket_url",url.split(";")[0]);result.put("token",devices.generateWebSocketToken(client,mac));result.put("simulated",true);
        return new Result<Map<String,Object>>().ok(result);
    }
    @GetMapping("/lab/{agentId}/config")
    public Result<Map<String,Object>> summary(@PathVariable String agentId){requireAgent(agentId);Map<String,Object> cfg=configs.getAgentConfigForLab(agentId);return new Result<Map<String,Object>>().ok(Map.of("selected_module",cfg.get("selected_module")));}
    @PostMapping("/lab/{agentId}/probe")
    public Result<Object> probe(@PathVariable String agentId,@RequestBody Map<String,Object> input)throws Exception{
        requireAgent(agentId);
        if(JsonUtils.toJsonString(input).length()>12_000_000)return new Result<Object>().error("Dữ liệu kiểm thử quá lớn");
        Map<String,Object> body=new HashMap<>(input);body.put("config",configs.getAgentConfigForLab(agentId));body.put("device_id",virtualMac(agentId));
        HttpRequest request=HttpRequest.newBuilder(URI.create(voiceUrl+"/_nckh/probe")).timeout(Duration.ofSeconds(180)).header("Content-Type","application/json").header("Authorization","Bearer "+params.getValue("server.secret",false)).POST(HttpRequest.BodyPublishers.ofString(JsonUtils.toJsonString(body))).build();
        try{
            HttpResponse<String> response=http.send(request,HttpResponse.BodyHandlers.ofString());
            if(response.statusCode()!=200)return new Result<Object>().error("Voice server không xử lý được yêu cầu (HTTP "+response.statusCode()+")");
            Map<String,Object> data=JsonUtils.parseMap(response.body());
            if(Boolean.FALSE.equals(data.get("ok")))return new Result<Object>().error(String.valueOf(data.get("error")));
            return new Result<Object>().ok(data);
        }catch(java.io.IOException exc){return new Result<Object>().error("Không kết nối được voice server. Kiểm tra log và container voice.");}
    }
    @GetMapping("/reminders/{deviceId}")
    public Result<List<Map<String,Object>>> reminders(@PathVariable String deviceId){
        requireDevice(deviceId);List<Map<String,Object>> rows=jdbc.queryForList("SELECT id,content,due_at,repeat_type,status,queued_at FROM ai_reminder_nckh WHERE device_id=? ORDER BY due_at DESC LIMIT 100",deviceId);
        for(Map<String,Object> row:rows)for(String k:List.of("due_at","queued_at")){Object value=row.get(k);if(value instanceof Timestamp t)row.put(k,t.toLocalDateTime().atOffset(ZoneOffset.UTC).toString());else if(value instanceof LocalDateTime t)row.put(k,t.atOffset(ZoneOffset.UTC).toString());}
        return new Result<List<Map<String,Object>>>().ok(rows);
    }
    @PostMapping("/reminders/{deviceId}")
    public Result<String> addReminder(@PathVariable String deviceId,@RequestBody Map<String,String> data){
        requireDevice(deviceId);String text=data.getOrDefault("content","").trim();String repeat=data.getOrDefault("repeat_type","none");
        if(text.isEmpty() || text.length()>500 || !List.of("none","daily","weekly").contains(repeat))return new Result<String>().error("Nội dung phải từ 1–500 ký tự và kiểu lặp hợp lệ");
        Instant due;
        try{String value=data.getOrDefault("due_at","");try{due=OffsetDateTime.parse(value).toInstant();}catch(DateTimeParseException e){due=LocalDateTime.parse(value).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).toInstant();}}
        catch(DateTimeParseException e){return new Result<String>().error("Ngày giờ không hợp lệ");}
        if(!due.isAfter(Instant.now()))return new Result<String>().error("Thời điểm nhắc phải ở tương lai");
        String id=UUID.randomUUID().toString().replace("-","");jdbc.update("INSERT INTO ai_reminder_nckh(id,device_id,content,due_at,repeat_type) VALUES(?,?,?,?,?)",id,deviceId,text,LocalDateTime.ofInstant(due,ZoneOffset.UTC),repeat);return new Result<String>().ok(id);
    }
    @DeleteMapping("/reminders/{deviceId}/{id}")
    public Result<Void> cancel(@PathVariable String deviceId,@PathVariable String id){requireDevice(deviceId);int count=jdbc.update("UPDATE ai_reminder_nckh SET status='cancelled' WHERE id=? AND device_id=? AND status IN ('pending','sending')",id,deviceId);return count==0?new Result<Void>().error("Không có lời nhắc đang chờ để hủy"):new Result<Void>();}
}
