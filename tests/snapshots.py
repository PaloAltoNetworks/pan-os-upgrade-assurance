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
            "mon": "off",
            "owner": "1",
            "id": "1"
        },
        "sres": {
            "peerip": "1.2.3.4",
            "name": "sres",
            "outer-if": "ethernet1/3",
            "gwid": "2",
            "localip": "0.0.0.0",
            "state": "init",
            "inner-if": "tunnel.2",
            "mon": "off",
            "owner": "1",
            "id": "2"
        }
    },
    "routes": {
        "default_0.0.0.0/0_ethernet1/3": {
            "virtual-router": "default",
            "destination": "0.0.0.0/0",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast"
        },
        "default_10.26.129.0/25_ethernet1/2": {
            "virtual-router": "default",
            "destination": "10.26.129.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast"
        },
        "default_10.26.130.0/25_ethernet1/2": {
            "virtual-router": "default",
            "destination": "10.26.130.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast"
        },
        "default_168.63.129.16/32_ethernet1/3": {
            "virtual-router": "default",
            "destination": "168.63.129.16/32",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast"
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
        "num-gtpu-pending": "0"
    },
    "content_version": {
        "version": "8647-7730"
    },
    "arp_table": {
        "ethernet1/1_10.0.2.1": {
            "interface": "ethernet1/1",
            "ip": "10.0.2.1",
            "mac": "12:34:56:78:9a:bc",
            "port": "ethernet1/1",
            "status": "e",
            "ttl": "19"
        },
        "ethernet1/2_10.0.1.1": {
            "interface": "ethernet1/2",
            "ip": "10.0.1.1",
            "mac": "12:34:56:78:9a:bc",
            "port": "ethernet1/2",
            "status": "c",
            "ttl": "153"
        }
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
            "authcode": None
        },
        "AutoFocus Device License": {
            "feature": "AutoFocus Device License",
            "description": "AutoFocus Device License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "September 25, 2031",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": "S7892156"
        },
        "Premium": {
            "feature": "Premium",
            "description": "24 x 7 phone support; advanced replacement hardware service",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "GlobalProtect Gateway": {
            "feature": "GlobalProtect Gateway",
            "description": "GlobalProtect Gateway License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "Threat Prevention": {
            "feature": "Threat Prevention",
            "description": "Threat Prevention",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "WildFire License": {
            "feature": "WildFire License",
            "description": "WildFire signature feed, integrated WildFire logs, WildFire API",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "PA-VM": {
            "feature": "PA-VM",
            "description": "Standard VM-300",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "Never",
            "expired": "no",
            "authcode": None
        },
        "PAN-DB URL Filtering": {
            "feature": "PAN-DB URL Filtering",
            "description": "Palo Alto Networks URL Filtering License",
            "serial": "007257000334668",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        }
    },
    "nics": {
        "ethernet1/1": "up",
        "ethernet1/2": "up",
        "ethernet1/3": "up",
        "tunnel": "up"
    }
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
            "id": "1"
        }
    },
    "routes": {
        "default_0.0.0.0/0_ethernet1/3": {
            "virtual-router": "default",
            "destination": "0.0.0.0/0",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast"
        },
        "default_10.26.129.0/25_ethernet1/2": {
            "virtual-router": "default",
            "destination": "10.26.129.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast"
        },
        "default_10.26.130.0/25_ethernet1/2": {
            "virtual-router": "default",
            "destination": "10.26.130.0/25",
            "nexthop": "10.26.129.1",
            "metric": "10",
            "flags": "A",
            "age": None,
            "interface": "ethernet1/2",
            "route-table": "unicast"
        },
        "default_168.63.129.16/32_ethernet1/3": {
            "virtual-router": "default",
            "destination": "168.63.129.16/32",
            "nexthop": "10.26.129.129",
            "metric": "10",
            "flags": "A S",
            "age": None,
            "interface": "ethernet1/3",
            "route-table": "unicast"
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
        "num-gtpu-pending": "0"
    },
    "content_version": {
        "version": "8647-7730"
    },
    "arp_table": {
        "ethernet1/1_10.0.2.11": {
            "interface": "ethernet1/1",
            "ip": "10.0.2.11",
            "mac": "(incomplete)",
            "port": "ethernet1/1",
            "status": "i",
            "ttl": "1"
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
            "authcode": None
        },
        "Premium": {
            "feature": "Premium",
            "description": "24 x 7 phone support; advanced replacement hardware service",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "GlobalProtect Gateway": {
            "feature": "GlobalProtect Gateway",
            "description": "GlobalProtect Gateway License",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "Threat Prevention": {
            "feature": "Threat Prevention",
            "description": "Threat Prevention",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "WildFire License": {
            "feature": "WildFire License",
            "description": "WildFire signature feed, integrated WildFire logs, WildFire API",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        },
        "PA-VM": {
            "feature": "PA-VM",
            "description": "Standard VM-300",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "Never",
            "expired": "no",
            "authcode": None
        },
        "PAN-DB URL Filtering": {
            "feature": "PAN-DB URL Filtering",
            "description": "Palo Alto Networks URL Filtering License",
            "serial": "007257000334667",
            "issued": "November 08, 2022",
            "expires": "November 01, 2023",
            "expired": "no",
            "base-license-name": "PA-VM",
            "authcode": None
        }
    },
    "nics": {
        "ethernet1/1": "down",
        "ethernet1/2": "up",
        "ethernet1/3": "up"
    }
}
