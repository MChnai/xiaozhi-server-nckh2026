"""Binary-safe MySQL backup, including on Windows PowerShell."""
import datetime
import subprocess
from pathlib import Path

from project import ROOT, load_env, compose_command, process_env
root=ROOT
try: load_env()
except ValueError as exc: raise SystemExit(str(exc))
out=root/'backups'/('robot-ai-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.sql')
out.parent.mkdir(exist_ok=True)
cmd=compose_command()+['exec','-T','db','sh','-c',
     'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump -urobot --single-transaction --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 xiaozhi_esp32_server']
with out.open('wb') as f:
    result=subprocess.run(cmd,cwd=root,env=process_env(),stdout=f)
if result.returncode:
    out.unlink(missing_ok=True)
    raise SystemExit("Sao lưu thất bại, chưa tạo tệp SQL.")
print("Đã sao lưu:",out)
