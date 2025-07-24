from datetime import datetime, timezone
import logging

import ee
import pytest

import openet.core.interpolate as interpolate
import openet.core.utils as utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


def scene_coll(
        variables,
        etf=[0.582401, 0.712461, 0.638224, 0.603958, 0.663011, 0.649473, 0.739954, 0.727325],
        et=[4.496038, 5.853539, 5.618148, 4.312284, 4.279988, 4.383169, 4.704309, 3.411190],
        ndvi=[0.532851, 0.643263, 0.590405, 0.601745, 0.620367, 0.630300, 0.616460, 0.707051]
):
    """Return a generic scene collection to test scene interpolation functions

    Parameters
    ----------
    variables : list
        The variables to return in the collection
    et_fraction : list
    et : list
    ndvi : list

    Returns
    -------
    ee.ImageCollection

    """
    img = (
        ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_035033_20160612')
        .select(['SR_B3']).double().multiply(0)
    )

    # The "time" is advanced to match the typical Landsat overpass time
    time1 = ee.Number(ee.Date.fromYMD(2016, 6, 28).advance(18, 'hours').millis())
    time2 = ee.Number(ee.Date.fromYMD(2016, 7, 5).advance(18, 'hours').millis())
    time3 = ee.Number(ee.Date.fromYMD(2016, 7, 6).advance(18, 'hours').millis())
    time4 = ee.Number(ee.Date.fromYMD(2016, 7, 13).advance(18, 'hours').millis())
    time5 = ee.Number(ee.Date.fromYMD(2016, 7, 14).advance(18, 'hours').millis())
    time6 = ee.Number(ee.Date.fromYMD(2016, 7, 22).advance(18, 'hours').millis())
    time7 = ee.Number(ee.Date.fromYMD(2016, 7, 29).advance(18, 'hours').millis())
    time8 = ee.Number(ee.Date.fromYMD(2016, 8, 6).advance(18, 'hours').millis())

    # TODO: Add code to convert et, et_fraction, and ndvi to lists if they
    #   are set as a single value

    # Don't add mask or time band to scene collection
    # since they are now added in the interpolation calls
    coll = ee.ImageCollection.fromImages([
        ee.Image([img.add(etf[0]), img.add(et[0]), img.add(ndvi[0])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160628', 'system:time_start': time1}),
        ee.Image([img.add(etf[1]), img.add(et[1]), img.add(ndvi[1])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160705', 'system:time_start': time2}),
        ee.Image([img.add(etf[2]), img.add(et[2]), img.add(ndvi[2])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160706', 'system:time_start': time3}),
        ee.Image([img.add(etf[3]), img.add(et[3]), img.add(ndvi[3])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160713', 'system:time_start': time4}),
        ee.Image([img.add(etf[4]), img.add(et[4]), img.add(ndvi[4])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160714', 'system:time_start': time5}),
        ee.Image([img.add(etf[5]), img.add(et[5]), img.add(ndvi[5])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160722', 'system:time_start': time6}),
        ee.Image([img.add(etf[6]), img.add(et[6]), img.add(ndvi[6])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160729', 'system:time_start': time7}),
        ee.Image([img.add(etf[7]), img.add(et[7]), img.add(ndvi[7])])
        .rename(['et_fraction', 'et', 'ndvi'])
        .set({'system:index': 'LC08_035033_20160806', 'system:time_start': time8}),
    ])

    return coll.select(variables)


def test_from_scene_et_fraction_t_interval_daily_values_interpolated(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction']),
        start_date='2016-07-01',
        end_date='2016-08-01',
        variables=['et', 'et_reference', 'et_fraction'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
                    'et_reference_band': 'eto',
                    'et_reference_resample': 'nearest'},
        t_interval='daily',
    )
    TEST_POINT = (-108.60235405579016, 39.13350444421074)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
    assert abs(output['et_fraction']['2016-07-01'] - 0.6381) <= tol
    assert abs(output['et_fraction']['2016-07-05'] - 0.7125) <= tol
    assert abs(output['et_fraction']['2016-07-07'] - 0.6333) <= tol
    assert abs(output['et_fraction']['2016-07-31'] - 0.7368) <= tol
    assert abs(output['et_reference']['2016-07-01'] - 4.1080) <= tol
    assert abs(output['et_reference']['2016-07-05'] - 8.2159) <= tol
    assert abs(output['et_reference']['2016-07-07'] - 7.8247) <= tol
    assert abs(output['et_reference']['2016-07-31'] - 5.7707) <= tol
    assert abs(output['et']['2016-07-01'] - 2.6215) <= tol
    assert abs(output['et']['2016-07-05'] - 5.8535) <= tol
    assert abs(output['et']['2016-07-07'] - 4.9556) <= tol
    assert abs(output['et']['2016-07-31'] - 4.2518) <= tol


@pytest.mark.parametrize(
    "et_reference_band, et_reference_date, et_reference, et_fraction, et",
    [
        ['eto', '2016-07-10', 9.7809, 0.6186, 9.7809 * 0.6186],
        ['etr', '2016-07-10', 13.9403, 0.6186, 13.9403 * 0.6186],
    ]
)
def test_from_scene_et_fraction_t_interval_daily_values_et_reference(
        et_reference_band, et_reference_date, et_reference, et_fraction, et, tol=0.001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction']),
        start_date='2016-07-01',
        end_date='2016-08-01',
        variables=['et', 'et_reference', 'et_fraction'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
                    'et_reference_band': et_reference_band,
                    'et_reference_resample': 'nearest'},
        t_interval='daily',
    )
    TEST_POINT = (-108.60235405579016, 39.13350444421074)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
    assert abs(output['et_reference'][et_reference_date] - et_reference) <= tol
    assert abs(output['et'][et_reference_date] - et) <= tol


# @pytest.mark.parametrize(
#     "et_reference_band, et_reference",
#     [
#         ['eto', 236.5],
#         ['etr', 310.3],
#     ]
# )
# def test_from_scene_et_fraction_t_interval_monthly_values(et_reference_band, et_reference, tol=0.0001):
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': et_reference_band,
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['ndvi']['2016-07-01'] - 0.6) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 0.4) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - et_reference) <= tol
#     assert abs(output['et']['2016-07-01'] - (et_reference * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_fraction_t_interval_custom_values(tol=0.0001):
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['ndvi']['2016-07-01'] - 0.6) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 0.4) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et']['2016-07-01'] - (310.3 * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_fraction_t_interval_custom_daily_count():
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et_fraction', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert output['daily_count']['2016-07-01'] == 31
#
#
# def test_from_scene_et_fraction_t_interval_custom_mask_partial_aggregations_true():
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01', end_date='2016-08-01',
#         variables=['et_fraction', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 2,
#                      'mask_partial_aggregations': True},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert output['daily_count']['2016-07-01'] is None
#
#
# def test_from_scene_et_fraction_t_interval_custom_mask_partial_aggregations_false():
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et_fraction', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 2,
#                      'mask_partial_aggregations': False},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     # CGM - 3 Landsat scenes with +/-2 days around each should be 15 days
#     #   There is probably an off by one error/bug in the interpolation somewhere
#     assert output['daily_count']['2016-07-01'] == 18
#
#
# def test_from_scene_et_fraction_t_interval_monthly_et_reference_factor(tol=0.0001):
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_factor': 0.5,
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['ndvi']['2016-07-01'] - 0.6) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 0.4) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3 * 0.5) <= tol
#     assert abs(output['et']['2016-07-01'] - (310.3 * 0.5 * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# @pytest.mark.parametrize(
#     "et_reference_band, et_reference",
#     [
#         ['eto', 236.05609131],
#         ['etr', 309.4239807128906],
#     ]
# )
# def test_from_scene_et_fraction_t_interval_monthly_et_reference_resample(
#         et_reference_band, et_reference, tol=0.0001):
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': et_reference_band,
#                     'et_reference_resample': 'bilinear'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['ndvi']['2016-07-01'] - 0.6) <= tol
#     # CGM - Reference ET and ET test values will be slightly different
#     #   with bilinear resampling, but ET fraction should be the same
#     assert abs(output['et_fraction']['2016-07-01'] - 0.4) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - et_reference) <= tol
#     assert abs(output['et']['2016-07-01'] - (et_reference * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_fraction_t_interval_monthly_interp_args_et_reference(tol=0.0001):
#     # Check that the et_reference parameters can be set through the interp_args
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'et_reference_band': 'etr',
#                      'et_reference_resample': 'nearest'},
#         model_args={},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['ndvi']['2016-07-01'] - 0.6) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 0.4) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et']['2016-07-01'] - (310.3 * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_t_interval_daily_values_eto(tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'eto',
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'eto',
#                     'et_reference_resample': 'nearest'},
#         t_interval='daily',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     import pprint
#     pprint.pprint(output)
#     assert abs(output['et_fraction']['2016-07-01'] - 0.6381) <= tol
#     assert abs(output['et_fraction']['2016-07-05'] - 0.7125) <= tol
#     assert abs(output['et_fraction']['2016-07-07'] - 0.6333) <= tol
#     assert abs(output['et_fraction']['2016-07-31'] - 0.7368) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 7.9324) <= tol
#     assert abs(output['et_reference']['2016-07-05'] - 8.2159) <= tol
#     assert abs(output['et_reference']['2016-07-10'] - 8.5653) <= tol
#     assert abs(output['et_reference']['2016-07-31'] - 5.9407) <= tol
#     assert abs(output['et']['2016-07-01'] - 5.0620) <= tol
#     assert abs(output['et']['2016-07-05'] - 8.2159) <= tol
#     assert abs(output['et']['2016-07-07'] - 8.5653) <= tol
#     assert abs(output['et']['2016-07-31'] - 5.9407) <= tol
#
#
# def test_from_scene_et_actual_t_interval_daily_values_etr(tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='daily',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et_fraction']['2016-07-10'] - 0.449444979429245) <= tol
#     assert abs(output['et_reference']['2016-07-10'] - 10.5) <= tol
#     assert abs(output['et']['2016-07-10'] - 4.71917200088501) <= tol
#     assert abs(output['et']['2016-07-01'] - 3.6936933994293213) <= tol
#     assert abs(output['et']['2016-07-31'] - 4.951923370361328) <= tol
#     assert '2016-08-01' not in output['et'].keys()
#     # assert output['count']['2016-07-01'] == 3
#
#
# @pytest.mark.parametrize(
#     "et_reference_band, et_reference, et",
#     [
#         ['eto', 236.5, 145.9705047607422],
#         ['etr', 310.3, 142.9622039794922],
#     ]
# )
# def test_from_scene_et_actual_t_interval_monthly_values(
#         et_reference_band, et_reference, et, tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': et_reference_band,
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': et_reference_band,
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - et) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - et_reference) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - et / et_reference) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_t_interval_custom_values_monthly(tol=0.0001):
#     # Check that the custom time interval and monthly time interval match
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - 142.9622039794922) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 142.9622039794922 / 310.3) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_t_interval_custom_daily_count():
#     # Check that the custom time interval and monthly time interval match
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert output['daily_count']['2016-07-01'] == 31
#
#
# def test_from_scene_et_actual_t_interval_custom_mask_partial_aggregations_true():
#     # Check that the custom time interval and monthly time interval match
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 2,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest',
#                      'mask_partial_aggregations': True},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert output['daily_count']['2016-07-01'] is None
#
#
# def test_from_scene_et_actual_t_interval_custom_mask_partial_aggregations_false():
#     # Check that the custom time interval and monthly time interval match
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'daily_count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 2,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest',
#                      'mask_partial_aggregations': False},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='custom',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert output['daily_count']['2016-07-01'] == 18
#
# def test_from_scene_et_actual_t_interval_monthly_et_reference_factor(tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_factor': 0.5,
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - 142.9622039794922) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3 * 0.5) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 142.9622039794922 / 310.3 / 0.5) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# @pytest.mark.parametrize(
#     "et_reference_band, et_reference, et",
#     [
#         ['eto', 236.05609131, 145.86253356933594],
#         ['etr', 309.4239807128906, 142.99319458007812],
#     ]
# )
# def test_from_scene_et_actual_t_interval_monthly_et_reference_resample(
#         et_reference_band, et_reference, et, tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': et_reference_band,
#                      'interp_resample': 'bilinear'},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': et_reference_band,
#                     'et_reference_resample': 'bilinear'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - et) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - et_reference) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - et / et_reference) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_t_interval_monthly_interp_args_et_reference(tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest',
#                      'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'et_reference_band': 'etr',
#                      'et_reference_resample': 'nearest'},
#         model_args={},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - 142.9622039794922) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et_fraction']['2016-07-01'] - 142.9622039794922 / 310.3) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_t_interval_daily_et_fraction_max(tol=0.0001):
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et'], et=[100, 100, 100]),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'et_fraction'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                      'interp_band': 'etr',
#                      'interp_resample': 'nearest',
#                      'et_fraction_min': 0.0,
#                      'et_fraction_max': 1.4},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='daily',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et_fraction']['2016-07-10'] - 1.4) <= tol
#
#
# def test_from_scene_et_fraction_t_interval_bad_value():
#     # Function should raise a ValueError if t_interval is not supported
#     with pytest.raises(ValueError):
#         interpolate.from_scene_et_fraction(
#             scene_coll(['et']),
#             start_date='2016-07-01',
#             end_date='2016-08-01',
#             variables=['et'],
#             interp_args={'interp_method': 'linear', 'interp_days': 32},
#             model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                         'et_reference_band': 'etr',
#                         'et_reference_resample': 'nearest'},
#             t_interval='deadbeef',
#         )
#
#
# def test_from_scene_et_fraction_t_interval_no_value():
#     # Function should raise an Exception if t_interval is not set
#     with pytest.raises(TypeError):
#         interpolate.from_scene_et_fraction(
#             scene_coll(['et']),
#             start_date='2016-07-01',
#             end_date='2016-08-01',
#             variables=['et', 'et_reference', 'et_fraction', 'count'],
#             interp_args={'interp_method': 'linear', 'interp_days': 32},
#             model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                         'et_reference_band': 'etr',
#                         'et_reference_resample': 'nearest'},
#         )
#
#
# def test_from_scene_et_actual_t_interval_bad_value():
#     # Function should raise a ValueError if t_interval is not supported
#     with pytest.raises(ValueError):
#         interpolate.from_scene_et_actual(
#             scene_coll(['et']),
#             start_date='2016-07-01',
#             end_date='2016-08-01',
#             variables=['et'],
#             interp_args={'interp_method': 'linear', 'interp_days': 32,
#                          'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                          'interp_band': 'etr', 'interp_resample': 'nearest'},
#             model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                         'et_reference_band': 'etr',
#                         'et_reference_resample': 'nearest'},
#             t_interval='deadbeef',
#         )
#
#
# def test_from_scene_et_actual_t_interval_no_value():
#     # Function should raise an Exception if t_interval is not set
#     with pytest.raises(TypeError):
#         interpolate.from_scene_et_actual(
#             scene_coll(['et']),
#             start_date='2016-07-01',
#             end_date='2016-08-01',
#             variables=['et'],
#             interp_args={'interp_method': 'linear', 'interp_days': 32,
#                          'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                          'interp_band': 'etr',
#                          'interp_resample': 'nearest'},
#             model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                         'et_reference_band': 'etr',
#                         'et_reference_resample': 'nearest'},
#         )
#
#
# def test_from_scene_et_fraction_interp_args_use_joins_true(tol=0.01):
#     # Check that the use_joins interp_args parameter works
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32, 'use_joins': True},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et']['2016-07-01'] - (310.3 * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_fraction_interp_args_use_joins_false(tol=0.01):
#     # Check that the use_joins interp_args parameter works
#     output_coll = interpolate.from_scene_et_fraction(
#         scene_coll(['et_fraction']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32, 'use_joins': False},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert abs(output['et']['2016-07-01'] - (310.3 * 0.4)) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_interp_args_use_joins_true(tol=0.01):
#     # Check that the use_joins interp_args parameter works
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1', 'interp_band': 'etr',
#                      'use_joins': True},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - 142.9622039794922) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert output['count']['2016-07-01'] == 3
#
#
# def test_from_scene_et_actual_interp_args_use_joins_false(tol=0.01):
#     # Check that the use_joins interp_args parameter works
#     output_coll = interpolate.from_scene_et_actual(
#         scene_coll(['et']),
#         start_date='2016-07-01',
#         end_date='2016-08-01',
#         variables=['et', 'et_reference', 'count'],
#         interp_args={'interp_method': 'linear', 'interp_days': 32,
#                      'interp_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1', 'interp_band': 'etr',
#                      'use_joins': True},
#         model_args={'et_reference_source': 'projects/openet/assets/reference_et/conus/gridmet/daily/v1',
#                     'et_reference_band': 'etr',
#                     'et_reference_resample': 'nearest'},
#         t_interval='monthly',
#     )
#     TEST_POINT = (-108.60235405579016, 39.13350444421074)
#     output = utils.point_coll_value(output_coll, TEST_POINT, scale=30)
#     assert abs(output['et']['2016-07-01'] - 142.9622039794922) <= tol
#     assert abs(output['et_reference']['2016-07-01'] - 310.3) <= tol
#     assert output['count']['2016-07-01'] == 3
