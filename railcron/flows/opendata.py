"""
Network Rail Opendata File Fetching

Prefect Flows that fetch ATOC timetables and data from the Rail Incident XML feed
available through the https://opendata.nationalrail.co.uk/ website.
"""
from datetime import datetime
from sys import argv, exc_info
import traceback

from prefect import flow, get_run_logger
from prefect.task_runners import SequentialTaskRunner

from utils.blocks import load_block, update_newfile_block
from utils.files import recompress, exec_rsync, tar_and_compress, unzip_file
from utils.misc import email_message

# Can not use RemoteFileSystem / fsspec to download file due to issues with redirects
# and fsspec expects a standard file system type of logic using file objects things
# e.g https://.../filename.txt

@flow(task_runner=SequentialTaskRunner())
def atoc_timetable():
    """Fetches latest ATOC Timetable *TTF ZIP from https://opendata.nationalrail.co.uk/"""
    logger = get_run_logger()
    opendata = load_block('opendata', 'atoc_timetable')
    try:
        auth_data = opendata.authenticate()
        data = opendata.get_file(auth_data, streaming=True)
        filepath = opendata.archive_atoc(data)
        if opendata.recompress:
            filepath = tar_and_compress(opendata.recompress, filepath, unzip_file(filepath))
        logger.debug(exec_rsync(opendata))
        logger.info(f"Flow atoc_timetable got new file: {filepath}")
        update_newfile_block("atoc", filepath)
    except Exception:
        msg = '<br/>'.join(traceback.format_exception(*exc_info()))
        logger.error(msg)
        email_message(opendata, "Error in Prefect Flow atoc_timetable", msg)


@flow(task_runner=SequentialTaskRunner())
def incidents():
    """Periodically fetches Incidents XML from https://opendata.nationalrail.co.uk/"""
    logger = get_run_logger()
    try:
        opendata = load_block('opendata', 'incidents')
        now = datetime.now()
        thehour = str(now.hour) if now.hour > 9 else "0" + str(now.hour)
        auth_data = opendata.authenticate()
        data = opendata.get_file(auth_data, streaming=False)
        filepath = opendata.archive_incidents(data, thehour)
        if opendata.recompress:
            filepath = recompress(opendata, filepath)
        logger.debug(exec_rsync(opendata))
        logger.info(f"Flow incidents got new file: {filepath}")
        update_newfile_block("incidents", filepath)
    except Exception:
        msg = '<br/>'.join(traceback.format_exception(*exc_info()))
        logger.error(msg)
        email_message(opendata, "Error in Prefect Flow incidents", msg)


if __name__ == "__main__":
    if argv[1] == 'all':
        atoc_timetable()
        incidents()
    else:
        locals()[argv[1]]()
