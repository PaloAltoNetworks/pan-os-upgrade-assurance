#!/usr/bin/env python

from panos_upgrade_assurance.utils import printer, SnapType
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare
import json


def load_snap(fname: str) -> dict:
    with open(fname, "r") as file:
        snap = json.loads(file.read())
    return snap


if __name__ == "__main__":
    snapshots = {"fw1": load_snap("fw1.snapshot"), "fw2": load_snap("fw2.snapshot")}

    reports = [
        "all",
        {"ip_sec_tunnels": {"properties": ["state"], "count_change_threshold": 5}},
        {"arp_table": {"properties": ["!ttl"], "count_change_threshold": 10}},
        {"nics": {"count_change_threshold": 10}},
        {"license": {"properties": ["!serial"]}},

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
        #     "properties": ["!issued", "all"] # compare all except
        # }},
        # {"license": {
        #     "properties": ["!issued", "serial"] # skip one and compare specific ones
        # }},
        # {"license": {
        #     "properties": ["Logging Service"]  # even works for parent level
        # }},
        # {"license": {
        #     "properties": ["Logging Service", "!custom"]  # combination with parent
        # }},
        # "!license",
        # "license",

        {"routes": {"properties": ["!flags"], "count_change_threshold": 10}},
        "!content_version",
        {
            "session_stats": {
                "thresholds": [
                    {"num-max": 10},
                    {"num-tcp": 10},
                ]
            }
        },
    ]

    compare = SnapshotCompare(
        snapshots["fw1"],
        snapshots["fw2"],
    )
    report = compare.compare_snapshots(reports)

    printer(report)
