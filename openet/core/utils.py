import argparse
import calendar
from datetime import datetime, timedelta
import itertools
import json
import logging
import os
import time

import ee


def arg_valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to check the format of dates entered as command
      line arguments.
    DEADBEEF - It would probably make more sense to have this function
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
        # return file_path
    else:
        raise argparse.ArgumentTypeError(f'{file_path} does not exist')


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

    # Extra operations are needed since update() does not set milliseconds to 0.
    # return ee.Date(date.update(hour=0, minute=0, second=0).millis()\
    #     .divide(1000).floor().multiply(1000))


def date_range(start_dt, end_dt, days=1, skip_leap_days=False):
    """Generate dates within a range (inclusive)

    Parameters
    ----------
    start_dt : datetime
        start date.
    end_dt : datetime
        end date.
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


def delay_task(delay_time=0, max_ready=-1):
    """Delay script execution based on number of RUNNING and READY tasks

    Parameters
    ----------
    delay_time : float, int
        Delay time in seconds between starting export tasks or checking the
        number of queued tasks if "max_ready" is > 0.  The default is 0.
        The delay time will be set to a minimum of 10 seconds if max_ready > 0.
    max_ready : int, optional
        Maximum number of queued "READY" tasks.  The default is -1 which
        implies no limit to the number of tasks that will be submitted.

    Returns
    -------
    None

    """
    # Force delay time to be a positive value
    # (since parameter used to support negative values)
    if delay_time < 0:
        delay_time = abs(delay_time)

    logging.debug(f'  Pausing {delay_time} seconds')

    if max_ready <= 0:
        time.sleep(delay_time)
    elif max_ready > 0:
        # Don't continue to the next export until the number of READY tasks
        # is greater than or equal to "max_ready"

        # Force delay_time to be at least 10 seconds if max_ready is set
        #   to avoid excessive EE calls
        delay_time = max(delay_time, 10)

        # Make an initial pause before checking tasks lists to allow
        #   for previous export to start up.
        time.sleep(delay_time)

        while True:
            ready_tasks = get_ee_tasks(states=['READY'], verbose=True)
            ready_task_count = len(ready_tasks.keys())
            # logging.debug('  Ready tasks: {}'.format(
            #     ', '.join(sorted(ready_tasks.keys()))))

            if ready_task_count >= max_ready:
                logging.debug('  {} tasks queued, waiting {} seconds to start '
                              'more tasks'.format(ready_task_count, delay_time))
                time.sleep(delay_time)
            else:
                logging.debug('  Continuing iteration')
                break


def get_ee_assets(asset_id, start_dt=None, end_dt=None, retries=6):
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
    params = {'parent': asset_id}

    # TODO: Add support or handling for case when only start or end is set
    if start_dt and end_dt:
        params['startTime'] = start_dt.isoformat() + '.000000000Z'
        params['endTime'] = end_dt.isoformat() + '.000000000Z'

    asset_id_list = None
    for i in range(retries):
        try:
            asset_id_list = [x['id'] for x in ee.data.listImages(params)['images']]
            break
        except ValueError:
            raise Exception('\nThe collection or folder does not exist, exiting')
        except Exception as e:
            logging.warning(
                f'  Error getting asset list, retrying ({i}/{retries})\n  {e}'
            )
            time.sleep((i+1) ** 2)

    if asset_id_list is None:
        raise Exception('\nUnable to retrieve task list, exiting')

    return asset_id_list


def get_ee_tasks(states=['RUNNING', 'READY'], verbose=False, retries=6):
    """Return current active tasks

    Parameters
    ----------
    states : list, optional
        List of task states to check (the default is ['RUNNING', 'READY']).
    verbose : bool, optional
        This parameter is deprecated and is no longer being used.
        To get verbose logging of the active tasks use utils.print_ee_tasks().
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
            logging.warning(
                f'  Error getting task list, retrying ({i}/{retries})\n  {e}'
            )
            time.sleep((i+1) ** 2)
    if task_list is None:
        raise Exception('\nUnable to retrieve task list, exiting')

    task_list = sorted(
        [task for task in task_list if task['state'] in states],
        key=lambda t: (t['state'], t['description'], t['id'])
    )
    # task_list = sorted([
    #     [t['state'], t['description'], t['id']] for t in task_list
    #     if t['state'] in states
    # ])

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
            start_dt = datetime.utcfromtimestamp(task['start_timestamp_ms'] / 1000)
            update_dt = datetime.utcfromtimestamp(task['update_timestamp_ms'] / 1000)
            logging.debug('  {:8s} {}  {:0.2f}  {}'.format(
                task['state'], task['description'],
                (update_dt - start_dt).total_seconds() / 3600,
                task['id'])
            )
        # elif task['state'] in states:
        else:
            logging.debug('  {:8s} {}'.format(task['state'], task['description']))

    logging.debug(f'  Tasks: {len(tasks)}\n')

    return tasks


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


# def getinfo(ee_obj, n=4):
#     """Make an exponential back off getInfo call on an Earth Engine object"""
#     output = None
#     for i in range(1, n):
#         try:
#             output = ee_obj.getInfo()
#         except ee.ee_exception.EEException as e:
#             if 'Earth Engine memory capacity exceeded' in str(e):
#                 logging.info('    Resending query ({}/10)'.format(i))
#                 logging.debug('    {}'.format(e))
#                 time.sleep(i ** 2)
#             else:
#                 raise e
#
#         if output:
#             break
#
#     return output


def ee_task_start(task, n=6):
    """Make an exponential backoff Earth Engine request"""
    for i in range(1, n):
        try:
            task.start()
            break
        except Exception as e:
            logging.info('    Resending query ({}/{})'.format(i, n))
            logging.debug('    {}'.format(e))
            time.sleep(i ** 2)
        # except ee.ee_exception.EEException as e:
        #     if ('Earth Engine memory capacity exceeded' in str(e) or
        #             'Earth Engine capacity exceeded' in str(e)):
        #         logging.info('    Resending query ({}/10)'.format(i))
        #         logging.debug('    {}'.format(e))
        #         time.sleep(i ** 2)
        #     else:
        #         raise e

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
    input_df : datetime

    Returns
    -------
    int

    """
    return 1000 * int(calendar.timegm(input_dt.timetuple()))


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
    # Report invalid tokens before returning valid selection
    # print "Invalid set: " + str(invalid)

    return selection


# def wrs2_list_2_str(tiles):
#     """Compact string representation of the WRS2 tile list"""
#     from collections import defaultdict
#     tile_dict = defaultdict(list)
#     for tile in tiles:
#         tile_dict[int(tile[1:4])].append(int(tile[5:8]))
#     tile_dict = {k: sorted(v) for k, v in tile_dict.items()}
#     return json.dumps(tile_dict, sort_keys=True) \
#         .replace('"', '').replace(' ', '')\
#         .replace('{', '').replace('}', '')
#
#
# def wrs2_str_2_list(tile_str):
#     tile_set = set()
#     for t in tile_str.replace('[', '').split('],'):
#         path = int(t.split(':')[0])
#         for row in t.split(':')[1].replace(']', '').split(','):
#             tile_set.add('p{:03d}r{:03d}'.format(path, int(row)))
#     return sorted(list(tile_set))


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
        for k, v in tile_dict.items()}
    # tile_dict = {k: sorted(v) for k, v in tile_dict.items()}
    tile_str = json.dumps(tile_dict, sort_keys=True) \
        .replace('"', '').replace(' ', '') \
        .replace('{', '').replace('}', '')

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


# Should these be test fixtures instead?
# I'm not sure how to make them fixtures and allow input parameters
def constant_image_value(image, crs='EPSG:32613', scale=1):
    """Extract the output value from a calculation done with constant images"""
    rr_params = {
        'reducer': ee.Reducer.first(),
        'geometry': ee.Geometry.Rectangle([0, 0, 10, 10], crs, False),
        'scale': scale,
    }
    return get_info(ee.Image(image).reduceRegion(**rr_params))


def point_image_value(image, xy, scale=1):
    """Extract the output value from a calculation at a point"""
    rr_params = {
        'reducer': ee.Reducer.first(),
        'geometry': ee.Geometry.Point(xy),
        'scale': scale,
    }
    return get_info(ee.Image(image).reduceRegion(**rr_params))


def point_coll_value(coll, xy, scale=1):
    """Extract the output value from a calculation at a point"""
    output = get_info(coll.getRegion(ee.Geometry.Point(xy), scale=scale))

    # Structure output to easily be converted to a Pandas dataframe
    # First key is band name, second key is the date string
    col_dict = {}
    info_dict = {}
    for i, k in enumerate(output[0][4:]):
        col_dict[k] = i + 4
        info_dict[k] = {}
    for row in output[1:]:
        date = datetime.utcfromtimestamp(row[3] / 1000.0).strftime('%Y-%m-%d')
        for k, v in col_dict.items():
            info_dict[k][date] = row[col_dict[k]]

    return info_dict
    # return pd.DataFrame.from_dict(info_dict)
