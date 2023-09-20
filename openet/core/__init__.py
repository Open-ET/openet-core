# from . import api
from . import common
from . import ensemble
from . import interpolate
from . import utils
from . import wrs2

try:
    from importlib import metadata
except ImportError:  # for Python<3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__package__.replace('.', '-') or __name__.replace('.', '-'))
# __version__ = metadata.version('openet-core')
