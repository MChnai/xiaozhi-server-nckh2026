package xiaozhi.modules.device.service.impl;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.service.OtaService;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.service.SysUserUtilService;
class DeviceEnrollmentPermissionTest {
    MockedStatic<MessageUtils> messages;
    AgentDao agents;DeviceDao devices;RedisUtils redis;DeviceServiceImpl service;
    @AfterEach void release(){messages.close();}
    @BeforeEach void setup(){messages=mockStatic(MessageUtils.class);messages.when(()->MessageUtils.getMessage(anyInt())).thenReturn("Không được phép");agents=mock(AgentDao.class);devices=mock(DeviceDao.class);redis=mock(RedisUtils.class);service=new DeviceServiceImpl(devices,mock(SysUserUtilService.class),mock(SysParamsService.class),redis,mock(OtaService.class),mock(DeviceAddressBookService.class),agents){{this.baseDao=devices;}};}
    DeviceManualAddDTO input(String mac){var d=new DeviceManualAddDTO();d.setAgentId("agent");d.setMacAddress(mac);d.setBoard("nckh-simulator");d.setAppVersion("2.0.0");return d;}
    void owner(long id){var a=new AgentEntity();a.setId("agent");a.setUserId(id);when(agents.selectById("agent")).thenReturn(a);}
    @Test void otherUsersAgentCannotReceiveDevice(){owner(8L);assertThrows(RenException.class,()->service.manualAddDevice(7L,input("02:AB:CD:EF:12:34")));verifyNoInteractions(devices,redis);}
    @Test void missingAgentCannotReceiveDevice(){assertThrows(RenException.class,()->service.manualAddDevice(7L,input("02:AB:CD:EF:12:34")));verifyNoInteractions(devices,redis);}
    @Test void invalidMacDoesNotTouchStorage(){owner(7L);assertThrows(RenException.class,()->service.manualAddDevice(7L,input("not-a-mac")));verifyNoInteractions(devices,redis);}
    @Test void deviceUsesCanonicalMacAndCurrentOwner(){owner(7L);service.manualAddDevice(7L,input("02:ab:cd:ef:12:34"));var capture=ArgumentCaptor.forClass(DeviceEntity.class);verify(devices).insert(capture.capture());assertEquals("02:AB:CD:EF:12:34",capture.getValue().getMacAddress());assertEquals(7L,capture.getValue().getUserId());assertEquals("agent",capture.getValue().getAgentId());}
}
