# Examples

This folder contains sample python code using **PanOS Upgrade Assurance** libraries. It's meant to provide a quick-starter, hence in most cases (to not over-complicate the code) defaults will be used.

**Note.**\
These examples were not written with security in mind. Please take caution when providing credentials.

## Examples list

folder | description
--- | ---
[`low_level_methods`](./low_level_methods/) | shows how to run the methods provided by the [`FirewallProxy`](../panos_upgrade_assurance/firewall_proxy.py) class - direct interaction with a device.
[`readiness_checks`](./readiness_checks/) | shows how to run readiness checks provided by the [`CheckFirewall`](../panos_upgrade_assurance/check_firewall.py) class
[`report`](./report/) | offline example, shows [`SnapshotCompare`](../panos_upgrade_assurance/snapshot_compare.py) class possibilities by generating a report from to saved snapshots (sample snapshots are provided)

## Usage

The [`low_level_methods`](./low_level_methods/) and [`readiness_checks`](./readiness_checks/) examples require a connection to a Palo Alto Next Generation Firewall. The IP address and credentials are provided as script parameters, for example:

```sh
./run_readiness_checks.py 1.2.3.4 username password
```

The [`report`](./report/) example does not take any parameters. The snapshots used in this script are hardcoded.

