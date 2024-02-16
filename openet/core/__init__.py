# from . import api
from . import landsat
from . import common
from . import ensemble
from . import interpolate
from . import utils
from . import wrs2

from importlib import metadata

__version__ = metadata.version(__package__.replace('.', '-') or __name__.replace('.', '-'))
# __version__ = metadata.version('openet-core')
