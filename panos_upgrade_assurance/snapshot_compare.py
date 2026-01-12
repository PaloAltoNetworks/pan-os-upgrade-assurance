from typing import Optional, Union, List, Dict
from panos_upgrade_assurance.utils import ConfigParser, SnapType
from panos_upgrade_assurance import exceptions


class SnapshotCompare:
    """Class comparing snapshots of Firewall Nodes.

    This object can be used to compare two Firewall snapshots made with the
    [`CheckFirewall.run_snapshots()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_snapshots)
    method and present results of this comparison. Its main purpose is to compare two snapshots made with the
    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class. However, the code is
    generic enough to compare any two dictionaries as long as they follow the schema below:

    ```python showLineNumbers
    {
        'root_key': {
            'key': value
        }
    }
    ```

    Where:

    * `root_key` has to be present and mapped to a method in the `self._functions_mapping` variable in order to be recognized
    during a comparison.
    * `value` can be either of a simple type (`str`, `int`, `float`, `bool`) or a nested `dict`.

    # Attributes

    _functions_mapping (dict): Internal variable containing the map of all valid report types mapped to the specific methods.

        This mapping is used to verify the requested report and to map the report to an actual method that will eventually run.
        Keys in this dictionary are report names as defined in the
        [`SnapType`](/panos/docs/panos-upgrade-assurance/api/utils#class-snaptype) class. Essentially, these are the same
        values that one would specify when creating a snapshot with the
        [`CheckFirewall.run_snapshots()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_snapshots)
        method. Values are references to the methods that will run.

    """

    def __init__(
        self,
        left_snapshot: Dict[str, Union[str, dict]],
        right_snapshot: Dict[str, Union[str, dict]],
    ) -> None:
        """SnapshotCompare constructor.

        Initializes an object by storing both snapshots to be compared.

        # Parameters

        left_snapshot (dict): First snapshot dictionary to be compared, usually the older one, for example a pre-upgrade snapshot.
        right_snapshot (dict): Second snapshot dictionary to be compared, usually the newer one, for example a post-upgrade
            snapshot.

        """
        self.left_snap = left_snapshot
        self.right_snap = right_snapshot
        self._functions_mapping = {
            SnapType.NICS: self.compare_type_generic,
            SnapType.ROUTES: self.compare_type_generic,
            SnapType.BGP_PEERS: self.compare_type_generic,
            SnapType.LICENSE: self.compare_type_generic,
            SnapType.ARP_TABLE: self.compare_type_generic,
            SnapType.CONTENT_VERSION: self.compare_type_generic,
            SnapType.SESSION_STATS: self.compare_type_metric_values,
            SnapType.IPSEC_TUNNELS: self.compare_type_generic,
            SnapType.FIB_ROUTES: self.compare_type_generic,
            SnapType.GLOBAL_JUMBO_FRAME: self.compare_type_generic,
            SnapType.INTERFACES_MTU: self.compare_type_generic,
            SnapType.ARE_ROUTES: self.compare_type_are_routes,
            SnapType.ARE_FIB_ROUTES: self.compare_type_generic,
        }

    def compare_snapshots(self, reports: Optional[List[Union[dict, str]]] = None) -> Dict[str, dict]:
        """A method that triggers the actual snapshot comparison.

        This is a single point of entry to generate a comparison report. It takes both reports stored in the class object and
        compares areas specified in the `reports` parameter.

        Refer to the [documentation on reporting](/panos/docs/panos-upgrade-assurance/configuration-details#reports) for
        details on the currently available snapshot areas and optional parameters that can be configured for them.

        # Parameters

        reports (list, optional): A list of reports - snapshot state areas with optional configuration.
            This parameter follows the [`dialect`](/panos/docs/panos-upgrade-assurance/dialect) of
            [`ConfigParser`](/panos/docs/panos-upgrade-assurance/api/utils#class-configparser) class.

            The reports list is essentially the list of keys present in the snapshots. These keys, however, are the state areas
            specified when the snapshot is made with the
            [`CheckFirewall.run_snapshots()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_snapshots)
            method. This means that the reports list is basically the list of state areas. The only difference is that for
            reports, it is possible to specify an additional configuration. This means that the list can be specified in two
            ways, as `str` or `dict` (in the same manner as for
            [`CheckFirewall.run_readiness_checks()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_readiness_checks)).

            For the elements specified as

            * `str` - the element value is the name of the report (state area),
            * `dict` - the element contains the report name (state area) as the key and report configuration as the element value.

        # Raises

        WrongDataTypeException: An exception is raised when the configuration in a data type is different than `str` or `dict`.

        # Returns

        dict: Result of comparison in a form of the Python dictionary. Keys in this dictionary are again state areas where values
            depend on the actual comparison method that was run.

        """

        result = {}
        reports = ConfigParser(valid_elements=set(self._functions_mapping.keys()), requested_config=reports).prepare_config()

        for report in reports:
            if isinstance(report, dict):
                report_type, report_config = list(report.items())[0]
                if report_config is None:
                    report_config = {}
                report_config.update({"report_type": report_type})
            elif isinstance(report, str):
                report_type = report
                report_config = {"report_type": report_type}
            else:
                raise exceptions.WrongDataTypeException(
                    f"Wrong configuration format for report: {report}."
                )  # NOTE checks are already validated in ConfigParser - this is never executed.

            self.validate_keys_exist(self.left_snap, self.right_snap, report_type)
            result.update({report_type: self._functions_mapping[report_type](**report_config)})

        return result

    @staticmethod
    def validate_keys_exist(left_dict: dict, right_dict: dict, key: Union[str, set, list]) -> None:
        """The static method to validate if a key or a list/set of keys is available in both dictionaries.

        This method looks for a given key or list/set of keys in two dictionaries. Its main purpose is to assure that when
        comparing a key-value pair from two dictionaries, it actually exists in both.

        # Parameters

        left_dict (dict): 1st dictionary to verify.
        right_dict (dict): 2nd dictionary to verify.
        key (str, set, list): Key name or set/list of keys to check.

        # Raises

        MissingKeyException: when key is not available in at least one snapshot.

        """

        if isinstance(key, str):
            key_set = set([key])
        elif isinstance(key, (set, list)):
            key_set = set(key)
        else:
            raise exceptions.WrongDataTypeException(f"The key variable is a {type(key)} but should be either: str, set or list")

        left_snap_missing_key = False if key_set.issubset(left_dict.keys()) else True
        right_snap_missing_key = False if key_set.issubset(right_dict.keys()) else True

        if left_snap_missing_key and right_snap_missing_key:
            raise exceptions.MissingKeyException(f"{key} (some elements if set/list) is missing in both snapshots")
        if left_snap_missing_key or right_snap_missing_key:
            raise exceptions.MissingKeyException(
                f"{key} (some elements if set/list) is missing in {'left snapshot' if left_snap_missing_key else 'right snapshot'}"
            )

    @staticmethod
    def calculate_diff_on_dicts(
        left_side_to_compare: Dict[str, Union[str, dict]],
        right_side_to_compare: Dict[str, Union[str, dict]],
        properties: Optional[List[str]] = None,
    ) -> Dict[str, dict]:
        """The static method to calculate a difference between two dictionaries.

        By default dictionaries are compared by going down all nested levels. It is possible to configure which keys on each
        level should be compared (by default we compare all available keys). This is done using the `properties` parameter.
        It's a list of keys that can be compared or skipped on each level. For example, when comparing route tables snapshots are
        formatted like:

        ```python showLineNumbers
        {
            "routes": {
                "default_0.0.0.0/0_ethernet1/3_10.26.129.129": {
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
        ```

        The keys to process here can be:

        - `default_0.0.0.0/0_ethernet1/3_10.26.129.129`,
        - `virtual-router`,
        - `destination`,
        - `nexthop`,
        - `metric`,
        - `flags`,
        - `age`,
        - `interface`,
        - `route-table`.

        This list follows [`ConfigParser`](/panos/docs/panos-upgrade-assurance/api/utils#class-configparser)
        [`dialect`](/panos/docs/panos-upgrade-assurance/dialect).

        The difference between dictionaries is calculated from three perspectives:

        1. are there any keys missing in the 2nd (right) dictionary that are present in the 1st (left) - this is represented
        under the `missing` key in the results.
        2. are there any keys in the 2nd (right) dictionary that are not present in the 1st (left) - this is represented under
        the `added` key in the results.
        3. for the keys that are present in both dictionaries, are values for these keys the same or different - this is
        represented under the `changed` key in the results.

        This is a **recursive** method. When calculating changed values, if a value for the key is `dict`, we run the method
        again on that dictionary - we go down one level in the nested structure. We do that to a point where the value is one of
        `str`, `int` type or None. Therefore, when the final comparison results are presented, the `changed` key usually contains
        a nested results structure. This means it contains a dictionary with the `missing`, `added`, and `changed` keys.
        Each comparison perspective contains the `passed` property that immediately informs if this comparison gave any results
        (`False`) or not (`True`).

        `properties` can be defined for any level of nested dictionaries which implies:

        - Allow comparison of specific parent dictionaries.
        - Skip specific parent dictionaries.
        - Allow comparison/exclusion of specific sub-dictionaries or keys only.
        - If given keys have parent-child relationship then all keys for a matching parent are compared.
        Meaning it doesn’t do an \"AND\" operation on the given properities for nested dictionaries.

        Also note that missing/added keys in parent dictionaries are not reported for comparison when specific keys
        are requested to be compared with the `properties` parameter.

        **Example**

        Let's assume we want to compare two dictionaries of the following structure:

        ```python showLineNumbers
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
        ```

        The result of this comparison would look like this:

        ```python showLineNumbers
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
        ```

        # Parameters

        left_side_to_compare (dict): 1st dictionary to compare. When this method is triggered by
            [`compare_snapshots()`](#snapshotcomparecompare_snapshots), the dictionary comes from the `self.left_snap` snapshot.
        right_side_to_compare (dict): 2nd dictionary to compare, comes from the self.right_snap snapshot. When this method is
            triggered by [`compare_snapshots()`](#snapshotcomparecompare_snapshots), the dictionary comes from the
            `self.right_snap` snapshot.
        properties (list(str), optional): The list of properties used to compare two dictionaries.

        # Raises

        WrongDataTypeException: Thrown when one of the `properties` elements has a wrong data type.

        # Returns

        dict: Summary of the differences between dictionaries. The output has the following format:

        ```python showLineNumbers title="Sample output"
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
        ```

        """
        result = dict(
            missing=dict(passed=True, missing_keys=[]),
            added=dict(passed=True, added_keys=[]),
            changed=dict(passed=True, changed_raw={}),
        )

        missing = left_side_to_compare.keys() - right_side_to_compare.keys()
        for key in missing:
            if ConfigParser.is_element_included(key, properties):
                result["missing"]["missing_keys"].append(key)
                result["missing"]["passed"] = False

        added = right_side_to_compare.keys() - left_side_to_compare.keys()
        for key in added:
            if ConfigParser.is_element_included(key, properties):
                result["added"]["added_keys"].append(key)
                result["added"]["passed"] = False

        common_keys = left_side_to_compare.keys() & right_side_to_compare.keys()

        item_changed = False
        for key in common_keys:
            if right_side_to_compare[key] != left_side_to_compare[key]:
                if (
                    left_side_to_compare[key] is None
                    or right_side_to_compare[key] is None
                    or isinstance(left_side_to_compare[key], (str, int))
                ):
                    if ConfigParser.is_element_included(key, properties):
                        result["changed"]["changed_raw"][key] = dict(
                            left_snap=left_side_to_compare[key],
                            right_snap=right_side_to_compare[key],
                        )
                        item_changed = True

                elif isinstance(left_side_to_compare[key], dict):
                    # Checking if we should further compare nested dicts - it doesnot work to check with is_element_included for
                    # this case since nested dict key might not be included but nested keys might be subject to comparison
                    if ConfigParser.is_element_explicit_excluded(key, properties):
                        continue  # skip to the next key

                    if properties and key in properties:
                        # call without properties - do not allow multi level (combined with parent) filtering..
                        nested_results = SnapshotCompare.calculate_diff_on_dicts(
                            left_side_to_compare=left_side_to_compare[key],
                            right_side_to_compare=right_side_to_compare[key],
                        )
                    else:
                        nested_results = SnapshotCompare.calculate_diff_on_dicts(
                            left_side_to_compare=left_side_to_compare[key],
                            right_side_to_compare=right_side_to_compare[key],
                            properties=properties,
                        )

                    SnapshotCompare.calculate_passed(nested_results)
                    if not nested_results["passed"]:
                        result["changed"]["changed_raw"][key] = nested_results
                        item_changed = True
                else:
                    raise exceptions.WrongDataTypeException(f"Unknown value format for key {key}.")
            result["changed"]["passed"] = not item_changed

        return result

    @staticmethod
    def calculate_passed(result: Dict[str, Union[dict, str]]) -> None:
        """The static method to calculate the upper level `passed` value.

        When two snapshots are compared, a dictionary that is the result of this comparison is structured as in the following
        [`compare_type_generic()`](#snapshotcomparecompare_type_generic) method: each root key contains a dictionary that has
        a structure returned by the [`calculate_diff_on_dicts()`](#snapshotcomparecalculate_diff_on_dicts) method.

        This method takes a dictionary under the root key and calculates the `passed` flag based on the all `passed` flags in
        that dictionary. This provides a quick way of finding out if any comparison made on data under a root key failed or not.

        To illustrate that, the `passed` flag added by this method is highlighted:

        ```python showLineNumbers title="Example"
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
                    'default_0.0.0.0/0_ethernet1/3_10.26.129.129'
                ],
                'passed': False
            },
            # highlight-next-line
            'passed': False
        }
        ```

        :::caution
        This method operates on the passed dictionary directly.
        :::

        # Parameters

        result (dict): A dictionary for which the `passed` property should be calculated.

        """
        passed = True
        for value in result.values():
            if isinstance(value, dict) and not value["passed"]:
                passed = False
        result["passed"] = passed

    def _calculate_metric_change_percentage(
        self,
        first_value: Union[str, int],
        second_value: Union[str, int],
        threshold: Union[str, float],
    ) -> Dict[str, Union[bool, float]]:
        """Compare differences between metric values against a given threshold.

        Values to be compared should be the `int` or `str` representation of `int`. This method is used when comparing a count of
        elements so a floating point value here is not expected. The threshold value, on the other hand, should be the `float` or
        `str` representation of `float`. This is a percentage value.

        The format of the returned value is the following:

        ```python showLineNumbers
        {
            passed: bool,
            change_percentage: float,
            change_threshold: float
        }
        ```

        Where:

        - `passed` is an information if the test passed:
            - `True` if difference is lower or equal to threshold,
            - `False` otherwise,
        - the actual difference represented as percentage,
        - the originally requested threshold (for reporting purposes).

        # Parameters

        first_value (int, str): First value to compare.
        second_value (int, str): Second value to compare.
        threshold (float, str): Maximal difference between values given as percentage.

        # Raises

        WrongDataTypeException: An exception is raised when the threshold value is not between `0` and `100` (typical percentage
            boundaries).

        # Returns

        dict: A dictionary with the comparison results.

        """
        first_value = int(first_value)
        second_value = int(second_value)
        threshold = float(threshold)

        result = dict(passed=True, change_percentage=float(0), change_threshold=threshold)

        if not (first_value == 0 and second_value == 0):
            if threshold < 0 or threshold > 100:
                raise exceptions.WrongDataTypeException("The threshold should be a percentage value between 0 and 100.")

            result["change_percentage"] = round(
                (abs(first_value - second_value) / (first_value if first_value >= second_value else second_value)) * 100,
                2,
            )
            if result["change_percentage"] > threshold:
                result["passed"] = False
        return result

    def _calculate_count_change_percentage(
        self,
        comparison_result: Dict[str, dict],
        left_snapshot_type_dict: Dict[str, Union[str, dict]],
        right_snapshot_type_dict: Dict[str, Union[str, dict]],
        count_change_threshold: Union[int, float],
    ) -> Dict[str, Union[bool, float]]:
        """Calculate the percentage of elements changed between two snapshots of a snapshot type.

        This method calculates what percentage of elements have been added, removed, or changed
        between two snapshot captures of a snapshot type, and determines if this percentage is within
        an acceptable threshold.

        # Parameters

        comparison_result (dict): The comparison result dictionary containing added, missing and changed keys for a snapshot type.
        left_snapshot_type_dict (dict): The left (usually older) snapshot dictionary for a particualar snapshot type.
        right_snapshot_type_dict (dict): The right (usually newer) snapshot dictionary for a particualar snapshot type.
        count_change_threshold (int, float): The maximum acceptable percentage change.

        # Raises

        WrongDataTypeException: If the threshold is not between 0 and 100.

        # Returns

        dict: A dictionary with the calculation results containing:
            - passed (bool): Whether the change percentage is within threshold
            - change_percentage (float): The calculated change percentage
            - change_threshold (float): The original threshold value
        """
        if count_change_threshold < 0 or count_change_threshold > 100:
            raise exceptions.WrongDataTypeException("The threshold should be a percentage value between 0 and 100.")

        added_count = len(comparison_result["added"]["added_keys"])
        missing_count = len(comparison_result["missing"]["missing_keys"])
        changed_count = len(comparison_result["changed"]["changed_raw"])
        left_total_count = len(left_snapshot_type_dict.keys())
        right_total_count = len(right_snapshot_type_dict.keys())

        if left_total_count == 0 and right_total_count == 0:  # diff should be 0 when both sides are empty
            diff = 0
        elif left_total_count == 0:
            diff = 1
        else:
            diff = (added_count + missing_count + changed_count) / left_total_count

        diff_percentage = round(float(diff) * 100, 2)
        passed = diff_percentage <= count_change_threshold

        return {"passed": passed, "change_percentage": diff_percentage, "change_threshold": float(count_change_threshold)}

    def compare_type_generic(
        self,
        report_type: str,
        properties: Optional[List[str]] = None,
        count_change_threshold: Optional[Union[int, float]] = None,
    ) -> Dict[str, Union[bool, dict]]:
        """The generic snapshot type comparison method.

        The generic method to compare two snapshots of a given type. It is meant to fit most of the comparison cases.
        It is capable of calculating both - a difference between two snapshots and the change count in the elements against a
        given threshold. The 1<sup>st</sup> calculation is done by the
        [`calculate_diff_on_dicts()`](#snapshotcomparecalculate_diff_on_dicts) method, the 2<sup>nd</sup> - internally.

        The changed elements count does not compare the count of elements in each snapshot. This value represents the number of
        actual changes, so elements added, missing and changed. This is compared against the number of elements in the left
        snapshot as this one is usually the 1st one taken and it's treated as a source of truth.

        The changed elements count is presented as a percentage. In scenarios where the right snapshot has more elements then the
        left one, it can give values greater than 100%.

        This method produces a complex set of nested dictionaries. Each level contains the `passed` flag indicating if the
        comparison of a particular type or for a particular level failed or not, and the actual comparison results.

        An example for the route tables, crafted in a way that almost each level fails:

        ```json showLineNumbers title="Example"
        {
            "added": {
                "added_keys": [
                    "default_10.26.129.0/25_ethernet1/2_10.26.129.1",
                    "default_168.63.129.16/32_ethernet1/3_10.26.129.129"
                ],
                "passed": "False"
            },
            "missing": {
                "missing_keys": [
                    "default_0.0.0.0/0_ethernet1/3_10.26.129.129"
                ],
                "passed": "False"
            },
            "changed": {
                # highlight-start
                "changed_raw": {
                    "default_10.26.130.0/25_ethernet1/2_10.26.129.1": {
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
                # highlight-end
                "passed": "False"
            },
            "count_change_percentage": {
                "change_percentage": 33.33,
                "change_threshold": 1,
                "passed": "False"
            },
            "passed": "False"
        }
        ```

        In the example above, you can also see a nested dictionary produced by the
        [`calculate_diff_on_dicts()`](#snapshotcomparecalculate_diff_on_dicts) method under `changed.changed_raw`.

        # Parameters

        report_type (str): Name of report (type) that has to be compared. Basically this is a snapshot state area, for example
            `nics`, `routes`, etc.
        properties (list(str), optional): (defaults to `None`) An optional list of properties to include or exclude when
            comparing snapshots. This parameter is passed directly to the
            [`calculate_diff_on_dicts()`](#snapshotcomparecalculate_diff_on_dicts) method. For details on this method parameters,
            see the [documentation](#snapshotcomparecalculate_diff_on_dicts) for this method.
        count_change_threshold (int, float, optional): (defaults to `None`) The maximum difference between number of changed
            elements in each snapshot (as percentage).

        # Returns

        dict: Comparison results.

        """
        result = {}

        report_type_left_snapshot = self.left_snap[report_type]["snapshot"]
        report_type_right_snapshot = self.right_snap[report_type]["snapshot"]

        if report_type_left_snapshot is None or report_type_right_snapshot is None:
            raise exceptions.SnapshotNoneComparisonException("Cannot compare snapshot when either side is None.")

        diff = self.calculate_diff_on_dicts(
            left_side_to_compare=report_type_left_snapshot,
            right_side_to_compare=report_type_right_snapshot,
            properties=properties,
        )
        result.update(diff)

        if count_change_threshold and result:
            count_change_result = self._calculate_count_change_percentage(
                comparison_result=result,
                left_snapshot_type_dict=report_type_left_snapshot,
                right_snapshot_type_dict=report_type_right_snapshot,
                count_change_threshold=count_change_threshold,
            )
            result.update({"count_change_percentage": count_change_result})

        self.calculate_passed(result)
        return result

    # CUSTOM COMPARISON METHODS
    def compare_type_metric_values(
        self,
        report_type: str,
        thresholds: Optional[List[Dict[str, Union[int, float]]]] = None,
    ) -> Optional[Dict[str, Union[bool, dict]]]:
        """Generic method to compare metric values of a snapshot type against given thresholds.

        In opposition to the [`compare_type_generic()`](#snapshotcomparecompare_type_generic) method, this one does not
        calculate the count change but the actual difference between the numerical values.
        A good example is a change in the session stats. The snapshot for this area is a dictionary with the keys taking values
        of different session types and values containing the actual session count:

        ```python showLineNumbers title="Example"
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
        ```

        This method:

        - sweeps through all the session types provided in the `thresholds` variable,
        - calculates the actual difference,
        - compares the actual difference with the threshold value (percentage) for a particular session type.

        It takes as parameter a list of dictionaries describing elements to compare, in a form of:

        ```json showLineNumbers
        {
            "element_type": threshold_value
        }
        ```

        Where:

        - `element_type` is a key which value we are going to compare,
        - `threshold_value` is a percentage value provided as either `int` or `float`. If the list is empty,
            the method will return `None`.

        :::caution
        This list **does not support** [`ConfigParser`](/panos/docs/panos-upgrade-assurance/api/utils#class-configparser)
        [`dialect`](/panos/docs/panos-upgrade-assurance/dialect).
        :::

        Below there is a sample list for the `sessions_stat` dictionary shown above that would calculate differences for the TCP
        and UDP sessions:

        ```json showLineNumbers
        [
            { "num-tcp": 1.5 },
            { "num-udp": 15 },
        ]
        ```

        # Parameters

        thresholds (list): (defaults to `None`) The list of elements to compare with thresholds.

        # Raises

        SnapshotSchemeMismatchException: Thrown when a snapshot element has a different set of properties in both snapshots.

        # Returns

        dict: The result of difference compared against a threshold. The result for each value is in the same form as returned \
            by the [`_calculate_metric_change_percentage()`](#snapshotcompare_calculate_metric_change_percentage) method. For the examples \
            above, the return value would be:

        ```python showLineNumbers title="Sample output"
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
        ```

        """

        if not thresholds:
            return None

        result = dict(
            passed=True,
        )

        report_type_left_snapshot = self.left_snap[report_type]["snapshot"]
        report_type_right_snapshot = self.right_snap[report_type]["snapshot"]

        if report_type_left_snapshot is None or report_type_right_snapshot is None:
            raise exceptions.SnapshotNoneComparisonException("Cannot compare snapshot when either side is None.")

        requested_elements = set(next(iter(unary_dict)) for unary_dict in thresholds)
        try:
            self.validate_keys_exist(
                report_type_left_snapshot,
                report_type_right_snapshot,
                requested_elements,
            )
        except exceptions.MissingKeyException as exc:  # raised when any requested key is missing in one of the snapshots
            raise exceptions.SnapshotSchemeMismatchException(
                f"Snapshots have missing keys in {requested_elements} for {report_type} report."
            ) from exc

        elements = ConfigParser(
            valid_elements=set(report_type_left_snapshot.keys()),
            requested_config=thresholds,
        ).prepare_config()

        for element in elements:
            element_type, threshold_value = list(element.items())[0]
            result.update(
                {
                    element_type: self._calculate_metric_change_percentage(
                        first_value=report_type_left_snapshot[element_type],
                        second_value=report_type_right_snapshot[element_type],
                        threshold=threshold_value,
                    )
                }
            )

        self.calculate_passed(result)
        return result

    def compare_type_are_routes(
        self, report_type: str, properties: Optional[List[str]] = None, count_change_threshold: Optional[Union[int, float]] = None
    ) -> Dict[str, Union[bool, dict]]:
        """Compare advanced routing engine routes between two snapshots of the are_routes type.

        This method specifically handles the advanced routing engine data format where:
        - Only installed routes for each destination (CIDR key) on each logical router are considered
        - Nexthops are organized as (ethernet, IP) pairs for comparison

        # Parameters

        report_type (str): Name of report (type) that has to be compared (always "are_routes" as of now)
        properties (list(str), optional): Optional list of properties to include/exclude when comparing
        count_change_threshold (int, float, optional): Maximum difference between number of changed
            elements in each snapshot (as percentage)

        # Returns

        dict: Comparison results with the same structure as compare_type_generic()

        """
        result = {}

        report_type_left_snapshot = self.left_snap[report_type]["snapshot"]
        report_type_right_snapshot = self.right_snap[report_type]["snapshot"]

        if report_type_left_snapshot is None or report_type_right_snapshot is None:
            raise exceptions.SnapshotNoneComparisonException("Cannot compare snapshot when either side is None.")

        # Extract normalized routing data from both snapshots
        left_normalized = self._normalize_are_routes(report_type_left_snapshot)
        right_normalized = self._normalize_are_routes(report_type_right_snapshot)

        # Perform comparison on the normalized data
        diff = self.calculate_diff_on_dicts(
            left_side_to_compare=left_normalized,
            right_side_to_compare=right_normalized,
            properties=properties,
        )
        result.update(diff)

        # Calculate threshold comparison if requested
        if count_change_threshold and result:
            count_change_result = self._calculate_count_change_percentage(
                comparison_result=result,
                left_snapshot_type_dict=left_normalized,
                right_snapshot_type_dict=right_normalized,
                count_change_threshold=count_change_threshold,
            )
            result.update({"count_change_percentage": count_change_result})

        self.calculate_passed(result)
        return result

    def _normalize_are_routes(self, are_routes: Dict) -> Dict:
        """Normalize advanced routing engine routes for comparison.

        For each logical router and destination:
        1. Select only installed routes
        2. Convert nexthop list to dict with ethernet_ip as keys

        # Parameters

        are_routes (dict): The ARE routes data from a snapshot

        # Returns

        dict: Normalized routing data for comparison
        """
        normalized = {}

        # Process each logical router
        for lr_name, routes in are_routes.items():
            normalized[lr_name] = {}

            # Process each destination prefix
            for prefix, route_entries in routes.items():
                # Filter for installed routes only
                installed_routes = [route for route in route_entries if route.get("installed", False)]

                if installed_routes:
                    # Use the first installed route (should be the best one)
                    best_route = installed_routes[0]
                    normalized[lr_name][prefix] = {
                        # Add all route attributes directly to the prefix dictionary
                        **{k: v for k, v in best_route.items() if k != "nexthops"},
                        # Add an empty nexthops dictionary that will be populated below
                        "nexthops": {},
                    }

                    # Convert nexthops list to a dictionary keyed by <interface>_<nexthop-ip>
                    if "nexthops" in best_route:
                        for nexthop in best_route["nexthops"]:
                            interface_name = nexthop.get("interfaceName", "none")
                            nexthop_ip = nexthop.get("ip", "direct")
                            nexthop_key = f"{interface_name}_{nexthop_ip}"
                            normalized[lr_name][prefix]["nexthops"][nexthop_key] = nexthop

        return normalized
