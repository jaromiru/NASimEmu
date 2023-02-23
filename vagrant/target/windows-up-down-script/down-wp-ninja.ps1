Write-Host "Stopping wordpress ninja"


$htaccess_file = "C:/wamp/www/wordpress/.htaccess"
Set-Content $htaccess_file -Value "Deny from All"


