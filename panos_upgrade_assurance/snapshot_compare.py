from typing import Optional, Union, List, Dict
from panos_upgrade_assurance.utils import ConfigParser, SnapType


class MissingKeyException(Exception):
    """Used when an exception about the missing keys in a dictionary is thrown."""
    pass

class WrongDataTypeException(Exception):
    """Used when a variable does not meet the data type requirements."""
    pass

class SnapshotSchemeMismatchException(Exception):
    """Used when a snapshot element contains different properties in both snapshots."""
    pass


class SnapshotCompare:
    """Class comparing snapshots of Firewall Nodes.

    This object can be used to compare two Firewall snapshots made with the :meth:`.CheckFirewall.run_snapshots` method and present results of this comparison.
    Its main purpose is to compare two snapshots made with the :class:`.CheckFirewall` class. However, the code is generic enough to compare any two dictionaries as long as they follow the schema below:

    ::

        {
            'root_key': {
                'key': value
            }
        }

    Where:

        * ``root_key`` has to be present and mapped to a method in the ``_functions_mapping`` variable in order to be recognized during a comparison. 
        * ``value`` can be either of a simple type (``str``, ``int``, ``float``, ``bool``) or a nested ``dict``. 

    :ivar _functions_mapping: Internal variable containing the map of all valid report types mapped to the specific methods.
        
        This mapping is used to verify the requested report and to map the report to an actual method that will eventually run. Keys in this dictionary are report names as defined in the :class:`.SnapType` class. Essentially, these are the same values that one would specify when creating a snapshot with the :meth:`.CheckFirewall.run_snapshots` method. Values are references to the methods that will run.
    :vartype _functions_mapping: dict

    """
    def __init__(
        self,
        left_snapshot: Dict[str, Union[str, dict]],
        right_snapshot: Dict[str, Union[str, dict]],
    ) -> None:
        """SnapshotCompare constructor.

        Initializes an object by storing both snapshots to be compared.

        :param left_snapshot: First snapshot dictionary to be compared, usually the older one, for example a pre-upgrade snapshot.
        :type left_snapshot: dict
        :param right_snapshot: Second snapshot dictionary to be compared, usually the newer one, for example a post-upgrade snapshot.
        :type right_snapshot: dict
        """
        self.left_snap = left_snapshot
        self.right_snap = right_snapshot
        self._functions_mapping = {
            SnapType.NICS: self.get_diff_and_threshold,
            SnapType.ROUTES: self.get_diff_and_threshold,
            SnapType.LICENSE: self.get_diff_and_threshold,
            SnapType.ARP_TABLE: self.get_diff_and_threshold,
            SnapType.CONTENT_VERSION: self.get_diff_and_threshold,
            SnapType.SESSION_STATS: self.get_count_change_percentage,
            SnapType.IPSEC_TUNNELS: self.get_diff_and_threshold
        }

    def compare_snapshots(
        self,
        reports: Optional[List[Union[dict, str]]] = None
    ) -> Dict[str, dict]:
        """A method that triggers the actual snapshot comparison.

        This is a single point of entry to generate a comparison report. It takes both reports stored in the class object and compares areas specified in the ``reports`` parameter.

        :param reports: A list of reports - snapshot state areas with optional configuration. This parameter follows the`dialect`_ of :class:`.ConfigParser` class.

            The reports list is essentially the list of keys present in the snapshots. These keys, however, are the state areas specified when the snapshot is made with the :meth:`.CheckFirewall.run_snapshots` method. This means that the reports list is basically the list of state areas. The only difference is that for reports, it is possible to specify an additional configuration. This means that the list can be specified in two ways, as ``str`` or ``dict`` (in the same manner as for :meth:`.CheckFirewall.run_readiness_checks`).

            For the elements specified as:

                * ``str`` - the element value is the name of the report (state area),
                * ``dict`` - the element contains the report name (state area) and the key value and report configuration as the element value.

            Refer to the :ref:`report_docs` documentation for details on the currently available snapshot areas and optional parameters that can be configured for them.

        :type reports: list, optional
        :raises WrongDataTypeException: An exception is raised when the configuration in a data type is different than ``str`` or ``dict``.
        :return: Result of comparison in a form of the Python dictionary.

            Keys in this dictionary are again state areas where values depend on the actual comparison method that was run. Again, refer to the :ref:`report_docs` documentation for details.

        :rtype: dict
        """

        result = {}
        reports = ConfigParser(
                               valid_elements=set(self._functions_mapping.keys()),
                               requested_config=reports
                  ).prepare_config()

        for report in reports:
            if isinstance(report, dict):
                report_type, report_config = list(report.items())[0]
                report_config.update({'report_type': report_type})
            elif isinstance(report, str):
                report_type = report
                report_config = {'report_type': report_type}
            else:
                raise WrongDataTypeException(f'Wrong configuration format for report: {report}.')

            self.key_checker(self.left_snap, self.right_snap, report_type)
            result.update({report_type: self._functions_mapping[report_type](**report_config)})

        return result

    @staticmethod
    def key_checker(left_dict: dict, right_dict: dict, key: str) -> None:
        """The static method to check if a key is available in both dictionaries.

        This method looks for a given key in two dictionaries. Its main purpose is to assure that when comparing a key-value pair from two dictionaries, it actually exists in both.

        :param left_dict: 1st dictionary to verify.
        :type left_dict: dict
        :param right_dict: 2nd dictionary to verify.
        :type right_dict: dict
        :param key: Key name to check.
        :type key: str
        :raises MissingKeyException: when key is not available in at least one snapshot.
        """
        left_snap_missing_key = False if key in left_dict else True
        right_snap_missing_key = False if key in right_dict else True

        if left_snap_missing_key and right_snap_missing_key:
            raise MissingKeyException(f"{key} is missing in both snapshots")
        if left_snap_missing_key or right_snap_missing_key:
            raise MissingKeyException(f"{key} is missing in {'left snapshot' if left_snap_missing_key else 'right snapshot'}")

    @staticmethod
    def calculate_change_percentage(
        first_value: Union[str,int],
        second_value: Union[str,int],
        threshold: Union[str,float]
    ) -> Dict[str, Union[bool, float]]:
        """The static method to compare differences between values against a given threshold.

        Values to be compared should be the ``int`` or ``str`` representation of ``int``. This method is used when comparing a count of elements so a floating point value here is not expected.
        The threshold value, on the other hand, should be the ``float`` or ``str`` representation of ``float``. This is a percentage value.

        :param first_value: First value to compare.
        :type first_value: int, str
        :param second_value: Second value to compare.
        :type second_value: int, str
        :param threshold: Maximal difference between values given as percentage.
        :type threshold: float, str
        :raises WrongDataTypeException: An exception is raised when the threshold value is not between ``0`` and ``100`` (typical percentage boundaries).
        :return: A dictionary with the comparison results.

            The format is as follows:

            ::

                {
                    passed: bool, 
                    change_percentage: float,
                    change_threshold: float
                }
            
            Where:

                * ``passed`` is an information if the test passed:
                    * ``True`` if difference is lower or equal to threshold,
                    * ``False`` otherwise,
                * the actual difference represented as percentage,
                * the originally requested threshold (for reporting purposes).

        :rtype: dict
        """
        first_value = int(first_value)
        second_value = int(second_value)
        threshold = float(threshold)

        result = dict(
            passed=True,
            change_percentage=float(0),
            change_threshold=threshold
        )

        if not (first_value == 0 and second_value == 0):
            if threshold < 0 or threshold > 100:
                raise WrongDataTypeException('The threshold should be a percentage value between 0 and 100.')

            result['change_percentage'] = round(
                (abs(first_value - second_value) / (first_value if first_value >= second_value else second_value)) * 100, 2)
            if result['change_percentage'] > threshold:
                result['passed'] = False
        return result

    @staticmethod
    def calculate_diff_on_dicts(
            left_side_to_compare: Dict[str, Union[str,dict]],
            right_side_to_compare: Dict[str, Union[str,dict]],
            properties: Optional[List[str]] = None,
    ) -> Dict[str, dict]:
        """The static method to calculate a difference between two dictionaries.


        :param left_side_to_compare: 1st dictionary to compare.

            When this method is triggered by :meth:`.compare_snapshots`, the dictionary comes from the ``self.left_snap`` snapshot.

        :type left_side_to_compare: dict

        :param right_side_to_compare: 2nd dictionary to compare, comes from the self.right_snap snapshot.

            When this method is triggered by :meth:`.compare_snapshots`, the dictionary comes from the ``self.right_snap`` snapshot.

        :type right_side_to_compare: dict

        :param properties: The list of properties used to compare two dictionaries.
            
            This is a list of the bottom most level keys. For example, when comparing route tables snapshots formatted like:

            ::

                {
                    "routes": {
                        "default_0.0.0.0/0_ethernet1/3": {
                            "virtual-router": "default",
                            "destination": "0.0.0.0/0",
                            "nexthop": "10.26.129.129",
                            "metric": "10",
                            "flags": "A S",
                            "age": null,
                            "interface": "ethernet1/3",
                            "route-table": "unicast"
                        },
                        ...
                    }
                }

            the bottom most level keys are: ``virtual-router``, ``destination``, ``nexthop``, ``metric``, ``flags``, ``age``, ``interface``, ``route-table``.
            
            This list follows :class:`.ConfigParser` `dialect`_, which means that default ``all`` and negation are supported.

        :type properties: list(str), optional
        :raises WrongDataTypeException: Thrown when one of the ``properties`` elements has a wrong data type.
        :return: Summary of the differences between dictionaries.

            The output has the following format:

            ::

                {
                    'missing': {
                        'passed': True,
                        'missing_keys': []
                    },
                    'added': {
                        'passed': True,
                        'added_keys': []
                    },
                    'changed': {
                        'passed': True,
                        'changed_raw': {}
                    }
                }

            The difference is calculated from three perspectives:

                1. are there any keys missing in the 2nd (right) dictionary that are present in the 1st (left) - this is represented under the ``missing`` key in the results.
                2. are there any keys in the 2nd (right) dictionary that are not present in the 1st (left) - this is represented under the ``added`` key in the results.
                3. for the keys that are present in both dictionaries, are values for these keys the same or different - this is represented under the ``changed`` key in the results.

            This is the **recursive** method. When calculating the changed values, if a value for the key is ``dict``, we run the method again on that dictionary - we go down one level in the nested structure. We do that to a point where the value is of the ``str`` type. 
            Therefore, when the final comparison results are presented, the ``changed`` key usually contains a nested results structure. This means it contains a dictionary with the ``missing``, ``added``, and ``changed`` keys.
            Each comparison perspective contains the ``passed`` property that immediately informs if this comparison gave any results (``False``) or not (``True``).

            Example:

                Let's assume we want to compare two dictionaries of the following structure:

                ::
                
                    left_dict = {
                        'root_key1'= {
                            'key'= 'value'
                        }
                        'root_key2'= {
                            'key'= 'value'
                        }
                    }

                    right_dict = {
                        'root_key2'= {
                            'key'= 'other_value'
                        }
                    }

                The result of this comparison would look like this:
                
                ::

                    {
                        "missing": {
                            "passed": false,
                            "missing_keys": [
                                "root_key1"
                            ]
                        },
                        "added": {
                            "passed": true,
                            "added_keys": []
                        },
                        "changed": {
                            "passed": false,
                            "changed_raw": {
                            "root_key2": {
                                "missing": {
                                    "passed": true,
                                    "missing_keys": []
                                },
                                "added": {
                                    "passed": true,
                                    "added_keys": []
                                },
                                "changed": {
                                    "passed": false,
                                    "changed_raw": {
                                        "key": {
                                            "left_snap": "value",
                                            "right_snap": "other_value"
                                        }
                                    }
                                },
                                "passed": false
                            }
                        }
                    }

        :rtype: dict
        """

        if not (left_side_to_compare and right_side_to_compare):
            return {}

        result = dict(
            missing=dict(
                passed=True,
                missing_keys=[]
            ),
            added=dict(
                passed=True,
                added_keys=[]
            ),
            changed=dict(
                passed=True,
                changed_raw={}
            )
        )

        missing = left_side_to_compare.keys() - right_side_to_compare.keys()
        if missing:
            result['missing']['passed'] = False
            for key in missing:
                result['missing']['missing_keys'].append(key)

        added = right_side_to_compare.keys() - left_side_to_compare.keys()
        if added:
            result['added']['passed'] = False
            for key in added:
                result['added']['added_keys'].append(key)

        common_keys = left_side_to_compare.keys() & right_side_to_compare.keys()
        at_lowest_level = True if isinstance(right_side_to_compare[list(common_keys)[0]], str) else False
        keys_to_check = ConfigParser(valid_elements=set(common_keys), requested_config=properties).prepare_config() if at_lowest_level else common_keys

        item_changed = False
        for key in keys_to_check:
            if right_side_to_compare[key] != left_side_to_compare[key]:
                if isinstance(left_side_to_compare[key], str):
                    result['changed']['changed_raw'][key] = dict(
                        left_snap=left_side_to_compare[key],
                        right_snap=right_side_to_compare[key]
                    )
                    item_changed = True
                elif isinstance(left_side_to_compare[key], dict):
                    nested_results = SnapshotCompare.calculate_diff_on_dicts(
                        left_side_to_compare=left_side_to_compare[key],
                        right_side_to_compare=right_side_to_compare[key],
                        properties=properties)

                    SnapshotCompare.calculate_passed(nested_results)
                    if not nested_results["passed"]:
                        result['changed']['changed_raw'][key] = nested_results
                        item_changed = True
                else:
                    raise WrongDataTypeException(f'Unknown value format for key {key}.')
            result['changed']['passed'] = not item_changed

        return result

    @staticmethod
    def calculate_passed(result: Dict[str, Union[dict, str]]) -> None:
        """The static method to calculate the upper level ``passed`` value.

        When two snapshots are compared, a dictionary that is the result of this comparison is structured as in the following :meth:`.get_diff_and_threshold` method: each root key contains a dictionary that has a structure returned by the :meth:`.calculate_diff_on_dicts` method.
        
        This method takes a dictionary under the root key and calculates the ``passed`` flag based on the all ``passed`` flags in that dictionary. This provides a quick way of finding out if any comparison made on data under a root key failed or not. 
        
        To illustrate that, the ``passed`` flag added by this method is marked with an arrow:

        ::

            {
                'added': {
                    'added_keys': [],
                    'passed': True
                },
                'changed': {
                    'changed_raw': {},
                    'passed': True
                },
                'missing': {
                    'missing_keys': [
                        'default_0.0.0.0/0_ethernet1/3'
                    ],
                    'passed': False
                },
                'passed': False   <-------###
            }

        :param result: The result of snapshot difference comparison.
        :type result: dict
        """
        passed = True
        for value in result.values():
            if isinstance(value, dict) and not value['passed']:
                passed = False
        result['passed'] = passed

    def get_diff_and_threshold(self,
            report_type: str,
            properties: Optional[List[str]] = None,
            count_change_threshold: Optional[Union[int, float]] = None
    ) -> Optional[Dict[str, Optional[Union[bool, dict]]]]:
        """The generic snapshot comparison method.

        The generic method to compare two snapshots of a given type. It is meant to fit most of the comparison cases.
        It is capable of calculating both - a difference between two snapshots and the change count in the elements against a given threshold. The 1\ :sup:`st` calculation is done by the :meth:`.calculate_diff_on_dicts` method, the 2\ :sup:`nd` - internally.

        The changed elements count does not compare the count of elements in each snapshot. This value represents the number of actual changes, so elements added, missing and changed. This is compared against the number of elements in the left snapshot as this one is usually the 1st one taken and it's treated as a source of truth. 

        The changed elements count is presented as a percentage. In scenarios where the right snapshot has more elements then the left one, it can give values greater than 100%.

        :param report_type: Name of report (type) that has to be compared.
        
            Basically this is a snapshot state area, for example ``nics``, ``routes``, etc.

        :type report_type: str
        :param properties: (defaults to ``None``) An optional list of properties to include or exclude when comparing snapshots.

            This parameter is passed directly to the :meth:`.calculate_diff_on_dicts` method. For details on this method parameters, see the documentation for this method.

        :type properties: list(str), optional
        :param count_change_threshold: (defaults to ``None``) The maximum difference between number of changed elements in each snapshot (as percentage).
        :type count_change_threshold: int, float, optional
        :return: Comparison results.

            This method produces a complex set of nested dictionaries. Each level contains the ``passed`` flag indicating if the comparison of a particular type or for a particular level failed or not, and the actual comparison results. 

            An example for the route tables, crafted in a way that almost each level fails:

            ::

                {
                    "added": {
                        "added_keys": [
                            "default_10.26.129.0/25_ethernet1/2",
                            "default_168.63.129.16/32_ethernet1/3"
                        ],
                        "passed": "False"
                    },
                    "missing": {
                        "missing_keys": [
                            "default_0.0.0.0/0_ethernet1/3"
                        ],
                        "passed": "False"
                    },
                    "changed": {
                        "changed_raw": {
                            "default_10.26.130.0/25_ethernet1/2": {
                                "added": {
                                    "added_keys": [],
                                    "passed": "True"
                                },
                                "missing": {
                                    "missing_keys": [],
                                    "passed": "True"
                                },
                                "changed": {
                                    "changed_raw": {
                                        "flags": {
                                            "left_snap": "A S",
                                            "right_snap": "A"
                                        }
                                    },
                                    "passed": "False"
                                },
                                "passed": "False"
                            }
                        },
                        "passed": "False"
                    },
                    "count_change_percentage": {
                        "change_percentage": 33.33,
                        "change_threshold": 1,
                        "passed": "False"
                    },
                    "passed": "False"
                }

            In the example above, you can also see a nested dictionary produced by the :meth:`.calculate_diff_on_dicts` method under ``changed.changed_raw``. 

        :rtype: dict
        """
        result = {}

        diff = SnapshotCompare.calculate_diff_on_dicts(
            left_side_to_compare=self.left_snap[report_type],
            right_side_to_compare=self.right_snap[report_type],
            properties=properties,
        )
        result.update(diff)

        if count_change_threshold and result:
            if count_change_threshold < 0 or count_change_threshold > 100:
                raise WrongDataTypeException('The threshold should be a percentage value between 0 and 100.')

            added_count = len(result['added']['added_keys'])
            missing_count = len(result['missing']['missing_keys'])
            changed_count = len(result['changed']['changed_raw'])
            left_total_count = len(self.left_snap[report_type].keys())
            right_total_count = len(self.right_snap[report_type].keys())

            diff = 1 if left_total_count == 0 else (added_count + missing_count + changed_count)/left_total_count
            diff_percentage = round(float(diff)*100,2)

            passed = diff_percentage <= count_change_threshold

            result.update({'count_change_percentage': dict(
                passed=passed,
                change_percentage=diff_percentage,
                change_threshold=float(count_change_threshold)
            )})

        if result:
            SnapshotCompare.calculate_passed(result)
        else:
            result = None
        return result

    # custom compare methods
    def get_count_change_percentage(
        self,
        report_type: str,
        thresholds: Optional[List[Dict[str, Union[int, float]]]] = None
    ) -> Optional[Dict[str, Union[bool, dict]]]:
        """The basic value change against a threshold comparison method.

        The generic method to calculate the change on values and compare them against a given threshold.

        In opposition to the :meth:`.get_diff_and_threshold` method, this one does not calculate the count change but the actual difference between the numerical values. 
        A good example is a change in the session count. The snapshot for this area is a dictionary with the keys taking values of different session types and values containing the actual session count:

        ::

            {
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
                    "num-tcp": "1",
                    "num-udp": "0",
                    ...
                }
            }

        This method:
        
            * sweeps through all the session types provided in the ``thresholds`` variable,
            * calculates the actual difference, 
            * compares the actual difference with the threshold value (percentage) for a particular session type.

        :param thresholds: (defaults to ``None``) The list of elements to compare.
        
            This is a list of dictionaries in the form of:
            
            ::
            
                {
                    element_type: threshold_value
                }
                
            where:
            
                * ``element_type`` is a key which value we are going to compare,
                * ``threshold_value`` is a percentage value provided as either ``int`` or ``float``. If the list is empty, the method will return ``None``. :class:`.ConfigParser` `dialect`_ is **NOT followed** for this variable.

            Below there is a sample list for the ``sessions_stat`` dictionary shown above that would calculate differences for the TCP and UDP sessions:

            ::

                [
                    { 'num-tcp': 1.5 },
                    { 'num-udp': 15 },
                ]
                
        :type thresholds: list
        :raises SnapshotSchemeMismatchException: Thrown when a snapshot element has a different set of properties in both snapshots.
        :return: The result of difference compared against a threshold.
        
            The result for each value is in the same form as returned by the :meth:`.calculate_change_percentage` method. For the examples above, the return value would be:

            ::

                {
                    'num-tcp': {
                        'change_percentage': 99.0,
                        'change_threshold': 1.5,
                        'passed': False
                    },
                    'num-udp': {
                        'change_percentage': 100.0,
                        'change_threshold': 15.0,
                        'passed': False
                    },
                    'passed': False
                }

        :rtype: dict, optional
        """

        if not thresholds:
            return None

        result = dict(
            passed=True,
        )

        if self.left_snap[report_type].keys() != self.right_snap[report_type].keys():
            raise SnapshotSchemeMismatchException(f'Snapshots contain different set of data for {report_type} report.')

        elements = ConfigParser(
                                    valid_elements=set(self.left_snap[report_type].keys()),
                                    requested_config=thresholds,
                        ).prepare_config()

        for element in elements:
            element_type, threshold_value = list(element.items())[0]
            self.key_checker(self.left_snap[report_type], self.right_snap[report_type], element_type)
            result.update({
                element_type: SnapshotCompare.calculate_change_percentage(
                    first_value=self.left_snap[report_type][element_type],
                    second_value=self.right_snap[report_type][element_type],
                    threshold=threshold_value
                )
            })

        SnapshotCompare.calculate_passed(result)
        return result
