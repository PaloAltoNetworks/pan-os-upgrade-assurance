class CommandRunFailedException(Exception):
    """Used when a command run on a device does not return the `success` status."""

    pass


class MalformedResponseException(Exception):
    """A generic exception class used when a response does not meet the expected standards."""

    pass


class DeviceNotLicensedException(Exception):
    """Used when no license is retrieved from a device."""

    pass


class ContentDBVersionsFormatException(Exception):
    """Used when parsing Content DB versions fail due to an unknown version format (assuming `XXXX-YYYY`)."""

    pass


class PanoramaConfigurationMissingException(Exception):
    """Used when checking Panorama connectivity on a device that was not configured with Panorama."""

    pass


class WrongDiskSizeFormatException(Exception):
    """Used when parsing free disk size information."""

    pass


class UpdateServerConnectivityException(Exception):
    """Used when connection to the Update Server cannot be established."""

    pass


class ContentDBVersionInFutureException(Exception):
    """Used when the installed Content DB version is newer than the latest available version."""

    pass


class WrongDataTypeException(Exception):
    """Used when passed configuration does not meet the data type requirements."""

    pass


class MissingKeyException(Exception):
    """Used when an exception about the missing keys in a dictionary is thrown."""

    pass


class SnapshotSchemeMismatchException(Exception):
    """Used when a snapshot element contains different properties in both snapshots."""

    pass


class UnknownParameterException(Exception):
    """Used when one of the requested configuration parameters processed by [`ConfigParser`](#class-configparser) is not a valid parameter."""

    pass
