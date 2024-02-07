#!/usr/bin/env python

from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos.panorama import Panorama
from argparse import ArgumentParser
from getpass import getpass
from pprint import pprint

if __name__ == "__main__":
    argparser = ArgumentParser(
        add_help=True,
        description="A simple script running all supported low level FirewallProxy class methods.",
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

    p_config = firewall.is_panorama_configured()
    print(f"\n  panorama configured: {p_config}")

    if p_config:
        print(f"\n  panorama connected: {firewall.is_panorama_connected()}")

    print(f"\n  pending changed: {firewall.is_pending_changes()}")
    print(f"\n  full commit pending: {firewall.is_full_commit_required()}")

    print(f"\n  ha configuration\n{firewall.get_ha_configuration()}")

    print(f"\n  nic statuses\n{firewall.get_nics()}")

    print(f"\n  licenses information\n{firewall.get_licenses()}")

    print(f"\n  support license information\n{firewall.get_support_license()}")

    print(f"\n  routes information\n{firewall.get_routes()}")

    print(f"\n  BGP peers information\n{firewall.get_bgp_peers()}")

    print(f"\n  arp entries information\n{firewall.get_arp_table()}")

    print(f"\n  session information\n{firewall.get_session_stats()}")

    print(f"\n  session information\n{firewall.get_sessions()}")

    print(f"\n  tunnels information\n{firewall.get_tunnels()}")

    print(f"\n  NTP SRVs information\n{firewall.get_ntp_servers()}")

    print(f"\n  content DB version: {firewall.get_content_db_version()}")

    print(f"\n  latest availble content DB version: {firewall.get_latest_available_content_version()}")

    print(f"\n  disk utilization: {firewall.get_disk_utilization()}")

    print(f"\n  available image versions: {firewall.get_available_image_data()}")

    print(f"\n  management plane clock: {firewall.get_mp_clock()}")

    print(f"\n  data plane clock: {firewall.get_dp_clock()}")

    print(f"\n  certificates: {firewall.get_certificates()}")

    print(f"\n  dynamic schedules: {firewall.get_update_schedules()}")

    print(f"\n  jobs: {firewall.get_jobs()}")


    print()
