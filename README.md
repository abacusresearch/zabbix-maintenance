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
python zabbix_maintenance.py start 0.25
python zabbix_maintenance.py start 0.25 zabbix.example.com
```

### Remove a maintenance period

```
python zabbix_maintenance.py stop
python zabbix_maintenance.py stop 3 zabbix.example.com
```

### Check if a maintenance for host exist on zabbix

```
python zabbix_maintenance.py check
python zabbix_maintenance.py check zabbix.example.com
```
