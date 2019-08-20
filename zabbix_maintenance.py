#!/usr/bin/python

from datetime import datetime, timedelta
import urllib2
import time
import json
import sys
import socket
import yaml

with open("/etc/zabbix/zabbix_maintenance.yml", 'r') as ymlfile:
    config = yaml.load(ymlfile)

user = config['user']
password = config['password']
server = config['server']
api = "https://" + server + "/api_jsonrpc.php"

def get_token():
    data = {'jsonrpc': '2.0', 'method': 'user.login', 'params': {'user': user, 'password': password},
            'id': '0'}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        authtoken = str(response.read().split(',')[1].split(':')[1].strip('"'))
        return authtoken


def get_host_id():
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "host.get", "params": {"output": "extend", "filter":
           {"host": [hostname]}}, "auth": token, "id": 0}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
    else:
        host = response.read().split("hostid")[1].split(',')[0].split(':')[1].strip('"')
        return host


def get_maintenance_id():
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.get", "params": {"output": "extend", "selectGroups": "extend",
                                                                      "selectTimeperiods": "extend", "hostids": hostid},
            "auth": token, "id": 0}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
    else:
        try:
            maintid = response.read().split('maintenanceid')[1].split(',')[0].split('"')[2]
            return int(maintid)
        except:
            print "No maintenance for host: " + hostname


def del_maintenance(mid):
    print "Found maintenance for host: " + hostname + " maintenance id: " + str(mid)
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.delete", "params": [mid], "auth": token, "id": 1}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        print "Removed existing maintenance"


def start_maintenance():
    maintids = get_maintenance_id()
    maint = isinstance(maintids, int)
    if maint is True:
        del_maintenance(maintids)
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
        {"name": "maintenance_" + hostname, "active_since": now, "active_till": until, "hostids": [hostid], "timeperiods":
        [{"timeperiod_type": 0, "period": period}]}, "auth": token, "id": 1}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        print "Added a " + str(period / int('3600')) + " hours maintenance on host: " + hostname
        sys.exit(0)

hostname = socket.getfqdn()
if sys.argv[3:]:
    hostname = sys.argv[3]

period = int('3600')
if sys.argv[2:]:
    period = int(sys.argv[2]) * int('3600')

now = int(time.time())
x = datetime.now() + timedelta(seconds=int(period))
float = str(time.mktime(x.timetuple()))
until = int(float.split('.')[0])

if len(sys.argv) > 1:
    if sys.argv[1] == "start":
        start_maintenance()
    elif sys.argv[1] == "stop":
        maintids = get_maintenance_id()
        maint = isinstance(maintids, int)
        if maint is True:
            del_maintenance(maintids)
    else:
        print "Error: did not receive action argument start or stop"
        sys.exit(1)
else:
    print sys.argv[0] + " <start|stop> [hours] [fqdn]"
    sys.exit(1)
