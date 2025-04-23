import argparse
import calendar
from datetime import datetime, timedelta, timezone
import itertools
import json
import logging
import os
import time

import ee


def affine_transform(image):
    """Get the affine transform of the image as an EE object

    Parameters
    ----------
    image : ee.Image

    Returns
    -------
    ee.List

    """
    return ee.List(ee.Dictionary(ee.Algorithms.Describe(image.projection())).get('transform'))


def arg_valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to check the format of dates entered as command line arguments
    It would probably make more sense to have this function
        parse the date using dateutil parser (http://labix.org/python-dateutil)
        and return the ISO format string

    Parameters
    ----------
    input_date : string

    Returns
    -------
    datetime

    Raises
    ------
    ArgParse ArgumentTypeError

    """
    try:
        return datetime.strptime(input_date, '%Y-%m-%d')
    except ValueError:
        msg = f'Not a valid date: "{input_date}".'
        raise argparse.ArgumentTypeError(msg)


def arg_valid_file(file_path):
    """Argparse specific function for testing if file exists

    Convert relative paths to absolute paths
    """
    if os.path.isfile(os.path.abspath(os.path.realpath(file_path))):
        return os.path.abspath(os.path.realpath(file_path))
    else:
        raise argparse.ArgumentTypeError(f'{file_path} does not exist')


def build_parent_folders(folder_id, set_public=False):
    """Build the asset folder including parents"""
    # Build any parent folders above the "3rd" level
    # i.e. after "projects/openet/assets" or "projects/openet/folder"
    public_policy = {'bindings': [{'role': 'roles/viewer', 'members': ['allUsers']}]}
    folder_id_split = folder_id.replace('projects/earthengine-legacy/assets/', '').split('/')
    for i in range(len(folder_id_split)):
        if i <= 3:
            continue
        folder_id = '/'.join(folder_id_split[:i])
        if not ee.data.getInfo(folder_id):
            print(f'  Building folder: {folder_id}')
            ee.data.createAsset({'type': 'FOLDER'}, folder_id)
            if set_public:
                ee.data.setIamPolicy(folder_id, public_policy)


def date_0utc(date):
    """Get the 0 UTC date for a date

    Parameters
    ----------
    date : ee.Date

    Returns
    -------
    ee.Date

    """
    return ee.Date.fromYMD(date.get('year'), date.get('month'), date.get('day'))


def date_range(start_dt, end_dt, days=1, skip_leap_days=False):
    """Generate dates within a range (inclusive)

    Parameters
    ----------
    start_dt : datetime
        Start date.
    end_dt : datetime
        End date.
    days : int, optional
        Step size (the default is 1).
    skip_leap_days : bool, optional
        If True, skip leap days while incrementing (the default is False).

    Yields
    ------
    datetime

    """
    import copy
    curr_dt = copy.copy(start_dt)
    while curr_dt <= end_dt:
        if not skip_leap_days or curr_dt.month != 2 or curr_dt.day != 29:
            yield curr_dt
        curr_dt += timedelta(days=days)


def date_years(start_dt, end_dt, exclusive_end_dates=False):
    """Generate separate start and end dates for each year in a date range

    Parameters
    ----------
    start_dt : datetime
        Start date.
    end_dt : datetime
        End date.
    exclusive_end_dates : bool, optional
        If True, set the end dates for each iteration range to be exclusive.

    Yields
    -------
    start and end datetimes for each year

    """
    if (end_dt - start_dt).days > 366:
        for year in range(start_dt.year, end_dt.year + 1):
            year_start_dt = max(datetime(year, 1, 1), start_dt)
            year_end_dt = datetime(year + 1, 1, 1) - timedelta(days=1)
            year_end_dt = min(year_end_dt, end_dt)
            if exclusive_end_dates:
                year_end_dt = year_end_dt + timedelta(days=1)
            yield year_start_dt, year_end_dt
    else:
        if exclusive_end_dates:
            yield start_dt, end_dt + timedelta(days=1)
        else:
            yield start_dt, end_dt


def delay_task(delay_time=0, task_max=-1, task_count=0):
    """Delay script execution based on number of READY tasks

    Parameters
    ----------
    delay_time : float, int
        Delay time in seconds between starting export tasks or checking the
        number of queued tasks if "ready_task_max" is > 0.  The default is 0.
        The delay time will be set to a minimum of 10 seconds if
        ready_task_max > 0.
    task_max : int, optional
        Maximum number of queued "READY" tasks.
    task_count : int
        The current/previous/assumed number of ready tasks.
        Value will only be updated if greater than or equal to ready_task_max.

    Returns
    -------
    int : ready_task_count

    """
    if task_max > 3000:
        raise ValueError('The maximum number of queued tasks must be less than 3000')

    # Force delay time to be a positive value since the parameter used to
    #   support negative values
    if delay_time < 0:
        delay_time = abs(delay_time)

    if (task_max is None or task_max <= 0) and (delay_time >= 0):
        # Assume task_max was not set and just wait the delay time
        logging.debug(f'  Pausing {delay_time} seconds, not checking task list')
        time.sleep(delay_time)
        return 0
    elif task_max and (task_count < task_max):
        # Skip waiting or checking tasks if a maximum number of tasks was set
        #   and the current task count is below the max
        logging.debug(f'  Ready tasks: {task_count}')
        return task_count

    # If checking tasks, force delay_time to be at least 10 seconds if
    #   ready_task_max is set to avoid excessive EE calls
    delay_time = max(delay_time, 10)

    # Make an initial pause before checking tasks lists to allow
    #   for previous export to start up
    # CGM - I'm not sure what a good default first pause time should be,
    #   but capping it at 30 seconds is probably fine for now
    logging.debug(f'  Pausing {min(delay_time, 30)} seconds for tasks to start')
    time.sleep(delay_time)

    # If checking tasks, don't continue to the next export until the number
    #   of READY tasks is greater than or equal to "ready_task_max"
    while True:
        ready_task_count = len(get_ee_tasks(states=['READY']).keys())
        logging.debug(f'  Ready tasks: {ready_task_count}')
        if ready_task_count >= task_max:
            logging.debug(f'  Pausing {delay_time} seconds')
            time.sleep(delay_time)
        else:
            logging.debug(f'  {task_max - ready_task_count} open task '
                          f'slots, continuing processing')
            break

    return ready_task_count


def dilate(img, pixels=1, reproject_flag=True):
    """Dilate (buffer) morphology function

    Parameters
    ----------
    img : ee.Image
        Input mask image with values of 0 and 1.
    pixels : int
        Number of pixels to dilate.  The default is 1.
    reproject_flag : bool
        If True, call reproject on the output image using the input image projection.
        This must be set True for the calculation to be done in terms of "pixels",
        but it could be set False if reproject is being applied later on to the image.
        The default is True.

    Returns
    -------
    ee.Image

    """
    output = img.fastDistanceTransform(pixels).sqrt().lte(pixels)
    if reproject_flag:
        output = output.reproject(img.projection())

    return output.rename('mask')


def erode(img, pixels=1, reproject_flag=True):
    """Erode (shrink) morphology function

    Parameters
    ----------
    img : ee.Image
        Input mask image with values of 0 and 1.
    pixels : int
        Number of pixels to erode.  The default is 1.
    reproject_flag : bool
        If True, call reproject on the output image using the input image projection.
        This must be set True for the calculation to be done in terms of "pixels",
        but it could be set False if reproject is being applied later on to the image.
        The default is True.

    Returns
    -------
    ee.Image

    """
    output = img.Not().fastDistanceTransform(pixels).sqrt().gt(pixels)
    if reproject_flag:
        output = output.reproject(img.projection())

    return output.rename('mask')


def get_info(ee_obj, max_retries=4):
    """Make an exponential back off getInfo call on an Earth Engine object"""
    # output = ee_obj.getInfo()
    output = None
    for i in range(1, max_retries):
        try:
            output = ee_obj.getInfo()
        except ee.ee_exception.EEException as e:
            if ('Earth Engine memory capacity exceeded' in str(e) or
                    'Earth Engine capacity exceeded' in str(e) or
                    'Too many concurrent aggregations' in str(e) or
                    'Computation timed out.' in str(e)):
                # TODO: Maybe add 'Connection reset by peer'
                logging.info(f'    Resending query ({i}/{max_retries})')
                logging.info(f'    {e}')
            else:
                # TODO: What should happen for unexpected EE exceptions?
                #   It might be better to reraise the exception and exit
                logging.info(f'    {e}')
                logging.info('    Unhandled Earth Engine exception')
                continue
        except Exception as e:
            logging.info(f'    Resending query ({i}/{max_retries})')
            logging.debug(f'    {e}')

        if output is not None:
            break

        time.sleep(i ** 3)

    return output


def get_ee_assets(asset_id, start_dt=None, end_dt=None, retries=4):
    """Return assets IDs in a collection

    Parameters
    ----------
    asset_id : str
        A folder or image collection ID.
    start_dt : datetime, optional
        Start date (inclusive).
    end_dt : datetime, optional
        End date (exclusive, similar to .filterDate()).
    retries : int, optional
        The number of times to retry getting the task list if there is an error.

    Returns
    -------
    list : Asset IDs

    """
    # # CGM - There was a bug in earthengine-api>=0.1.326 that caused listImages()
    # #   to return an empty list if the startTime and endTime parameters are set
    # # Switching to a .aggregate_array(system:index).getInfo() approach below for now
    # #   since getList is flagged for deprecation
    # # This may have been fixed in a later update and should be reviewed
    coll = ee.ImageCollection(asset_id)
    if start_dt and end_dt:
        coll = coll.filterDate(start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
    # params = {'parent': asset_id}
    # if start_dt and end_dt:
    #     # CGM - Do both start and end need to be set to apply filtering?
    #     params['startTime'] = start_dt.isoformat() + '.000000000Z'
    #     params['endTime'] = end_dt.isoformat() + '.000000000Z'

    asset_id_list = None
    for i in range(retries):
        try:
            asset_id_list = coll.aggregate_array('system:index').getInfo()
            asset_id_list = [f'{asset_id}/{id}' for id in asset_id_list]
            # asset_id_list = [x['id'] for x in ee.data.listImages(params)['images']]
            break
        except ValueError:
            raise Exception('\nThe collection or folder does not exist, exiting')
        except Exception as e:
            logging.warning(f'  Error getting asset list, retrying ({i}/{retries})\n  {e}')
            time.sleep((i+1) ** 3)

    if asset_id_list is None:
        raise Exception('\nUnable to retrieve task list, exiting')

    return asset_id_list


def get_ee_tasks(states=['RUNNING', 'READY'], retries=4):
    """Return current active tasks

    Parameters
    ----------
    states : list, optional
        List of task states to check (the default is ['RUNNING', 'READY']).
    retries : int, optional
        The number of times to retry getting the task list if there is an error.

    Returns
    -------
    dict : task descriptions (key) and full task info dictionary (value)

    """
    logging.debug('\nRequesting Task List')
    task_list = None
    for i in range(retries):
        try:
            # TODO: getTaskList() is deprecated, switch to listOperations()
            task_list = ee.data.getTaskList()
            # task_list = ee.data.listOperations()
            break
        except Exception as e:
            logging.warning(f'  Error getting task list, retrying ({i}/{retries})\n  {e}')
            time.sleep((i+1) ** 3)
    if task_list is None:
        raise Exception('\nUnable to retrieve task list, exiting')

    task_list = sorted(
        [task for task in task_list if task['state'] in states],
        key=lambda t: (t['state'], t['description'], t['id'])
    )

    # Convert the task list to a dictionary with the task name as the key
    return {task['description']: task for task in task_list}


def print_ee_tasks(tasks):
    """Print a summary of the current active tasks

    Parameters
    ----------
    tasks : dict
        Task dictionary generated by utils.get_ee_tasks().

    Returns
    -------
    None

    """
    # TODO: Add a parameter to control the log level
    logging.debug('Active Tasks')
    if tasks:
        logging.debug('  {:8s} {}'.format('STATE', 'DESCRIPTION'))
        logging.debug('  {:8s} {}'.format('=====', '==========='))
    else:
        logging.debug('  None')

    for desc, task in tasks.items():
        if task['state'] == 'RUNNING':
            start_dt = datetime.fromtimestamp(task['start_timestamp_ms'] / 1000, tz=timezone.utc)
            update_dt = datetime.fromtimestamp(task['update_timestamp_ms'] / 1000, tz=timezone.utc)
            logging.debug('  {:8s} {}  {:0.2f}  {}'.format(
                task['state'], task['description'],
                (update_dt - start_dt).total_seconds() / 3600,
                task['id'])
            )
        else:
            logging.debug('  {:8s} {}'.format(task['state'], task['description']))

    logging.debug(f'  Tasks: {len(tasks)}\n')

    return tasks


def ee_task_start(task, n=4):
    """Make an exponential backoff Earth Engine request"""
    for i in range(1, n):
        try:
            task.start()
            break
        except Exception as e:
            logging.info(f'    Resending query ({i}/{n})')
            logging.debug(f'    {e}')
            time.sleep(i ** 3)

    return task


def is_number(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


def millis(input_dt):
    """Convert datetime to milliseconds since epoch

    Parameters
    ----------
    input_dt : datetime

    Returns
    -------
    int

    """
    return 1000 * int(calendar.timegm(input_dt.timetuple()))


def parse_landsat_id(system_index):
    """Return the components of an EE Landsat Collection 1 system:index

    Parameters
    ----------
    system_index : str

    Notes
    -----
    LXSS_PPPRRR_YYYYMMDD
    LC08_030036_20210725

    """
    sensor = system_index[0:4]
    path = int(system_index[5:8])
    row = int(system_index[8:11])
    year = int(system_index[12:16])
    month = int(system_index[16:18])
    day = int(system_index[18:20])

    return sensor, path, row, year, month, day


def parse_int_set(nputstr=""):
    """Return list of numbers given a string of ranges

    http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-of-numbers-in-python.html
    """
    selection = set()
    invalid = set()
    # tokens are comma separated values
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            selection.add(int(i))
        except:
            # if not, then it might be a range
            try:
                token = [int(k.strip()) for k in i.split('-')]
                if len(token) > 1:
                    token.sort()
                    # we have items separated by a dash
                    # try to build a valid range
                    first = token[0]
                    last = token[len(token) - 1]
                    for x in range(first, last + 1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)

    return selection


# These functions support writing WRS2 path/row dictionary collapsed to ranges
def wrs2_set_2_str(tiles):
    """Convert WRS2 tile set to a compact string/dictionary representation"""
    from collections import defaultdict
    tile_dict = defaultdict(list)
    for tile in tiles:
        tile_dict[int(tile[1:4])].append(int(tile[5:8]))
    # CGM - I don't think string of a list is exactly JSON, but it seems to work
    tile_dict = {
        k: '[{}]'.format(list_2_str_ranges(v))
        for k, v in tile_dict.items()
    }
    tile_str = (
        json.dumps(tile_dict, sort_keys=True)
        .replace('"', '').replace(' ', '')
        .replace('{', '').replace('}', '')
    )

    return tile_str


def wrs2_str_2_set(tile_str, wrs2_fmt='p{:03d}r{:03d}'):
    """Convert string/dictionary representation of the WRS tiles to a set"""
    tile_set = set()
    for t in tile_str.replace('[', '').split('],'):
        path = int(t.split(':')[0])
        # CGM - The right bracket will appear in the string sometimes
        rows = str_ranges_2_list(t.split(':')[1].replace(']', ''))
        for row in sorted(rows):
            tile_set.add(wrs2_fmt.format(path, int(row)))

    return tile_set


def str_ranges_2_list(nputstr=""):
    """Return list of numbers given a string of ranges

    http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-of-numbers-in-python.html
    """
    selection = set()
    invalid = set()
    # tokens are comma separated values
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            selection.add(int(i))
        except:
            # if not, then it might be a range
            try:
                token = [int(k.strip()) for k in i.split('-')]
                if len(token) > 1:
                    token.sort()
                    # we have items separated by a dash
                    # try to build a valid range
                    first = token[0]
                    last = token[len(token) - 1]
                    for x in range(first, last + 1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)

    return sorted(list(selection))


def list_2_str_ranges(i):
    """Return range strings given a list of numbers

    Modified from the example here:
    https://stackoverflow.com/questions/4628333/converting-a-list-of-integers-into-range-in-python
    """
    output = []
    for a, b in itertools.groupby(enumerate(sorted(set(i))), lambda pair: pair[1] - pair[0]):
        b = list(b)
        # Only create ranges for 3 or more numbers
        if b[0][1] != b[-1][1] and abs(b[-1][1] - b[0][1]) > 1:
            output.append('{}-{}'.format(b[0][1], b[-1][1]))
        elif b[0][1] != b[-1][1]:
            output.append('{},{}'.format(b[0][1], b[-1][1]))
        else:
            output.append('{}'.format(b[0][1]))

    return ','.join(output)


def ver_str_2_num(version_str):
    """Return a version number string as a list of integers for sorting or comparison

    Parameters
    ----------
    version_str : str

    Returns
    -------
    list of integers

    Notes
    -----
    0.20.6 -> [0, 20, 6]

    """
    return list(map(int, version_str.split('.')))


def constant_image_value(image, crs='EPSG:32613', scale=1):
    """Extract the output value from a "constant" image"""
    rr_params = {
        'reducer': ee.Reducer.first(),
        'geometry': ee.Geometry.Rectangle([0, 0, 10, 10], crs, False),
        'scale': scale,
    }
    return get_info(ee.Image(image).reduceRegion(**rr_params))


def point_image_value(image, xy, scale=1):
    """Extract the output value from an image at a point"""
    rr_params = {
        'reducer': ee.Reducer.first(),
        'geometry': ee.Geometry.Point(xy),
        'scale': scale,
    }
    return get_info(ee.Image(image).reduceRegion(**rr_params))


def point_coll_value(coll, xy, scale=1):
    """Extract the output value from a collection at a point"""
    output = get_info(coll.getRegion(ee.Geometry.Point(xy), scale=scale))
    # Structure output to easily be converted to a Pandas dataframe
    # First key is band name, second key is the date string
    col_dict = {}
    info_dict = {}
    for i, k in enumerate(output[0][4:]):
        col_dict[k] = i + 4
        info_dict[k] = {}

    for row in output[1:]:
        # TODO: Add support for images that don't have a system:time_start
        date = datetime.fromtimestamp(row[3] / 1000.0, tz=timezone.utc).strftime('%Y-%m-%d')
        for k, v in col_dict.items():
            info_dict[k][date] = row[col_dict[k]]

    return info_dict
