from dataclasses import dataclass
from copy import deepcopy
from typing import Optional, Union, List, Dict, Iterable
from enum import Enum

class UnknownParameterException(Exception):
    """Used when one of the requested configuration parameters processed by :class:`.ConfigParser` is not a valid parameter."""
    pass

class WrongDataTypeException(Exception):
    """Used when a variable does not meet data type requirements."""
    pass

class CheckType:
    """Class mapping check configuration strings for commonly used variables.

    Readiness checks configuration passed to the :class:`.CheckFirewall` class is in a form of a list of strings. These strings are compared in several places to parse the configuration and set the proper checks. This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the code.
    """
    PANORAMA = "panorama"
    HA = "ha"
    NTP_SYNC = "ntp_sync"
    CANDIDATE_CONFIG = "candidate_config"
    EXPIRED_LICENSES = "expired_licenses"
    CONTENT_VERSION = "content_version"
    SESSION_EXIST = "session_exist"
    ARP_ENTRY_EXIST = "arp_entry_exist"
    IPSEC_TUNNEL_STATUS = "ip_sec_tunnel_status"
    FREE_DISK_SPACE = "free_disk_space"

class SnapType:
    """Class mapping the snapshot configuration strings to the commonly used variables.

    Snapshot configuration passed to the :class:`.CheckFirewall` class is in a form of a list of strings. These strings are compared in several places to parse the configuration and set proper snapshots.
    This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the code.
    """
    NICS = "nics"
    ROUTES = "routes"
    LICENSE = "license"
    ARP_TABLE = "arp_table"
    CONTENT_VERSION = "content_version"
    SESSION_STATS = "session_stats"
    IPSEC_TUNNELS = "ip_sec_tunnels"

class CheckStatus(Enum):
    """Class containing possible statuses for the check results.

    Its main purpose is to extend the simple ``True/False`` logic in a way that would provide more details/explanation in case a check fails. 
    """
    SUCCESS = 0
    FAIL = 1
    ERROR = 2
    SKIPPED = 3

@dataclass
class CheckResult:
    """Class representing the readiness check results.

    It provides two types of information:

        * ``status`` which represents information about the check outcome,
        * ``reason`` a reason behind the particular outcome, this comes in handy when a check fails.

    Most of the :class:`.CheckFirewall` methods use this class to store the return values, but mostly internally. The :meth:`.CheckFirewall.run_readiness_checks` method translates this class into the python primitives: ``str`` and ``bool``.
    
    :ivar status: Holds the status of a check.
    :type status: :class:`.CheckStatus`
    :ivar reason: Holds a reason explaining why a check fails. Provides no value if the check is successful. 
    :type reason: str
    """
    status: CheckStatus = CheckStatus.FAIL
    reason: str = ""

    def __str__(self):
        """Class' string representation.

        :return: A string combined from the ``self.status`` and ``self.reason`` variables. Provides a human readable representation of the class. Perfect to provide a reason for a particular check outcome.
        :rtype: str
        """
        return f'[{self.status.name}] {self.reason}'

    def __bool__(self):
        """Class' boolean representation.

        :return: A boolean value interpreting the value of the current ``state``: 

            * ``True`` when ``status`` is :attr:`.CheckStatus.SUCCESS`,
            * ``False`` otherwise.

        :rtype: bool
        """
        return True if self.status == CheckStatus.SUCCESS else False

class ConfigParser:
    """Class responsible for parsing the provided configuration.
    
    This class is universal, meaning it parses configuration provided as the list of strings or dictionaries and verifies it against the list of valid configuration items. 
    There are no hardcoded items against which the configuration is checked.

    It assumes and understands the following _`dialect`:

        * all configuration elements are case-sensitive,
        * if an element is ``str``, it is the name of an element,
        * if an element is ``dict``, the key is treated as the name of the element and the value is simply a configuration for this element,
        * the ``all`` item is equal to all items from the valid configuration elements,
        * an empty list is the same as the list containing only the ``all`` item,
        * excluding elements are supported by prefixing an item with an exclamation mark, for example, ``'!config'`` will skip the ``'config'`` element.
        
            These elements are called ``not-elements``. They are useful when combined with ``all``.
            For example: a list of: ``['all', '!tcp']`` or simply ``['!tcp']`` would take all valid elements except for ``tcp``.
            
            Having that said:

        * a list containing only ``not-elements`` is treated as if ``'all'`` would have been specified explicitly,
        * order does not matter,
        * you can override elements implicitly specified with ``all``. This means that:
        
            * when:
        
                * the following list is passed:

                    ::

                        [
                            'all', 
                            { 'content_version': {
                                'version': '1234-5678'}
                            }
                        ]
                    
                *  ``content_version`` is a valid element
            
            * then:
                
                * ``all`` is expanded to all valid elements but
                * ``content_version`` is skipped during expansion (since an explicit definition for it is already available).

    :ivar _requested_config_names: Contains only element names of the requested configuration (see `dialect`_ above). When no requested configuration is passed (implicit ``'all'``, see `dialect`_), this is equal to ``self.valid_elements``.
    :type _requested_config_names: set
    """

    def __init__(self, valid_elements: Iterable, requested_config: Optional[List[Union[str, dict]]] = None):
        """ConfigParser constructor.

        Introduces some initial verification logic:

            * ``valid_elements`` is converted to ``set`` - this way we get rid of all duplicates,
            * if ``requested_config`` is ``None`` we immediately treat it as if ``all``  was passed implicitly (see `dialect`_) - it's expanded to ``valid_elements``
            * ``_requested_config_names`` is introduced as ``requested_config`` stripped of any element configurations. Additionally, we do verification if elements of this variable match ``valid_elements``. An exception is thrown if not.

        :param valid_elements: Valid elements against which we check the requested config.
        :type: iterable
        :param requested_config: (defaults to ``None``) A list of requested configuration items with an optional configuration.
        :type requested_config: list, optional
        :raises UnknownParameterException: An exception is raised when a requested configuration element is not one of the valid elements.
        """
        self.valid_elements = set(valid_elements)

        if requested_config:    # if not None or not empty list
            self.requested_config = deepcopy(requested_config)
            self._requested_config_names = set([ ConfigParser._extract_element_name(config_keyword) for config_keyword in self.requested_config ])
            for config_name in self._requested_config_names:
                if not self._is_element_included(element=config_name):
                    raise UnknownParameterException(f'Unknown configuration parameter passed: {config_name}.')
        else:
            self._requested_config_names = set(valid_elements)
            self.requested_config = list(valid_elements)  # Meaning 'all' valid tests

    def _is_element_included(self, element: str) -> bool:
        """Method verifying if a config element is a correct (supported) value.

        This method can also handle ``not-elements`` (see `dialect`_).

        :meta private:
        :param element: The config element to verify. This can be a ``not-element``.

            This parameter is verified against ``self.valid_elements`` ``set``. Key word ``'all'`` is also accepted.
        :type element: str
        :return: ``True`` if the value is correct, ``False`` otherwise.
        :rtype: bool
        """
        if element in self.valid_elements or (element.startswith('!') and element[1:] in self.valid_elements):
            return True
        elif element == 'all' and 'all' in self.requested_config:
            return True
        else:
            return False

    @staticmethod
    def _extract_element_name(config: Union[str, dict]) -> str:
        """Static method that extracts the name from a config element.

        If a config element is a string, the actual config element is returned. For elements of a dictionary type, the 1\ :sup:`st` key is returned.

        :meta private:
        :param config: A config element to provide a name for.
        :type config: str,dict
        :raises WrongDataTypeException: Thrown when config does not meet requirements.
        :return: The config element name.
        :rtype: str
        """
        if isinstance(config, str):
            return config
        elif isinstance(config, dict):
            if len(config) == 1:
                return list(config.keys())[0]
            else:
                raise WrongDataTypeException(
                    'Dict provided as config definition has incorrect format, it is supposed to have only one key {key:[]}')
        else:
            raise WrongDataTypeException('Config definition is neither string or dict')

    def _expand_all(self) -> None:
        """Expand key word ``'all'`` to  ``self.valid_elements``.
        
        During expansion, elements from ``self.valid_elements`` which are already available in ``self.requested_config`` are skipped.
        This way we do not introduce duplicates for elements that were provided explicitly. 

        :meta private:
        :return: None, as this method directly operates on ``self.requested_config``.
        """
        pure_names = set([
            (name[1:] if name.startswith('!') else name) for name in self._requested_config_names if name != 'all'
        ])
        self.requested_config.extend(list(self.valid_elements - pure_names))
        self.requested_config.remove("all")

    def prepare_config(self) -> List[Union[str,dict]]:
        """Parse the input config and return a machine-usable configuration.

        The parsed configuration retains element types. This means that an element of a dictionary type will remain a dictionary in the parsed config.

        This method handles most of the `dialect`_'s logic.

        :return: The parsed configuration.
        :rtype: list
        """
        if all( (config_name.startswith('!') for config_name in self._requested_config_names) ):
                self.requested_config.insert(0, "all")

        if "all" in self.requested_config:
            self._expand_all()

        final_configs = []

        for config_element in self.requested_config:
            if not ConfigParser._extract_element_name(config_element).startswith('!'):
                final_configs.append(config_element)

        return final_configs


def interpret_yes_no(boolstr: str) -> bool:
        """Interpret ``yes``/``no`` as booleans.
        
        :param boolstr: ``yes`` or ``no``, a typical device response for simple boolean-like queries.
        :type boolstr: str
        :raises WrongDataTypeException: An exception is raised when ``boolstr`` is neither ``yes`` or ``no``.
        :return: ``True`` for *yes*, ``False`` for *no*.
        :rtype: bool
        """
        if not boolstr in ['yes', 'no']:
            raise WrongDataTypeException(f'Cannot interpret following string as boolean: {boolstr}.')

        return True if boolstr == 'yes' else False

def printer(report: dict, indent_level: int = 0) -> None:
    """Print reports in human friendly format.

    :param report: Dict with reports from tests.
    :type report: dict
    :param indent_level: Indentation level.
    :type indent_level: int
    """
    delim = '   |'
    if 'passed' in report:
        print(f'{delim*indent_level} passed: {report["passed"]}')
        if report['passed']:
            return
    for k, v in report.items():
        if k != 'passed':
            if isinstance(v, list):
                print(f'{delim*indent_level} {k}:')
                for element in v:
                    print(f'{delim*(indent_level +1)}- {element}')
            elif isinstance(v, dict):
                print(f'{delim * indent_level} {k}:')
                printer(v, indent_level + 1)
            else:
                print(f'{delim * indent_level} {k}: {v}')
