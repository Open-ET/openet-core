from datetime import datetime
import math
import pprint

import ee
import pytest

import openet.core.gapfill as gapfill
import openet.core.utils as utils


@pytest.mark.parametrize(
    "month, xy, expected",
    [
        # Central Valley, CA
        [1, [-116, 47], 0.2447],
        [7, [-116, 47], 0.6176],
        # Lake Tahoe
        [1, [-120, 39], 0.7437],
        [7, [-120, 39], 0.7359],
    ]
)
def test_veget_etf_climatology(month, xy, expected, tol=0.0001):
    output_img = gapfill.veget_etf_climatology(month=month)
    output = utils.point_image_value(output_img, xy)['etf']
    assert abs(output - expected) <= 0.0001


@pytest.mark.parametrize(
    "xy, expected",
    [
        # Central Valley, CA
        [[-116, 47], 0.1],
        # Lake Tahoe
        [[-120, 39], 0.8],
    ]
)
def test_nalcms_etf(xy, expected, tol=0.0001):
    output_img = gapfill.nalcms_etf()
    output = utils.point_image_value(output_img, xy)['etf']
    assert abs(output - expected) <= tol


def test_compute_monthly_et_fraction(tol=0.01):
    et_coll = ee.ImageCollection([
        ee.Image.constant(6).rename('et').set({
            'system:time_start': ee.Date('2017-07-01').millis(),
            'mgrs_tile': '10S',
        }),
        ee.Image.constant(4).rename('et').set({
            'system:time_start': ee.Date('2017-08-01').millis(),
            'mgrs_tile': '10S',
        }),
    ])
    eto_coll = ee.ImageCollection([
        ee.Image.constant(10).rename('eto').set({
            'system:time_start': ee.Date('2017-07-01').millis(),
            'mgrs_tile': '10S',
        }),
        ee.Image.constant(8).rename('eto').set({
            'system:time_start': ee.Date('2017-08-01').millis(),
            'mgrs_tile': '10S',
        })
    ])
    output_coll = gapfill.compute_monthly_et_fraction(
        et_coll=et_coll, et_reference_coll=eto_coll, et_band='et', et_reference_band='eto'
    )
    output_img = output_coll.first()
    output = utils.constant_image_value(output_img)
    assert abs(output['et_fraction'] - 0.6) <= tol
    assert abs(output['et_reference'] - 10) <= tol
    assert abs(output['et'] - 6) <= tol

    # Check properties
    assert output_img.getInfo()['properties']['month'] == 7
    assert output_img.getInfo()['properties']['mgrs_tile'] == '10S'


def test_compute_monthly_climatology():
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    years = [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019]
    month = 7
    input_coll = ee.ImageCollection.fromImages([
        ee.Image.constant([value]).rename(['etf_test']).toDouble().set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            # 'mgrs_tile': '10S'
        })
        for value, year in zip(values, years)
    ])

    output_img = gapfill.compute_monthly_climatology(
        input_coll=input_coll,
        month=month,
        climo_year_start=min(years),
        climo_year_end=max(years),
        climo_min_count=3,
        input_band='etf_test',
        output_band='etf',
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert abs(output['etf'] - (sum(values) / len(values))) <= 0.01
    assert output['count'] == len(years)

    # Check properties
    output_info = output_img.getInfo()
    assert output_info['properties']['month'] == month
    assert output_info['properties']['climo_min_count'] == 3
    assert output_info['properties']['climo_year_start'] == min(years)
    assert output_info['properties']['climo_year_end'] == max(years)
    # assert output_info['properties']['mgrs_tile'] == '10S'


def test_compute_monthly_climatology_climo_min_count():
    # Check to see that the climo_min_count parameter works as expected
    # Build the test collection with half of the images masked
    #   then vary the climo_min_count value until the output is masked
    values = [0, 0, 0, 0, 0, 0.6, 0.7, 0.8, 0.9, 1.0]
    expected = 0.8
    years = [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019]
    month = 7
    input_coll = ee.ImageCollection.fromImages([
        ee.Image.constant([value]).rename(['et_fraction']).toDouble()
            .updateMask(int(round(value)))
            .set({'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis()})
        for value, year in zip(values, years)
    ])

    # A min count of 4 should pass since there are 5 years of values
    output_img = gapfill.compute_monthly_climatology(
        input_coll=input_coll, month=month, 
        climo_year_start=min(years), climo_year_end=max(years),
        climo_min_count=4,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert abs(output['et_fraction'] - expected) <= 0.01
    assert output['count'] == 5

    # A min count of 5 should also pass with 5 years of data since the check is .gte()
    output_img = gapfill.compute_monthly_climatology(
        input_coll=input_coll, month=month, 
        climo_year_start=min(years), climo_year_end=max(years),
        climo_min_count=5,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert abs(output['et_fraction'] - expected) <= 0.01
    assert output['count'] == 5

    # A min count of 6 should fail and return none for both et_fraction and count
    output_img = gapfill.compute_monthly_climatology(
        input_coll=input_coll, month=month, 
        climo_year_start=min(years), climo_year_end=max(years),
        climo_min_count=6,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert output['et_fraction'] is None
    assert output['count'] is None


def test_filled_monthly_et_fill_value_1month():
    # Check that the climo fill value is used if the input values are masked
    eto = [ 10,  10,  10,  10,  10,  10, 10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8, 0.9,  0, 0.7, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,   9,  0,   7,   6,   4,    3,  1]
    etf_climo = 2

    # Output ET values are rounded to the nearest integer
    expected = eto[6] * (etf_climo + ((etf[5] - etf_climo) * 0.5) + ((etf[7] - etf_climo) * 0.5))
    expected = int(round(expected))

    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([etf_climo, 5]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([3]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2011-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=1,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    pprint.pprint(output)
    assert output['et_unfilled'] is None
    assert abs(output['et_filled'] - expected) < 0.01
    assert output['filled_mask'] == 2


def test_filled_monthly_et_fill_value_2months():
    # Check that the climo fill value is used if the input values are masked
    eto = [ 10,  10,  10,  10,  10,  10, 10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8,   0,  0,   0, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,   0,  0,   0,   6,   4,    3,  1]
    etf_climo = 2

    # Output ET values are rounded to the nearest integer
    expected = (
        eto[6] *
        (etf_climo + ((etf[4] - etf_climo) * 0.184) + ((etf[8] - etf_climo) * 0.184))
    )
    expected = int(round(expected))

    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([etf_climo, 5]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([3]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2011-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=2,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    pprint.pprint(output)
    assert output['et_unfilled'] is None
    assert abs(output['et_filled'] - expected) < 0.01
    assert output['filled_mask'] == 2


@pytest.mark.parametrize(
    "etf_climo",
    [
        0.9,
        2.0,
        0.1,
    ]
)
def test_filled_monthly_et_fill_value_combo(etf_climo):
    # Check that the climo fill value is used if the input values are masked
    eto = [ 10,  10,  10,  10,  10,  10, 10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8,   0,  0, 0.7, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,   0,  0,   7,   6,   4,    3,  1]

    # Output ET values are rounded to the nearest integer
    expected = (
        eto[6] * (etf_climo + ((etf[4] - etf_climo) * 0.184) + ((etf[7] - etf_climo) * 0.5))
    )
    # print('\nExpected')
    # print(expected)
    expected = int(round(expected))

    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([etf_climo, 5]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([3]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2011-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=2,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    pprint.pprint(output)
    assert output['et_unfilled'] is None
    assert abs(output['et_filled'] - expected) < 0.01
    assert output['filled_mask'] == 2


def test_filled_monthly_et_unfilled_value():
    # Check that unfilled value is passed through
    eto = [ 10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8, 1.0, 0.9, 0.7, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,  10,   9,   7,   6,   4,    3,  1]
    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([2, 5]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([3]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2012-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=1,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert abs(output['et_unfilled'] - 9) < 0.01
    assert abs(output['et_filled'] - 9) < 0.01
    assert output['filled_mask'] == 1


def test_filled_monthly_et_climo_value():
    # Check that the climo fill value is used if the input values are masked
    # B
    eto = [ 10,  10,  10,  10,  10,  10, 10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8,   0,  0,   0, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,   0,  0,   0,   6,   4,    3,  1]
    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([2, 5]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([3]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2012-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=1,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert output['et_unfilled'] is None
    assert abs(output['et_filled'] - 20) < 0.01
    assert output['filled_mask'] == 2


def test_filled_monthly_et_default_value():
    # Check that the default fill value is used if the input and climo are masked
    eto = [ 10,  10,  10,  10,  10,  10, 10,  10,  10,  10,  10,  10]
    etf = [0.1, 0.1, 0.2, 0.5, 0.8, 1.0,  0, 0.7, 0.6, 0.4, 0.3, 0.1]
    et =  [  1,   1,   2,   5,   8,  10,  0,   7,   6,   4,    3,  1]
    input_coll = ee.ImageCollection.fromImages([
        ee.Image([
            ee.Image.constant(etf[m_i]).rename(['et_fraction']).toDouble().updateMask(int(math.ceil(etf[m_i]))),
            ee.Image.constant(et[m_i]).rename(['et']).toDouble().updateMask(int(math.ceil(et[m_i]))),
            ee.Image.constant(eto[m_i]).rename(['et_reference']).toDouble()
        ]).set({
            'system:time_start': ee.Date(f'{year}-{month:02d}-01').millis(),
            'system:index': f'{year}-{month:02d}-01',
            'month': month,
            'mgrs_tile': '10S'
        })
        for year in range(2010, 2015)
        for m_i, month in enumerate(range(1, 13))
    ])

    etf_climo_img = ee.Image.constant([0, 0]).updateMask([0, 0]).rename(['et_fraction', 'count'])
    etf_default_img = ee.Image.constant([2]).rename(['et_fraction'])

    output_img = gapfill.filled_monthly_et(
        input_coll=input_coll,
        img_date='2012-07-01',
        etf_climo_img=etf_climo_img,
        etf_default_img=etf_default_img,
        fill_months=1,
    )
    output = utils.constant_image_value(ee.Image(output_img))
    assert output['et_unfilled'] is None
    assert abs(output['et_filled'] - 20) < 0.01
    assert output['filled_mask'] == 3
