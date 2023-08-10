import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from xmltodict import parse as xml_parse
import xml.etree.ElementTree as ET
from pan.xapi import PanXapiError
from panos_upgrade_assurance.exceptions import (
    CommandRunFailedException,
    MalformedResponseException,
    ContentDBVersionsFormatException,
    PanoramaConfigurationMissingException,
    WrongDiskSizeFormatException,
    DeviceNotLicensedException,
    UpdateServerConnectivityException,
)


@pytest.fixture(scope="function")
def fw_proxy_mock():
    fw_proxy_obj = FirewallProxy()
    fw_proxy_obj.op = MagicMock()
    yield fw_proxy_obj


class TestFirewallProxy:
    def test_op_parser_correct_response_default_params(self, fw_proxy_mock):
        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        cmd = "Example cmd"

        assert (
            fw_proxy_mock.op_parser(cmd)
            == xml_parse(ET.tostring(raw_response.find("result"), encoding="utf8", method="xml"))["result"]
        )

        fw_proxy_mock.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_proxy_mock.vsys)

    def test_op_parser_correct_response_custom_params(self, fw_proxy_mock):
        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_proxy_mock.op_parser(cmd, True, True) == raw_response.find("result")

        fw_proxy_mock.op.assert_called_with(cmd, xml=False, cmd_xml=False, vsys=fw_proxy_mock.vsys)

    def test_op_parser_incorrect(self, fw_proxy_mock):
        xml_text = "<response status='fail'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(CommandRunFailedException) as exc_info:
            fw_proxy_mock.op_parser(cmd)

        expected = f"Failed to run command: {cmd}."
        assert expected in str(exc_info.value)

        fw_proxy_mock.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_proxy_mock.vsys)

    def test_op_parser_none(self, fw_proxy_mock):
        xml_text = "<response status='success'><noresult example='1'></noresult></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(MalformedResponseException) as exc_info:
            fw_proxy_mock.op_parser(cmd)

        expected = f"No result field returned for: {cmd}"
        assert expected in str(exc_info.value)

        fw_proxy_mock.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_proxy_mock.vsys)

    def test_is_pending_changes_true(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.is_pending_changes()  # assert == True

    def test_is_pending_changes_false(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert not fw_proxy_mock.is_pending_changes()  # assert == False

    def test_is_full_commit_required_true(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.is_full_commit_required()

    def test_is_full_commit_required_false(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert not fw_proxy_mock.is_full_commit_required()

    def test_is_panorama_configured_true(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>SomePanoramaConfig</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.is_panorama_configured()

    def test_is_panorama_configured_false(self, fw_proxy_mock):
        xml_text = "<response status='success'><result></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert not fw_proxy_mock.is_panorama_configured()

    def test_is_panorama_connected_no_panorama(self, fw_proxy_mock):
        xml_text = "<response status='success'><result></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(PanoramaConfigurationMissingException) as exc_info:
            fw_proxy_mock.is_panorama_connected()

        expected = "Device not configured with Panorama."
        assert expected in str(exc_info.value)

    def test_is_panorama_connected_no_string_response(self, fw_proxy_mock):
        xml_text = "<response status='success'><result><key1>value1</key1><key2>value2</key2></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(MalformedResponseException) as exc_info:
            fw_proxy_mock.is_panorama_connected()

        expected = "Response from device is not type of string."
        assert expected in str(exc_info.value)

    def test_is_panorama_connected_true(self, fw_proxy_mock):
        xml_text = """<response status='success'><result>
            Panorama Server 1 : 1.2.3.4
                Connected     : yes
                HA state      : disconnected
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.is_panorama_connected()

    def test_is_panorama_connected_false(self, fw_proxy_mock):
        xml_text = """<response status='success'><result>
            Panorama Server 1 : 1.2.3.4
                Connected     : no
                HA state      : disconnected
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert not fw_proxy_mock.is_panorama_connected()  # assert == False

    def test_is_panorama_connected_no_typical_structure(self, fw_proxy_mock):
        xml_text = """<response status='success'><result>
            some line : to break code
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(MalformedResponseException) as exc_info:
            fw_proxy_mock.is_panorama_connected()

        expected = "Panorama configuration block does not have typical structure: <some line : to break code>."
        assert expected in str(exc_info.value)

    def test_get_ha_configuration(self, fw_proxy_mock):
        xml_text = """<response status='success'><result>
        {'enabled': 'yes'}
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_ha_configuration() == """{'enabled': 'yes'}"""

    def test_get_nics_none(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <hw>
                </hw>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        with pytest.raises(MalformedResponseException) as exc_info:
            fw_proxy_mock.get_nics()

        expected = "Malformed response from device, no [hw] element present."
        assert expected in str(exc_info.value)

    def test_get_nics_ok(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <hw>
                    <entry>
                        <name>ethernet1/1</name>
                        <id>16</id>
                        <type>0</type>
                        <mac>aa:bb:cc:dd:ee:ff:aa</mac>
                        <speed>ukn</speed>
                        <duplex>ukn</duplex>
                        <state>up</state>
                        <mode>(autoneg)</mode>
                        <st>ukn/ukn/up</st>
                    </entry>
                    <entry>
                        <name>ethernet1/2</name>
                        <id>17</id>
                        <type>0</type>
                        <mac>aa:bb:cc:dd:ee:ff:ab</mac>
                        <speed>ukn</speed>
                        <duplex>ukn</duplex>
                        <state>up</state>
                        <mode>(autoneg)</mode>
                        <st>ukn/ukn/up</st>
                    </entry>
                </hw>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_nics() == {"ethernet1/1": "up", "ethernet1/2": "up"}

    def test_get_nics_single_entry(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <hw>
                    <entry>
                        <name>ethernet1/1</name>
                        <id>16</id>
                        <type>0</type>
                        <mac>aa:bb:cc:dd:ee:ff:aa</mac>
                        <speed>ukn</speed>
                        <duplex>ukn</duplex>
                        <state>up</state>
                        <mode>(autoneg)</mode>
                        <st>ukn/ukn/up</st>
                    </entry>
                </hw>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_nics() == {"ethernet1/1": "up"}

    def test_get_licenses(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <licenses>
                    <entry>
                        <feature>PAN-DB URL Filtering</feature>
                        <description>Palo Alto Networks URL Filtering License</description>
                        <serial>00000000000000</serial>
                        <issued>April 20, 2023</issued>
                        <expires>December 31, 2023</expires>
                        <expired>no</expired>
                        <base-license-name>PA-VM</base-license-name>
                        <authcode />
                    </entry>
                </licenses>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_licenses() == {
            "PAN-DB URL Filtering": {
                "authcode": None,
                "base-license-name": "PA-VM",
                "description": "Palo Alto Networks URL Filtering " "License",
                "expired": "no",
                "expires": "December 31, 2023",
                "feature": "PAN-DB URL Filtering",
                "issued": "April 20, 2023",
                "serial": "00000000000000",
            },
        }

    def test_get_licenses_not_licensed_exception(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <licenses>
                </licenses>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        with pytest.raises(DeviceNotLicensedException) as exception_msg:
            fw_proxy_mock.get_licenses()

        assert str(exception_msg.value) == "Device possibly not licenced - no license information available in the API response."

    def test_get_support_license(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <SupportInfoResponse>
                    <Links>
                        <Link>
                            <Title>Contact Us</Title>
                            <Url>https://www.paloaltonetworks.com/company/contact-us.html</Url>
                        </Link>
                        <Link>
                            <Title>Support Home</Title>
                            <Url>https://www.paloaltonetworks.com/support/tabs/overview.html</Url>
                        </Link>
                    </Links>
                    <Support>
                        <Contact />
                        <ExpiryDate />
                        <SupportLevel />
                        <SupportDescription>Device not found on this update server</SupportDescription>
                    </Support>
                </SupportInfoResponse>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_support_license() == {"support_expiry_date": "", "support_level": ""}

    def test_get_support_license_connectivity_exception(self, fw_proxy_mock):
        fw_proxy_mock.op.side_effect = PanXapiError(
            "Failed to check support info due to Unknown error. Please check network connectivity and try again."
        )

        with pytest.raises(UpdateServerConnectivityException) as exception_msg:
            fw_proxy_mock.get_support_license()

        assert (
            str(exception_msg.value)
            == "Failed to check support info due to Unknown error. Please check network connectivity and try again."
        )

    def test_get_support_license_panxapierror_exception(self, fw_proxy_mock):
        fw_proxy_mock.op.side_effect = PanXapiError("Some other exception message.")

        with pytest.raises(PanXapiError) as exception_msg:
            fw_proxy_mock.get_support_license()

        assert str(exception_msg.value) == "Some other exception message."

    def test_get_routes(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <flags>flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf,
                    B:bgp, Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2,
                    E:ecmp, M:multicast</flags>
                <entry>
                    <virtual-router>default</virtual-router>
                    <destination>0.0.0.0/0</destination>
                    <nexthop>10.10.11.1</nexthop>
                    <metric>10</metric>
                    <flags>A S E </flags>
                    <age />
                    <interface>ethernet1/1</interface>
                    <route-table>unicast</route-table>
                </entry>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_routes() == {
            "default_0.0.0.0/0_ethernet1/1": {
                "age": None,
                "destination": "0.0.0.0/0",
                "flags": "A S E",
                "interface": "ethernet1/1",
                "metric": "10",
                "nexthop": "10.10.11.1",
                "route-table": "unicast",
                "virtual-router": "default",
            },
        }

    def test_get_arp_table(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <dp>dp0</dp>
                <timeout>1800</timeout>
                <total>1</total>
                <entries>
                    <entry>
                        <interface>ethernet1/1</interface>
                        <ip>10.10.11.1</ip>
                        <mac>aa:bb:cc:dd:ee:ff:ab</mac>
                        <port>ethernet1/1</port>
                        <status> c </status>
                        <ttl>1777</ttl>
                    </entry>
                </entries>
                <max>32000</max>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_arp_table() == {
            "ethernet1/1_10.10.11.1": {
                "interface": "ethernet1/1",
                "ip": "10.10.11.1",
                "mac": "aa:bb:cc:dd:ee:ff:ab",
                "port": "ethernet1/1",
                "status": "c",
                "ttl": "1777",
            },
        }

    def test_get_sessions(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <entry>
                    <dst>8.8.8.8</dst>
                    <xsource>10.10.11.2</xsource>
                    <source>10.10.11.2</source>
                    <xdst>8.8.8.8</xdst>
                    <xsport>32336</xsport>
                    <xdport>3</xdport>
                    <sport>32336</sport>
                    <dport>3</dport>
                    <proto>1</proto>
                    <from>zone</from>
                    <to>zone</to>
                    <start-time>Wed May 31 07:59:22 2023</start-time>
                    <nat>False</nat>
                    <srcnat>False</srcnat>
                    <dstnat>False</dstnat>
                    <proxy>False</proxy>
                    <decrypt-mirror>False</decrypt-mirror>
                    <state>ACTIVE</state>
                    <type>FLOW</type>
                    <total-byte-count>196</total-byte-count>
                    <idx>20</idx>
                    <vsys-idx>1</vsys-idx>
                    <vsys>vsys1</vsys>
                    <application>ping</application>
                    <security-rule>aqll</security-rule>
                    <ingress>ethernet1/1</ingress>
                    <egress>ethernet1/1</egress>
                    <flags> </flags>
                </entry>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_sessions() == [
            {
                "application": "ping",
                "decrypt-mirror": "False",
                "dport": "3",
                "dst": "8.8.8.8",
                "dstnat": "False",
                "egress": "ethernet1/1",
                "flags": None,
                "from": "zone",
                "idx": "20",
                "ingress": "ethernet1/1",
                "nat": "False",
                "proto": "1",
                "proxy": "False",
                "security-rule": "aqll",
                "source": "10.10.11.2",
                "sport": "32336",
                "srcnat": "False",
                "start-time": "Wed May 31 07:59:22 2023",
                "state": "ACTIVE",
                "to": "zone",
                "total-byte-count": "196",
                "type": "FLOW",
                "vsys": "vsys1",
                "vsys-idx": "1",
                "xdport": "3",
                "xdst": "8.8.8.8",
                "xsource": "10.10.11.2",
                "xsport": "32336",
            },
        ]

    def test_get_session_stats(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <age-accel-en>True</age-accel-en>
                <age-accel-thresh>80</age-accel-thresh>
                <age-accel-tsf>2</age-accel-tsf>
                <age-scan-ssf>8</age-scan-ssf>
                <age-scan-thresh>80</age-scan-thresh>
                <age-scan-tmo>10</age-scan-tmo>
                <cps>0</cps>
                <dis-def>60</dis-def>
                <dis-sctp>30</dis-sctp>
                <dis-tcp>90</dis-tcp>
                <dis-udp>60</dis-udp>
                <hw-offload>True</hw-offload>
                <hw-udp-offload>True</hw-udp-offload>
                <icmp-unreachable-rate>200</icmp-unreachable-rate>
                <ipv6-fw>True</ipv6-fw>
                <kbps>0</kbps>
                <max-pending-mcast>0</max-pending-mcast>
                <num-active>0</num-active>
                <num-bcast>0</num-bcast>
                <num-gtpc>0</num-gtpc>
                <num-gtpu-active>0</num-gtpu-active>
                <num-gtpu-pending>0</num-gtpu-pending>
                <num-http2-5gc>0</num-http2-5gc>
                <num-icmp>0</num-icmp>
                <num-imsi>0</num-imsi>
                <num-installed>0</num-installed>
                <num-max>1800000</num-max>
                <num-mcast>0</num-mcast>
                <num-pfcpc>0</num-pfcpc>
                <num-predict>0</num-predict>
                <num-sctp-assoc>0</num-sctp-assoc>
                <num-sctp-sess>0</num-sctp-sess>
                <num-tcp>0</num-tcp>
                <num-udp>0</num-udp>
                <oor-action>drop</oor-action>
                <pps>0</pps>
                <run-tc>True</run-tc>
                <strict-checksum>True</strict-checksum>
                <sw-cutthrough>False</sw-cutthrough>
                <tcp-cong-ctrl>3</tcp-cong-ctrl>
                <tcp-diff-syn-rej>True</tcp-diff-syn-rej>
                <tcp-no-refresh-fin-rst>False</tcp-no-refresh-fin-rst>
                <tcp-nonsyn-rej>True</tcp-nonsyn-rej>
                <tcp-reject-siw-enable>False</tcp-reject-siw-enable>
                <tcp-reject-siw-thresh>4</tcp-reject-siw-thresh>
                <tcp-strict-rst>True</tcp-strict-rst>
                <tmo-5gcdelete>15</tmo-5gcdelete>
                <tmo-cp>30</tmo-cp>
                <tmo-def>30</tmo-def>
                <tmo-icmp>6</tmo-icmp>
                <tmo-sctp>3600</tmo-sctp>
                <tmo-sctpcookie>60</tmo-sctpcookie>
                <tmo-sctpinit>5</tmo-sctpinit>
                <tmo-sctpshutdown>60</tmo-sctpshutdown>
                <tmo-tcp>3600</tmo-tcp>
                <tmo-tcp-delayed-ack>25</tmo-tcp-delayed-ack>
                <tmo-tcp-unverif-rst>30</tmo-tcp-unverif-rst>
                <tmo-tcphalfclosed>120</tmo-tcphalfclosed>
                <tmo-tcphandshake>10</tmo-tcphandshake>
                <tmo-tcpinit>5</tmo-tcpinit>
                <tmo-tcptimewait>15</tmo-tcptimewait>
                <tmo-udp>30</tmo-udp>
                <tunnel-accel>True</tunnel-accel>
                <vardata-rate>10485760</vardata-rate>
                <dp>*.dp0</dp>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_session_stats() == {
            "age-accel-thresh": "80",
            "age-accel-tsf": "2",
            "age-scan-ssf": "8",
            "age-scan-thresh": "80",
            "age-scan-tmo": "10",
            "cps": "0",
            "dis-def": "60",
            "dis-sctp": "30",
            "dis-tcp": "90",
            "dis-udp": "60",
            "icmp-unreachable-rate": "200",
            "kbps": "0",
            "max-pending-mcast": "0",
            "num-active": "0",
            "num-bcast": "0",
            "num-gtpc": "0",
            "num-gtpu-active": "0",
            "num-gtpu-pending": "0",
            "num-http2-5gc": "0",
            "num-icmp": "0",
            "num-imsi": "0",
            "num-installed": "0",
            "num-max": "1800000",
            "num-mcast": "0",
            "num-pfcpc": "0",
            "num-predict": "0",
            "num-sctp-assoc": "0",
            "num-sctp-sess": "0",
            "num-tcp": "0",
            "num-udp": "0",
            "pps": "0",
            "tcp-cong-ctrl": "3",
            "tcp-reject-siw-thresh": "4",
            "tmo-5gcdelete": "15",
            "tmo-cp": "30",
            "tmo-def": "30",
            "tmo-icmp": "6",
            "tmo-sctp": "3600",
            "tmo-sctpcookie": "60",
            "tmo-sctpinit": "5",
            "tmo-sctpshutdown": "60",
            "tmo-tcp": "3600",
            "tmo-tcp-delayed-ack": "25",
            "tmo-tcp-unverif-rst": "30",
            "tmo-tcphalfclosed": "120",
            "tmo-tcphandshake": "10",
            "tmo-tcpinit": "5",
            "tmo-tcptimewait": "15",
            "tmo-udp": "30",
            "vardata-rate": "10485760",
        }

    def test_get_tunnels(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <dp>dp0</dp>
                <num_ipsec>1</num_ipsec>
                <num_sslvpn>0</num_sslvpn>
                <hop />
                <IPSec>
                    <entry>
                        <name>my-tunnel</name>
                        <id>1</id>
                        <gwid>1</gwid>
                        <inner-if>tunnel.1</inner-if>
                        <outer-if>ethernet1/1</outer-if>
                        <localip>1.2.3.4</localip>
                        <peerip>6.6.6.6</peerip>
                        <state>init</state>
                        <mon>off</mon>
                        <owner>1</owner>
                    </entry>
                </IPSec>
                <SSL-VPN />
                <GlobalProtect-Gateway />
                <GlobalProtect-site-to-site />
                <total>1</total>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_tunnels() == {
            "GlobalProtect-Gateway": {},
            "GlobalProtect-site-to-site": {},
            "IPSec": {
                "my-tunnel": {
                    "gwid": "1",
                    "id": "1",
                    "inner-if": "tunnel.1",
                    "localip": "1.2.3.4",
                    "mon": "off",
                    "name": "my-tunnel",
                    "outer-if": "ethernet1/1",
                    "owner": "1",
                    "peerip": "6.6.6.6",
                    "state": "init",
                }
            },
            "SSL-VPN": {},
            "hop": {},
        }

    def test_get_latest_available_content_version_ok(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <content-updates last-updated-at="2023/05/31 08:18:33 PDT">
                    <entry>
                        <version>8696-7977</version>
                        <app-version>8696-7977</app-version>
                        <filename>panupv2-all-contents-8696-7977</filename>
                        <size>64</size>
                        <size-kb>66392</size-kb>
                        <released-on>2023/04/11 13:08:12 PDT</released-on>
                        <release-notes>
        <![CDATA[ https://proditpdownloads.paloaltonetworks.com/content/content-8696-7977.html?__token__=exp=1682613690~acl=/content/content-8696-7977.html*~hmac=95575a9f15f9d6da9016e9a7c319b75710d6596f620c2806b1af345a8ab83307 ]]>
        </release-notes>
                        <downloaded>no</downloaded>
                        <current>no</current>
                        <previous>no</previous>
                        <installing>no</installing>
                        <features>Apps, Threats</features>
                        <update-type>Full</update-type>
                        <feature-desc>Unknown</feature-desc>
                        <sha256>4984d16667f694d0574cd9ffee58c74edfcea9f866d1724d44be5de02d9f4c9b</sha256>
                    </entry>
                    <entry>
                        <version>8698-7988</version>
                        <app-version>8698-7988</app-version>
                        <filename>panupv2-all-contents-8698-7988</filename>
                        <size>64</size>
                        <size-kb>66408</size-kb>
                        <released-on>2023/04/17 19:02:31 PDT</released-on>
                        <release-notes>
        <![CDATA[ https://proditpdownloads.paloaltonetworks.com/content/content-8698-7988.html?__token__=exp=1682613690~acl=/content/content-8698-7988.html*~hmac=1ebcc182d27511a6dd75760a9c2b0b996c29d8f30a9f55fb2d8e7a4204bb7e05 ]]>
        </release-notes>
                        <downloaded>no</downloaded>
                        <current>no</current>
                        <previous>no</previous>
                        <installing>no</installing>
                        <features>Apps, Threats</features>
                        <update-type>Full</update-type>
                        <feature-desc>Unknown</feature-desc>
                        <sha256>3ae74c9ed12cf8093f17cc1d88c3d5a59fcfa8226c5fea278ac084c234b355c4</sha256>
                    </entry>
                </content-updates>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_latest_available_content_version() == "8698-7988"

    def test_get_latest_available_content_version_parse_fail(self, fw_proxy_mock):
        xml_text = "<response status='success'><result>Not Parsable</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(ContentDBVersionsFormatException) as exc_info:
            fw_proxy_mock.get_latest_available_content_version()

        expected = "Cannot parse list of available updates for Content DB."
        assert expected in str(exc_info.value)

    def test_get_content_db_version(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <system>
                    <hostname>PA-VM</hostname>
                    <app-version>8556-7343</app-version>
                    <plugin_versions>
                        <entry name="vm_series" version="3.0.2">
                            <pkginfo>vm_series-3.0.2</pkginfo>
                        </entry>
                        <entry name="dlp" version="3.0.1">
                            <pkginfo>dlp-3.0.1-c9</pkginfo>
                        </entry>
                    </plugin_versions>
                    <platform-family>vm</platform-family>
                    <vpn-disable-mode>off</vpn-disable-mode>
                    <multi-vsys>off</multi-vsys>
                    <operational-mode>normal</operational-mode>
                    <advanced-routing>off</advanced-routing>
                    <device-certificate-status>None</device-certificate-status>
                </system>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_content_db_version() == "8556-7343"

    def test_get_ntp_servers(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <ntp-server-1>
                    <authentication-type>none</authentication-type>
                    <name>0.pool.ntp.org</name>
                    <reachable>no</reachable>
                    <status>available</status>
                </ntp-server-1>
                <ntp-server-2>
                    <authentication-type>none</authentication-type>
                    <name>1.pool.ntp.org</name>
                    <reachable>no</reachable>
                    <status>available</status>
                </ntp-server-2>
                <synched>1.pool.ntp.org</synched>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_ntp_servers() == {
            "ntp-server-1": {"authentication-type": "none", "name": "0.pool.ntp.org", "reachable": "no", "status": "available"},
            "ntp-server-2": {"authentication-type": "none", "name": "1.pool.ntp.org", "reachable": "no", "status": "available"},
            "synched": "1.pool.ntp.org",
        }

    def test_get_disk_utilization_ok(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[ Filesystem Size Used Avail Use% Mounted on
        /dev/root       38G  5.0G  31G    14% /
        none            16G  136K  16G     1% /dev
        /dev/md5       100M  0     100M   12% /opt/pancfg
        /dev/md6        23G  2.2G  20G    11% /opt/panrepo
        tmpfs           16G  253M  16G     2% /dev/shm
        /dev/md9       1.8T  4.1G  1.7T    1% /opt/panraid/ld1
        /dev/md8        73G  1.2G  68G     2% /opt/panlogs
        tmpfs          1.0M  4.0K  1020K   1% /opt/pancfg/mgmt/lcaas/ssl/private
        ]]>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_disk_utilization() == {
            "/": 31744,
            "/dev": 16384,
            "/dev/shm": 16384,  # nosec
            "/opt/pancfg": 100,
            "/opt/pancfg/mgmt/lcaas/ssl/private": 0,
            "/opt/panlogs": 69632,
            "/opt/panraid/ld1": 1782579,
            "/opt/panrepo": 20480,
        }

    def test_get_disk_utilization_wrong_format(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[Filesystem      Size  Used Avail Use% Mounted on
        /dev/root       6.9G  5.1G  1.5X  78% /
        none            7.9G   76K  7.9G   1% /dev
        /dev/sda5        16G  1.2G   14G   8% /opt/pancfg
        /dev/sda6       7.9G  1.6G  5.9G  22% /opt/panrepo
        tmpfs            12G  8.4G  3.0G  74% /dev/shm
        cgroup_root     7.9G     0  7.9G   0% /cgroup
        /dev/sda8        21G   63M   20G   1% /opt/panlogs
        tmpfs            12M     0   12M   0% /opt/pancfg/mgmt/lcaas/ssl/private
        ]]>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(WrongDiskSizeFormatException) as exc_info:
            fw_proxy_mock.get_disk_utilization()

        expected = "Free disk size has wrong format."
        assert expected in str(exc_info.value)

    def test_get_disk_utilization_invalid_size(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[Filesystem      Size  Used Avail Use% Mounted on
        /dev/root       6.9G  5.1G    AG  78% /
        none            7.9G   76K  7.9G   1% /dev
        /dev/sda5        16G  1.2G   14G   8% /opt/pancfg
        /dev/sda6       7.9G  1.6G  5.9G  22% /opt/panrepo
        tmpfs            12G  8.4G  3.0G  74% /dev/shm
        cgroup_root     7.9G     0  7.9G   0% /cgroup
        /dev/sda8        21G   63M   20G   1% /opt/panlogs
        tmpfs            12M     0   12M   0% /opt/pancfg/mgmt/lcaas/ssl/private
        ]]>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(
            MalformedResponseException,
            match=r"Reported disk space block does not have typical structure: .*$",
        ):
            fw_proxy_mock.get_disk_utilization()

    def test_get_disk_utilization_index_fail(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[Filesystem      Size  Used Avail Use% Mounted on
        /dev/root       6.9G  5.1G
        ]]>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response
        with pytest.raises(
            MalformedResponseException,
            match=r"Reported disk space block does not have typical structure: .*$",
        ):
            fw_proxy_mock.get_disk_utilization()

    def test_get_disk_utilization_no_unit(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[Filesystem      Size  Used Avail Use% Mounted on
        tmpfs            12M     0   12   0% /opt/pancfg/mgmt/lcaas/ssl/private
        ]]>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_disk_utilization() == {"/opt/pancfg/mgmt/lcaas/ssl/private": 0}

    def test_get_available_image_data(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <sw-updates last-updated-at="2023/05/31 11:47:34">
                    <msg />
                    <versions>
                        <entry>
                            <version>11.0.1</version>
                            <filename>PanOS_vm-11.0.1</filename>
                            <size>492</size>
                            <size-kb>504796</size-kb>
                            <released-on>2023/03/29 15:05:25</released-on>
                            <release-notes>
        <![CDATA[ https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes ]]>
        </release-notes>
                            <downloaded>no</downloaded>
                            <current>no</current>
                            <latest>yes</latest>
                            <uploaded>no</uploaded>
                        </entry>
                        <entry>
                            <version>11.0.0</version>
                            <filename>PanOS_vm-11.0.0</filename>
                            <size>1037</size>
                            <size-kb>1062271</size-kb>
                            <released-on>2022/11/17 08:45:28</released-on>
                            <release-notes>
        <![CDATA[ https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes ]]>
        </release-notes>
                            <downloaded>no</downloaded>
                            <current>no</current>
                            <latest>no</latest>
                            <uploaded>no</uploaded>
                        </entry>
                    </versions>
                </sw-updates>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_available_image_data() == {
            "11.0.0": {
                "current": "no",
                "downloaded": "no",
                "filename": "PanOS_vm-11.0.0",
                "latest": "no",
                "release-notes": "https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes",
                "released-on": "2022/11/17 08:45:28",
                "size": "1037",
                "size-kb": "1062271",
                "uploaded": "no",
                "version": "11.0.0",
            },
            "11.0.1": {
                "current": "no",
                "downloaded": "no",
                "filename": "PanOS_vm-11.0.1",
                "latest": "yes",
                "release-notes": "https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes",
                "released-on": "2023/03/29 15:05:25",
                "size": "492",
                "size-kb": "504796",
                "uploaded": "no",
                "version": "11.0.1",
            },
        }

    def test_get_available_image_data_connectivity_exception(self, fw_proxy_mock):
        fw_proxy_mock.op.side_effect = PanXapiError(
            "Failed to check upgrade info due to Unknown error. Please check network connectivity and try again."
        )

        with pytest.raises(UpdateServerConnectivityException) as exception_msg:
            fw_proxy_mock.get_available_image_data()

        assert (
            str(exception_msg.value)
            == "Failed to check upgrade info due to Unknown error. Please check network connectivity and try again."
        )

    def test_get_available_image_data_panxapierror_exception(self, fw_proxy_mock):
        fw_proxy_mock.op.side_effect = PanXapiError("Some other exception message.")

        with pytest.raises(PanXapiError) as exception_msg:
            fw_proxy_mock.get_available_image_data()

        assert str(exception_msg.value) == "Some other exception message."

    def test_get_mp_clock(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>Wed May 31 11:50:21 PDT 2023 </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_mp_clock() == {
            "day": "31",
            "day_of_week": "Wed",
            "month": "May",
            "time": "11:50:21",
            "tz": "PDT",
            "year": "2023",
        }

    def test_get_dp_clock(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <member>dataplane time: Wed May 31 11:52:34 PDT 2023 </member>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_dp_clock() == {
            "day": "31",
            "day_of_week": "Wed",
            "month": "May",
            "time": "11:52:34",
            "tz": "PDT",
            "year": "2023",
        }

    def test_get_jobs(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <job>
                    <tenq>2023/08/07 04:00:40</tenq>
                    <tdeq>04:00:40</tdeq>
                    <id>4</id>
                    <user>Auto update agent</user>
                    <type>WildFire</type>
                    <status>FIN</status>
                    <queued>NO</queued>
                    <stoppable>no</stoppable>
                    <result>OK</result>
                    <tfin>2023/08/07 04:00:45</tfin>
                    <description/>
                    <positionInQ>0</positionInQ>
                    <progress>2023/08/07 04:00:45</progress>
                    <details>
                        <line>Configuration committed successfully</line>
                        <line>Successfully committed last configuration</line>
                    </details>
                    <warnings/>
                </job>
                <job>
                    <tenq>2023/08/07 03:59:57</tenq>
                    <tdeq>03:59:57</tdeq>
                    <id>1</id>
                    <user/>
                    <type>AutoCom</type>
                    <status>FIN</status>
                    <queued>NO</queued>
                    <stoppable>no</stoppable>
                    <result>OK</result>
                    <tfin>2023/08/07 04:00:28</tfin>
                    <description/>
                    <positionInQ>0</positionInQ>
                    <progress>100</progress>
                    <details>
                        <line>Configuration committed successfully</line>
                        <line>Successfully committed last configuration</line>
                    </details>
                    <warnings/>
                </job>
            </result>
        </response>
        """

        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_jobs() == {
            "4": {
                "tenq": "2023/08/07 04:00:40",
                "tdeq": "04:00:40",
                "user": "Auto update agent",
                "type": "WildFire",
                "status": "FIN",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:45",
                "description": None,
                "positionInQ": "0",
                "progress": "2023/08/07 04:00:45",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
            "1": {
                "tenq": "2023/08/07 03:59:57",
                "tdeq": "03:59:57",
                "user": None,
                "type": "AutoCom",
                "status": "FIN",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:28",
                "description": None,
                "positionInQ": "0",
                "progress": "100",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
        }

    def test_get_jobs_no_jobs(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
            </result>
        </response>
        """

        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_jobs() == {}

    def test_get_certificates(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <config>
                    <shared>
                        <certificate>
                            <entry name="acertificate">
                                <algorithm>RSA</algorithm>
                                <ca>no</ca>
                                <common-name>cert</common-name>
                                <expiry-epoch>1718699772</expiry-epoch>
                                <issuer>root</issuer>
                                <issuer-hash>5198cade</issuer-hash>
                                <not-valid-after>Jun 18 08:36:12 2024 GMT</not-valid-after>
                                <not-valid-before>Jun 19 08:36:12 2023 GMT</not-valid-before>
                                <public-key>public-key-data</public-key>
                                <private-key>private-key-data</private-key>
                                <subject>cert</subject>
                                <subject-hash>5ec67661</subject-hash>
                            </entry>
                            <entry name="bcertificate">
                                <algorithm>EC</algorithm>
                                <ca>no</ca>
                                <common-name>cert</common-name>
                                <expiry-epoch>1718699772</expiry-epoch>
                                <issuer>root</issuer>
                                <issuer-hash>5198cade</issuer-hash>
                                <not-valid-after>Jun 18 08:36:12 2024 GMT</not-valid-after>
                                <not-valid-before>Jun 19 08:36:12 2023 GMT</not-valid-before>
                                <public-key>public-key-data</public-key>
                                <private-key>private-key-data</private-key>
                                <subject>cert</subject>
                                <subject-hash>5ec67661</subject-hash>
                            </entry>
                        </certificate>
                    </shared>
                </config>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_certificates() == {
            "acertificate": {
                "algorithm": "RSA",
                "ca": "no",
                "common-name": "cert",
                "expiry-epoch": "1718699772",
                "issuer": "root",
                "issuer-hash": "5198cade",
                "not-valid-after": "Jun 18 08:36:12 2024 GMT",
                "not-valid-before": "Jun 19 08:36:12 2023 GMT",
                "public-key": "public-key-data",
                "subject": "cert",
                "subject-hash": "5ec67661",
            },
            "bcertificate": {
                "algorithm": "EC",
                "ca": "no",
                "common-name": "cert",
                "expiry-epoch": "1718699772",
                "issuer": "root",
                "issuer-hash": "5198cade",
                "not-valid-after": "Jun 18 08:36:12 2024 GMT",
                "not-valid-before": "Jun 19 08:36:12 2023 GMT",
                "public-key": "public-key-data",
                "subject": "cert",
                "subject-hash": "5ec67661",
            },
        }

    def test_get_certificates_no_certificate(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <config>
                    <shared>
                        <application/>
                        <application-group/>
                        <service/>
                        <service-group/>
                        <botnet/>
                    </shared>
                </config>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_certificates() == {}
