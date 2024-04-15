from collections import OrderedDict
import pytest
from unittest.mock import MagicMock
from panos.firewall import Firewall
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
    GetXpathConfigFailedException,
)
from datetime import datetime


@pytest.fixture(scope="function")
def fw_proxy_mock():
    fw_proxy_obj = FirewallProxy(Firewall())
    fw_proxy_obj._fw.op = MagicMock()
    fw_proxy_obj._fw.generate_xapi = MagicMock()
    fw_proxy_obj._fw.xapi.get = MagicMock()
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

    def test_get_parser_correct_response_defaults(self, fw_proxy_mock):
        input_xpath = "/some/xpath"
        xml_output_text = """
        <response status="success">
            <result>
                <element>value</element>
            </result>
        </response>
        """
        xml_output = ET.fromstring(xml_output_text)
        fw_proxy_mock.xapi.get.return_value = xml_output

        response = fw_proxy_mock.get_parser(input_xpath)
        mocked_response = xml_parse(ET.tostring(xml_output.find("result"), encoding="utf8", method="xml"))["result"]

        assert response == mocked_response

    def test_get_parser_correct_response_in_xml(self, fw_proxy_mock):
        input_xpath = "/some/xpath"
        xml_output_text = """
        <response status="success">
            <result>
                <element>value</element>
            </result>
        </response>
        """
        xml_output = ET.fromstring(xml_output_text)
        fw_proxy_mock.xapi.get.return_value = xml_output

        response = fw_proxy_mock.get_parser(input_xpath, True)
        mocked_response = xml_output.find("result")

        assert response == mocked_response

    def test_get_parser_no_xpath_exception(self, fw_proxy_mock):
        with pytest.raises(GetXpathConfigFailedException) as exc_info:
            fw_proxy_mock.get_parser(None)
        assert "No XPATH provided." in str(exc_info.value)

    def test_get_parser_incorrect_response(self, fw_proxy_mock):
        input_xpath = "/some/xpath"
        xml_output_text = """
        <response status="noauth">
            <result/>
        </response>
        """
        xml_output = ET.fromstring(xml_output_text)
        fw_proxy_mock.xapi.get.return_value = xml_output

        with pytest.raises(GetXpathConfigFailedException) as exc_info:
            fw_proxy_mock.get_parser(input_xpath)

        expected = f'Failed get data under XPATH: {input_xpath}, status: {xml_output.get("status")}.'
        assert expected == str(exc_info.value)

    def test_get_parser_no_response(self, fw_proxy_mock):
        input_xpath = "/some/xpath"
        xml_output_text = '<response status="success"/>'
        xml_output = ET.fromstring(xml_output_text)
        fw_proxy_mock.xapi.get.return_value = xml_output

        with pytest.raises(GetXpathConfigFailedException) as exc_info:
            fw_proxy_mock.get_parser(input_xpath)

        expected = f"No data found under XPATH: {input_xpath}, or path does not exist."
        assert expected == str(exc_info.value)

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
            "default_0.0.0.0/0_ethernet1/1_10.10.11.1": {
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

    def test_get_routes_same_dest(self, fw_proxy_mock):
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
                <entry>
                    <virtual-router>default</virtual-router>
                    <destination>0.0.0.0/0</destination>
                    <nexthop>10.10.12.1</nexthop>
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
            "default_0.0.0.0/0_ethernet1/1_10.10.11.1": {
                "age": None,
                "destination": "0.0.0.0/0",
                "flags": "A S E",
                "interface": "ethernet1/1",
                "metric": "10",
                "nexthop": "10.10.11.1",
                "route-table": "unicast",
                "virtual-router": "default",
            },
            "default_0.0.0.0/0_ethernet1/1_10.10.12.1": {
                "age": None,
                "destination": "0.0.0.0/0",
                "flags": "A S E",
                "interface": "ethernet1/1",
                "metric": "10",
                "nexthop": "10.10.12.1",
                "route-table": "unicast",
                "virtual-router": "default",
            },
        }

    def test_get_routes_nexthop_name(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <flags>flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf,
                    B:bgp, Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2,
                    E:ecmp, M:multicast</flags>
                <entry>
                    <virtual-router>default</virtual-router>
                    <destination>0.0.0.0/0</destination>
                    <nexthop>public vr</nexthop>
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
            "default_0.0.0.0/0_ethernet1/1_public-vr": {
                "age": None,
                "destination": "0.0.0.0/0",
                "flags": "A S E",
                "interface": "ethernet1/1",
                "metric": "10",
                "nexthop": "public vr",
                "route-table": "unicast",
                "virtual-router": "default",
            },
        }

    def test_get_bgp_peers(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <entry peer="Peer1" vr="default">
                    <peer-group>Peer-Group1</peer-group>
                    <peer-router-id>169.254.8.2</peer-router-id>
                    <remote-as>64512</remote-as>
                    <status>Established</status>
                    <status-duration>3804</status-duration>
                    <password-set>no</password-set>
                    <passive>no</passive>
                    <multi-hop-ttl>2</multi-hop-ttl>
                    <peer-address>169.254.8.2:35355</peer-address>
                    <local-address>169.254.8.1:179</local-address>
                    <reflector-client>not-client</reflector-client>
                    <same-confederation>no</same-confederation>
                    <aggregate-confed-as>yes</aggregate-confed-as>
                    <peering-type>Unspecified</peering-type>
                    <connect-retry-interval>15</connect-retry-interval>
                    <open-delay>0</open-delay>
                    <idle-hold>15</idle-hold>
                    <prefix-limit>5000</prefix-limit>
                    <holdtime>30</holdtime>
                    <holdtime-config>30</holdtime-config>
                    <keepalive>10</keepalive>
                    <keepalive-config>10</keepalive-config>
                    <msg-update-in>2</msg-update-in>
                    <msg-update-out>1</msg-update-out>
                    <msg-total-in>385</msg-total-in>
                    <msg-total-out>442</msg-total-out>
                    <last-update-age>3</last-update-age>
                    <last-error/>
                    <status-flap-counts>2</status-flap-counts>
                    <established-counts>1</established-counts>
                    <ORF-entry-received>0</ORF-entry-received>
                    <nexthop-self>no</nexthop-self>
                    <nexthop-thirdparty>yes</nexthop-thirdparty>
                    <nexthop-peer>no</nexthop-peer>
                    <config>
                        <remove-private-as>no</remove-private-as>
                    </config>
                    <peer-capability>
                        <list>
                            <capability>Multiprotocol Extensions(1)</capability>
                            <value>IPv4 Unicast</value>
                        </list>
                        <list>
                            <capability>Route Refresh(2)</capability>
                            <value>yes</value>
                        </list>
                        <list>
                            <capability>4-Byte AS Number(65)</capability>
                            <value>64512</value>
                        </list>
                        <list>
                            <capability>Route Refresh (Cisco)(128)</capability>
                            <value>yes</value>
                        </list>
                    </peer-capability>
                    <prefix-counter>
                        <entry afi-safi="bgpAfiIpv4-unicast">
                            <incoming-total>2</incoming-total>
                            <incoming-accepted>2</incoming-accepted>
                            <incoming-rejected>0</incoming-rejected>
                            <policy-rejected>0</policy-rejected>
                            <outgoing-total>0</outgoing-total>
                            <outgoing-advertised>0</outgoing-advertised>
                        </entry>
                    </prefix-counter>
                </entry>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_bgp_peers() == {
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
        }

    def test_get_bgp_peers_no_peers(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result/>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_bgp_peers() == {}

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

        response = datetime.strptime("Wed May 31 11:50:21 2023", "%a %b %d %H:%M:%S %Y")

        assert fw_proxy_mock.get_mp_clock() == response

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

        response = datetime.strptime("Wed May 31 11:52:34 2023", "%a %b %d %H:%M:%S %Y")

        assert fw_proxy_mock.get_dp_clock() == response

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

    def test_get_jobs_single_job(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
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

    def test_get_update_schedules(self, fw_proxy_mock):
        xml_text = """
        <response status="success" code="19">
            <result total-count="1" count="1">
                <update-schedule ptpl="lab" src="tpl">
                <anti-virus ptpl="lab" src="tpl">
                    <recurring ptpl="lab" src="tpl">
                    <threshold ptpl="lab" src="tpl">15</threshold>
                    <daily ptpl="lab" src="tpl">
                        <at ptpl="lab" src="tpl">00:30</at>
                        <action ptpl="lab" src="tpl">download-and-install</action>
                    </daily>
                    <sync-to-peer ptpl="lab" src="tpl">yes</sync-to-peer>
                    </recurring>
                </anti-virus>
                <wildfire ptpl="lab" src="tpl">
                    <recurring ptpl="lab" src="tpl">
                    <every-15-mins ptpl="lab" src="tpl">
                        <at ptpl="lab" src="tpl">4</at>
                        <action ptpl="lab" src="tpl">download-only</action>
                        <sync-to-peer ptpl="lab" src="tpl">yes</sync-to-peer>
                    </every-15-mins>
                    </recurring>
                </wildfire>
                <global-protect-datafile ptpl="lab" src="tpl">
                    <recurring ptpl="lab" src="tpl">
                    <none ptpl="lab" src="tpl"/>
                    </recurring>
                </global-protect-datafile>
                <wf-private ptpl="lab" src="tpl">
                    <recurring ptpl="lab" src="tpl">
                    <none ptpl="lab" src="tpl"/>
                    </recurring>
                </wf-private>
                <global-protect-clientless-vpn ptpl="lab" src="tpl">
                    <recurring>
                    <daily>
                        <at>01:45</at>
                        <action>download-and-install</action>
                    </daily>
                    </recurring>
                </global-protect-clientless-vpn>
                <threats>
                    <recurring>
                    <weekly>
                        <day-of-week>wednesday</day-of-week>
                        <at>01:02</at>
                        <action>download-only</action>
                    </weekly>
                    </recurring>
                </threats>
                </update-schedule>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.xapi.get.return_value = raw_response
        # fw_proxy_mock.op.return_value = raw_response
        # fw_proxy_mock.get_parser.return_value = raw_response

        response = {
            "@ptpl": "lab",
            "@src": "tpl",
            "anti-virus": {
                "@ptpl": "lab",
                "@src": "tpl",
                "recurring": {
                    "@ptpl": "lab",
                    "@src": "tpl",
                    "daily": {
                        "@ptpl": "lab",
                        "@src": "tpl",
                        "action": {"#text": "download-and-install", "@ptpl": "lab", "@src": "tpl"},
                        "at": {"#text": "00:30", "@ptpl": "lab", "@src": "tpl"},
                    },
                    "sync-to-peer": {"#text": "yes", "@ptpl": "lab", "@src": "tpl"},
                    "threshold": {"#text": "15", "@ptpl": "lab", "@src": "tpl"},
                },
            },
            "global-protect-clientless-vpn": {
                "@ptpl": "lab",
                "@src": "tpl",
                "recurring": {"daily": {"action": "download-and-install", "at": "01:45"}},
            },
            "global-protect-datafile": {
                "@ptpl": "lab",
                "@src": "tpl",
                "recurring": {"@ptpl": "lab", "@src": "tpl", "none": {"@ptpl": "lab", "@src": "tpl"}},
            },
            "threats": {"recurring": {"weekly": {"action": "download-only", "at": "01:02", "day-of-week": "wednesday"}}},
            "wf-private": {
                "@ptpl": "lab",
                "@src": "tpl",
                "recurring": {"@ptpl": "lab", "@src": "tpl", "none": {"@ptpl": "lab", "@src": "tpl"}},
            },
            "wildfire": {
                "@ptpl": "lab",
                "@src": "tpl",
                "recurring": {
                    "@ptpl": "lab",
                    "@src": "tpl",
                    "every-15-mins": {
                        "@ptpl": "lab",
                        "@src": "tpl",
                        "action": {"#text": "download-only", "@ptpl": "lab", "@src": "tpl"},
                        "at": {"#text": "4", "@ptpl": "lab", "@src": "tpl"},
                        "sync-to-peer": {"#text": "yes", "@ptpl": "lab", "@src": "tpl"},
                    },
                },
            },
        }

        assert fw_proxy_mock.get_update_schedules() == response

    def test_get_update_schedules_empty_response(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.xapi.get.return_value = raw_response

        assert fw_proxy_mock.get_update_schedules() == {}

    def test_get_update_schedules_no_update_schedules_key(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <some-element>
                </some-element>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.xapi.get.return_value = raw_response

        assert fw_proxy_mock.get_update_schedules() == {}

    def test_get_redistribution_status_up_agent_multiple_clients(self, fw_proxy_mock):
        show_redist_service_client_all_xml = """
        <response status="success">
            <result>
                <entry>
                    <host>1.1.1.1</host>
                    <port>34518</port>
                    <vsys>vsys1</vsys>
                    <version>6</version>
                    <status>idle</status>
                    <redistribution>I    </redistribution>
                </entry>
                <entry>
                    <host>1.1.1.2</host>
                    <port>34518</port>
                    <vsys>vsys1</vsys>
                    <version>6</version>
                    <status>idle</status>
                    <redistribution>I    </redistribution>
                </entry>
            </result>
        </response>"""
        show_redist_service_client_all_xml_raw_response = ET.fromstring(show_redist_service_client_all_xml)

        show_redist_service_agent_all_xml = """
        <response status="success">
            <result>
                <entry name="FW3367">
                    <vsys>vsys1</vsys>
                    <vsys_hub>no</vsys_hub>
                    <host>1.1.1.1</host>
                    <peer-address>1.1.1.1</peer-address>
                    <port>5007</port>
                    <state>conn:idle</state>
                    <status-msg>-</status-msg>
                    <version>0x6</version>
                    <last-heard-time>1701651677</last-heard-time>
                    <job-id>0</job-id>
                    <num_sent_msgs>0</num_sent_msgs>
                    <num_recv_msgs>0</num_recv_msgs>
                </entry>
            </result>
        </response>
        """
        show_redist_service_agent_all_xml_raw_response = ET.fromstring(show_redist_service_agent_all_xml)

        fw_proxy_mock.op.side_effect = [
            show_redist_service_client_all_xml_raw_response,
            show_redist_service_agent_all_xml_raw_response,
        ]

        assert fw_proxy_mock.get_redistribution_status() == {
            "agents": OrderedDict(
                [
                    ("@name", "FW3367"),
                    ("vsys", "vsys1"),
                    ("vsys_hub", "no"),
                    ("host", "1.1.1.1"),
                    ("peer-address", "1.1.1.1"),
                    ("port", "5007"),
                    ("state", "conn:idle"),
                    ("status-msg", "-"),
                    ("version", "0x6"),
                    ("last-heard-time", "1701651677"),
                    ("job-id", "0"),
                    ("num_sent_msgs", "0"),
                    ("num_recv_msgs", "0"),
                ]
            ),
            "clients": [
                OrderedDict(
                    [
                        ("host", "1.1.1.1"),
                        ("port", "34518"),
                        ("vsys", "vsys1"),
                        ("version", "6"),
                        ("status", "idle"),
                        ("redistribution", "I"),
                    ]
                ),
                OrderedDict(
                    [
                        ("host", "1.1.1.2"),
                        ("port", "34518"),
                        ("vsys", "vsys1"),
                        ("version", "6"),
                        ("status", "idle"),
                        ("redistribution", "I"),
                    ]
                ),
            ],
        }

    def test_get_redistribution_status_up_empty_results(self, fw_proxy_mock):
        show_redist_service_client_all_xml = """
        <response status="success">
            <result>
                <entry></entry>
            </result>
        </response>"""
        show_redist_service_client_all_xml_raw_response = ET.fromstring(show_redist_service_client_all_xml)

        show_redist_service_agent_all_xml = """
        <response status="success">
            <result>
                <entry></entry>
            </result>
        </response>
        """
        show_redist_service_agent_all_xml_raw_response = ET.fromstring(show_redist_service_agent_all_xml)

        fw_proxy_mock.op.side_effect = [
            show_redist_service_client_all_xml_raw_response,
            show_redist_service_agent_all_xml_raw_response,
        ]

        assert fw_proxy_mock.get_redistribution_status() == {"clients": [], "agents": []}

    def test_get_redistribution_status_wrong_panos_version(self, fw_proxy_mock):
        """This tests what happens if this method is run against an older firewall that doesn't support the
        redist commands."""
        xml_text = """
        <response status="error" code="17">
            <msg>
                <line>
                    <![CDATA[ show -> redistribution  is unexpected]]>
                </line>
            </msg>
        </response>"""
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        with pytest.raises(CommandRunFailedException):
            fw_proxy_mock.get_redistribution_status()

    def test_get_user_id_service_status_down(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[
        User ID service info: 
            User id service:               down           
            Reason:                        user_id service is not enabled
        ]]>
            </result>
        </response>"""  # noqa: W291
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_user_id_service_status() == {"status": "down"}

    def test_get_user_id_service_status_up(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <![CDATA[
        User ID service info: 
            User id service:               up           
            listening port:                5007           
            number of clients:             1
        ]]>
            </result>
        </response>"""  # noqa: W291
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_user_id_service_status() == {"status": "up"}

    def test_get_device_software_version(self, fw_proxy_mock):
        fw_proxy_mock._fw.xapi.op = MagicMock()

        xml_text = """
        <response status="success">
            <result>
                <system>
                    <hostname>testfw</hostname>
                    <ip-address>1.1.1.1</ip-address>
                    <public-ip-address>unknown</public-ip-address>
                    <netmask>255.255.254.0</netmask>
                    <default-gateway>1.1.1.1</default-gateway>
                    <is-dhcp>no</is-dhcp>
                    <mac-address>ab:cd:ef:11:22:33</mac-address>
                    <time>Sun Dec  3 18:27:29 2023
        </time>
                    <uptime>179 days, 5:07:34</uptime>
                    <devicename>testfw</devicename>
                    <family>7000</family>
                    <model>PA-7050</model>
                    <serial>11111111111</serial>
                    <cloud-mode>non-cloud</cloud-mode>
                    <sw-version>9.1.12-h3</sw-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <app-version>8709-8047</app-version>
                    <app-release-date></app-release-date>
                    <av-version>4455-4972</av-version>
                    <av-release-date>2023/05/18 14:50:34 PDT</av-release-date>
                    <threat-version>8709-8047</threat-version>
                    <threat-release-date></threat-release-date>
                    <wf-private-version>0</wf-private-version>
                    <wf-private-release-date>unknown</wf-private-release-date>
                    <url-db>paloaltonetworks</url-db>
                    <wildfire-version>0</wildfire-version>
                    <wildfire-release-date></wildfire-release-date>
                    <url-filtering-version>20231204.20037</url-filtering-version>
                    <global-protect-datafile-version>1684375262</global-protect-datafile-version>
                    <global-protect-datafile-release-date>2023/05/17 19:01:02</global-protect-datafile-release-date>
                    <global-protect-clientless-vpn-version>97-245</global-protect-clientless-vpn-version>
                    <global-protect-clientless-vpn-release-date>2023/01/27 14:38:39 PST</global-protect-clientless-vpn-release-date>
                    <logdb-version>9.1.22</logdb-version>
                    <platform-family>7000</platform-family>
                    <high-speed-log-forwarding-mode>off</high-speed-log-forwarding-mode>
                    <vpn-disable-mode>off</vpn-disable-mode>
                    <multi-vsys>on</multi-vsys>
                    <operational-mode>normal</operational-mode>
                    <device-certificate-status>Valid</device-certificate-status>
                </system>
            </result>
        </response>
        """

        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock._fw.xapi.op.return_value = raw_response

        from packaging import version

        assert fw_proxy_mock.get_device_software_version() == version.parse("9.1.12.3")
        assert fw_proxy_mock.get_device_software_version() < version.parse("9.1.13")
        assert fw_proxy_mock.get_device_software_version() < version.parse("9.1.12.4")
        assert fw_proxy_mock.get_device_software_version() < version.parse("10.1.1")
        assert fw_proxy_mock.get_device_software_version() > version.parse("9.0.4.2")

    def test_get_fib_routes(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <dp>dp0</dp>
                <total>16</total>
                <fibs>
                    <entry>
                        <id>2</id>
                        <vr>VR-MAIN</vr>
                        <max>32768</max>
                        <type>0</type>
                        <ecmp>0</ecmp>
                        <entries>
                            <entry>
                                <id>19</id>
                                <dst>0.0.0.0/0</dst>
                                <interface>ethernet1/1</interface>
                                <nh_type>0</nh_type>
                                <flags>ug</flags>
                                <nexthop>10.10.11.1</nexthop>
                                <mtu>1500</mtu>
                            </entry>
                            <entry>
                                <id>1</id>
                                <dst>1.1.1.1/32</dst>
                                <interface>loopback.10</interface>
                                <nh_type>3</nh_type>
                                <flags>uh</flags>
                                <nexthop>1.2.3.4</nexthop>
                                <mtu>1500</mtu>
                            </entry>
                        </entries>
                        <nentries>16</nentries>
                    </entry>
                    <entry>
                        <id>3</id>
                        <vr>VR-MAIN</vr>
                        <max>32768</max>
                        <type>1</type>
                        <ecmp>0</ecmp>
                        <entries/>
                        <nentries>0</nentries>
                    </entry>
                </fibs>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_fib() == {
            "0.0.0.0/0_ethernet1/1_10.10.11.1": {
                "Destination": "0.0.0.0/0",
                "Interface": "ethernet1/1",
                "Next Hop Type": "0",
                "Flags": "ug",
                "Next Hop": "10.10.11.1",
                "MTU": "1500",
            },
            "1.1.1.1/32_loopback.10_1.2.3.4": {
                "Destination": "1.1.1.1/32",
                "Interface": "loopback.10",
                "Next Hop Type": "3",
                "Flags": "uh",
                "Next Hop": "1.2.3.4",
                "MTU": "1500",
            },
        }

    def test_get_fib_routes_none(self, fw_proxy_mock):
        xml_text = """
        <response status="success">
            <result>
                <dp>dp0</dp>
                <total>0</total>
                <fibs/>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert fw_proxy_mock.get_fib() == {}

    def test_get_system_time_rebooted(self, fw_proxy_mock):
        fw_proxy_mock.op = MagicMock()

        xml_text = """
        <response status="success">
            <result>
                <system>
                    <hostname>testfw</hostname>
                    <ip-address>1.1.1.1</ip-address>
                    <public-ip-address>unknown</public-ip-address>
                    <netmask>255.255.254.0</netmask>
                    <default-gateway>1.1.1.1</default-gateway>
                    <is-dhcp>no</is-dhcp>
                    <mac-address>ab:cd:ef:11:22:33</mac-address>
                    <time>Sun Dec  3 18:27:29 2023</time>
                    <uptime>5 days, 1:02:03</uptime>
                    <devicename>testfw</devicename>
                    <family>7000</family>
                    <model>PA-7050</model>
                    <serial>11111111111</serial>
                    <cloud-mode>non-cloud</cloud-mode>
                    <sw-version>9.1.12-h3</sw-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <app-version>8709-8047</app-version>
                    <app-release-date></app-release-date>
                    <av-version>4455-4972</av-version>
                    <av-release-date>2023/05/18 14:50:34 PDT</av-release-date>
                    <threat-version>8709-8047</threat-version>
                    <threat-release-date></threat-release-date>
                    <wf-private-version>0</wf-private-version>
                    <wf-private-release-date>unknown</wf-private-release-date>
                    <url-db>paloaltonetworks</url-db>
                    <wildfire-version>0</wildfire-version>
                    <wildfire-release-date></wildfire-release-date>
                    <url-filtering-version>20231204.20037</url-filtering-version>
                    <global-protect-datafile-version>1684375262</global-protect-datafile-version>
                    <global-protect-datafile-release-date>2023/05/17 19:01:02</global-protect-datafile-release-date>
                    <global-protect-clientless-vpn-version>97-245</global-protect-clientless-vpn-version>
                    <global-protect-clientless-vpn-release-date>2023/01/27 14:38:39 PST</global-protect-clientless-vpn-release-date>
                    <logdb-version>9.1.22</logdb-version>
                    <platform-family>7000</platform-family>
                    <high-speed-log-forwarding-mode>off</high-speed-log-forwarding-mode>
                    <vpn-disable-mode>off</vpn-disable-mode>
                    <multi-vsys>on</multi-vsys>
                    <operational-mode>normal</operational-mode>
                    <device-certificate-status>Valid</device-certificate-status>
                </system>
            </result>
        </response>
        """

        raw_response = ET.fromstring(xml_text)
        fw_proxy_mock.op.return_value = raw_response

        assert type(fw_proxy_mock.get_system_time_rebooted()) is datetime
