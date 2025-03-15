import pprint

import openet.core.export as export


def test_mgrs_export_tiles():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
    )
    # Hardcoding these values for now, but they could be changed to conditionals
    assert list(output[0].keys()) == ['crs', 'extent', 'geo', 'index', 'maxpixels', 'shape', 'utm', 'wrs2_tiles']
    assert output[0]['crs'] == 'EPSG:32610'
    assert output[0]['extent'] == [399975, 3699975, 779985, 4399995]
    assert output[0]['geo'] == [30, 0, 399975, 0, -30, 4399995]
    assert output[0]['index'] == '10S'
    assert output[0]['maxpixels'] == 295571779
    assert output[0]['shape'] == [12667, 23334]
    assert output[0]['utm'] == 10
    assert 'p042r035' in output[0]['wrs2_tiles']


def test_mgrs_export_tiles_study_area_features_param():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
        study_area_property='STUSPS',
        study_area_features=['CA'],
    )
    assert ['10S', '10T', '11S', '11T'] == [tile['index'] for tile in output]


def test_mgrs_export_tiles_mgrs_keep_list_param():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
        study_area_property='STUSPS',
        study_area_features=['CA', 'NV'],
        mgrs_tiles=['10S'],
    )
    assert ['10S'] == [tile['index'] for tile in output]


def test_mgrs_export_tiles_mgrs_skip_list_param():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
        study_area_property='STUSPS',
        study_area_features=['CA', 'NV'],
        mgrs_skip_list=['10S'],
    )
    assert ['10T', '11S', '11T'] == [tile['index'] for tile in output]


def test_mgrs_export_tiles_utm_zones_param():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
        study_area_property='STUSPS',
        study_area_features=['CA', 'NV'],
        utm_zones=[11],
    )
    assert ['11S', '11T'] == [tile['index'] for tile in output]


def test_mgrs_export_tiles_wrs2_tiles_param():
    output = export.mgrs_export_tiles(
        study_area_coll_id='TIGER/2018/States',
        mgrs_coll_id='projects/openet/assets/mgrs/conus/gridmet/zones',
        study_area_property='STUSPS',
        study_area_features=['CA'],
        mgrs_tiles=['10S'],
        wrs2_tiles=['p042r035']
    )
    assert ['p042r035'] == output[0]['wrs2_tiles']
