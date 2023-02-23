#!/bin/bash

apache2IsStarted=0


disable_everything()
{
  echo "Disabling all services"

  /vagrant/linux-up-down-script/down-apache2.sh
  /vagrant/linux-up-down-script/down-drupal.sh
  /vagrant/linux-up-down-script/down-phpwiki.sh
  /vagrant/linux-up-down-script/down-proftpd.sh
  /vagrant/linux-up-down-script/down-mysql.sh
}

apache2()
{
  if [ $apache2IsStarted -eq 0 ]
  then
    apache2IsStarted=1
    /vagrant/linux-up-down-script/up-apache2.sh
  fi
}

drupal()
{
  apache2
  /vagrant/linux-up-down-script/up-drupal.sh
}

proftpd()
{
  apache2
  /vagrant/linux-up-down-script/up-proftpd.sh
}

phpwiki(){
  apache2
  /vagrant/linux-up-down-script/up-phpwiki.sh
}

mysql(){
  /vagrant/linux-up-down-script/up-mysql.sh
}

disable_everything

for option in "$@"
do
  case $option in
    "80_linux_drupal")
      drupal
      ;;
    "21_linux_proftpd")
      proftpd
      ;;
    "80_linux_phpwiki")
      phpwiki
      ;;
    "3306_any_mysql")
      mysql
      ;;
    *)
      >&2 echo "Unknown arg : $option"
      ;;
  esac
done
