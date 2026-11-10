"""Real MCP state/dispatcher with a simulated peer; no physical GPIO."""
import asyncio
import importlib
import json
import re
import sys
from types import SimpleNamespace
import pytest
from core.auth import AuthManager
from core.utils.robot_tools import validate_robot_arguments

def test_device_token_is_bound_to_mac_client_secret_and_expiry(monkeypatch):
    import core.auth as module
    monkeypatch.setattr(module.time,'time',lambda:1800000000);auth=AuthManager('secret-one',expire_seconds=60)
    token=auth.generate_token('client','02:00:00:00:00:01');assert auth.verify_token(token,'client','02:00:00:00:00:01')
    assert not auth.verify_token(token,'other','02:00:00:00:00:01');assert not auth.verify_token(token,'client','02:00:00:00:00:02')
    assert not AuthManager('secret-two').verify_token(token,'client','02:00:00:00:00:01')
    monkeypatch.setattr(module.time,'time',lambda:1800000061);assert not auth.verify_token(token,'client','02:00:00:00:00:01')
@pytest.mark.parametrize('name,args',[
 ('self.robot.set_servo',{'part':'neck','angle':181}),('self.robot.set_servo',{'part':'neck','angle':True}),
 ('self.robot.move',{'direction':'forward','duration_ms':2001}),('self.robot.wave_hand',{'which':'both','times':11}),
 ('self.led.set_mode',{'led':'nose','mode':'on'}),('self.robot.get_distance',{'extra':1})])
def test_robot_arguments_rejected_before_network(name,args):
    with pytest.raises(ValueError):validate_robot_arguments(name,args)
def load_mcp(monkeypatch,lightweight_logger):
    monkeypatch.setitem(sys.modules,'core.utils.util',SimpleNamespace(sanitize_tool_name=lambda s:re.sub(r'[^a-zA-Z0-9_-]','_',s),get_vision_url=lambda cfg:'http://vision'))
    monkeypatch.setitem(sys.modules,'core.utils.auth',SimpleNamespace(AuthToken=None))
    for key in list(sys.modules):
        if key.startswith('core.providers.tools.device_mcp'):monkeypatch.delitem(sys.modules,key)
    return importlib.import_module('core.providers.tools.device_mcp')
def test_mcp_handshake_names_and_response_correlate(monkeypatch,lightweight_logger):
    module=load_mcp(monkeypatch,lightweight_logger)
    async def run():
        client=module.MCPClient();sent=[];conn=SimpleNamespace(features={'mcp':True},func_handler=None)
        async def send(raw):
            payload=json.loads(raw)['payload'];sent.append(payload)
            await module.handle_mcp_message(conn,client,{'jsonrpc':'2.0','id':payload['id'],'result':{'content':[{'type':'text','text':'{"distance_cm":42}'}],'isError':False}})
        conn.websocket=SimpleNamespace(send=send)
        await module.handle_mcp_message(conn,client,{'id':2,'result':{'tools':[{'name':'self.robot.get_distance','description':'distance','inputSchema':{'type':'object','properties':{}}}]}})
        assert await client.is_ready();result=await module.call_mcp_tool(conn,client,'self_robot_get_distance','{}',timeout=1)
        assert json.loads(result)['distance_cm']==42;assert sent[0]['id']==3 and sent[0]['params']['name']=='self.robot.get_distance';assert not client.call_results
    asyncio.run(run())
def test_mcp_timeout_and_cancel_always_cleanup_future(monkeypatch,lightweight_logger):
    module=load_mcp(monkeypatch,lightweight_logger)
    async def run():
        client=module.MCPClient();await client.add_tool({'name':'self.robot.get_distance','description':'distance','inputSchema':{}});await client.set_ready(True)
        async def send(raw):pass
        conn=SimpleNamespace(features={'mcp':True},websocket=SimpleNamespace(send=send))
        with pytest.raises(TimeoutError):await module.call_mcp_tool(conn,client,'self_robot_get_distance','{}',timeout=.01)
        assert not client.call_results
        task=asyncio.create_task(module.call_mcp_tool(conn,client,'self_robot_get_distance','{}',timeout=10));await asyncio.sleep(.01);task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert not client.call_results
        with pytest.raises(ValueError):await module.call_mcp_tool(conn,client,'self_robot_get_distance','{invalid}')
        assert not client.call_results
    asyncio.run(run())
