# working on metasploitable3-ub1404 
sudo DEBIAN_FRONTEND=noninteractive apt install -y -o Dpkg::Options::="--force-confdef" php5 php5-mysql

# get phpwiki-1.5.0
wget --no-check-certificate -O phpwiki-1.5.0.zip https://sourceforge.net/projects/phpwiki/files/PhpWiki%201.5%20%28current%29/phpwiki-1.5.0.zip/download -nv
unzip -q phpwiki-1.5.0.zip 

# configure phpwiki
cp phpwiki-1.5.0/config/config-dist.ini phpwiki-1.5.0/config/config.ini
sed -i '/;ADMIN_USER/c\ADMIN_USER = admin' phpwiki-1.5.0/config/config.ini
sed -i '/;ADMIN_PASSWD/c\ADMIN_PASSWD = admin1245' phpwiki-1.5.0/config/config.ini
sed -i '/DATABASE_TYPE =/c\DATABASE_TYPE = SQL' phpwiki-1.5.0/config/config.ini
sed -i '/DATABASE_DSN =/c\DATABASE_DSN = "mysql://phpwiki:wiki1234@unix(/run/mysql-default/mysqld.sock)/phpwiki"' phpwiki-1.5.0/config/config.ini

# setup mysql
sudo mysqladmin create phpwiki -S /run/mysql-default/mysqld.sock -u root --password='sploitme'
sudo mysql -e "SET @@global.sql_mode='MYSQL40'" -S /run/mysql-default/mysqld.sock -u root --password='sploitme'
sudo mysql -e "GRANT select, insert, update, delete, lock tables ON phpwiki.* TO phpwiki@localhost IDENTIFIED BY 'wiki1234';" -S /run/mysql-default/mysqld.sock -u root --password='sploitme'
sudo mysql phpwiki -S /run/mysql-default/mysqld.sock -u root --password='sploitme' < phpwiki-1.5.0/schemas/mysql-initialize.sql

# setup www-data
sudo mkdir /var/www/html/phpwiki
sudo cp -r phpwiki-1.5.0/* /var/www/html/phpwiki
sudo chown -R www-data:www-data /var/www/html/phpwiki/

# cleanup
rm phpwiki-1.5.0.zip
sudo service apache2 restart
