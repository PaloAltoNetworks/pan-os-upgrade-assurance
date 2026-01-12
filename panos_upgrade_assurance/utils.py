from __future__ import annotations
from dataclasses import dataclass, asdict
from copy import deepcopy
from typing import Optional, Union, List, Iterable, Iterator, Set, Dict
from enum import Enum
from panos_upgrade_assurance import exceptions
import sys

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:  # TypeAlias is added in python 3.10 so import from typing_extensions if python version is lower
    from typing_extensions import TypeAlias


class CheckType:
    """Class mapping check configuration strings for commonly used variables.

    Readiness checks configuration passed to the
    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration and set the proper checks. This class is
    used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the
    code.
    """

    PANORAMA = "panorama"
    HA = "ha"
    NTP_SYNC = "ntp_sync"
    CANDIDATE_CONFIG = "candidate_config"
    EXPIRED_LICENSES = "expired_licenses"
    ACTIVE_SUPPORT = "active_support"
    CONTENT_VERSION = "content_version"
    SESSION_EXIST = "session_exist"
    ARP_ENTRY_EXIST = "arp_entry_exist"
    IPSEC_TUNNEL_STATUS = "ip_sec_tunnel_status"
    FREE_DISK_SPACE = "free_disk_space"
    MP_DP_CLOCK_SYNC = "planes_clock_sync"
    CERTS = "certificates_requirements"
    UPDATES = "dynamic_updates"
    JOBS = "jobs"
    GLOBAL_JUMBO_FRAME = "global_jumbo_frame"
    SYSTEM_ENVIRONMENTALS = "environmentals"
    DP_CPU_UTILIZATION = "dp_cpu_utilization"
    MP_CPU_UTILIZATION = "mp_cpu_utilization"


class SnapType:
    """Class mapping the snapshot configuration strings to the commonly used variables.

    Snapshot configuration passed to the
    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration and set proper snapshots.
    This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be
    referenced in the code.
    """

    NICS = "nics"
    ROUTES = "routes"
    BGP_PEERS = "bgp_peers"
    LICENSE = "license"
    ARP_TABLE = "arp_table"
    CONTENT_VERSION = "content_version"
    SESSION_STATS = "session_stats"
    IPSEC_TUNNELS = "ip_sec_tunnels"
    FIB_ROUTES = "fib_routes"
    GLOBAL_JUMBO_FRAME = "global_jumbo_frame"
    INTERFACES_MTU = "mtu"
    ARE_ROUTES = "are_routes"
    ARE_FIB_ROUTES = "are_fib_routes"


class HealthType:
    """Class mapping the health check configuration strings to commonly used variables.

    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration.

    This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be
    referenced in the code.
    """

    DEVICE_ROOT_CERTIFICATE_ISSUE = "device_root_certificate_issue"
    DEVICE_CDSS_AND_PANORAMA_CERTIFICATE_ISSUE = "cdss_and_panorama_certificate_issue"


class SnapStatus(Enum):
    """Status enum for snapshot operations.

    Represents the possible statuses for snapshot operations:

    * `SUCCESS` - Snapshot was successfully captured
    * `ERROR` - An error occurred during snapshot capture
    """

    SUCCESS = 0
    ERROR = 1


class CheckStatus(Enum):
    """Class containing possible statuses for the check results.

    Its main purpose is to extend the simple `True`/`False` logic in a way that would provide more details/explanation in case a
    check fails. It provides the following statuses:

    * `SUCCESS`
    * `FAIL`
    * `ERROR`
    * `SKIPPED`

    """

    SUCCESS = 0
    FAIL = 1
    ERROR = 2
    SKIPPED = 3


class SupportedHashes(Enum):
    """Class listing supported hashing methods.

    Algorithms listed here are order from less to most secure (this order follows many criteria, some of them are mentioned
    [here](https://en.wikipedia.org/wiki/Hash_function_security_summary)).

    By extending the `Enum` class we can easily use this class to compare two hashing methods in terms of their security,
    for example:

    ```python showLineNumbers title="Example"
    bool(SupportedHashes.MD5.value < SupportedHashes.SHA256.value)
    ```

    would produce `True`.
    """

    MD5 = 1
    SHA1 = 2
    SHA256 = 3
    SHA384 = 4
    SHA512 = 5


def enum_state_dict_factory(data):
    """Custom dict factory to handle Enum values in dataclasses.

    Converts SnapStatus or CheckStatus enums to boolean (SUCCESS=True, others=False).
    Also includes the original enum name as a string.
    """
    result = {}

    for key, value in data:
        if key == "status" and (isinstance(value, SnapStatus) or isinstance(value, CheckStatus)):
            # Convert Status enum to boolean
            result["state"] = value == SnapStatus.SUCCESS if isinstance(value, SnapStatus) else value == CheckStatus.SUCCESS
            # Keep the original status name
            result["status"] = value.name
        else:
            result[key] = value
    return result


@dataclass
class SnapResult:
    """Class representing the result of a snapshot operation.

    It provides three types of information:

    * `status` which represents the outcome of the snapshot operation,
    * `reason` explaining why a snapshot operation succeeded or failed,
    * `snapshot` containing the actual snapshot data when successful.

    # Attributes

    status (SnapStatus): Holds the status of a snapshot operation. See [`SnapStatus`](#class-snapstatus) class for details.
    reason (str): Explanation of the snapshot outcome, particularly useful for error conditions.
    snapshot (Optional[dict]): Contains the actual snapshot data when successful, None otherwise.
    """

    status: SnapStatus = SnapStatus.ERROR
    reason: str = ""
    snapshot: Optional[Dict[str, Union[str, dict, bool]]] = None

    def __str__(self):
        """This class' string representation.

        # Returns

        str: a string combined from the `self.status` and `self.reason` variables. Provides a human readable representation of
        the snapshot operation.
        """
        return f"[{self.status.name}] {self.reason}"

    def __bool__(self):
        """Class' boolean representation.

        # Returns

        bool: a boolean value interpreting the value of the current `status`:

        * `True` when `status` [`SnapStatus.SUCCESS`](#class-snapstatus)
        * `False` otherwise.
        """
        return True if self.status == SnapStatus.SUCCESS else False

    def to_dict(self) -> dict:
        """Convert the SnapResult object to a dictionary.

        Converts the enum status to a more serializable format and adds state boolean value for success or failure.

        # Returns

        dict: A dictionary containing the state (boolean), status (string), reason, and snapshot data.

        ```python showLineNumbers title="Sample output"
        {
            'reason': '',
            'snapshot': {'ethernet1/1': 'up',
                         'ethernet1/2': 'up',
                         'ethernet1/3': 'down'},
            'state': True,
            'status': 'SUCCESS'
        }
        ```

        """
        return asdict(self, dict_factory=enum_state_dict_factory)


@dataclass
class CheckResult:
    """Class representing the readiness check results.

    It provides two types of information:

    * `status` which represents information about the check outcome,
    * `reason` a reason behind the particular outcome, this comes in handy when a check fails.

    Most of the [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) methods use this
    class to store the return values, but mostly internally. The
    [`CheckFirewall.run_readiness_checks()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_readiness_checks)
    method translates this class into the python primitives: `str` and `bool`.

    # Attributes

    status (CheckStatus): Holds the status of a check. See [`CheckStatus`](#class-checkstatus) class for details.
    reason (str): Holds a reason explaining why a check fails. Provides no value if the check is successful.

    """

    status: CheckStatus = CheckStatus.FAIL
    reason: str = ""

    def __str__(self):
        """This class' string representation.

        # Returns

        str: a string combined from the `self.status` and `self.reason` variables. Provides a human readable representation of
        the class. Perfect to provide a reason for a particular check outcome.

        """
        return f"[{self.status.name}] {self.reason}"

    def __bool__(self):
        """Class' boolean representation.

        # Returns

        bool: a boolean value interpreting the value of the current `state`:

        * `True` when `status` [`CheckStatus.SUCCESS`](#class-checkstatus)
        * `False` otherwise.

        """
        return True if self.status == CheckStatus.SUCCESS else False

    def to_dict(self) -> dict:
        """Convert the CheckResult object to a dictionary.

        Converts the enum status to a more serializable format and adds state boolean value for success or failure.

        # Returns

        dict: A dictionary containing the state (boolean), status (string), and reason.

        ```python showLineNumbers title="Sample output"
        {
            'reason': 'Pending changes found on device.',
            'state': False,
            'status': 'FAIL'
        }
        ```

        """
        return asdict(self, dict_factory=enum_state_dict_factory)


class ConfigParser:
    """Class responsible for parsing the provided configuration.

    This class is universal, meaning it parses configuration provided as the list of strings or dictionaries and verifies it
    against the list of valid configuration items.
    There are no hardcoded items against which the configuration is checked. This class is used in many places in this package
    and it uses a specific [`dialect`](/panos/docs/panos-upgrade-assurance/dialect).

    `ConfigElement` (`str`, `dict`): Type alias for a configuration element in `requested_config` which is either a string or a
        dictionary with a single key. This alias is being used over the `ConfigParser` class to increase clarification.

    :::note
    Configuration elements beginning with an exclamation mark (!) is referred to as `not-element`s in this dialect and it should
    be considered such in any place documented in the `ConfigParser` class. Please refer to the `dialect` documentation for
    details.
    :::

    # Attributes

    _requested_config_element_names (set): Contains only element names of the requested configuration. When no requested
        configuration is passed, this is equal to `self.valid_elements` which is like an implicit `'all'`.
    _requested_all_not_elements (bool): Identifies if requested configurations consists of all `not-element`s.

    """

    ConfigElement: TypeAlias = Union[str, dict]

    def __init__(
        self,
        valid_elements: Iterable,
        requested_config: Optional[List[ConfigElement]] = None,
        explicit_elements: Optional[Set[str]] = None,
    ):
        """ConfigParser constructor.

        Introduces some initial verification logic:

        * `valid_elements` is converted to `set` - this way we get rid of all duplicates,
        * if `requested_config` is `None` we immediately treat it as if `all`  was passed implicitly
            (see [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)) - it's expanded to `valid_elements`
        * `_requested_config_element_names` is introduced as `requested_config` stripped of any element configurations.
            Meaning top level keys of nested dictionaries in the `requested_config` are used as element names.
            Additionally, we do verification if all elements of this variable match `valid_elements`,
            if they do not, an exception is thrown by default.
        * `_requested_all_not_elements` is set to `True` if all elements of `requested_config` are `not-element`s.

        # Parameters

        valid_elements (Iterable): Valid elements against which we check the requested config.
        requested_config (list, optional): (defaults to `None`) A list of requested configuration items with an optional
            configuration.
        explicit_elements (set, optional): (defaults to `None`) A set of elements that should only be included when
            explicitly requested.

        # Raises

        UnknownParameterException: An exception is raised when a requested configuration element is not one of the valid elements.

        """
        self.valid_elements = set(valid_elements)
        self.explicit_elements = set(explicit_elements) if explicit_elements else set()

        if requested_config:  # if not None or not empty list
            self.requested_config = deepcopy(requested_config)
            self._requested_config_element_names = set(self._iter_config_element_names(self.requested_config))
            self._requested_all_not_elements = self.is_all_not_elements(self._requested_config_element_names)

            for element_name in self._requested_config_element_names:
                if not self._is_valid_element_name(element_name):
                    raise exceptions.UnknownParameterException(f"Unknown configuration parameter passed: {element_name}.")
        else:
            self._requested_config_element_names = set(valid_elements) - self.explicit_elements
            self.requested_config = list(self._requested_config_element_names)  # 'all' valid tests except explicit ones
            self._requested_all_not_elements = False

    @staticmethod
    def is_all_not_elements(config: Iterable[ConfigElement]) -> bool:
        """Method to check if all config elements are `not-element`s (all exclusive).

        # Parameters

        config (Iterable): List of config elements.

        # Returns

        bool: `True` if all config elements are `not-element`s (exclusive) or config is empty, otherwise returns `False`.

        """
        if all((ConfigParser._extract_element_name(config_element).startswith("!") for config_element in config)):
            return True

        return False

    @staticmethod
    def is_element_included(
        element_name: str, config: Union[Iterable[ConfigElement], None], all_not_elements_check: bool = True
    ) -> bool:
        """Method verifying if a given element name should be included according to the config.

        # Parameters

        element_name (str): Element name to check if it's included in the provided `config`.
        config (Iterable): Config to check against.
        all_not_elements_check (bool, optional): (defaults to `True`) Accept element as included if all the `config` elements are
            `not-element`s; otherwise it checks if the element is explicitly included without making an
            [`is_all_not_elements()`](#configparseris_all_not_elements) method call.

        # Returns

        bool: `True` if element name is included or if all config elements are `not-element`s depending on the
            `all_not_elements_check` parameter.

        """
        if not config:  # if config list is None or empty list it should be included
            return True

        # TODO can we accomplish following 2 lines with a decorator perhaps? which is replicated in a few methods
        config_with_opts = any((isinstance(config_element, dict) for config_element in config))
        extracted_config = set(ConfigParser._iter_config_element_names(config)) if config_with_opts else config

        if ConfigParser.is_element_explicit_excluded(element_name, extracted_config):
            return False
        elif element_name in extracted_config or "all" in extracted_config:
            return True
        elif all_not_elements_check and ConfigParser.is_all_not_elements(extracted_config):
            return True

        return False

    @staticmethod
    def is_element_explicit_excluded(element_name: str, config: Union[Iterable[ConfigElement], None]) -> bool:
        """Method verifying if a given element should be excluded according to the config.

        Explicit excluded means the element is present as a `not-element` in the requested config, for example \"ntp_sync\" is
        excluded explicitly in the following config `["!ntp_sync", "candidate_config"]`.

        # Parameters

        element_name (str): Element name to check if it's present as a `not-element` in the provided `config`.
        config (Iterable): Config to check against.

        # Returns

        bool: `True` if element is present as a `not-element`, otherwise `False`.

        """
        if not config:  # if config is empty or None then it is not excluded
            return False

        config_with_opts = any((isinstance(config_element, dict) for config_element in config))
        extracted_config = set(ConfigParser._iter_config_element_names(config)) if config_with_opts else config

        if f"!{element_name}" in extracted_config:  # if !element_name is in config
            return True

        return False

    @staticmethod
    def _extract_element_name(element: ConfigElement) -> str:
        """Method that extracts the name from a config element.

        If a config element is a string, the actual config element is returned. For elements of a dictionary type, the
        1<sup>st</sup> key is returned.

        # Parameters

        element (ConfigElement): A config element to provide a name for.

        # Raises

        WrongDataTypeException: Thrown when element does not meet requirements.

        # Returns

        str: The config element name.

        """
        if isinstance(element, str):
            return element
        elif isinstance(element, dict):
            if len(element) == 1:
                return list(element.keys())[0]
            else:
                raise exceptions.WrongDataTypeException(
                    "Dict provided as config definition has incorrect format, it is supposed to have only one key {key:[]}"
                )
        else:
            raise exceptions.WrongDataTypeException("Config definition is neither string or dict")

    @staticmethod
    def _iter_config_element_names(config: Iterable[ConfigElement]) -> Iterator[str]:
        """Generator for extracted config element names.

        This method provides a convenient way to iterate over configuration items with their config element names extracted by
        [`_extract_element_name()`](#configparser_extract_element_name) method.

        # Parameters

        config (Iterable): Iterable config items as str or dict.

        # Returns

        Iterator: For config element names extracted by [`ConfigParser._extract_element_name()`](#configparser_extract_element_name)

        """
        for config_element in config:
            yield ConfigParser._extract_element_name(config_element)

    def _strip_element_name(self, element_name: str) -> str:
        """Get element name with exclamation mark removed if so.

        Returns element name removing exclamation mark for a `not-element` config.

        # Parameters

        element_name (str): Element name.

        # Returns

        str: Element name with exclamation mark stripped of from the beginning.

        """
        return element_name[1:] if element_name.startswith("!") else element_name

    def _is_valid_element_name(self, element_name: str) -> bool:
        """Method verifying if a config element name is a correct (supported) value.

        This method can also handle `not-element`s (see [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)).

        # Parameters

        element_name (str): The config element name to verify. This can be a `not-element` as well. This parameter is verified
             against `self.valid_elements` set. Key word `'all'` is also accepted.

        # Returns

        bool: `True` if the value is correct, `False` otherwise.

        """
        if self._strip_element_name(element_name) in self.valid_elements:
            return True
        elif element_name == "all" and "all" in self.requested_config:
            return True
        else:
            return False

    def get_config_element_by_name(self, element_name: str) -> Union[ConfigElement, None]:
        """Get configuration element from requested configuration for the provided config element name.

        This method returns config element as str or dict from `self.requested_config` for the provided config element name.
        It does not support returning `not-element` of a given config element.

        # Parameters

        element_name (str): Element name.

        # Returns

        ConfigElement: str if element is provided as string or dict if element is provided as dict with optional configuration in
            the requested configuration.

        """
        if element_name in self.requested_config:
            return element_name
        else:
            return next(
                (
                    config_element
                    for config_element in self.requested_config
                    if isinstance(config_element, dict) and element_name in config_element
                ),
                None,
            )

    def prepare_config(self) -> List[ConfigElement]:
        """Parse the input config and return a machine-usable configuration.

        The parsed configuration retains element types. This means that an element of a dictionary type will remain a dictionary
        in the parsed config.

        This method handles most of the [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)'s logic.

        # Returns

        List[ConfigElement]: The parsed configuration.

        """
        final_configs = []

        for valid_element in self.valid_elements:
            if self.is_element_explicit_excluded(valid_element, self._requested_config_element_names):
                continue
            elif self._requested_all_not_elements:
                if valid_element not in self.explicit_elements:
                    final_configs.append(valid_element)
            elif self.is_element_included(valid_element, self._requested_config_element_names, all_not_elements_check=False):
                # get element from original requested_config (via valid_element) and put it to final config
                config_element = self.get_config_element_by_name(valid_element)
                if config_element is not None:
                    final_configs.append(config_element)
                elif "all" in self.requested_config and valid_element not in self.explicit_elements:
                    final_configs.append(valid_element)
            else:
                continue  # donot add element if element is not included while not all exclusive

        return final_configs


def interpret_yes_no(boolstr: str) -> bool:
    """Interpret `yes`/`no` and `on`/`off` as booleans.

    # Parameters

    boolstr (str): `yes`, `no`, `on` or `off`, a typical device response for simple boolean-like queries.

    # Raises

    WrongDataTypeException: An exception is raised when `boolstr` is neither `yes`, `no`, `on` or `off`.

    # Returns

    bool: `True` for *yes* / *on*, `False` otherwise.

    """
    if boolstr not in ["yes", "no", "on", "off"]:
        raise exceptions.WrongDataTypeException(f"Cannot interpret following string as boolean: {boolstr}.")

    return True if boolstr in ["yes", "on"] else False


def printer(report: dict, indent_level: int = 0) -> None:  # pragma: no cover - exclude from pytest coverage
    """Print reports in human friendly format.

    # Parameters

    report (dict): Dict with reports from tests.
    indent_level (int): Indentation level.

    """
    delim = "   |"
    if "passed" in report:
        print(f'{delim*indent_level} passed: {report["passed"]}')
        if report["passed"]:
            return
    for k, v in report.items():
        if k != "passed":
            if isinstance(v, list):
                print(f"{delim*indent_level} {k}:")
                for element in v:
                    if isinstance(element, dict):
                        print(f"{delim*(indent_level +1)}- ")
                        printer(element, indent_level + 1)
                    else:
                        print(f"{delim*(indent_level +1)}- {element}")
            elif isinstance(v, dict):
                print(f"{delim * indent_level} {k}:")
                printer(v, indent_level + 1)
            else:
                print(f"{delim * indent_level} {k}: {v}")
