#!/usr/bin/env python

from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import printer
from panos.panorama import Panorama
from argparse import ArgumentParser
from getpass import getpass

if __name__ == "__main__":
    argparser = ArgumentParser(
        add_help=True,
        description="A simple script running upgrade assurance checks on device.",
    )

    argparser.add_argument(
        "-d, --device",
        type=str,
        dest="device",
        metavar="ADDRESS",
        help="Device (Panorama or Firewall) address",
        required=True,
    )
    argparser.add_argument(
        "-u, --username",
        type=str,
        dest="username",
        metavar="USER",
        help="Username used to connect to a device",
        required=True,
    )
    argparser.add_argument(
        "-p, --password",
        type=str,
        dest="password",
        metavar="PASS",
        help="Password matching the account specified in --username",
        default=None,
    )
    argparser.add_argument(
        "-s, --serial",
        type=str,
        dest="serial",
        metavar="SERIAL",
        help="Serial number of a device, used when --device is pointing to a Panorama",
        default=None,
    )
    argparser.add_argument(
        "-v, --vsys",
        type=str,
        dest="vsys",
        metavar="VSYS",
        help="Name of a VSYS to connect to",
        default=None,
    )

    args = argparser.parse_args()

    address = args.device
    username = args.username
    password = args.password
    if not password:
        password = getpass(f"{username} password: ")

    serial = args.serial
    vsys = args.vsys

    if serial:
        panorama = Panorama(
            hostname=address, api_password=password, api_username=username
        )
        firewall = FirewallProxy(serial=serial)
        panorama.add(firewall)
    else:
        firewall = FirewallProxy(
            hostname=address, api_password=password, api_username=username, vsys=vsys
        )

    check_node = CheckFirewall(firewall)

    checks = [
        "all",
        "panorama",
        "ntp_sync",
        "candidate_config",
        "active_support",
        # checks below have optional configuration
        {"ha": {"skip_config_sync": True, "ignore_non_functional": True}},
        {"content_version": {"version": "8635-7675"}},
        {"expired_licenses": {"skip_licenses": ["Threat Preventon"]}},
        {"planes_clock_sync": {"diff_threshold": 2}},
        {"free_disk_space": {"image_version": "10.1.6-h6"}},
        {"certificates_size": {"minimum_key_size": 1024}},
        # checks below require additional configuration
        {
            "session_exist": {
                "source": "134.238.135.137",
                "destination": "10.1.0.4",
                "dest_port": "80",
            }
        },
        {"arp_entry_exist": {"ip": "10.0.1.1"}},
        {"ip_sec_tunnel_status": {"tunnel_name": "ipsec_tun"}},
    ]

    check_readiness = check_node.run_readiness_checks(
        checks_configuration=checks,
        # report_style=True
    )
    printer(check_readiness)
    node_state = check_node.check_is_ha_active(
        skip_config_sync=True,
        ignore_non_functional=True
        )
    print(bool(node_state), node_state)
