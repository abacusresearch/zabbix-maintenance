#!/usr/bin/env python3

"""
Set maintenance for host
"""

import os
import sys
import time
import json
import socket
import platform
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import yaml

# determine config file path
if platform.system() == "Windows":
    CONFIG_PATH = r"C:\ProgramData\zabbix\zabbix_maintenance.yml"
else:
    CONFIG_PATH = "/etc/zabbix/zabbix_maintenance.yml"

if os.path.isfile(CONFIG_PATH):
    CONFIGFILE = CONFIG_PATH
else:
    CONFIGFILE = "zabbix_maintenance.yml"

# load YAML
with open(CONFIGFILE, "r", encoding="utf-8") as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.SafeLoader)

user = config["user"]
password = config["password"]
server = config["server"]
API_URL = f"https://{server}/api_jsonrpc.php"


def get_token():
    """Get token from user"""
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": user, "password": password},
        "id": "0",
    }
    req = urllib.request.Request(
        API_URL, headers={"Content-Type": "application/json-rpc"}
    )
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data) as response:
            body = json.load(response)
            token = body.get("result")
            if not token:
                print("Can't get auth token")
                sys.exit(1)
            return token
        # response = urllib.request.urlopen(req, data)
    except urllib.error.HTTPError as e:
        print("Error:", e)
        sys.exit(1)


def get_host_id(check=False):
    """get hostid to create new maintenance object"""
    token = get_token()
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": "extend",
            "filter": {"host": [hostname]},
        },
        "auth": token,
        "id": 0,
    }
    req = urllib.request.Request(
        API_URL, headers={"Content-Type": "application/json-rpc"}
    )
    data = json.dumps(payload).encode("utf-8")

    try:
        # response = urllib.request.urlopen(req, data)
        with urllib.request.urlopen(req, data) as response:
            body = json.load(response)
            result = body.get("result", [])
            if not result:
                if check:
                    return False
                print(f"Host {hostname} not found on {server}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print("Error:", e)
        if check:
            return False
        sys.exit(1)
    return result[0]["hostid"]


def get_maintenance_id(name):
    """check for existing maintenance object in zabbix"""
    hostid = get_host_id()
    token = get_token()
    payload = {
        "jsonrpc": "2.0",
        "method": "maintenance.get",
        "params": {
            "output": "extend",
            "selectGroups": "extend",
            "selectTimeperiods": "extend",
            "hostids": hostid,
            "search": {
                "name": name
            },
            "startSearch": "true"
        },
        "auth": token,
        "id": 0,
    }
    req = urllib.request.Request(
        API_URL, headers={"Content-Type": "application/json-rpc"}
    )
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data) as response:
            body = json.load(response)
            result = body.get("result", [])
            if not result:
                print(f"No maintenance for host: {hostname}")
                return None
            maintenance = result[0]
            return int(maintenance["maintenanceid"])
    except urllib.error.HTTPError as e:
        print("Error:", e)
        return None


def del_maintenance(mid):
    """delete whole maintenance object"""
    print(f"Found maintenance for host: {hostname}, maintenance id: {mid}")
    token = get_token()
    payload = {
        "jsonrpc": "2.0",
        "method": "maintenance.delete",
        "params": [mid],
        "auth": token,
        "id": 1,
    }
    req = urllib.request.Request(
        API_URL, headers={"Content-Type": "application/json-rpc"}
    )
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data) as response:
            body = json.load(response)
            result = body.get("result", [])
            if not result:
                print(f"Could not delete Maintenance for host: {hostname}")
                return None
    except urllib.error.HTTPError as e:
        print("Error:", e)
        sys.exit(1)
    print("Removed existing maintenance")
    return None


def create_maintenance(name, since, till, hostids, timeperiods, task_desc):
    """create new maintenance object"""
    token = get_token()
    payload = {
        "jsonrpc": "2.0",
        "method": "maintenance.create",
        "params": {
            "name": name,
            "active_since": since,
            "active_till": till,
            "hostids": hostids,
            "timeperiods": timeperiods,
        },
        "auth": token,
        "id": 1,
    }
    req = urllib.request.Request(
        API_URL, headers={"Content-Type": "application/json-rpc"}
    )
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data) as response:
            body = json.load(response)
            result = body.get("result", [])
            if not result:
                print(f"Could not create Maintenance for host: {hostname}")
                return None
    except urllib.error.HTTPError as e:
        print("Error:", e)
        sys.exit(1)
    print(task_desc)
    return None


def start_maintenance():
    """create maintenance object from now, replace existing maintenance object in zabbix"""
    name = f"maintenance_{hostname}"
    mid = get_maintenance_id(name)
    hostid = get_host_id()
    since = now
    till = until

    # if existing maintenance, delete it and recreate it
    if isinstance(mid, int):
        # remove old
        del_maintenance(mid)
    # fresh creation
    create_maintenance(
        name,
        since,
        till,
        [hostid],
        [{"timeperiod_type": 0, "period": PERIOD}],
        f"Added a {PERIOD//3600}-hour maintenance on host: {hostname}",
    )


def stop_maintenance():
    """delete maintenance object if it exists"""
    name = f"maintenance_{hostname}"
    mid = get_maintenance_id(name)
    if isinstance(mid, int):
        # remove old
        del_maintenance(mid)


def check_host_id():
    """check if host exists on zabbix and check maintenance object for the host"""
    name = f"maintenance_{hostname}"
    if get_host_id(check=True):
        mid = get_maintenance_id(name)
        print(f"MaintenanceId {mid} with Host {hostname} found on {server}")
        sys.exit(0)
    else:
        print(f"Host {hostname} not found on {server}")
        sys.exit(2)


# --- main ---
# hostname override
if "hostname" in config:
    hostname = config["hostname"]
else:
    hostname = socket.getfqdn()

if len(sys.argv) == 4:
    hostname = sys.argv[3]
elif len(sys.argv) == 3:
    hostname = sys.argv[2]

# period in seconds
PERIOD = 3600
if len(sys.argv) == 4:
    hours_arg = int(sys.argv[2])
    if hours_arg < 148159:
        PERIOD = hours_arg * 3600
    else:
        print("Error: maximum size of a period is 148159 hours")
        sys.exit(1)

now = int(time.time())
until_float = time.mktime((datetime.now() + timedelta(seconds=PERIOD)).timetuple())
until = int(str(until_float).split(".", maxsplit=1)[0])

if len(sys.argv) > 1:
    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_maintenance()
    elif cmd == "stop":
        stop_maintenance()
    elif cmd == "check":
        check_host_id()
    else:
        print("Error: action must be start, stop or check")
        sys.exit(1)
else:
    print(f"Usage: {sys.argv[0]} <start|stop|check> [hours] [fqdn]")
    sys.exit(1)
