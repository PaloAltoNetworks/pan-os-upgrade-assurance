#!/usr/bin/env python

from panos_upgrade_assurance.firewall_proxy import FirewallProxy
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

    proxy = FirewallProxy(address, username, password)


    p_config = proxy.is_panorama_configured()
    print(f'\n  panorama configured: {p_config}')

    if p_config:
        print(f'\n  panorama connected: {proxy.is_panorama_connected()}')

    print(f'\n  pending changed: {proxy.is_pending_changes()}')
    print(f'\n  full commit pending: {proxy.is_full_commit_required()}')

    print(f'\n  ha configuration\n{proxy.get_ha_configuration()}')

    print(f'\n  nic statuses\n{proxy.get_nics()}')

    print(f'\n  licenses information\n{proxy.get_licenses()}')

    print(f'\n  routes information\n{proxy.get_routes()}')

    print(f'\n  arp entries information\n{proxy.get_arp_table()}')

    print(f'\n  session information\n{proxy.get_session_stats()}')

    print(f'\n  session information\n{proxy.get_sessions()}')

    print(f'\n  tunnels information\n{proxy.get_tunnels()}')

    print(f'\n  NTP SRVs information\n{proxy.get_ntp_servers()}')

    print(f'\n  content DB version: {proxy.get_content_db_version()}')

    print(f'\n  latest availble content DB version: {proxy.get_latest_available_content_version()}')

    print(f'\n  disk utilization: {proxy.get_disk_utilization()}')

    print(f'\n  available image versions: {proxy.get_available_image_data()}')

    print(f'\n  management plane clock: {proxy.get_mp_clock()}')

    print(f'\n  data plane clock: {proxy.get_dp_clock()}')

    print()