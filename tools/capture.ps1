# 用 PresentMon 采集一份 CSV。需要先安装 PresentMon（Windows）。
# 参数按你安装的版本可能不同，先运行 PresentMon.exe --help 看一眼。
param(
    [string]$ProcessName = "game.exe",
    [int]$Seconds = 60,
    [string]$Out = "capture.csv"
)

$exe = (Get-Command PresentMon.exe -ErrorAction SilentlyContinue)
if (-not $exe) {
    Write-Host "没找到 PresentMon.exe。到 https://github.com/GameTechDev/PresentMon/releases 下载后放到 PATH。"
    exit 1
}

Write-Host "采集 $ProcessName，$Seconds 秒 -> $Out"
& $exe.Source --process_name $ProcessName --output_file $Out --capture_seconds $Seconds
if (-not (Test-Path $Out)) {
    Write-Host "第一次没生成文件，尝试短参数形式..."
    & $exe.Source -process_name $ProcessName -output_file $Out -capture_seconds $Seconds
}
if (Test-Path $Out) {
    Write-Host "完成：$Out"
} else {
    Write-Host "采集失败：确认游戏进程名，或运行 PresentMon.exe --help 查看参数。"
    exit 1
}
