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

        # {"license": {
        #     "properties": ["!serial", "!issued", "!authcode", "!expires", "!custom", "non-existing"] # exclude higher level
        # }},
        # {"license": {
        #     "properties": ["!serial", "!issued", "!authcode", "!expires", "non-existing", "!_Log_Storage_TB"] # works in multi-levels
        # }},
        # {"license": {
        #     "properties": ["all"]
        # }},
        # {"license": {
        #     "properties": ["!serial", "!issued", "!authcode", "!expires", "non-existing"] # invalid config is ignored and all is appended if all other are valid exclusions..
        # }},
        # {"license": {
        #     "properties": ["serial", "non-existing"] # compare only requested
        # }},
        # {"license": {
        #     "properties": ["custom"]  # if key exists in some sub-dicts, it will compare all the keys for the other dicts since this will be treated as non-existing key and ignored! NOTE: now it only ignores top level for added/missing
        # }},
        # {"license": {
        #     "properties": ["!issued", "all"] # compare all except
        # }},
        # {"license": {
        #     "properties": ["!issued", "serial"] # skip one and compare specific ones
        # }},

        # {"license": {
        #     "properties": ["Logging Service", "!custom"]  # combination with parent
        # }},
        # "!license",
        # "license",
        # {"license": {
        #     "properties": ["!Logging Service","!X feature"]
        # }},

        ######## Top level keys - not intented but works
        # {"license": {
        #     "properties": ["Logging Service"]  # even works for parent level
        # }},
        # {"license": {
        #     "properties": ["!Logging Service"]  # even works for parent level
        # }},
        # {"license": {
        #     "properties": ["issued", "PAN-DB URL Filtering"]  # even works for parent level - but without multi level
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
        #     "properties": ["!_Log_Storage_TB"]  # works..
        # }},
        # {"license": {
        #     "properties": ["_Log_Storage_TB"]  # works
        # }},
        # {"license": {
        #     "properties": ["_Log_Storage_TB","issued"]  # works
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
        #     "properties": ["all"]  # works
        # }},
        # {"license": {
        #     "properties": ["!logtype"]  # works
        # }},
        {"license": {
            "properties": ["!Logging Service", "issued"]  # works
        }},

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
