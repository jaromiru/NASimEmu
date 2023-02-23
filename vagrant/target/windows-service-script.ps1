
param (
    [string[]]$services = '',
    [string]$ip = '127.0.0.1'
)


function ResetEverything
{
    C:/vagrant/windows-up-down-script/down-windows-services.ps1
# be careful, there are some dependencies between wamp, mysql and wp-ninja
#    C:/vagrant/windows-up-down-script/down-wamp.ps1
    C:/vagrant/windows-up-down-script/up-wamp.ps1
#    C:/vagrant/windows-up-down-script/down-mysql.ps1
    C:/vagrant/windows-up-down-script/down-wp-ninja.ps1
    C:/vagrant/windows-up-down-script/down-elasticsearch.ps1

}


function WordpressNinja
{
#    C:/vagrant/windows-up-down-script/up-wamp.ps1
    C:/vagrant/windows-up-down-script/up-wp-ninja.ps1 -ip $ip
}

function ElasticSearch
{
    C:/vagrant/windows-up-down-script/up-elasticsearch.ps1
}

function MySQL
{
    C:/vagrant/windows-up-down-script/up-mysql.ps1
}

ResetEverything
if($services){
    foreach ($service in $services.Split(',')) {
        switch($service){
            "80_windows_wp_ninja"{
                WordpressNinja
            }
            "9200_windows_elasticsearch"{
                ElasticSearch
            }
            "3306_any_mysql"{
                MySQL
            }
            default{
                 Write-Error "Unknown arg $service"
            }
        }
    }
}