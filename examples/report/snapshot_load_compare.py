#!/usr/bin/env python

from panos_upgrade_assurance.utils import printer, SnapType
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare
import json


def load_snap(fname: str) -> dict:
    with open(fname, "r") as file:
        snap = json.loads(file.read())
    return snap


if __name__ == "__main__":
    # snapshots = {"fw1": load_snap("fw1.snapshot"), "fw2": load_snap("fw2.snapshot")}
    # snapshots = {"fw1": load_snap("arp_table_left.snapshot"), "fw2": load_snap("arp_table_right.snapshot")}
    # snapshots = {"fw1": load_snap("lic-1.json"), "fw2": load_snap("lic-2.json")}
    snapshots = {"fw1": load_snap("lic-5.json"), "fw2": load_snap("lic-6.json")}


    reports = [
        # "all",
        # {"ip_sec_tunnels": {"properties": ["state"], "count_change_threshold": 5}},
        # {"arp_table": {"properties": ["!ttl"], "count_change_threshold": 10}},
        # {"nics": {"count_change_threshold": 10}},
        # {"license": {"properties": ["!serial"]}},

        # NOTE lic-* files and below tests are added for testing during review - will be removed afterwards

        # "!license",
        # "license",
        ######## Top level keys - not intented but works
        # {"license": {
        #     "properties": ["Logging Service"]  # even works for parent level
        # }},
        # {"license": {
        #     "properties": ["!Logging Service"]  # also support if property exists in different levels in different dicts
        # }},
        # {"license": {
        #     "properties": ["issued", "PAN-DB URL Filtering"]  # multi-level "AND" operation (combination with parent) for properties is not supported on purpose - "PAN-DB URL Filtering" diff will be made for all its attributes since its the parent
        # }},
        # {"license": {
        #     "properties": ["X feature"]
        # }},
        # {"license": {
        #     "properties": ["!X feature"]
        # }},
        # {"license": {
        #     "properties": ["C feature"]
        # }},

        ######## 1st and 2nd level keys
        # {"license": {
        #     "properties": ["!_Log_Storage_TB"]  # works
        # }},
        # {"license": {
        #     "properties": ["_Log_Storage_TB"]  # works
        # }},
        # {"license": {
        #     "properties": ["_Log_Storage_TB","issued"]  # works
        # }},
        # {"license": {
        #     "properties": ["issued", "!logtype"]  # works
        # }},
        # {"license": {
        #     "properties": ["serial", "!logtype"]  # works
        # }},
        # {"license": {
        #     "properties": ["custom"]  # works
        # }},
        # {"license": {
        #     "properties": ["!custom"]  # works
        # }},
        # {"license": {
        #     "properties": ["alogging"]  # works
        # }},
        # {"license": {
        #     "properties": ["blogging"]  # works
        # }},
        # {"license": {
        #     "properties": ["something"]  # since no such key is there it passes - works
        # }},
        # {"license": {
        #     "properties": ["serial", "non-existing"] # works - compare only requested
        # }},
        # {"license": {
        #     "properties": ["all"]  # works
        # }},
        # {"license": {
        #     "properties": ["!issued", "all"] # works - compare all except
        # }},
        # {"license": {
        #     "properties": ["!logtype"]  # works
        # }},
        {"license": {
            "properties": ["!Logging Service", "issued"]  # works
        }},
        # {"license": {
        #     "properties": ["authcode"]  # works when one of them is null
        # }},

        # {"routes": {"properties": ["!flags"], "count_change_threshold": 10}},
        # "!content_version",
        # {
        #     "session_stats": {
        #         "thresholds": [
        #             {"num-max": 10},
        #             {"num-tcp": 10},
        #         ]
        #     }
        # },
    ]

    compare = SnapshotCompare(
        snapshots["fw1"],
        snapshots["fw2"],
    )
    report = compare.compare_snapshots(reports)

    printer(report)
