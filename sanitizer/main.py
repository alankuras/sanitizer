#!/usr/bin/env python3
# ------------------------------------------- #
#
# Logfile Sanitizer
#
#
# v.1.3 June 2022
# 
# ------------------------------------------- #
import configparser
import json
import zipfile
from shutil import chown, rmtree
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from log_file_factory import LogFileFactory, SOURCE
from datetime import datetime, timezone


argparse_help = """
This tool does the sanitization of logs

Usage:

python sanitizer/main.py -s -l /tmp
    above will sanitize and put the logs into /tmp from all namespaces defined in config.cfg

python sanitizer/main.py -d -l .
    above will dump logs without sanitization creating the folder structure in your current working directory

python sanitizer/main.py -s -l /tmp -n "kube-public, kube-system"
    above will sanitize and put the logs into /tmp from namespaces kube-public and kube-system, ignoring namespaces from config.cfg

additional examples:
python sanitizer/main.py -s -l . --since 5h --config ./config.cfg
python sanitizer/main.py -s -l /tmp --since=60m
python sanitizer/main.py -s -l /tmp --since-time=2022-02-21T10:00:00.00Z

# you can dump/sanitize both logs, current and previous, and will be added to the same zip file
python3 sanitizer/main.py -d -l . --zip --since=60m
python3 sanitizer/main.py -d -l . --since=240m --previous --zip --chown

# dump logs from default namespace, creating files in your cwd, for the last 4 hours, without gzip compression of each file, adding everything to zip, changing the owner
python3 sanitizer/main.py --dump -n default -l . --since=240m --zip --chown --uncompressed

"""
parser = ArgumentParser(description=argparse_help, formatter_class=RawDescriptionHelpFormatter)
parser.add_argument("--namespaces", "-n", help="Alternative namespace list, namespaces from config will be ignored", required=False, default="")
parser.add_argument("--previous", "-p", help="dump pod logs (stdout) for a previous instantiation of a container", action='store_true', required=False)
parser.add_argument("--config", "-c", help="Alternative config file", required=False, default="")
parser.add_argument("--zip", "-z", help="Compress the directory with logs afterwards", action='store_true', required=False)
parser.add_argument("--chown", "-ch", help="Only works with --zip/-z, changing the uid:gid of a zip file as specified in config", action='store_true', required=False)
parser.add_argument("--uncompressed", "-u", help="By default dump and sanitization saves logs as compressed gzip files, this forbids the compression", action='store_true', required=False)

filter_group = parser.add_mutually_exclusive_group()
filter_group.add_argument("--since", help="Only return logs newer than a relative duration like 5s, 2m, or 3h. Only one of since-time / since may be used")
filter_group.add_argument("--since-time", help="Only return logs after a specific date (RFC3339). Only one of since-time / since may be used")

parser_req = parser.add_argument_group("mandatory arguments")
parser_req.add_argument("--logs_location", "-l", help="Path to directory where logs will be created", required=True)

action_group = parser_req.add_mutually_exclusive_group(required=True)
action_group.add_argument("--sanitize", "-s", help="Dump and sanitize logs", action='store_true')
action_group.add_argument("--dump", "-d", help="Dump only (without sanitization)", action='store_true')

args = parser.parse_args()

config = configparser.ConfigParser()
if args.config:
    config.read(Path(args.config))
else:
    config.read(Path(Path(__file__).parent, "config.cfg"))

regexes = json.loads(config.get("DEFAULT", "regexes"))

if args.namespaces:
    namespaces = args.namespaces
else:
    namespaces = json.loads(config.get("DEFAULT", "namespaces"))

timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H%z")
logs_location = Path(
    args.logs_location,
    timestamp
)
logs_location.mkdir(parents=True, exist_ok=True)

log_file_factory = LogFileFactory(
    source=SOURCE.OPENSHIFT,
    logs_location=logs_location,
    namespaces=namespaces,
    regexes=regexes,
    filters=(args.since, args.since_time, args.previous)
)

compress = False if args.uncompressed else True
for log_file in log_file_factory:
    if args.sanitize:
        log_file.sanitize_and_dump(compress=compress)
    else:
        log_file.dump(compress=compress)


if args.zip:
    with zipfile.ZipFile(Path(logs_location.parent, f"{timestamp}.zip"), "w", zipfile.ZIP_DEFLATED) as zip_file:
        for entry in logs_location.rglob("*"):
            zip_file.write(entry, entry.relative_to(logs_location))
    if args.chown:
        try:
            chown(
                Path(logs_location.parent, f"{timestamp}.zip"),
                user=json.loads(config.get("DEFAULT", "uid")),
                group=json.loads(config.get("DEFAULT", "gid"))
            )
        except Exception as e:
            print(f"Exception occured while changing the owner of zip file : {e}")
    rmtree(logs_location)
