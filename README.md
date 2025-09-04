# zabbix-maintenance

forked from http://www.devops-share.com/put-host-in-zabbix-maintenance-with-python

#### Table of Contents

1. [Overview](#overview)
2. [Config](#config)
3. [Usage](#usage)

## Setup

Install the python-yaml package
```
apt-get install python-yaml
```

## Config

Replace username, password and server in the config file /etc/zabbix/zabbix_maintenance.yml.

```
user: "username"
password: "password"
server: "zabbix.example.com"
```
Optional
```
hostname: "<fqdn>"
```


## Usage

```
python zabbix_maintenance.py <start|stop> [hours] [fqdn] 
```
If no time value specified, the default is used (1 hour)

If no fqdn specified, the local host name is used

### Add a maintenance period

```
python zabbix_maintenance.py start
python zabbix_maintenance.py start -t 0.25
python zabbix_maintenance.py start -t 0.25 -s zabbix.example.com
```

### Remove a maintenance period

```
python zabbix_maintenance.py stop
python zabbix_maintenance.py stop -s zabbix.example.com
```

### Check if a maintenance for host exist on zabbix

```
python zabbix_maintenance.py check
python zabbix_maintenance.py check -s zabbix.example.com
```

## Additional usage for zabbix_maintenance_v7.py

### Add a maintenance with keyword (works currently only on zabbix_maintenance_v7.py)

This helps to prevent overwriting/deleting mutliple maintenance items.

```
python zabbix_maintenance_v7.py start -t 0.25 -k "apt" -s zabbix.example.com
# delete the maintenance item with keyword
python zabbix_maintenance_v7.py stop -k "apt" -s zabbix.example.com
```

### Remove a maintenance period only with id (works currently only on zabbix_maintenance_v7.py)

```
# first, show all items and their ids
python zabbix_maintenance_v7.py check -s zabbix.example.com
# output example:
#  121: maintenance_zabbix.example.com_apt
#  122: maintenance_zabbix.example.com_malu
#  123: maintenance_zabbix.example.com
python zabbix_maintenance_v7.py stop -s zabbix.example.com -i 123
```
