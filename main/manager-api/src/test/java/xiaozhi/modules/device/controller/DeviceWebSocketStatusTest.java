package xiaozhi.modules.device.controller;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.springframework.test.util.ReflectionTestUtils;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;

class DeviceWebSocketStatusTest {
    @Test void onlyOwnedDevicesAreForwardedAndSecretStaysInternal() throws Exception {
        DeviceService devices=mock(DeviceService.class);SysParamsService params=mock(SysParamsService.class);
        DeviceController controller=new DeviceController(devices,mock(DeviceAddressBookService.class),mock(RedisUtils.class),params);
        ReflectionTestUtils.setField(controller,"useWebsocketStatus",true);
        var owned=new UserShowDeviceListVO();owned.setMacAddress("AA:00:00:00:00:01");
        when(devices.getUserDeviceList(7L,"agent")).thenReturn(List.of(owned));when(params.getValue("server.secret",false)).thenReturn("internal-only");
        AtomicReference<String> body=new AtomicReference<>(),auth=new AtomicReference<>();
        var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/_nckh/online",exchange->{
            body.set(new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8));
            auth.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] result="{\"AA:00:00:00:00:01\":{\"isAlive\":true}}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200,result.length);exchange.getResponseBody().write(result);exchange.close();
        });server.start();
        ReflectionTestUtils.setField(controller,"voiceUrl","http://127.0.0.1:"+server.getAddress().getPort());
        try(MockedStatic<SecurityUser> login=mockStatic(SecurityUser.class)){
            login.when(SecurityUser::getUserId).thenReturn(7L);
            var result=controller.forwardToMqttGateway("agent","{\"device_ids\":[\"OTHER\"]}");
            assertEquals(0,result.getCode());assertTrue(body.get().contains(owned.getMacAddress()));assertFalse(body.get().contains("OTHER"));
            assertEquals("Bearer internal-only",auth.get());assertFalse(result.getData().contains("internal-only"));
            verify(devices,never()).getDeviceOnlineData(anyString());
        }finally{server.stop(0);}
    }
    @Test void emptyOwnedListDoesNotQueryVoice() {
        DeviceService devices=mock(DeviceService.class);var params=mock(SysParamsService.class);
        var controller=new DeviceController(devices,mock(DeviceAddressBookService.class),mock(RedisUtils.class),params);
        ReflectionTestUtils.setField(controller,"useWebsocketStatus",true);
        when(devices.getUserDeviceList(7L,"other-agent")).thenReturn(List.of());
        try(MockedStatic<SecurityUser> login=mockStatic(SecurityUser.class)){
            login.when(SecurityUser::getUserId).thenReturn(7L);
            assertEquals("{}",controller.forwardToMqttGateway("other-agent","{}").getData());verifyNoInteractions(params);
        }
    }
    @Test void voiceUnavailableDoesNotPretendDevicesAreOffline() {
        DeviceService devices=mock(DeviceService.class);var params=mock(SysParamsService.class);
        var controller=new DeviceController(devices,mock(DeviceAddressBookService.class),mock(RedisUtils.class),params);
        ReflectionTestUtils.setField(controller,"useWebsocketStatus",true);ReflectionTestUtils.setField(controller,"voiceUrl","http://127.0.0.1:1");
        var d=new UserShowDeviceListVO();d.setMacAddress("AA:00:00:00:00:01");when(devices.getUserDeviceList(7L,"agent")).thenReturn(List.of(d));
        when(params.getValue("server.secret",false)).thenReturn("secret");
        try(MockedStatic<SecurityUser> login=mockStatic(SecurityUser.class)){
            login.when(SecurityUser::getUserId).thenReturn(7L);
            assertNotEquals(0,controller.forwardToMqttGateway("agent","{}").getCode());
        }
    }
}
