import importlib.metadata
from importlib import metadata

try:
    __version__ = metadata.version(__package__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "devel"
