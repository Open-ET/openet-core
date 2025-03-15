import logging

import ee

from . import utils


def mgrs_export_tiles(
        study_area_coll_id,
        mgrs_coll_id,
        study_area_property=None,
        study_area_features=[],
        mgrs_tiles=[],
        mgrs_skip_list=[],
        utm_zones=[],
        wrs2_tiles=[],
        mgrs_property='mgrs',
        utm_property='utm',
        wrs2_property='wrs2',
        cell_size=30,
):
    """Select MGRS tiles and metadata that intersect the study area geometry

    Parameters
    ----------
    study_area_coll_id : str
        Study area feature collection asset ID.
    mgrs_coll_id : str
        MGRS feature collection asset ID.
    study_area_property : str, optional
        Property name to use for inList() filter call of study area collection.
        Filter will only be applied if both 'study_area_property' and
        'study_area_features' parameters are both set.
    study_area_features : list, optional
        List of study area feature property values to filter on.
    mgrs_tiles : list, optional
        User defined MGRS tile subset.
    mgrs_skip_list : list, optional
        User defined list MGRS tiles to skip.
    utm_zones : list, optional
        User defined UTM zone subset.
    wrs2_tiles : list, optional
        User defined WRS2 tile subset.
    mgrs_property : str, optional
        MGRS property in the MGRS feature collection (the default is 'mgrs').
    utm_property : str, optional
        UTM zone property in the MGRS feature collection (the default is 'utm').
    wrs2_property : str, optional
        WRS2 property in the MGRS feature collection (the default is 'wrs2').
    cell_size : float, optional
        Cell size for transform and shape calculation (the default is 30).

    Returns
    ------
    list of dicts: export information

    """
    # Build and filter the study area feature collection
    logging.debug('Building study area collection')
    logging.debug(f'  {study_area_coll_id}')
    study_area_coll = ee.FeatureCollection(study_area_coll_id)
    if ((study_area_property == 'STUSPS') and
            ('CONUS' in [x.upper() for x in study_area_features])):
        # Exclude AK, HI, AS, GU, PR, MP, VI, (but keep DC)
        study_area_features = [
            'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL', 'GA',
            'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME',
            'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ',
            'NM', 'NV', 'NY', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD',
            'TN', 'TX', 'UT', 'VA', 'VT', 'WA', 'WI', 'WV', 'WY',
        ]
    study_area_features = sorted(list(set(study_area_features)))

    if study_area_property and study_area_features:
        logging.debug('  Filtering study area collection')
        logging.debug(f'  Property: {study_area_property}')
        logging.debug(f'  Features: {",".join(study_area_features)}')
        study_area_coll = study_area_coll.filter(
            ee.Filter.inList(study_area_property, study_area_features)
        )

    logging.debug('Building MGRS tile list')
    tiles_coll = ee.FeatureCollection(mgrs_coll_id).filterBounds(study_area_coll.geometry())

    # Filter collection by user defined lists
    if utm_zones:
        logging.debug(f'  Filter user UTM Zones:    {utm_zones}')
        tiles_coll = tiles_coll.filter(ee.Filter.inList(utm_property, utm_zones))
    if mgrs_skip_list:
        logging.debug(f'  Filter MGRS skip list:    {mgrs_skip_list}')
        tiles_coll = tiles_coll.filter(ee.Filter.inList(mgrs_property, mgrs_skip_list).Not())
    if mgrs_tiles:
        logging.debug(f'  Filter MGRS tiles/zones:  {mgrs_tiles}')
        # Allow MGRS tiles to be subsets of the full tile code
        #   i.e. mgrs_tiles = 10TE, 10TF
        mgrs_filters = [
            ee.Filter.stringStartsWith(mgrs_property, mgrs_id.upper())
            for mgrs_id in mgrs_tiles
        ]
        tiles_coll = tiles_coll.filter(ee.call('Filter.or', mgrs_filters))

    # Drop the MGRS tile geometry to simplify the getInfo call
    def drop_geometry(ftr):
        return ee.Feature(None).copyProperties(ftr)

    logging.debug('  Requesting tile/zone info')
    tiles_info = utils.get_info(tiles_coll.map(drop_geometry))

    # Constructed as a list of dicts to mimic other interpolation/export tools
    tiles_list = []
    for tile_ftr in tiles_info['features']:
        mgrs_id = tile_ftr['properties']['mgrs'].upper()
        tile_extent = [
            int(tile_ftr['properties']['xmin']),
            int(tile_ftr['properties']['ymin']),
            int(tile_ftr['properties']['xmax']),
            int(tile_ftr['properties']['ymax'])
        ]
        tile_geo = [cell_size, 0, tile_extent[0], 0, -cell_size, tile_extent[3]]
        tile_shape = [
            int((tile_extent[2] - tile_extent[0]) / cell_size),
            int((tile_extent[3] - tile_extent[1]) / cell_size)
        ]
        tiles_list.append({
            'crs': 'EPSG:{:d}'.format(int(tile_ftr['properties']['epsg'])),
            'extent': tile_extent,
            'geo': tile_geo,
            'index': tile_ftr['properties']['mgrs'].upper(),
            'maxpixels': tile_shape[0] * tile_shape[1] + 1,
            'shape': tile_shape,
            'utm': int(mgrs_id[:2]),
            'wrs2_tiles': sorted(utils.wrs2_str_2_set(tile_ftr['properties'][wrs2_property])),
        })

    # Apply the user defined WRS2 tile list
    if wrs2_tiles:
        logging.debug(f'  Filter WRS2 tiles: {wrs2_tiles}')
        for tile in tiles_list:
            tile['wrs2_tiles'] = sorted(list(set(tile['wrs2_tiles']) & set(wrs2_tiles)))

    # Only return export tiles that have intersecting WRS2 tiles
    export_list = [t for t in sorted(tiles_list, key=lambda k: k['index']) if t['wrs2_tiles']]

    return export_list
