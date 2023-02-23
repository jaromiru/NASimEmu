param (
    [string]$ip = '127.0.0.1'
)

Write-Host "Starting wordpresss"


$htaccess_file = "C:/wamp/www/wordpress/.htaccess"
Set-Content $htaccess_file -Value ""

$script_location = "C:/Program Files/wordpress/update_ip.ps1"
$script_fixed_location = "C:/Program Files/wordpress/update_ip_fix.ps1"

set-content $script_fixed_location -Value ("`$ipaddr = `"$ip`"`n")
get-content -Path $script_location -Tail 15 | add-Content $script_fixed_location


(Get-Content $script_fixed_location) -Replace ':8585', '' | Set-Content $script_fixed_location


schtasks /End /tn "update_wp_db"
schtasks /Delete /tn "update_wp_db" /f
schtasks /Create /tn "update_wp_db_fix" /tr "'cmd.exe' /c powershell -File '$script_fixed_location'" /sc onstart /NP /ru "SYSTEM" /f
schtasks /Run /tn "update_wp_db_fix"