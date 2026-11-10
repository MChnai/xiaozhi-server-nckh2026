import asyncio
import base64
import importlib
import importlib.util
import io
import json
import sys
import types
import wave
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import pytest
from core.utils.lunar_vn import solar_to_lunar
from core.reminder_scheduler import parse_due
ROOT=Path(__file__).resolve().parents[3]
@pytest.mark.parametrize('solar,expected',[
 ('1968-01-29',(1,1,1968,False)),('2024-02-10',(1,1,2024,False)),
 ('2025-01-29',(1,1,2025,False)),('2026-02-17',(1,1,2026,False)),
 ('2023-03-22',(1,2,2023,True)),('2023-04-19',(29,2,2023,True)),('2027-02-06',(1,1,2027,False))])
def test_vietnamese_lunar_tet_and_leap_month(solar,expected):
    r=solar_to_lunar(solar);assert tuple(r[k] for k in ('day','month','year','leap_month'))==expected

def test_lunar_invalid_and_unsupported_dates():
    for s in ('2026-02-30','1899-01-01','2100-01-01'):
        with pytest.raises(ValueError):solar_to_lunar(s)

def test_iso_z_on_docker_python310():
    assert parse_due('2027-02-06T00:30:00Z',now=datetime(2026,1,1))==datetime(2027,2,6,0,30)

def test_gold_price_units_and_bad_data(lightweight_logger):
    m=importlib.import_module('plugins_func.functions.get_gold_price')
    def payload(code,buy=100):return {'success':True,'current_time':'2026-11-06','data':[{'type_code':code,'buy':buy,'sell':110,'update_time':1}]}
    assert m.parse_prices(payload('SJL1L10'),'SJL1L10')['prices'][0]['unit']=='VND/lượng'
    assert m.parse_prices(payload('XAUUSD'),'XAUUSD')['prices'][0]['unit']=='USD/oz'
    for buy in (0,-1,True,float('nan'),'123'):
        with pytest.raises(ValueError):m.parse_prices(payload('SJL1L10',buy),'SJL1L10')
    with pytest.raises(ValueError):m.parse_prices(payload('XAUUSD'),'SJL1L10')

def test_translation_requires_key_and_rejects_input(lightweight_logger,monkeypatch):
    m=importlib.import_module('plugins_func.functions.translate_text');monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    assert 'Chưa cấu hình' in asyncio.run(m.translate_text('Xin chào')).result
    assert '1–2000' in asyncio.run(m.translate_text('x'*2001)).result
    assert 'vi-en' in asyncio.run(m.translate_text('Xin chào','xx')).result

def test_translation_json_contract(lightweight_logger,monkeypatch):
    m=importlib.import_module('plugins_func.functions.translate_text');monkeypatch.setenv('DEEPSEEK_API_KEY','unit-key')
    response=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'translation':'Hello','english_ipa':'/həˈləʊ/','explanation_vi':'Lời chào'})))])
    create=Mock(return_value=response);client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    class Fake:
        def __init__(self,**kw):pass
        def __enter__(self):return client
        def __exit__(self,*a):pass
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(OpenAI=Fake))
    result=m.translate('Xin chào','vi-en');assert result['translation']=='Hello' and result['direction']=='vi-en'
    assert create.call_args.kwargs['response_format']=={'type':'json_object'}
    assert create.call_args.kwargs['messages'][1]['content']=='Xin chào'

def test_edge_discards_partial_audio_and_falls_back_in_vietnamese(monkeypatch):
    from core.utils.edge_audio import synthesize_edge
    calls=[]
    class Fake:
        def __init__(self,text,voice,**kw):self.voice=voice;calls.append(voice)
        async def stream(self):
            if self.voice=='vi-VN-HoaiMyNeural':
                yield {'type':'audio','data':b'partial'}
                raise RuntimeError('upstream interrupted')
            yield {'type':'audio','data':b'complete'}
    monkeypatch.setitem(sys.modules,'edge_tts',SimpleNamespace(Communicate=Fake))
    assert asyncio.run(synthesize_edge('xin chao','vi-VN-HoaiMyNeural',attempts=1))==b'complete'
    assert calls==['vi-VN-HoaiMyNeural','vi-VN-NamMinhNeural']

def test_edge_cancellation_is_not_retried(monkeypatch):
    from core.utils.edge_audio import synthesize_edge
    class Fake:
        def __init__(self,*a,**kw):pass
        async def stream(self):
            raise asyncio.CancelledError()
            yield
    monkeypatch.setitem(sys.modules,'edge_tts',SimpleNamespace(Communicate=Fake))
    with pytest.raises(asyncio.CancelledError):asyncio.run(synthesize_edge('hi','vi-VN-HoaiMyNeural'))

def valid_wav():
    output=io.BytesIO()
    with wave.open(output,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*1600)
    return output.getvalue()

def test_offline_tts_auth_and_valid_wav(monkeypatch):
    import httpx
    from core.utils.offline_audio import synthesize_local
    monkeypatch.setenv('NCKH_SERVER_SECRET','unit-secret');original=httpx.AsyncClient
    def handler(request):
        assert request.headers['Authorization']=='Bearer unit-secret';assert json.loads(request.content)['text']=='Xin chào'
        return httpx.Response(200,content=valid_wav())
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert asyncio.run(synthesize_local('http://piper:5100','Xin chào','vi'))[:4]==b'RIFF'

def test_offline_tts_rejects_html_disguised_as_audio(monkeypatch):
    import httpx
    from core.utils.offline_audio import synthesize_local
    monkeypatch.setenv('NCKH_SERVER_SECRET','unit-secret');original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'<html>'+b'x'*100)),**kw))
    with pytest.raises(wave.Error):asyncio.run(synthesize_local('http://piper:5100','Xin chào','vi'))

def test_music_exact_match_accents_and_no_traversal(lightweight_logger,tmp_path):
    m=importlib.import_module('plugins_func.functions.play_music');song=tmp_path/'Quê-hương.mp3';song.write_bytes(b'audio')
    assert m.find_song(tmp_path,'que huong')==song
    assert m.find_song(tmp_path,'../../etc/passwd') is None
    assert m.find_song(tmp_path,'random')==song

def handler(monkeypatch,lightweight_logger):
    fake=types.ModuleType('config.config_loader');fake.merge_configs=lambda a,b:{**a,**b}
    monkeypatch.setitem(sys.modules,'config.config_loader',fake);sys.modules.pop('core.api.nckh_handler',None)
    cls=importlib.import_module('core.api.nckh_handler').NckhHandler
    return cls({'manager-api':{'secret':'unit-secret'},'server':{}},SimpleNamespace(reminder_service=SimpleNamespace(connections={})))

def test_lab_requires_server_secret(monkeypatch,lightweight_logger):
    h=handler(monkeypatch,lightweight_logger);r=asyncio.run(h.probe(SimpleNamespace(headers={},json=AsyncMock())));assert r.status==401

def test_lab_tts_uses_selected_agent_and_encodes_audio(monkeypatch,lightweight_logger):
    h=handler(monkeypatch,lightweight_logger);tts=SimpleNamespace(text_to_speak=AsyncMock(return_value=valid_wav()))
    def initialize(cfg):
        assert cfg['selected_module']['TTS']=='Piper' and cfg['plugins']=={'play_music':{}};return tts
    monkeypatch.setitem(sys.modules,'core.utils.modules_initialize',SimpleNamespace(initialize_tts=initialize))
    data={'kind':'tts','text':'Xin chào','config':{'selected_module':{'TTS':'Piper'},'plugins':{'play_music':'{}'}}}
    req=SimpleNamespace(headers={'Authorization':'Bearer unit-secret'},json=AsyncMock(return_value=data));r=json.loads(asyncio.run(h.probe(req)).text)
    assert r['ok'] and r['mime']=='audio/wav';assert base64.b64decode(r['audio_base64'])==valid_wav()

def test_lab_does_not_expose_provider_error_credentials(monkeypatch,lightweight_logger):
    h=handler(monkeypatch,lightweight_logger)
    def fail(cfg):raise RuntimeError('secret-api-key https://private?token=123')
    monkeypatch.setitem(sys.modules,'core.utils.modules_initialize',SimpleNamespace(initialize_tts=fail))
    req=SimpleNamespace(headers={'Authorization':'Bearer unit-secret'},json=AsyncMock(return_value={'kind':'tts','text':'x'}));r=asyncio.run(h.probe(req))
    assert 'secret-api-key' not in r.text and 'token=123' not in r.text

def test_cli_mcp_validates_hardware_bounds():
    spec=importlib.util.spec_from_file_location('nckh_cli',ROOT/'deploy/nckh/robot_client.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    result=m.mcp_reply({'id':3,'method':'tools/call','params':{'name':'self.robot.get_distance','arguments':{}}},75)
    assert json.loads(result['result']['content'][0]['text'])['distance_cm']==75
    bad=m.mcp_reply({'id':4,'method':'tools/call','params':{'name':'self.robot.set_servo','arguments':{'part':'neck','angle':181}}});assert bad['error']['code']==-32602
    assert m.mcp_reply({'method':'notifications/initialized'}) is None
