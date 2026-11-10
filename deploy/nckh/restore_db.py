"""Restore only an explicitly selected, trusted MySQL dump."""
from project import load_env, compose_command, process_env
import argparse
import subprocess
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description='Khôi phục DB; thay thế dữ liệu hiện tại')
    p.add_argument('--file',required=True,type=Path);p.add_argument('--confirm-restore',action='store_true');args=p.parse_args()
    if not args.confirm_restore:p.error('Cần --confirm-restore vì thao tác thay thế dữ liệu hiện tại. Sao lưu trước khi chạy.')
    if not args.file.is_file() or args.file.stat().st_size==0:p.error('Không có tệp SQL sao lưu hợp lệ')
    root=Path(__file__).resolve().parents[2]
    load_env()
    cmd=compose_command()+['exec','-T','db','sh','-c','MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -urobot --default-character-set=utf8mb4 xiaozhi_esp32_server']
    with args.file.open('rb') as src:result=subprocess.run(cmd,cwd=root,env=process_env(),stdin=src)
    if result.returncode:raise SystemExit('Khôi phục thất bại; xem lỗi MySQL phía trên.')
    subprocess.run(compose_command()+['exec','-T','redis','redis-cli','FLUSHDB'],cwd=root,env=process_env(),check=True)
    subprocess.run(compose_command()+['restart','api','voice'],cwd=root,env=process_env(),check=True)
    print('Đã khôi phục DB. Chờ API/voice healthy rồi kiểm tra dữ liệu.')
if __name__=='__main__':main()
