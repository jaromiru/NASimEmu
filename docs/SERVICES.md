# OS

## Attacker

* OS: Kali linux
* Box: [kalilinux/rolling](https://app.vagrantup.com/kalilinux/boxes/rolling)


## Linux

* OS: Ubuntu 14.04 Metasploitable3
* Box: [rapid7/metasploitable3-ub1404](https://app.vagrantup.com/rapid7/boxes/metasploitable3-ub1404)


## Windows

* OS: Windows 2008 Metasploitable3
* Box: [rapid7/metasploitable3-win2k8](https://app.vagrantup.com/rapid7/boxes/metasploitable3-win2k8)

# Services and Exploits

## mysql
* OS: any
* Port: 3306
* CVE: -
* Service name in NASimEmu: 3306_any_mysql

This service is not exploitable. In the default scenarios, it is used as a `sensitive_service`, which is installed on all sensitive nodes (and on 10% of non-sensitive nodes).

## proftpd

* OS: Linux
* Port: 21
* CVE: [CVE-2015-3306](https://www.cve.org/CVERecord?id=CVE-2015-3306)
* Service name in NASimEmu: 21_linux_proftpd


[More information about the exploit.](https://www.rapid7.com/db/modules/exploit/unix/ftp/proftpd_modcopy_exec/)

## drupal

* Os: Linux
* Port: 80
* Path: /drupal/
* Service name in NASimEmu: 80_linux_drupal

[More information about the vulnerability](https://www.drupal.org/node/2765575).

[More information about the exploit.](https://www.rapid7.com/db/modules/exploit/unix/webapp/drupal_coder_exec/)

## Elasticsearch

The exploit use a security issue in the ElasticSearch prior to version 1.2.0. 

* OS: Windows
* Port: 9200
* CVE: [CVE-2014-3120](https://www.cve.org/CVERecord?id=CVE-2014-3120)
* Service name in NASimEmu: 9200_windows_elasticsearch

The vulnerability is available in the Windows metasploitable VM : for more information [here](https://github.com/rapid7/metasploitable3/wiki/Vulnerabilities#elasticsearch).

[More information about the exploit.](https://www.rapid7.com/db/modules/exploit/multi/elasticsearch/script_mvel_rce)


## Wordpress

The exploit use a security issue in the Ninja Forms plugin (before version 2.9.42.1). 

* OS: Windows
* Port: 80
* Path: /wordpress/
* CVE: [CVE-2016-1209](https://www.cve.org/CVERecord?id=CVE-2016-1209)
* Service name in NASimEmu: 80_windows_wp_ninja

The vulnerability is available in the Windows metasploitable VM : for more information [here](https://github.com/rapid7/metasploitable3/wiki/Vulnerabilities#wordpress).

[More information about the exploit.](https://www.rapid7.com/db/modules/exploit/multi/http/wp_ninja_forms_unauthenticated_file_upload/)


## phpwiki 

* OS: Linux
* Port: 80
* Path: /phpwiki/
* CVE: [CVE-2014-5519](https://www.cve.org/CVERecord?id=CVE-2014-5519)
* Service name in NASimEmu: 80_linux_phpwiki

[More information about the exploit.](https://www.rapid7.com/db/modules/exploit/multi/http/phpwiki_ploticus_exec/)
