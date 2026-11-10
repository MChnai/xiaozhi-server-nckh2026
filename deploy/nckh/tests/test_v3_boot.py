import asyncio
import importlib.util
import json
import shutil
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'deploy/nckh'))
from project import ensure_env, parse_env, validate_env, process_env, redact
from install import decode_rows, evaluate_health
from model_cache import validate_model, write_manifest, promote
from core.service_supervisor import run_services

def test_fresh_env_and_safe_resume(tmp_path):
    scripts=tmp_path/'deploy/nckh';scripts.mkdir(parents=True)
    shutil.copy(ROOT/'deploy/nckh/.env.example',scripts/'.env.example')
    first=ensure_env('192.168.1.2',tmp_path)
    second=ensure_env('192.168.1.3',tmp_path)
    assert first['MYSQL_PASSWORD']==second['MYSQL_PASSWORD']
    assert first['NCKH_SERVER_SECRET']==second['NCKH_SERVER_SECRET']
    assert second['NCKH_PUBLIC_HOST']=='192.168.1.3'
    assert (tmp_path/'music').is_dir()

@pytest.mark.parametrize('line', ['A=x\nA=y', 'not-an-env', 'A="x" garbage', "A='missing",'A=${OTHER}'])
def test_reject_ambiguous_env(tmp_path,line):
    p=tmp_path/'env';p.write_text(line)
    with pytest.raises(ValueError):parse_env(p)

def test_bom_quotes_comments_and_secrets(tmp_path):
    p=tmp_path/'env';p.write_text('\ufeffA="hello world" # text\nB=abc # hi\nC=abc#hi\nD=\'key$literal\'\n')
    assert parse_env(p)=={'A':'hello world','B':'abc','C':'abc#hi','D':'key$literal'}
    assert redact('Bearer abc.def MySecret',{'DEEPSEEK_API_KEY':'MySecret'})=='Bearer [ĐÃ ẨN] [ĐÃ ẨN]'

def test_shell_vars_do_not_override_project(monkeypatch):
    monkeypatch.setenv('MYSQL_PASSWORD','wrong-shell-value')
    assert 'MYSQL_PASSWORD' not in process_env()

def test_health_failure_is_terminal():
    for row in [{'State':'restarting'},{'State':'exited'},{'State':'running','Health':'unhealthy'}]:
        assert evaluate_health([dict(row,Service='voice')],'voice')[0]=='failed'
    assert evaluate_health([{'Service':'voice','State':'running','Health':'starting'}],'voice')[0]=='waiting'
    assert evaluate_health([{'Service':'voice','State':'running','Health':'healthy'}],'voice')[0]=='ready'
    assert evaluate_health([],'voice')[0]=='waiting'

def test_compose_json_versions():
    row={'Service':'voice','State':'running','Health':'healthy'}
    assert decode_rows(json.dumps([row]))==decode_rows(json.dumps(row))==[row]

def fake_model(folder):
    folder.mkdir()
    (folder/'model.bin').write_bytes(b'X'*1_000_001)
    for name in ('config.json','tokenizer.json','preprocessor_config.json','vocabulary.json'):(folder/name).write_text('{}')
    write_manifest(folder,'test')

def test_model_checksum_blocks_incomplete_or_corrupted_cache(tmp_path):
    out=tmp_path/'model';fake_model(out)
    assert validate_model(out)
    (out/'tokenizer.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='thay đổi'):validate_model(out)

def test_model_promotion_preserves_old_until_new_valid(tmp_path):
    old,new=tmp_path/'model',tmp_path/'staging';fake_model(old);fake_model(new)
    (old/'old-cache-marker').write_text('old')
    (new/'model.bin').unlink()
    with pytest.raises(ValueError):promote(new,old)
    assert (old/'old-cache-marker').is_file()
    (new/'model.bin').write_bytes(b'X'*1_000_001)
    promote(new,old)
    assert validate_model(old) and not new.exists() and not (old/'old-cache-marker').exists()

def test_startup_failure_cancels_other_services():
    async def scenario():
        ready1,ready2=asyncio.Event(),asyncio.Event()
        cancelled=asyncio.Event()
        async def fail():raise OSError('address already in use')
        async def wait():
            try:await asyncio.Future()
            finally:cancelled.set()
        with pytest.raises(RuntimeError,match='WebSocket') as error:
            await run_services([('WebSocket',fail,ready1),('HTTP',wait,ready2)],lambda:asyncio.Future(),startup_timeout=.2)
        assert isinstance(error.value.__cause__,OSError) and cancelled.is_set()
    asyncio.run(scenario())

def test_healthy_only_after_all_listeners_ready_and_later_failure_fatal():
    async def scenario():
        a,b=asyncio.Event(),asyncio.Event();announced=[]
        async def first():
            a.set();await asyncio.Future()
        async def second():
            await asyncio.sleep(.02);b.set();await asyncio.sleep(.02);raise RuntimeError('listener died')
        def announce():
            assert a.is_set() and b.is_set();announced.append(True)
        with pytest.raises(RuntimeError,match='HTTP'):
            await run_services([('WS',first,a),('HTTP',second,b)],lambda:asyncio.Future(),on_ready=announce)
        assert announced==[True]
    asyncio.run(scenario())

def test_startup_deadline_and_normal_shutdown():
    async def scenario():
        a=asyncio.Event()
        async def wait():await asyncio.Future()
        with pytest.raises(TimeoutError):
            await run_services([('ASR',wait,a)],lambda:asyncio.Future(),startup_timeout=.01)
        a.set()
        async def stop():await asyncio.sleep(.01)
        await run_services([('WS',wait,a)],stop)
    asyncio.run(scenario())

def test_v3_sql_only_adds_new_changeset():
    import yaml
    base=ROOT/'main/manager-api/src/main/resources/db/changelog'
    changes=yaml.safe_load((base/'db.changelog-nckh.yaml').read_text())['databaseChangeLog']
    ids=[item['changeSet']['id'] for item in changes[1:]]
    assert len(ids)==len(set(ids))==3
    for item in changes[1:]:
        assert (base/item['changeSet']['changes'][0]['sqlFile']['path']).is_file()

def test_nckh_plugins_do_not_override_vietnamese_lunar():
    import ast
    path=ROOT/'main/xiaozhi-server/plugins_func/loadplugins.py'
    # The import smoke check exercises this without AST in a separate process as well.
    namespace={};exec(compile(ast.parse(path.read_text()),str(path),'exec'),namespace)
    assert 'get_time' not in namespace['NCKH_PLUGINS']
    assert {'get_lunar','add_reminder','list_reminders','delete_reminder','get_gold_price','translate_text','play_music','get_weather_vn','get_news_from_vnexpress'}<=namespace['NCKH_PLUGINS']
