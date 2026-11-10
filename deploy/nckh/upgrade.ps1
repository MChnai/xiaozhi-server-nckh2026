param([Parameter(Mandatory=$true)][string]$LanHost)
$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $projectRoot
try {
    if (Test-Path ".env") {
        $db = docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml ps --status running --services db
        if ($LASTEXITCODE -ne 0) { throw "Không đọc được cấu hình v3. Xem HUONG_DAN_V3.md." }
        if ($db -contains "db") {
            python deploy/nckh/backup_db.py
            if ($LASTEXITCODE -ne 0) { throw "Sao lưu DB v3 thất bại; đã dừng." }
        }
    }
    python deploy/nckh/install.py --host $LanHost
    if ($LASTEXITCODE -ne 0) { throw "Nâng cấp chưa hoàn tất. Xem thư mục diagnostics." }
} finally { Pop-Location }
