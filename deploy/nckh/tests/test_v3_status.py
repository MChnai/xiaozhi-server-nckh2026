import asyncio
import json
import threading
from types import SimpleNamespace
import pytest

class Request:
    def __init__(self,body,auth='Bearer internal-secret'):
        self.headers={'Authorization':auth};self.body=body
    async def json(self):return self.body

def handler():
    from core.api.nckh_handler import NckhHandler
    ready=threading.Event();ready.set()
    own=SimpleNamespace(need_bind=False,bind_completed_event=ready,stop_event=threading.Event())
    server=SimpleNamespace(ready=ready,reminder_service=SimpleNamespace(connections={'AA:00:00:00:00:01':own,'BB:00:00:00:00:02':own}))
    return NckhHandler({'server':{'auth_key':'internal-secret'},'manager-api':{'secret':'internal-secret'}},server)

def test_online_is_authenticated_and_only_returns_requested_devices():
    async def run():
        api=handler()
        denied=await api.online(Request({'device_ids':['BB:00:00:00:00:02']},auth='Bearer wrong'))
        assert denied.status==401
        response=await api.online(Request({'device_ids':['aa:00:00:00:00:01','CC:00:00:00:00:03']}))
        body=json.loads(response.text)
        assert set(body)=={'AA:00:00:00:00:01','CC:00:00:00:00:03'}
        assert body['AA:00:00:00:00:01']['isAlive'] is True
        assert body['CC:00:00:00:00:03']['isAlive'] is False
    asyncio.run(run())

@pytest.mark.parametrize('body',[[],{}, {'device_ids':'all'}, {'device_ids':[None]}, {'device_ids':['x']*1001}])
def test_online_rejects_invalid_queries(body):
    assert asyncio.run(handler().online(Request(body))).status==400

def test_status_exposes_booleans_without_keys(monkeypatch):
    monkeypatch.setenv('NCKH_LLM_MODE','demo');monkeypatch.setenv('DEEPSEEK_API_KEY','secret-api-key')
    monkeypatch.setenv('OPENWEATHER_API_KEY','secret-weather-key')
    body={'kind':'status','config':{'selected_module':{'LLM':'LLM_NCKH'},'LLM':{'LLM_NCKH':{'api_key':'private-model-key'}}},'device_id':'missing'}
    response=asyncio.run(handler().probe(Request(body)))
    assert response.status==200
    data=json.loads(response.text)
    assert data['mode']=='demo' and data['deepseek_configured'] and data['weather_configured']
    assert data['simulator_online'] is False
    assert not any(value in response.text for value in ['secret-api-key','secret-weather-key','private-model-key','internal-secret'])
