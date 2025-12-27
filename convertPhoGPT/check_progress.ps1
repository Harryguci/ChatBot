$file = Get-Item "models\phogpt-4b-chat-q4_k_m.gguf" -ErrorAction SilentlyContinue
if ($file) {
    $sizeGB = [math]::Round($file.Length / 1GB, 2)
    $expectedSize = 2.36
    $progress = [math]::Round(($file.Length / 2536000000) * 100, 1)

    Write-Host "File: $($file.Name)"
    Write-Host "Size: $sizeGB GB / $expectedSize GB"
    Write-Host "Progress: $progress%"
    Write-Host "Last modified: $($file.LastWriteTime)"

    if ($sizeGB -ge $expectedSize) {
        Write-Host ""
        Write-Host "Download complete!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Download in progress..." -ForegroundColor Yellow
    }
} else {
    Write-Host "File not found" -ForegroundColor Red
}
