#!/usr/bin/env python

from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import  printer, CheckType
import sys

if __name__ == '__main__':


    if len(sys.argv) != 4:
        print('Wrong parameters passed.')
        print('This script takes 3 parameters in the following format:')
        print(f'\t{sys.argv[0]} fw_address username password')
        exit(1)

    address = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    checks = [
        'all',
        'panorama',
        'ha',
        'ntp_sync',
        'candidate_config',
        'expired_licenses',
        'content_version',
        # all tests below require config
        {'free_disk_space':{
            'image_version': '10.1.6-h6'
        }},
        {'session_exist': {
            'source': '134.238.135.137',
            'destination': '10.1.0.4',
            'dest_port': '80'
        }},
        {'arp_entry_exist': {'ip': '10.0.1.1'} },
        {'ip_sec_tunnel_status': {
            'tunnel_name': 'ipsec_tun'
        }}
    ]

    check_node = CheckFirewall(FirewallProxy(address, username, password))
    check_readiness = check_node.run_readiness_checks(
        checks_configuration=checks, 
        # report_style=True
    )
    printer(check_readiness)
