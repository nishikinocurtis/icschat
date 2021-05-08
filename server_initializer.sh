USER=root
PASSWORD=admin

mysql -u$USER -p$PASSWORD -e "create database ICSCHAT;"
mysql -u$USER -p$PASSWORD -e "use ICSCHAT;"
mysql -u$USER -p$PASSWORD -e "create table 'users' ( \
                         'uid' int not null auto_increment, \
                         'username' varchar(50) not null, \
                         'password' varchar(260) not null, \
                         'publickey' varchar(500) not null, \
                         primary key('uid')\
                         ) default charset=utf-8;"
mysql -u$USER -p$PASSWORD -e "CREATE TABLE 'state' ( \
                         'pkey' int NOT NULL AUTO_INCREMENT, \
                         'uid' int NOT NULL, \
                         'state' tinyint NOT NULL, \
                         PRIMARY KEY ('pkey') \
                         ) ENGINE=InnoDB DEFAULT CHARSET=utf8;"
mysql -u$USER -p$PASSWORD -e ""

# unfinished!!!

