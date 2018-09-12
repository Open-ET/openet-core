import ee
import pytest

import openet.interp as interp


def test_ee_init():
    assert ee.Number(1).getInfo() == 1
