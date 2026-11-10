param([Parameter(Mandatory=$true)][string]$LanHost, [switch]$StopPrevious)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$arguments = @("deploy/nckh/install.py", "--host", $LanHost)
if ($StopPrevious) { $arguments += "--stop-previous" }
python @arguments
if ($LASTEXITCODE -ne 0) { throw "Cài đặt chưa hoàn tất. Xem thư mục diagnostics." }
