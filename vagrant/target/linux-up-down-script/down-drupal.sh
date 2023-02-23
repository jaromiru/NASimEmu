
mkdir -p /home/vagrant/backup
if [ -d /var/www/html/drupal ] &&  [ ! -d /home/vagrant/backup/drupal ]
then
  cp -a /var/www/html/drupal /home/vagrant/backup/drupal
fi
rm -f -R /var/www/html/drupal