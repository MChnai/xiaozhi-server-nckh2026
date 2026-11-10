package xiaozhi.modules.config.controller;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.springframework.jdbc.core.JdbcTemplate;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;
class NckhLabControllerTest {
    MockedStatic<MessageUtils> messages;
    AgentService agents;DeviceService devices;ConfigService configs;SysParamsService params;JdbcTemplate jdbc;NckhLabController controller;
    @AfterEach void release(){messages.close();}
    @BeforeEach void setup(){
        messages=mockStatic(MessageUtils.class);messages.when(()->MessageUtils.getMessage(anyInt())).thenReturn("Không được phép");
        agents=mock(AgentService.class);devices=mock(DeviceService.class);configs=mock(ConfigService.class);params=mock(SysParamsService.class);jdbc=mock(JdbcTemplate.class);
        controller=new NckhLabController(agents,devices,configs,params,jdbc);when(agents.checkAgentPermission("agent",7L)).thenReturn(true);
        AgentInfoVO agent=new AgentInfoVO();agent.setId("agent");when(agents.getAgentById("agent")).thenReturn(agent);
    }
    MockedStatic<SecurityUser> login(){var s=mockStatic(SecurityUser.class);s.when(SecurityUser::getUserId).thenReturn(7L);return s;}
    void ownDevice(){var d=new DeviceEntity();d.setMacAddress("02:00:00:00:00:01");d.setAgentId("agent");d.setUserId(7L);when(devices.getDeviceByMacAddress(d.getMacAddress())).thenReturn(d);}
    @Test void otherAgentCannotCreateVirtualDevice(){try(var s=login()){assertThrows(RenException.class,()->controller.virtualDevice("other"));verifyNoInteractions(devices);}}
    @Test void virtualMacStableAndNoServerSecret()throws Exception{
        when(params.getValue("server.websocket",true)).thenReturn("ws://192.168.1.2:8000/xiaozhi/v1/");when(devices.generateWebSocketToken(anyString(),anyString())).thenReturn("device-token");
        try(var s=login()){var a=controller.virtualDevice("agent").getData();var b=controller.virtualDevice("agent").getData();assertEquals(a.get("device_id"),b.get("device_id"));assertTrue(a.get("device_id").toString().startsWith("02:"));assertEquals(Set.of("device_id","client_id","websocket_url","token","simulated"),a.keySet());var dto=ArgumentCaptor.forClass(DeviceManualAddDTO.class);verify(devices,times(2)).manualAddDevice(eq(7L),dto.capture());assertEquals("nckh-simulator",dto.getValue().getBoard());}
    }
    @Test void summaryDoesNotExposeCloudCredentials(){when(configs.getAgentConfigForLab("agent")).thenReturn(Map.of("selected_module",Map.of("TTS","TTS_NCKH"),"LLM",Map.of("api_key","private")));try(var s=login()){assertEquals(Set.of("selected_module"),controller.summary("agent").getData().keySet());}}
    @Test void otherUsersRemindersCannotBeReadOrCancelled(){var d=new DeviceEntity();d.setUserId(8L);d.setAgentId("agent");when(devices.getDeviceByMacAddress("mac")).thenReturn(d);try(var s=login()){assertThrows(RenException.class,()->controller.reminders("mac"));assertThrows(RenException.class,()->controller.cancel("mac","id"));verifyNoInteractions(jdbc);}}
    @Test void invalidDateAndRepeatDoNotWrite(){ownDevice();try(var s=login()){assertNotEquals(0,controller.addReminder("02:00:00:00:00:01",Map.of("content","test","due_at","oops")).getCode());assertNotEquals(0,controller.addReminder("02:00:00:00:00:01",Map.of("content","test","due_at","2099-01-01T08:00:00+07:00","repeat_type","monthly")).getCode());verifyNoInteractions(jdbc);}}
    @Test void vietnameseTimeStoredAsUtc(){ownDevice();try(var s=login()){assertEquals(0,controller.addReminder("02:00:00:00:00:01",Map.of("content","Uống nước","due_at","2099-01-01T08:30:00+07:00","repeat_type","daily")).getCode());verify(jdbc).update(contains("INSERT INTO ai_reminder_nckh"),anyString(),eq("02:00:00:00:00:01"),eq("Uống nước"),eq(LocalDateTime.of(2099,1,1,1,30)),eq("daily"));}}
    @Test void cancellationIsDeviceScopedAndHonest(){ownDevice();try(var s=login()){assertNotEquals(0,controller.cancel("02:00:00:00:00:01","x' OR 1=1 --").getCode());verify(jdbc).update(contains("device_id=?"),eq("x' OR 1=1 --"),eq("02:00:00:00:00:01"));}}
    @Test void databaseTimesReturnUtcOffset(){ownDevice();Map<String,Object> row=new HashMap<>();row.put("due_at",Timestamp.valueOf("2099-01-01 01:30:00"));when(jdbc.queryForList(anyString(),eq("02:00:00:00:00:01"))).thenReturn(new ArrayList<>(List.of(row)));try(var s=login()){assertEquals("2099-01-01T01:30Z",controller.reminders("02:00:00:00:00:01").getData().get(0).get("due_at"));}}
}
