snap1 = {
    "ip_sec_tunnels": {
        "ipsec_tun": {
            "peerip": "10.26.129.5",
            "name": "ipsec_tun",
            "outer-if": "ethernet1/2",
            "gwid": "1",
            "localip": "0.0.0.1",
            "state": "init",
            "inner-if": "tunnel.1",
            "mon": "on",
            "owner": "1",
            "id": "1",
        },
        "sres": {
            "peerip": "1.2.3.4",
            "name": "sres",
            "outer-if": "ethernet1/3",
            "gwid": "2",
            "localip": "5.6.7.8",
            "state": "init",
            "inner-if": "tunnel.2",
            "mon": "off",
            "owner": "1",
            "id": "2",
        },
        "priv_tun": {
            "peerip": "10.26.128.5",
            "name": "priv_tun",
            "outer-if": "ethernet1/4",
            "gwid": "3",
            "localip": "0.0.0.1",
            "state": "active",
            "inner-if": "tunnel.3",
            "mon": "on",
            "owner": "1",
            "id": "3",
        }
    },
    "routes": {
        "default_0.0.0.0/0_ethernet1/3_10.26.129.129": {
            "virtual-router": "default",
            "destination": "0.0.0.0/0",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast",
        },
        "default_10.26.129.0/25_ethernet1/2_10.26.129.1": {
            "virtual-router": "default",
            "destination": "10.26.129.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast",
        },
        "default_10.26.130.0/25_ethernet1/2_10.26.129.1": {
            "virtual-router": "default",
            "destination": "10.26.130.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast",
        },
        "default_168.63.129.16/32_ethernet1/3_10.26.129.129": {
            "virtual-router": "default",
            "destination": "168.63.129.16/32",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast",
        },
    },
    "bgp_peers": {
        "default_Peer-Group1_Peer1": {
            "@peer": "Peer1",
            "@vr": "default",
            "peer-group": "Peer-Group1",
            "peer-router-id": "169.254.8.2",
            "remote-as": "64512",
            "status": "Established",
            "status-duration": "3804",
            "password-set": "no",
            "passive": "no",
            "multi-hop-ttl": "2",
            "peer-address": "169.254.8.2:35355",
            "local-address": "169.254.8.1:179",
            "reflector-client": "not-client",
            "same-confederation": "no",
            "aggregate-confed-as": "yes",
            "peering-type": "Unspecified",
            "connect-retry-interval": "15",
            "open-delay": "0",
            "idle-hold": "15",
            "prefix-limit": "5000",
            "holdtime": "30",
            "holdtime-config": "30",
            "keepalive": "10",
            "keepalive-config": "10",
            "msg-update-in": "2",
            "msg-update-out": "1",
            "msg-total-in": "385",
            "msg-total-out": "442",
            "last-update-age": "3",
            "last-error": None,
            "status-flap-counts": "2",
            "established-counts": "1",
            "ORF-entry-received": "0",
            "nexthop-self": "no",
            "nexthop-thirdparty": "yes",
            "nexthop-peer": "no",
            "config": {"remove-private-as": "no"},
            "peer-capability": {
                "list": [
                    {"capability": "Multiprotocol Extensions(1)", "value": "IPv4 Unicast"},
                    {"capability": "Route Refresh(2)", "value": "yes"},
                    {"capability": "4-Byte AS Number(65)", "value": "64512"},
                    {"capability": "Route Refresh (Cisco)(128)", "value": "yes"},
                ]
            },
            "prefix-counter": {
                "entry": {
                    "@afi-safi": "bgpAfiIpv4-unicast",
                    "incoming-total": "2",
                    "incoming-accepted": "2",
                    "incoming-rejected": "0",
                    "policy-rejected": "0",
                    "outgoing-total": "0",
                    "outgoing-advertised": "0",
                }
            },
        }
    },
    "session_stats": {
        "tmo-5gcdelete": "15",
        "tmo-sctpshutdown": "60",
        "tmo-tcp": "3600",
        "tmo-tcpinit": "5",
        "pps": "2",
        "tmo-tcp-delayed-ack": "250",
        "num-max": "819200",
        "age-scan-thresh": "80",
        "tmo-tcphalfclosed": "120",
        "num-active": "3",
        "tmo-sctp": "3600",
        "dis-def": "60",
        "num-mcast": "0",
        "icmp-unreachable-rate": "200",
        "tmo-tcptimewait": "15",
        "age-scan-ssf": "8",
        "tmo-udp": "30",
        "vardata-rate": "10485760",
        "age-scan-tmo": "10",
        "dis-sctp": "30",
        "dis-tcp": "90",
        "tcp-reject-siw-thresh": "4",
        "num-udp": "0",
        "tmo-sctpcookie": "60",
        "num-http2-5gc": "0",
        "tmo-icmp": "6",
        "max-pending-mcast": "0",
        "age-accel-thresh": "80",
        "num-gtpc": "0",
        "tmo-def": "30",
        "num-predict": "0",
        "age-accel-tsf": "2",
        "num-icmp": "0",
        "num-gtpu-active": "0",
        "tmo-cp": "30",
        "num-pfcpc": "0",
        "tmo-sctpinit": "5",
        "tmo-tcp-unverif-rst": "30",
        "num-bcast": "0",
        "cps": "0",
        "num-installed": "47",
        "num-tcp": "50",
        "dis-udp": "60",
        "num-sctp-assoc": "0",
        "num-sctp-sess": "0",
        "tmo-tcphandshake": "10",
        "kbps": "1",
        "num-gtpu-pending": "0",
    },
    "content_version": {"version": "8647-7730"},
    "arp_table": {
        "ethernet1/1_10.0.2.1": {
            "interface": "ethernet1/1",
            "ip": "10.0.2.1",
            "mac": "12:34:56:78:9a:bc",
            "port": "ethernet1/1",
            "status": "e",
            "ttl": "19",
        },
        "ethernet1/2_10.0.1.1": {
            "interface": "ethernet1/2",
            "ip": "10.0.1.1",
            "mac": "12:34:56:78:9a:bc",
            "port": "ethernet1/2",
            "status": "c",
            "ttl": "153",
        },
    },
    "license": {
        "DNS Security": {
            "feature": "DNS Security",
            "description": "Palo Alto Networks DNS Security License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "AutoFocus Device License": {
            "feature": "AutoFocus Device License",
            "description": "AutoFocus Device License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "September 25, 2031",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": "S7892156",
        },
        "Premium": {
            "feature": "Premium",
            "description": "24 x 7 phone support; advanced replacement hardware service",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "GlobalProtect Gateway": {
            "feature": "GlobalProtect Gateway",
            "description": "GlobalProtect Gateway License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "Threat Prevention": {
            "feature": "Threat Prevention",
            "description": "Threat Prevention",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "WildFire License": {
            "feature": "WildFire License",
            "description": "WildFire signature feed, integrated WildFire logs, WildFire API",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "PA-VM": {
            "feature": "PA-VM",
            "description": "Standard VM-300",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "Never",
            "expired": "no",
            "authcode": None,
        },
        "PAN-DB URL Filtering": {
            "feature": "PAN-DB URL Filtering",
            "description": "Palo Alto Networks URL Filtering License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "Logging Service": {
            "feature": "Logging Service",
            "description": "Device Logging Service",
            "custom": {
                "_Log_Storage_TB": "7"
            },
            "serial": "007257000334668",
            "issued": "June 29, 2022",
            "expires": "August 04, 2024",
            "expired": "no",
            "authcode": None,
        },
    },
    "nics": {"ethernet1/1": "up", "ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"},
}


snap2 = {
    "ip_sec_tunnels": {
        "ipsec_tun": {
            "peerip": "10.26.129.5",
            "name": "ipsec_tun",
            "outer-if": "ethernet1/2",
            "localip": "0.0.0.1",
            "state": "init",
            "inner-if": "tunnel.1",
            "mon": "off",
            "owner": "1",
            "id": "1",
        },
        "priv_tun": {
            "peerip": "10.26.128.5",
            "name": "priv_tun",
            "outer-if": "ethernet1/4",
            "gwid": "3",
            "localip": "0.0.0.1",
            "state": "init",
            "inner-if": "tunnel.3",
            "mon": "on",
            "owner": "1",
            "id": "3",
        }
    },
    "routes": {
        "default_0.0.0.0/0_ethernet1/3_10.26.129.129": {
            "virtual-router": "default",
            "destination": "0.0.0.0/0",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast",
        },
        "default_10.26.129.0/25_ethernet1/2_10.26.129.1": {
            "virtual-router": "default",
            "destination": "10.26.129.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast",
        },
        "default_10.26.130.0/25_ethernet1/2_10.26.129.1": {
            "virtual-router": "default",
            "destination": "10.26.130.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast",
        },
        "default_168.63.129.16/32_ethernet1/3_10.26.129.129": {
            "virtual-router": "default",
            "destination": "168.63.129.16/32",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast",
        },
    },
    "bgp_peers": {
        "default_Peer-Group1_Peer1": {
            "@peer": "Peer1",
            "@vr": "default",
            "peer-group": "Peer-Group1",
            "peer-router-id": "169.254.8.2",
            "remote-as": "64512",
            "status": "Idle",
            "status-duration": "0",
            "password-set": "no",
            "passive": "no",
            "multi-hop-ttl": "2",
            "peer-address": "169.254.8.2",
            "local-address": "169.254.8.1",
            "reflector-client": "not-client",
            "same-confederation": "no",
            "aggregate-confed-as": "yes",
            "peering-type": "Unspecified",
            "connect-retry-interval": "15",
            "open-delay": "0",
            "idle-hold": "15",
            "prefix-limit": "5000",
            "holdtime": "0",
            "holdtime-config": "30",
            "keepalive": "0",
            "keepalive-config": "10",
            "msg-update-in": "0",
            "msg-update-out": "0",
            "msg-total-in": "0",
            "msg-total-out": "0",
            "last-update-age": "0",
            "last-error": None,
            "status-flap-counts": "0",
            "established-counts": "0",
            "ORF-entry-received": "0",
            "nexthop-self": "no",
            "nexthop-thirdparty": "yes",
            "nexthop-peer": "no",
            "config": {"remove-private-as": "no"},
            "peer-capability": {
                "list": [
                    {"capability": "Multiprotocol Extensions(1)", "value": "IPv4 Unicast"},
                    {"capability": "Route Refresh(2)", "value": "yes"},
                    {"capability": "4-Byte AS Number(65)", "value": "64512"},
                    {"capability": "Route Refresh (Cisco)(128)", "value": "yes"},
                ]
            },
            "prefix-counter": {
                "entry": {
                    "@afi-safi": "bgpAfiIpv4-unicast",
                    "incoming-total": "2",
                    "incoming-accepted": "2",
                    "incoming-rejected": "0",
                    "policy-rejected": "0",
                    "outgoing-total": "0",
                    "outgoing-advertised": "0",
                }
            },
        }
    },
    "session_stats": {
        "tmo-5gcdelete": "15",
        "tmo-sctpshutdown": "60",
        "tmo-tcp": "3600",
        "tmo-tcpinit": "5",
        "pps": "0",
        "tmo-tcp-delayed-ack": "250",
        "num-max": "819200",
        "age-scan-thresh": "80",
        "tmo-tcphalfclosed": "120",
        "num-active": "4",
        "tmo-sctp": "3600",
        "dis-def": "60",
        "num-mcast": "0",
        "icmp-unreachable-rate": "200",
        "tmo-tcptimewait": "15",
        "age-scan-ssf": "8",
        "tmo-udp": "30",
        "vardata-rate": "10485760",
        "age-scan-tmo": "10",
        "dis-sctp": "30",
        "dis-tcp": "90",
        "tcp-reject-siw-thresh": "4",
        "num-udp": "0",
        "tmo-sctpcookie": "60",
        "num-http2-5gc": "0",
        "tmo-icmp": "6",
        "max-pending-mcast": "0",
        "age-accel-thresh": "80",
        "num-gtpc": "0",
        "tmo-def": "30",
        "num-predict": "0",
        "age-accel-tsf": "2",
        "num-icmp": "0",
        "num-gtpu-active": "0",
        "tmo-cp": "30",
        "num-pfcpc": "0",
        "tmo-sctpinit": "5",
        "tmo-tcp-unverif-rst": "30",
        "num-bcast": "0",
        "cps": "0",
        "num-installed": "93",
        "num-tcp": "70",
        "dis-udp": "60",
        "num-sctp-assoc": "0",
        "num-sctp-sess": "0",
        "tmo-tcphandshake": "10",
        "kbps": "0",
        "num-gtpu-pending": "0",
    },
    "content_version": {"version": "8647-7730"},
    "arp_table": {
        "ethernet1/1_10.0.2.11": {
            "interface": "ethernet1/1",
            "ip": "10.0.2.11",
            "mac": "(incomplete)",
            "port": "ethernet1/1",
            "status": "i",
            "ttl": "1",
        }
    },
    "license": {
        "DNS Security": {
            "feature": "DNS Security",
            "description": "Palo Alto Networks DNS Security License",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "Premium": {
            "feature": "Premium",
            "description": "24 x 7 phone support; advanced replacement hardware service",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "GlobalProtect Gateway": {
            "feature": "GlobalProtect Gateway",
            "description": "GlobalProtect Gateway License",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "Threat Prevention": {
            "feature": "Threat Prevention",
            "description": "Threat Prevention",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "WildFire License": {
            "feature": "WildFire License",
            "description": "WildFire signature feed, integrated WildFire logs, WildFire API",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "PA-VM": {
            "feature": "PA-VM",
            "description": "Standard VM-300",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "Never",
            "expired": "no",
            "authcode": None,
        },
        "PAN-DB URL Filtering": {
            "feature": "PAN-DB URL Filtering",
            "description": "Palo Alto Networks URL Filtering License",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None,
        },
        "Logging Service": {
            "feature": "Logging Service",
            "description": "Device Logging Service",
            "custom": {
                "_Log_Storage_TB": "9"
            },
            "serial": "007257000334667",
            "issued": "June 29, 2022",
            "expires": "August 04, 2024",
            "expired": "no",
            "authcode": None,
        },
    },
    "nics": {"ethernet1/1": "down", "ethernet1/2": "up", "ethernet1/3": "up"},
}
