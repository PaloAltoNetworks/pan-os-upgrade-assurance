---
sidebar_label: snapshot_compare
title: snapshot_compare
---

## class `MissingKeyException`

Used when an exception about the missing keys in a dictionary is thrown.

## class `WrongDataTypeException`

Used when a variable does not meet the data type requirements.

## class `SnapshotSchemeMismatchException`

Used when a snapshot element contains different properties in both snapshots.

## class `SnapshotCompare`

Class comparing snapshots of Firewall Nodes.

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

### `SnapshotCompare.__init__`

```python
def __init__(left_snapshot: Dict[str, Union[str, dict]],
             right_snapshot: Dict[str, Union[str, dict]]) -> None
```

SnapshotCompare constructor.

Initializes an object by storing both snapshots to be compared.

**Arguments**:

- `left_snapshot` (`dict`): First snapshot dictionary to be compared, usually the older one, for example a pre-upgrade snapshot.
- `right_snapshot` (`dict`): Second snapshot dictionary to be compared, usually the newer one, for example a post-upgrade snapshot.

### `SnapshotCompare.compare_snapshots`

```python
def compare_snapshots(
        reports: Optional[List[Union[dict, str]]] = None) -> Dict[str, dict]
```

A method that triggers the actual snapshot comparison.

This is a single point of entry to generate a comparison report. It takes both reports stored in the class object and compares areas specified in the ``reports`` parameter.

**Arguments**:

- `reports` (`list, optional`): A list of reports - snapshot state areas with optional configuration. This parameter follows the`dialect`_ of :class:`.ConfigParser` class.
The reports list is essentially the list of keys present in the snapshots. These keys, however, are the state areas specified when the snapshot is made with the :meth:`.CheckFirewall.run_snapshots` method. This means that the reports list is basically the list of state areas. The only difference is that for reports, it is possible to specify an additional configuration. This means that the list can be specified in two ways, as ``str`` or ``dict`` (in the same manner as for :meth:`.CheckFirewall.run_readiness_checks`).

For the elements specified as:

    * ``str`` - the element value is the name of the report (state area),
    * ``dict`` - the element contains the report name (state area) and the key value and report configuration as the element value.

Refer to the :ref:`report_docs` documentation for details on the currently available snapshot areas and optional parameters that can be configured for them.

**Raises**:

- `WrongDataTypeException`: An exception is raised when the configuration in a data type is different than ``str`` or ``dict``.

**Returns**:

`dict`: Result of comparison in a form of the Python dictionary.
Keys in this dictionary are again state areas where values depend on the actual comparison method that was run. Again, refer to the :ref:`report_docs` documentation for details.

### `SnapshotCompare.key_checker`

```python
@staticmethod
def key_checker(left_dict: dict, right_dict: dict, key: str) -> None
```

The static method to check if a key is available in both dictionaries.

This method looks for a given key in two dictionaries. Its main purpose is to assure that when comparing a key-value pair from two dictionaries, it actually exists in both.

**Arguments**:

- `left_dict` (`dict`): 1st dictionary to verify.
- `right_dict` (`dict`): 2nd dictionary to verify.
- `key` (`str`): Key name to check.

**Raises**:

- `MissingKeyException`: when key is not available in at least one snapshot.

### `SnapshotCompare.calculate_change_percentage`

```python
@staticmethod
def calculate_change_percentage(
        first_value: Union[str, int], second_value: Union[str, int],
        threshold: Union[str, float]) -> Dict[str, Union[bool, float]]
```

The static method to compare differences between values against a given threshold.

Values to be compared should be the ``int`` or ``str`` representation of ``int``. This method is used when comparing a count of elements so a floating point value here is not expected.
The threshold value, on the other hand, should be the ``float`` or ``str`` representation of ``float``. This is a percentage value.

**Arguments**:

- `first_value` (`int, str`): First value to compare.
- `second_value` (`int, str`): Second value to compare.
- `threshold` (`float, str`): Maximal difference between values given as percentage.

**Raises**:

- `WrongDataTypeException`: An exception is raised when the threshold value is not between ``0`` and ``100`` (typical percentage boundaries).

**Returns**:

`dict`: A dictionary with the comparison results.
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

### `SnapshotCompare.calculate_diff_on_dicts`

```python
@staticmethod
def calculate_diff_on_dicts(
        left_side_to_compare: Dict[str, Union[str, dict]],
        right_side_to_compare: Dict[str, Union[str, dict]],
        properties: Optional[List[str]] = None) -> Dict[str, dict]
```

The static method to calculate a difference between two dictionaries.

**Arguments**:

- `left_side_to_compare` (`dict`): 1st dictionary to compare.
When this method is triggered by :meth:`.compare_snapshots`, the dictionary comes from the ``self.left_snap`` snapshot.
- `right_side_to_compare` (`dict`): 2nd dictionary to compare, comes from the self.right_snap snapshot.
When this method is triggered by :meth:`.compare_snapshots`, the dictionary comes from the ``self.right_snap`` snapshot.
- `properties` (`list(str), optional`): The list of properties used to compare two dictionaries.
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

**Raises**:

- `WrongDataTypeException`: Thrown when one of the ``properties`` elements has a wrong data type.

**Returns**:

`dict`: Summary of the differences between dictionaries.
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

### `SnapshotCompare.calculate_passed`

```python
@staticmethod
def calculate_passed(result: Dict[str, Union[dict, str]]) -> None
```

The static method to calculate the upper level ``passed`` value.

When two snapshots are compared, a dictionary that is the result of this comparison is structured as in the following :meth:`.get_diff_and_threshold` method: each root key contains a dictionary that has a structure returned by the :meth:`.calculate_diff_on_dicts` method.

This method takes a dictionary under the root key and calculates the ``passed`` flag based on the all ``passed`` flags in that dictionary. This provides a quick way of finding out if any comparison made on data under a root key failed or not. 

To illustrate that, the ``passed`` flag added by this method is marked with an arrow:

**Arguments**:

- `result` (`dict`): The result of snapshot difference comparison.

### `SnapshotCompare.get_diff_and_threshold`

```python
def get_diff_and_threshold(
    report_type: str,
    properties: Optional[List[str]] = None,
    count_change_threshold: Optional[Union[int, float]] = None
) -> Optional[Dict[str, Optional[Union[bool, dict]]]]
```

The generic snapshot comparison method.

The generic method to compare two snapshots of a given type. It is meant to fit most of the comparison cases.
It is capable of calculating both - a difference between two snapshots and the change count in the elements against a given threshold. The 1\ :sup:`st` calculation is done by the :meth:`.calculate_diff_on_dicts` method, the 2\ :sup:`nd` - internally.

The changed elements count does not compare the count of elements in each snapshot. This value represents the number of actual changes, so elements added, missing and changed. This is compared against the number of elements in the left snapshot as this one is usually the 1st one taken and it's treated as a source of truth. 

The changed elements count is presented as a percentage. In scenarios where the right snapshot has more elements then the left one, it can give values greater than 100%.

**Arguments**:

- `report_type` (`str`): Name of report (type) that has to be compared.
Basically this is a snapshot state area, for example ``nics``, ``routes``, etc.
- `properties` (`list(str), optional`): (defaults to ``None``) An optional list of properties to include or exclude when comparing snapshots.
This parameter is passed directly to the :meth:`.calculate_diff_on_dicts` method. For details on this method parameters, see the documentation for this method.
- `count_change_threshold` (`int, float, optional`): (defaults to ``None``) The maximum difference between number of changed elements in each snapshot (as percentage).

**Returns**:

`dict`: Comparison results.
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

### `SnapshotCompare.get_count_change_percentage`

```python
def get_count_change_percentage(
    report_type: str,
    thresholds: Optional[List[Dict[str, Union[int, float]]]] = None
) -> Optional[Dict[str, Union[bool, dict]]]
```

The basic value change against a threshold comparison method.

The generic method to calculate the change on values and compare them against a given threshold.

In opposition to the :meth:`.get_diff_and_threshold` method, this one does not calculate the count change but the actual difference between the numerical values. 
A good example is a change in the session count. The snapshot for this area is a dictionary with the keys taking values of different session types and values containing the actual session count:

**Arguments**:

- `thresholds` (`list`): (defaults to ``None``) The list of elements to compare.
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

**Raises**:

- `SnapshotSchemeMismatchException`: Thrown when a snapshot element has a different set of properties in both snapshots.

**Returns**:

`dict, optional`: The result of difference compared against a threshold.
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

