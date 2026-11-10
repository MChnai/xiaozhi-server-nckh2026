"""Show bounded startup/health diagnostics without printing project secrets."""
import json
import subprocess
import sys
from project import ROOT, load_env, compose_command, process_env, redact
from install import decode_rows

def main():
    try:
        settings=load_env()
    except ValueError as exc:
        print('[LỖI]',exc)
        return 1
    command=compose_command()
    for parts in [['ps','-a'],['logs','--no-color','--tail','70','api','voice','web','piper']]:
        try:
            run=subprocess.run(command+parts,cwd=ROOT,env=process_env(),text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=30)
            print(redact(run.stdout or run.stderr,settings))
        except (OSError,subprocess.SubprocessError) as exc:
            print('Không đọc được Docker:',type(exc).__name__)
            return 1
    try:
        result=subprocess.run(command+['ps','-a','--format','json'],cwd=ROOT,env=process_env(),text=True,capture_output=True,timeout=20)
        for row in decode_rows(result.stdout):
            if row.get('Service') not in ('api','voice','web','piper'):continue
            name=row.get('Name')
            if not name:continue
            run=subprocess.run(['docker','inspect','--format','{{json .State.Health}}',name],cwd=ROOT,env=process_env(),text=True,capture_output=True,timeout=15)
            print(row['Service']+' healthcheck:',redact(run.stdout,settings))
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print('Không lấy được chi tiết healthcheck:',type(exc).__name__)
        return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
