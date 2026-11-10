import asyncio
import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest


def test_demo_never_constructs_a_cloud_client(monkeypatch, lightweight_logger):
    monkeypatch.setenv("NCKH_LLM_MODE", "demo")
    from core.providers.llm.nckh.nckh import LLMProvider
    llm=LLMProvider({})
    assert llm.delegate is None
    result=list(llm.response_with_functions("s",[],[]))
    assert "kiểm tra kết nối" in result[0][0] and result[0][1] is None


def test_deepseek_missing_key_fails_clearly(monkeypatch, lightweight_logger):
    monkeypatch.setenv("NCKH_LLM_MODE", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY",raising=False)
    from core.providers.llm.nckh.nckh import LLMProvider
    with pytest.raises(ValueError,match="DEEPSEEK_API_KEY"):
        LLMProvider({})


def test_weather_without_key_does_not_make_http_request(monkeypatch,lightweight_logger):
    monkeypatch.delenv("OPENWEATHER_API_KEY",raising=False)
    from plugins_func.functions.get_weather_vn import get_weather_vn
    result=asyncio.run(get_weather_vn("Da Lat,VN"))
    assert "OPENWEATHER_API_KEY" in result.result


def test_news_parses_vietnamese_and_limits_results(lightweight_logger):
    from plugins_func.functions.get_news_from_vnexpress import parse_feed
    xml="""<rss><channel><item><title>Đà Lạt</title><description>&lt;p&gt;Trời đẹp&lt;/p&gt;</description><link>https://vnexpress.net/x</link></item><item><title>Hai</title></item></channel></rss>""".encode()
    rows=parse_feed(xml,1)
    assert len(rows)==1 and rows[0]['title']=='Đà Lạt'
    assert rows[0]['description']=='Trời đẹp'


def test_plugin_contract_injects_connection_only_where_required(lightweight_logger):
    import inspect
    from plugins_func.register import all_function_registry, ToolType
    for name in ['add_reminder','list_reminders','delete_reminder','get_weather_vn','get_news_from_vnexpress']:
        importlib.import_module('plugins_func.functions.'+name)
        item=all_function_registry[name]
        params=inspect.signature(item.func).parameters
        assert ('conn' in params) == (item.type == ToolType.SYSTEM_CTL)


def test_weather_result_is_string_for_openai_tool_history(monkeypatch,lightweight_logger):
    import plugins_func.functions.get_weather_vn as mod
    monkeypatch.setenv('OPENWEATHER_API_KEY','test-secret')
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,url,params):
            assert params['lang']=='vi' and params['units']=='metric'
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'name':'Dalat','main':{'temp':20,'humidity':60},'weather':[{'description':'mây'}],'dt':1})
    monkeypatch.setattr(mod.httpx,'AsyncClient',Client)
    result=asyncio.run(mod.get_weather_vn('Da Lat,VN'))
    assert isinstance(result.result,str)
    assert json.loads(result.result)['temperature_c']==20


def test_phowhisper_caches_model_and_uses_pcm16(monkeypatch,tmp_path):
    # Exercise provider behavior with a fake inference backend. No real accuracy claim.
    base=types.ModuleType('core.providers.asr.base')
    base.ASRProviderBase=type('ASRProviderBase',(),{})
    monkeypatch.setitem(sys.modules,'core.providers.asr.base',base)
    calls=[]
    class Model:
        def __init__(self,*a,**kw):calls.append(('load',kw))
        def transcribe(self,audio,**kw):
            calls.append(('transcribe',kw))
            assert audio.dtype==np.float32 and np.max(audio)<=1
            return iter([SimpleNamespace(text=' Xin chào ',no_speech_prob=.1),SimpleNamespace(text='rác',no_speech_prob=.9)]),None
    backend=types.ModuleType('faster_whisper');backend.WhisperModel=Model
    monkeypatch.setitem(sys.modules,'faster_whisper',backend)
    mod=importlib.import_module('core.providers.asr.pho_whisper_ct2')
    (tmp_path/'model.bin').touch()
    cfg={'model_path':str(tmp_path),'output_dir':str(tmp_path)}
    a=mod.ASRProvider(cfg);b=mod.ASRProvider(cfg)
    assert a.model is b.model
    assert len([x for x in calls if x[0]=='load'])==1
    pcm=np.full(3200,1000,dtype='<i2').tobytes()
    text,_=asyncio.run(a.speech_to_text([], 's',SimpleNamespace(pcm_bytes=pcm,file_path=None)))
    assert text=='Xin chào'
    opts=calls[-1][1]
    assert opts['language']=='vi' and opts['condition_on_previous_text'] is False
    assert asyncio.run(a.speech_to_text([],'s',None))==('',None)
    assert a._transcribe(bytes(6400))==''
    with pytest.raises(ValueError):a._transcribe(b'x')
