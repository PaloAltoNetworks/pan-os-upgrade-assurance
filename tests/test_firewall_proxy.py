import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.firewall_proxy import FirewallProxy, CommandRunFailedException,MalformedResponseException,PanoramaConfigurationMissingException,ContentDBVersionsFormatException,WrongDiskSizeFormatException
from panos_upgrade_assurance.utils import interpret_yes_no
from xmltodict import parse as xml_parse
import xml.etree.ElementTree as ET

@pytest.fixture(scope="function")
def fw_node():
    tested_class = FirewallProxy()
    tested_class.op = MagicMock()
    yield tested_class

class TestFirewallProxy:
    def test_op_parser_correct_response_default_params(self, fw_node):

        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_node.op_parser(cmd) == xml_parse(
            ET.tostring(raw_response.find('result'), encoding='utf8', method='xml'))['result']

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_op_parser_correct_response_custom_params(self, fw_node):

        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_node.op_parser(cmd, True, True) == raw_response.find("result")

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=False, vsys=fw_node.vsys)

    def test_op_parser_incorrect(self, fw_node):

        xml_text = "<response status='fail'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(CommandRunFailedException) as exc_info:
            fw_node.op_parser(cmd)

        expected = f'Failed to run command: {cmd}.'
        assert expected in str(exc_info.value)

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_op_parser_none(self, fw_node):

        xml_text = "<response status='success'><noresult example='1'></noresult></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(MalformedResponseException) as exc_info:
            fw_node.op_parser(cmd)

        expected = f'No result field returned for: {cmd}'
        assert expected in str(exc_info.value)

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_is_pending_changes_true(self, fw_node):

        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_pending_changes() == True

    def test_is_pending_changes_false(self, fw_node):

        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_pending_changes() == False

    def test_is_full_commit_required_true(self, fw_node):

        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_full_commit_required() == True

    def test_is_full_commit_required_false(self, fw_node):

        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_full_commit_required() == False

    def test_is_panorama_configured_true(self, fw_node):

        xml_text = "<response status='success'><result>SomePanoramaConfig</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_panorama_configured() == True

    def test_is_panorama_configured_false(self, fw_node):

        xml_text = "<response status='success'><result></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_panorama_configured() == False

    def test_is_panorama_connected_no_panorama(self, fw_node):
        xml_text = "<response status='success'><result></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        with pytest.raises(PanoramaConfigurationMissingException) as exc_info:
            fw_node.is_panorama_connected()

        expected = f'Device not configured with Panorama.'
        assert expected in str(exc_info.value)

    def test_is_panorama_connected_no_string_response(self, fw_node):
        xml_text = "<response status='success'><result><key1>value1</key1><key2>value2</key2></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        with pytest.raises(MalformedResponseException) as exc_info:
            fw_node.is_panorama_connected()

        expected = f'Response from device is not type of string.'
        assert expected in str(exc_info.value)

    def test_is_panorama_connected_true(self, fw_node):
        xml_text = """<response status='success'><result>
            Panorama Server 1 : 1.2.3.4
                Connected     : yes
                HA state      : disconnected
            Panorama Server 2 : 5.6.7.8
                Connected     : yes
                HA state      : disconnected
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        
        assert fw_node.is_panorama_connected() == True

    def test_is_panorama_connected_no_typical_structure(self, fw_node):
        xml_text = """<response status='success'><result>
            some line : to break code
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        with pytest.raises(MalformedResponseException) as exc_info:
            fw_node.is_panorama_connected()

        expected = f'Panorama configuration block does not have typical structure: <some line : to break code>.'
        assert expected in str(exc_info.value)

    def test_get_ha_configuration(self, fw_node):

        xml_text = """<response status='success'><result>
        {'enabled': 'yes'}
        </result></response>"""
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.get_ha_configuration() == """{'enabled': 'yes'}"""

    def test_get_nics_none(self, fw_node):

        xml_text = """
        <response status="success">
            <result>
                <hw>
                </hw>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        with pytest.raises(MalformedResponseException) as exc_info:
            fw_node.get_nics()

        expected = f'Malformed response from device, no [hw] element present.'
        assert expected in str(exc_info.value)

    def test_get_nics_ok(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_nics() == {'ethernet1/1': 'up', 'ethernet1/2': 'up'}

    def test_get_licenses(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_licenses() == {
            'PAN-DB URL Filtering': {'authcode': None,
                                     'base-license-name': 'PA-VM',
                                     'description': 'Palo Alto Networks URL Filtering '
                                                    'License',
                                     'expired': 'no',
                                     'expires': 'December 31, 2023',
                                     'feature': 'PAN-DB URL Filtering',
                                     'issued': 'April 20, 2023',
                                     'serial': '00000000000000'},
        }

    def test_get_support_license(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_support_license() == {'support_expiry_date': '', 'support_level': ''}
    
    def test_get_routes(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_routes() == {
            'default_0.0.0.0/0_ethernet1/1': {'age': None,
                                  'destination': '0.0.0.0/0',
                                  'flags': 'A S E',
                                  'interface': 'ethernet1/1',
                                  'metric': '10',
                                  'nexthop': '10.10.11.1',
                                  'route-table': 'unicast',
                                  'virtual-router': 'default'},
        }

    def test_get_arp_table(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_arp_table() == {
            'ethernet1/1_10.10.11.1': {'interface': 'ethernet1/1',
                             'ip': '10.10.11.1',
                             'mac': 'aa:bb:cc:dd:ee:ff:ab',
                             'port': 'ethernet1/1',
                             'status': 'c',
                             'ttl': '1777'},
        }

    def test_get_sessions(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_sessions() == [
            {'application': 'ping',
              'decrypt-mirror': 'False',
              'dport': '3',
              'dst': '8.8.8.8',
              'dstnat': 'False',
              'egress': 'ethernet1/1',
              'flags': None,
              'from': 'zone',
              'idx': '20',
              'ingress': 'ethernet1/1',
              'nat': 'False',
              'proto': '1',
              'proxy': 'False',
              'security-rule': 'aqll',
              'source': '10.10.11.2',
              'sport': '32336',
              'srcnat': 'False',
              'start-time': 'Wed May 31 07:59:22 2023',
              'state': 'ACTIVE',
              'to': 'zone',
              'total-byte-count': '196',
              'type': 'FLOW',
              'vsys': 'vsys1',
              'vsys-idx': '1',
              'xdport': '3',
              'xdst': '8.8.8.8',
              'xsource': '10.10.11.2',
              'xsport': '32336'},
        ]

    def test_get_tunnels(self, fw_node):

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
                        <localip>0.0.0.0</localip>
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
        fw_node.op.return_value = raw_response

        assert fw_node.get_tunnels() == {
            'GlobalProtect-Gateway': {},
            'GlobalProtect-site-to-site': {},
            'IPSec': {'my-tunnel': {'gwid': '1',
                                    'id': '1',
                                    'inner-if': 'tunnel.1',
                                    'localip': '0.0.0.0',
                                    'mon': 'off',
                                    'name': 'my-tunnel',
                                    'outer-if': 'ethernet1/1',
                                    'owner': '1',
                                    'peerip': '6.6.6.6',
                                    'state': 'init'}},
            'SSL-VPN': {},
            'hop': {},
        }

    def test_get_latest_available_content_version_ok(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_latest_available_content_version() == "8698-7988"

    def test_get_latest_available_content_version_parse_fail(self, fw_node):
        xml_text = "<response status='success'><result>Not Parsable</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        with pytest.raises(ContentDBVersionsFormatException) as exc_info:
            fw_node.get_latest_available_content_version()

        expected = f'Cannot parse list of available updates for Content DB.'
        assert expected in str(exc_info.value)

    def test_get_content_db_version(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_content_db_version() == "8556-7343"

    def test_get_ntp_servers(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_ntp_servers() == {
            'ntp-server-1': {'authentication-type': 'none',
                             'name': '0.pool.ntp.org',
                             'reachable': 'no',
                             'status': 'available'},
            'ntp-server-2': {'authentication-type': 'none',
                             'name': '1.pool.ntp.org',
                             'reachable': 'no',
                             'status': 'available'},
            'synched': '1.pool.ntp.org',
        }

# CHECK THIS ONE BECAUSE IT IS NOT WORKING PROPERLY

    def test_get_disk_utilization_ok(self, fw_node):

        xml_text = """
        <response status="success">
            <result>
        <![CDATA[ Filesystem Size Used Avail Use% Mounted on /dev/root 6.9G 5.2G 1.4G 79% / none 7.9G 72K 7.9G 1% /dev /dev/sda5 16G 1.2G 14G 8% /opt/pancfg /dev/sda6 7.9G 1.6G 5.9G 22% /opt/panrepo tmpfs 12G 8.7G 2.7G 77% /dev/shm cgroup_root 7.9G 0 7.9G 0% /cgroup /dev/sda8 21G 197M 20G 1% /opt/panlogs ]]>
        </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.get_disk_utilization() == { 
        }

# AFTER SOLVE THIS ONE!!

    # def test_get_disk_utilization_parse_fail(self, fw_node):
    #     xml_text = "<response status='success'><result>Not Parsable</result></response>"
    #     raw_response = ET.fromstring(xml_text)
    #     fw_node.op.return_value = raw_response
    #     with pytest.raises(WrongDiskSizeFormatException) as exc_info:
    #         fw_node.get_disk_utilization()

    #     expected = f'Free disk size has wrong format.'
    #     assert expected in str(exc_info.value)

    def test_get_available_image_data(self, fw_node):

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
        fw_node.op.return_value = raw_response

        assert fw_node.get_available_image_data() == {
            '11.0.0': {'current': 'no',
                       'downloaded': 'no',
                       'filename': 'PanOS_vm-11.0.0',
                       'latest': 'no',
                       'release-notes': 'https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes',
                       'released-on': '2022/11/17 08:45:28',
                       'size': '1037',
                       'size-kb': '1062271',
                       'uploaded': 'no',
                       'version': '11.0.0'},
            '11.0.1': {'current': 'no',
                       'downloaded': 'no',
                       'filename': 'PanOS_vm-11.0.1',
                       'latest': 'yes',
                       'release-notes': 'https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes',
                       'released-on': '2023/03/29 15:05:25',
                       'size': '492',
                       'size-kb': '504796',
                       'uploaded': 'no',
                       'version': '11.0.1'},
        }

    def test_get_mp_clock(self, fw_node):

        xml_text = """
        <response status="success">
            <result>Wed May 31 11:50:21 PDT 2023 </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.get_mp_clock() == {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:50:21',
            'tz': 'PDT',
            'year': '2023',
        }

    def test_get_dp_clock(self, fw_node):

        xml_text = """
        <response status="success">
            <result>
                <member>dataplane time: Wed May 31 11:52:34 PDT 2023 </member>
            </result>
        </response>
        """
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.get_dp_clock() == {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:52:34',
            'tz': 'PDT',
            'year': '2023',
        }