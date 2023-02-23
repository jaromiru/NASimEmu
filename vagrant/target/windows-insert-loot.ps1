
$loot_path = "C:/loot"
Write-Host "Creating loot at $loot_path"

$enc = [system.Text.Encoding]::UTF8
$date = Get-Date -Format "mm-ss-FFFFFFF"
$date_in_byte = $enc.GetBytes($date)
$md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider

# Issue with dash
$hash = [System.BitConverter]::ToString($md5.ComputeHash($date_in_byte))

Set-Content $loot_path -Value "LOOT=$hash"
icacls $loot_path /setowner kylo_ren
icacls $loot_path /deny BUILTIN\Users:F
