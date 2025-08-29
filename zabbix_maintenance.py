#!/usr/bin/python3

from datetime import datetime, timedelta
import json
import platform
import socket
import sys
import time
import urllib.request, urllib.error, urllib.parse
import yaml
import os.path

if platform.system() == "Windows":
    path = 'C:\ProgramData\zabbix\zabbix_maintenance.yml'
else:
    path = '/etc/zabbix/zabbix_maintenance.yml'
if os.path.isfile(path) == True:
    configfile = path
else:
    configfile = 'zabbix_maintenance.yml'

with open(configfile, 'r') as ymlfile:
    config = yaml.load(ymlfile, yaml.SafeLoader)

user = config['user']
password = config['password']
server = config['server']
api = "https://" + server + "/api_jsonrpc.php"

def get_token():
    data = {'jsonrpc': '2.0', 'method': 'user.login', 'params': {'user': user, 'password': password},
            'id': '0'}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
        sys.exit(1)
    else:
        body = json.loads(response.read())
        if not body['result']:
            print("can't get authtoken")
            sys.exit(1)
        else:
            return body['result']


def get_host_id(check=False):
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "host.get", "params": {"output": "extend", "filter":
           {"host": [hostname]}}, "auth": token, "id": 0}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
    else:
        body = json.loads(response.read())
        if not body['result']:
            if check:
                return False
            else:
                print(("Host " + hostname + " not found on " + server))
                sys.exit(1)
        else:
            return body['result'][0]['hostid']


def get_maintenance_id():
    global maintenance
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.get", "params": {"output": "extend", "selectGroups": "extend",
                                                                      "selectTimeperiods": "extend", "hostids": hostid},
            "auth": token, "id": 0}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
    else:
        body = json.loads(response.read())
        if not body['result']:
            print(("No maintenance for host: " + hostname))
        else:
            maintenance = body['result'][0]
            return int(body['result'][0]['maintenanceid'])


def del_maintenance(mid):
    print(("Found maintenance for host: " + hostname + " maintenance id: " + str(mid)))
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.delete", "params": [mid], "auth": token, "id": 1}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
        sys.exit(1)
    else:
        print("Removed existing maintenance")


def start_maintenance():
    maintids = get_maintenance_id()
    maint = isinstance(maintids, int)
    if maint is True:
        del_maintenance(maintids)
        extend_mnt = {"timeperiod_type": 0, "period": period}
        maintenance['timeperiods'].append(extend_mnt)
        if until < int(maintenance['active_till']):
            update_maintenance(maintenance['timeperiods'],int(maintenance['active_till']),"Added")
        else:
            update_maintenance(maintenance['timeperiods'],until,"Added")
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
        {"name": "maintenance_" + hostname, "active_since": now, "active_till": until, "hostids": [hostid], "timeperiods":
        [{"timeperiod_type": 0, "period": period}]}, "auth": token, "id": 1}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
        sys.exit(1)
    else:
        print("Added a %i:%02i hours maintenance on host: %s" % (period // 3600, period%3600//60, hostname ))
        sys.exit(0)


def update_maintenance(mnt,act_t,task):
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
        {"name": "maintenance_" + hostname, "active_since": int(maintenance['active_since']), "active_till": act_t, "hostids": [hostid], "timeperiods": mnt}, "auth": token, "id": 1}
    req = urllib.request.Request(api)
    data_json = json.dumps(data)
    data_json = data_json.encode('utf-8')
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib.request.urlopen(req, data_json)
    except urllib.error.HTTPError as ue:
        print(("Error: " + str(ue)))
        sys.exit(1)
    else:
        print((task + " period on host: " + hostname))
        sys.exit(0)


def stop_maintenance():
    maintids = get_maintenance_id()
    maint = isinstance(maintids, int)
    if maint is True:
        if len(maintenance['timeperiods']) > 1:
            min_period = 86400
            period_position = 0
            for item in range(len(maintenance['timeperiods'])):
                if min_period > int(maintenance['timeperiods'][item]['period']):
                    min_period = int(maintenance['timeperiods'][item]['period'])
                    period_position = item
            del maintenance['timeperiods'][period_position]
            del_maintenance(maintids)
            update_maintenance(maintenance['timeperiods'],int(maintenance['active_till']),"Removed")
        else:
            del_maintenance(maintids)


def check_host_id():
    if get_host_id(True):
        print(("Host " + hostname + " found on " + server))
        sys.exit(0)
    else:
        print(("Host " + hostname + " not found on " + server))
        sys.exit(1)


if 'hostname' in config:
    hostname = config['hostname']
else:
    hostname = socket.getfqdn()

if sys.argv[3:]:
    hostname = sys.argv[3]

period = 3600
if sys.argv[2:]:
    if float(sys.argv[2]) < 148159:
        period = int(float(sys.argv[2]) * 3600)
    else:
        print("Error: maximum size of a period is 148159 hours")
        sys.exit(1)
now = int(time.time())
x = datetime.now() + timedelta(seconds=int(period))
until = int(time.mktime(x.timetuple()))

if len(sys.argv) > 1:
    if sys.argv[1] == "start":
        start_maintenance()
    elif sys.argv[1] == "stop":
        stop_maintenance()
    elif sys.argv[1] == "check":
        check_host_id()
    else:
        print("Error: did not receive action argument start, stop or check")
        sys.exit(1)
else:
    print((sys.argv[0] + " <start|stop|check> [hours] [fqdn]"))
    sys.exit(1)
