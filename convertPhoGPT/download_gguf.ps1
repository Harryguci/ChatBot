# Download PhoGPT GGUF from Hugging Face

$url = "https://huggingface.co/vinai/PhoGPT-4B-Chat-gguf/resolve/main/PhoGPT-4B-Chat-Q4_K_M.gguf?download=true"
$output = "models\phogpt-4b-chat-q4_k_m.gguf"

Write-Host "=========================================="
Write-Host "PhoGPT GGUF Download"
Write-Host "=========================================="
Write-Host ""
Write-Host "Source: $url"
Write-Host "Target: $output"
Write-Host "Size: 2.36 GB"
Write-Host "This may take 10-20 minutes..."
Write-Host ""

# Enable TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Download with progress
try {
    Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing

    Write-Host ""
    Write-Host "=========================================="
    Write-Host "Download Complete!"
    Write-Host "=========================================="
    Write-Host ""

    $file = Get-Item $output
    Write-Host "File: $($file.Name)"
    Write-Host ("Size: {0:N2} GB" -f ($file.Length / 1GB))
    Write-Host "Location: $($file.DirectoryName)"
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "Error: Download failed"
    Write-Host $_.Exception.Message
    Write-Host ""
    exit 1
}
