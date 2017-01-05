# zabbix-maintenance

forked from http://www.devops-share.com/put-host-in-zabbix-maintenance-with-python

#### Table of Contents

1. [Overview](#overview)
2. [Config](#config)
3. [Usage](#usage)

## Config

Replace username, password and server in the script.

```
user = "username"
password = "password"
server = "zabbix.example.com"
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
python zabbix_maintenance.py start 3
python zabbix_maintenance.py start 3 zabbix.example.com
```

### Remove a maintenance period

```
python zabbix_maintenance.py stop
python zabbix_maintenance.py stop 3 zabbix.example.com
```
