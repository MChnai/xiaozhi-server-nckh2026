from pathlib import Path
import os
import subprocess
import sys
import tempfile
import shutil
import yaml

ROOT=Path(__file__).resolve().parents[3]


def test_compose_uses_local_source_and_persistent_private_database():
    cfg=yaml.safe_load((ROOT/'compose.nckh.yaml').read_text())
    assert set(cfg['services'])=={'db','redis','api','voice','web','model-setup','piper','vieneu'}
    for name in ('api','voice','web'):
        assert (ROOT/cfg['services'][name]['build']['dockerfile']).is_file()
    assert 'ports' not in cfg['services']['db'] and 'ports' not in cfg['services']['redis']
    assert cfg['services']['api']['depends_on']['db']['condition']=='service_healthy'
    assert cfg['services']['voice']['environment']['NCKH_LLM_MODE']=='${NCKH_LLM_MODE:-demo}'


def test_new_liquibase_history_is_separate_and_has_valid_paths():
    base=ROOT/'main/manager-api/src/main/resources/db/changelog'
    cfg=yaml.safe_load((base/'db.changelog-nckh.yaml').read_text())
    assert (base/cfg['databaseChangeLog'][0]['include']['file']).is_file()
    assert (base/cfg['databaseChangeLog'][1]['changeSet']['changes'][0]['sqlFile']['path']).is_file()


def test_setup_preserves_existing_env_and_rejects_loopback(tmp_path):
    project=tmp_path/'project'
    scripts=project/'deploy/nckh';scripts.mkdir(parents=True)
    for name in ('setup.py','project.py','.env.example'):
        shutil.copy(ROOT/'deploy/nckh'/name,scripts/name)
    result=subprocess.run([sys.executable,str(scripts/'setup.py'),'--host','127.0.0.1'],capture_output=True)
    assert result.returncode and not (project/'.env').exists()
    subprocess.run([sys.executable,str(scripts/'setup.py'),'--host','192.168.1.19'],check=True,capture_output=True)
    original=(project/'.env').read_bytes()
    assert b'MYSQL_PASSWORD=\n' not in original
    result=subprocess.run([sys.executable,str(scripts/'setup.py'),'--host','192.168.1.20'],capture_output=True)
    assert result.returncode==0
    after=(project/'.env').read_text()
    assert 'NCKH_PUBLIC_HOST=192.168.1.20' in after
    for line in original.decode().splitlines():
        if line.startswith(('MYSQL_', 'NCKH_SERVER_SECRET=')):
            assert line in after


def test_api_config_preserves_auth_and_local_reminder_settings(monkeypatch):
    import asyncio
    import importlib.util
    from types import SimpleNamespace
    async def get_config():
        return {'server':{'auth':{'enabled':True,'allowed_devices':['A']},'websocket':'ws://lan:8000/nckh/v1/'}}
    fake=SimpleNamespace(init_service=lambda cfg:None,get_server_config=get_config,
        get_agent_models=None,get_correct_words=None,
        DeviceNotFoundException=type('DeviceNotFoundException',(Exception,),{}),
        DeviceBindException=type('DeviceBindException',(Exception,),{}))
    monkeypatch.setitem(sys.modules,'config.manage_api_client',fake)
    spec=importlib.util.spec_from_file_location('test_nckh_loader',ROOT/'main/xiaozhi-server/config/config_loader.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    cfg={'manager-api':{'url':'http://api:8003/xiaozhi','secret':'test-secret'},
         'server':{'ip':'0.0.0.0','port':8000,'timezone_offset':7},'reminders':{'enabled':True}}
    result=asyncio.run(mod.get_config_from_api_async(cfg))
    assert result['server']['auth']=={'enabled':True,'allowed_devices':['A']}
    assert result['server']['websocket']=='ws://lan:8000/nckh/v1/'
    assert result['server']['timezone_offset']==7
    assert result['reminders']=={'enabled':True}
