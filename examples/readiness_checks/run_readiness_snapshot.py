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
        description="A simple script running upgrade assurance snapshot on device.",
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

    areas = [
        # 'all',
        "nics",
        "routes",
        "fib_routes",
        "bgp_peers",
        "license",
        "arp_table",
        "content_version",
        "session_stats",
        "ip_sec_tunnels",
    ]

    snap = check_node.run_snapshots(snapshots_config=areas)
    printer(snap)
