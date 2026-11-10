import asyncio
import json
from unittest.mock import AsyncMock
import queue
import threading
from datetime import datetime
from types import SimpleNamespace
import pytest
from core.reminder_scheduler import parse_due, next_due, ReminderStore, ReminderService


def test_naive_user_time_is_vietnam_not_host_timezone():
    assert parse_due("2027-01-01T07:30:00", now=datetime(2026,1,1)) == datetime(2027,1,1,0,30)
    assert parse_due("2027-01-01T07:30:00+07:00", now=datetime(2026,1,1)) == datetime(2027,1,1,0,30)


def test_reject_past_due_date():
    with pytest.raises(ValueError):
        parse_due("2026-01-01T00:00:00Z", now=datetime(2026,1,2))

@pytest.mark.parametrize("repeat,now,expected", [
    ("none", datetime(2027,1,1), None),
    ("daily", datetime(2027,1,3,0,1), datetime(2027,1,4)),
    ("weekly", datetime(2027,1,15), datetime(2027,1,22))])
def test_repeat_skips_missed_occurrences(repeat, now, expected):
    assert next_due(datetime(2027,1,1), repeat, now) == expected


def test_database_queries_are_scoped_and_parameterized():
    store = ReminderStore()
    calls=[]
    store._query=lambda *a,**kw: calls.append((a,kw)) or 1
    store.cancel("device-A", "x' OR 1=1 --")
    sql,args = calls[-1][0]
    assert "device_id=%s" in sql
    assert args == ("x' OR 1=1 --", "device-A")
    assert "OR 1=1" not in sql


def test_store_rejects_invalid_inputs_before_connecting():
    store=ReminderStore()
    for device,content,repeat in [("","hi","none"),("d","","none"),("d","a"*501,"daily"),("d","hi","monthly")]:
        with pytest.raises(ValueError):
            store.add(device,content,datetime(2027,1,1),repeat)


def make_connection(device="A"):
    ready=threading.Event();ready.set()
    return SimpleNamespace(websocket=SimpleNamespace(send=AsyncMock()),session_id='test-session',bind_completed_event=ready,device_id=device, tts=SimpleNamespace(tts_text_queue=queue.Queue(),tts_audio_queue=queue.Queue()),
        need_bind=False,stop_event=threading.Event(),client_is_speaking=False,client_have_voice=False,client_abort=True)

class FakeStore:
    def __init__(self):
        self.rows=[dict(id="r",device_id="A",content="Uống nước",due_at=datetime(2026,1,1),repeat_type="none")]
        self.claims=[];self.finished=[];self.released=[]
    def due(self, now, device_ids):return [r for r in self.rows if r["device_id"] in device_ids]
    def is_sending(self,rid):return True
    def claim(self, rid, now):self.claims.append(rid);return True
    def finish(self, row, now):self.finished.append(row['id'])
    def release(self,rid):self.released.append(rid)

def service():
    return ReminderService({"reminders":{"enabled":True}}, SimpleNamespace(warning=lambda *a:None), FakeStore())


def test_offline_and_busy_devices_are_not_claimed():
    s=service()
    asyncio.run(s.tick())
    assert not s.store.claims
    c=make_connection();s.attach(c);c.client_is_speaking=True
    asyncio.run(s.tick())
    assert not s.store.claims


def test_online_notification_uses_complete_tts_sequence():
    s=service();c=make_connection();s.attach(c)
    asyncio.run(s.tick())
    messages=list(c.tts.tts_text_queue.queue)
    assert [m.sentence_type.value for m in messages] == ["FIRST","MIDDLE","LAST"]
    assert messages[1].content_detail == "Đến giờ nhắc: Uống nước"
    assert len({m.sentence_id for m in messages})==1
    assert not c.client_abort
    assert not s.store.finished
    sid=c.sentence_id;c._reminder_audio_frames=2
    asyncio.run(s.complete(c,sid))
    assert s.store.finished==['r']
    assert json.loads(c.websocket.send.call_args.args[0]) == {'type':'tts','state':'start','session_id':'test-session'}
    assert c.client_is_speaking


def test_reconnection_cleanup_does_not_remove_the_new_connection():
    s=service();old=make_connection();new=make_connection()
    s.attach(old);s.attach(new);s.detach(old)
    assert s.connections['A'] is new


def test_queue_failure_releases_claim_for_retry():
    s=service();s.attach(make_connection())
    def fail(*args):raise RuntimeError('queue error')
    s.enqueue=fail
    with pytest.raises(RuntimeError):asyncio.run(s.tick())
    assert s.store.released==['r'] and not s.store.finished


def test_speech_started_during_database_claim_defers_notification():
    s=service();c=make_connection();s.attach(c)
    def claim(rid,now):
        c.client_have_voice=True
        return True
    s.store.claim=claim
    asyncio.run(s.tick())
    assert s.store.released==['r'] and not s.store.finished
    assert c.tts.tts_text_queue.empty()


def test_reminder_without_audio_is_retried_not_marked_complete():
    s=service();c=make_connection();s.attach(c);asyncio.run(s.tick());asyncio.run(s.complete(c,c.sentence_id))
    assert s.store.released==['r'] and not s.store.finished

def test_reminder_partial_tts_failure_is_retried():
    s=service();c=make_connection();s.attach(c);asyncio.run(s.tick());c._reminder_audio_frames=5;c._reminder_failed=True
    asyncio.run(s.complete(c,c.sentence_id));assert s.store.released==['r'] and not s.store.finished

def test_reminder_disconnected_in_flight_is_retried():
    s=service();c=make_connection();s.attach(c);asyncio.run(s.tick());s.detach(c);asyncio.run(s.tick())
    assert s.store.released==['r'] and not s.store.finished

def test_mac_case_does_not_lose_active_device():
    from core.reminder_scheduler import device_key
    s=service();c=make_connection('02:ab:cd:ef:12:34');s.attach(c)
    assert s.connections[device_key('02:AB:CD:EF:12:34')] is c
    s.detach(c);assert not s.connections

def test_cancelled_inflight_reminder_is_aborted_and_not_finished(monkeypatch):
    import sys
    s=service();c=make_connection();s.attach(c);asyncio.run(s.tick());s.store.is_sending=lambda rid:False
    abort=AsyncMock();monkeypatch.setitem(sys.modules,'core.handle.abortHandle',SimpleNamespace(handleAbortMessage=abort))
    asyncio.run(s.tick());abort.assert_awaited_once_with(c);assert s.store.released==['r'] and not s.store.finished
