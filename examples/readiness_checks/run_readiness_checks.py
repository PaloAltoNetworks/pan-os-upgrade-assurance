#!/usr/bin/env python

from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import printer
from panos.panorama import Panorama
from argparse import ArgumentParser
from getpass import getpass
from pprint import pprint

if __name__ == "__main__":

    address = "13.74.81.226"
    password = "pek_vrZsxl2emqud"
    firewall = FirewallProxy(
        hostname=address, api_password=password, api_username="panadmin"
    )

    check_node = CheckFirewall(firewall)

    checks = [
        # "planes_clock_sync",
        {"dynamic_updates": {
            "test_window": 500
        }}
    ]

    pprint(firewall.get_update_schedules())
    pprint(firewall.get_mp_clock())
    # exit()
    check_readiness = check_node.run_readiness_checks(
        checks_configuration=checks,
        # report_style=True
    )
    printer(check_readiness)
