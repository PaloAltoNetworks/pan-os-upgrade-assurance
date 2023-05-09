---
sidebar_label: utils
title: utils
---

## UnknownParameterException

```python
class UnknownParameterException(Exception)
```

Used when one of the requested configuration parameters processed by :class:`.ConfigParser` is not a valid parameter.

## WrongDataTypeException

```python
class WrongDataTypeException(Exception)
```

Used when a variable does not meet data type requirements.

## CheckType

```python
class CheckType()
```

Class mapping check configuration strings for commonly used variables.

Readiness checks configuration passed to the :class:`.CheckFirewall` class is in a form of a list of strings. These strings are compared in several places to parse the configuration and set the proper checks. This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the code.

## SnapType

```python
class SnapType()
```

Class mapping the snapshot configuration strings to the commonly used variables.

Snapshot configuration passed to the :class:`.CheckFirewall` class is in a form of a list of strings. These strings are compared in several places to parse the configuration and set proper snapshots.
This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the code.

## CheckStatus

```python
class CheckStatus(Enum)
```

Class containing possible statuses for the check results.

Its main purpose is to extend the simple ``True/False`` logic in a way that would provide more details/explanation in case a check fails.

## CheckResult

```python
@dataclass
class CheckResult()
```

Class representing the readiness check results.

It provides two types of information:

    * ``status`` which represents information about the check outcome,
    * ``reason`` a reason behind the particular outcome, this comes in handy when a check fails.

Most of the :class:`.CheckFirewall` methods use this class to store the return values, but mostly internally. The :meth:`.CheckFirewall.run_readiness_checks` method translates this class into the python primitives: ``str`` and ``bool``.


### \_\_str\_\_

```python
def __str__()
```

Class&#x27; string representation.

**Returns**:

`str`: A string combined from the ``self.status`` and ``self.reason`` variables. Provides a human readable representation of the class. Perfect to provide a reason for a particular check outcome.

### \_\_bool\_\_

```python
def __bool__()
```

Class&#x27; boolean representation.

**Returns**:

`bool`: A boolean value interpreting the value of the current ``state``: 
* ``True`` when ``status`` is :attr:`.CheckStatus.SUCCESS`,
* ``False`` otherwise.

## ConfigParser

```python
class ConfigParser()
```

Class responsible for parsing the provided configuration.

This class is universal, meaning it parses configuration provided as the list of strings or dictionaries and verifies it against the list of valid configuration items. 
There are no hardcoded items against which the configuration is checked.

It assumes and understands the following _`dialect`:

    * all configuration elements are case-sensitive,
    * if an element is ``str``, it is the name of an element,
    * if an element is ``dict``, the key is treated as the name of the element and the value is simply a configuration for this element,
    * the ``all`` item is equal to all items from the valid configuration elements,
    * an empty list is the same as the list containing only the ``all`` item,
    * excluding elements are supported by prefixing an item with an exclamation mark, for example, ``&#x27;!config&#x27;`` will skip the ``&#x27;config&#x27;`` element.

        These elements are called ``not-elements``. They are useful when combined with ``all``.
        For example: a list of: ``[&#x27;all&#x27;, &#x27;!tcp&#x27;]`` or simply ``[&#x27;!tcp&#x27;]`` would take all valid elements except for ``tcp``.

        Having that said:

    * a list containing only ``not-elements`` is treated as if ``&#x27;all&#x27;`` would have been specified explicitly,
    * order does not matter,
    * you can override elements implicitly specified with ``all``. This means that:

        * when:

            * the following list is passed:

                ::

                    [
                        &#x27;all&#x27;, 
                        { &#x27;content_version&#x27;: {
                            &#x27;version&#x27;: &#x27;1234-5678&#x27;}
                        }
                    ]

            *  ``content_version`` is a valid element

        * then:

            * ``all`` is expanded to all valid elements but
            * ``content_version`` is skipped during expansion (since an explicit definition for it is already available).


### \_\_init\_\_

```python
def __init__(valid_elements: Iterable,
             requested_config: Optional[List[Union[str, dict]]] = None)
```

ConfigParser constructor.

Introduces some initial verification logic:

    * ``valid_elements`` is converted to ``set`` - this way we get rid of all duplicates,
    * if ``requested_config`` is ``None`` we immediately treat it as if ``all``  was passed implicitly (see `dialect`_) - it&#x27;s expanded to ``valid_elements``
    * ``_requested_config_names`` is introduced as ``requested_config`` stripped of any element configurations. Additionally, we do verification if elements of this variable match ``valid_elements``. An exception is thrown if not.

**Arguments**:

- `valid_elements`: Valid elements against which we check the requested config.
- `requested_config` (`list, optional`): (defaults to ``None``) A list of requested configuration items with an optional configuration.

**Raises**:

- `UnknownParameterException`: An exception is raised when a requested configuration element is not one of the valid elements.

### prepare\_config

```python
def prepare_config() -> List[Union[str, dict]]
```

Parse the input config and return a machine-usable configuration.

The parsed configuration retains element types. This means that an element of a dictionary type will remain a dictionary in the parsed config.

This method handles most of the `dialect`_&#x27;s logic.

**Returns**:

`list`: The parsed configuration.

### interpret\_yes\_no

```python
def interpret_yes_no(boolstr: str) -> bool
```

Interpret ``yes``/``no`` as booleans.

**Arguments**:

- `boolstr` (`str`): ``yes`` or ``no``, a typical device response for simple boolean-like queries.

**Raises**:

- `WrongDataTypeException`: An exception is raised when ``boolstr`` is neither ``yes`` or ``no``.

**Returns**:

`bool`: ``True`` for *yes*, ``False`` for *no*.

### printer

```python
def printer(report: dict, indent_level: int = 0) -> None
```

Print reports in human friendly format.

**Arguments**:

- `report` (`dict`): Dict with reports from tests.
- `indent_level` (`int`): Indentation level.

