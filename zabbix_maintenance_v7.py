#!/usr/bin/env python3

"""Set maintenance for host"""

import argparse
import os
import sys
import time
import socket
import platform
from datetime import datetime, timedelta
import yaml
import requests


# --- argument parser ---
parser = argparse.ArgumentParser(
    description="Tool to start, "
    "stop or check maintenance for a specific host on zabbix"
)
parser.add_argument(
    "action", choices=["start", "stop", "check"], help="Action to perform"
)
parser.add_argument(
    "--time-period",
    "-t",
    nargs="?",
    type=float,
    default=None,
    help="Number of hours for maintenance (only for start/stop). Maximum is 148159 hours."
)
parser.add_argument(
    "--target-host",
    "-s",
    nargs="?",
    type=str,
    default=None,
    help="Target host to set or check maintenance"
)
parser.add_argument(
    "--config-file",
    "-c",
    nargs="?",
    type=str,
    default=None,
    help=r'Path of the config file (default of Windows "C:\ProgramData\zabbix\zabbix_maintenance.yml"'
    ', on Linux "/etc/zabbix/zabbix_maintenance.yml")'
)
parser.add_argument(
    "--keyword",
    "-k",
    nargs="?",
    type=str,
    default=None,
    help="Add a keyword for the maintenance item."
)
parser.add_argument(
    "--delete-all",
    "-rm",
    action="store_true",
    help="Delete all maintenance items. Works only for 'stop' action."
)
args = parser.parse_args()


# --- variables ---
# determine config file path
if args.config_file is not None:
    CONFIG_PATH = args.config_file
elif platform.system() == "Windows":
    CONFIG_PATH = r"C:\ProgramData\zabbix\zabbix_maintenance.yml"
elif platform.system() == "Linux":
    CONFIG_PATH = "/etc/zabbix/zabbix_maintenance.yml"
else:
    CONFIG_PATH = "/etc/zabbix/zabbix_maintenance.yml"

# check if the file exists on 'CONFIG_PATH'
if os.path.isfile(CONFIG_PATH):
    CONFIG_FILE = CONFIG_PATH
else:
    # use the file in current directory
    CONFIG_FILE = "zabbix_maintenance.yml"

# load YAML
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.SafeLoader)
except FileNotFoundError:
    print(f'File "{CONFIG_FILE}" not found!')
    sys.exit(2)

# get hostname from 'CONFIG_FILE'
if "hostname" in config:
    hostname = config["hostname"]
elif args.target_host is not None:
    hostname = args.target_host
else:
    hostname = socket.getfqdn()

# need PERIOD in seconds for zabbix
PERIOD = 3600
if args.time_period is not None:
    HOURS_ARG = args.time_period
else:
    HOURS_ARG = 1

# max hours is 148159
if HOURS_ARG < 148159:
    PERIOD = int(HOURS_ARG * 3600)
else:
    print("Error: maximum size of a period is 148159 hours")
    sys.exit(1)

# set variables from CONFIG_FILE
user = config["user"]
password = config["password"]
server = config["server"]
API_URL = f"https://{server}/api_jsonrpc.php"
# set maintenance object name
# if keyword was provided, use it as suffix in object name
if args.keyword:
    MAINTENANCE_NAME = f"maintenance_{hostname}_{args.keyword}"
else:
    MAINTENANCE_NAME = f"maintenance_{hostname}"

now = int(time.time())
until = int(time.mktime((datetime.now() + timedelta(seconds=PERIOD)).timetuple()))


# --- functions ---


def handle_zabbix_error(data):
    """Check for zabbix API error"""
    if "error" in data:
        error = data["error"]
        print(f"Zabbix API Error {error['code']}: {error['message']}")
        print(f"\t Details: {error['data']}")
        logout_user()
        return True  # error found
    return False  # no error found


def handle_request_execption(err):
    """handle errors for requests"""
    print("An error occured during the request:")
    print(f"\t Type: {type(err).__name__}")
    print(f"\t Message: {err}")
    logout_user()


def login_api_user():
    """Login user and return auth token"""
    headers = {"Content-Type": "application/json-rpc"}
    json = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": user, "password": password},
        "id": 1,
    }
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        auth_token = data["result"]
        return auth_token
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


def logout_user():
    """Because of user.login, we have to proper logout the user to prevent too many open sessions"""
    json = {
        "jsonrpc": "2.0",
        "method": "user.logout",
        "params": [],
        "auth": token,
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        return None
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


def get_host_id(host):
    """get hostid from zabbix server"""
    json = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {"filter": {"host": host}, "output": "extend"},
        "auth": token,
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        result = data["result"]
        if not result:
            print(f'Host "{hostname}" not found!')
            logout_user()
            sys.exit(2)
        else:
            hostid = result[0]["hostid"]
            return hostid
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


def get_maintenance_id(hostid, maintenance_name):
    """get maintenanceid with filter on 'maintenance_name'"""
    # If keyword is None, then show all maintenance items for specified target host
    # If keyword is an empty sting (like 'check -k ""'), then show only the item which
    # matches with hostname in it's name
    # If keyword is provided (not empty), then search for exact matching name
    json = {
        "jsonrpc": "2.0",
        "method": "maintenance.get",
        "params": {
            "output": "extend",
            "selectGroups": "extend",
            "selectTimeperiods": "extend",
            "hostids": hostid,
            "search": {"name": maintenance_name},
            # "startSearch": True if args.keyword is None else False,
            "startSearch": args.keyword is None,
            # "searchWildcardsEnabled": False if args.keyword is None else True,
            "searchWildcardsEnabled": args.keyword is not None,
        },
        "auth": token,
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        result = data["result"]
        if not result:
            print(
                f'Host "{hostname}" with hostid "{hostid}" has no maintenance defined.'
            )
            return None
        # Marco Lucarelli:
        # maintenanceid = result[0]['maintenanceid']
        # collect all "maintenanceid", "name" results and create dict
        maintenanceid = {m["maintenanceid"]: m["name"] for m in result}
        print("Follow maintenance item(s) was found:")
        for maintenanceids, maintenancename in maintenanceid.items():
            print(f"{maintenanceids}: {maintenancename}")
        return maintenanceid
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


def del_maintenance(maintenanceid):
    """delete existing maintenance object"""
    json = {
        "jsonrpc": "2.0",
        "method": "maintenance.delete",
        "params": [maintenanceid],
        "auth": token,
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        print(
            f'Successfully deleted maintenance object with maintenanceid "{maintenanceid}"'
        )
        return True
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


def create_maintenance(maintenance_name, since, till, hostid, timeperiod):
    """create maintenance object with period"""
    json = {
        "jsonrpc": "2.0",
        "method": "maintenance.create",
        "params": {
            "name": maintenance_name,
            "active_since": since,
            "active_till": till,
            "hostids": [hostid],
            "timeperiods": {"period": timeperiod, "timeperiod_type": 0},
        },
        "auth": token,
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    try:
        r = requests.post(API_URL, json=json, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if handle_zabbix_error(data):
            return None
        print(
            f'Added a {timeperiod//3600}:{timeperiod%3600//60:02n} hour maintenance on host "{hostname}"'
        )
        return True
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        handle_request_execption(err)
        return None


# --- main ---

# create auth token
token = login_api_user()

match args.action:
    case "check":
        host_id = get_host_id(hostname)
        get_maintenance_id(host_id, MAINTENANCE_NAME)
    case "stop":
        host_id = get_host_id(hostname)
        maintenance_id = get_maintenance_id(host_id, MAINTENANCE_NAME)
        if maintenance_id is None:
            print("Nothing to do.")
        elif len(maintenance_id) == 1:
            for mid, mname in maintenance_id.items():
                del_maintenance(mid)
        elif args.delete_all:
            for mid, mname in maintenance_id.items():
                del_maintenance(mid)
        else:
            print(
                'Multiple maintenance items was found, '
                'please use "--keyword, -k" or "--delete-all, -rm" to specify your request.\n'
            )
            sys.exit(1)
    case "start":
        host_id = get_host_id(hostname)
        maintenance_id = get_maintenance_id(host_id, MAINTENANCE_NAME)
        if maintenance_id is None:
            create_maintenance(MAINTENANCE_NAME, now, until, host_id, PERIOD)
        elif len(maintenance_id) == 1:
            for mid, mname in maintenance_id.items():
                del_maintenance(mid)
            create_maintenance(MAINTENANCE_NAME, now, until, host_id, PERIOD)
        else:
            print(
                'Multiple maintenance items was found, '
                'please use "--keyword, -k" to specify your request.\n'
            )
            sys.exit(1)

# always log user out
logout_user()
