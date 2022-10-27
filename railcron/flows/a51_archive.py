"""
A51 Archive File Fetching

Generated flows for fetching data from https://cdn.area51.onl/archive/rail/*

A51 Archive flows for getting yesterday's bzip2 files of their
DARWIN/TD/TRUST data. These designed to fetch any new/ungotten files from
yesterday's month because archiving process delayed in zipping up files sometimes.
"""
import asyncio
import os
from sys import argv, exc_info
import traceback

from prefect import flow, get_run_logger
from prefect.task_runners import SequentialTaskRunner

from utils.blocks import load_block, update_newfile_block
from utils.files import archive_data_to_file, async_recompress, exec_rsync
from utils.misc import create_flows, get_current_ymd, email_message

# did not use S3 file system block because it is just a thin wrapper around s3fs
# and did not use s3fs because would only use get_file() and no streaming support
# Did not use s3_download() either because no streaming support

def pass_filter(existing_files, filename, year, mon, day):
    """Filter for checking if current file is already in archive"""
    # can't do this because LastModified of files is the next day or even later
    # if not (x['LastModified'].year == int(yyear) and x['LastModified'].month == int(ymon) and
    #         x['LastModified'].day == int(yday)): continue
    firstpart = os.path.splitext(filename)[0]
    if firstpart.isdigit() and int(firstpart) < 10:
        firstpart = "0" + firstpart
    if firstpart in existing_files:
        return False
    # if day specified, then getting a specific file or set of them
    if day:
        if firstpart.isdigit():
            if int(firstpart) != int(day):
                return False
        else:
            mon2 = str(mon) if int(mon) > 9 else "0" + str(mon)
            day2 = str(day) if int(day) > 9 else "0" + str(day)
            if not firstpart.startswith(f"{year}{mon2}{day2}"):
                return False
    return True


async def process_object(cfg, year, mon, filename):
    """Process S3 object and archive it when it passes filter"""
    firstpart = os.path.splitext(filename)[0]
    data = await cfg.get_https_s3_file(year, mon, filename)
    # force day.tbz2 files to 0-day.tbz2
    if firstpart.isdigit() and int(firstpart) < 10:
        filename = "0" + filename
    filepath_prefix = cfg.get_filepath_prefix(year, mon)
    filepath = archive_data_to_file(data, filepath_prefix, filename)
    # the tbz2 files are optimally compressed
    if os.path.splitext(filename)[1] == ".gz" and cfg.settings.recompress:
        filepath = await async_recompress(cfg, filepath)
    return filepath


def flow_generator(fname):
    """Generator of flow functions based on configurations in YAML cfg"""

    async def infunc(year: int = None, mon: int = None, day: int = None):
        """Fetch file based on A51 Block configuration

           Args:
               year: integer of year part of key (directory)
                     Default of None means yesterday's year
               mon:  integer of month (directory)
                     Default of None means yesterday's month
               day:  integer
                     Default of None means get all files up to yesterday
                     If specified, means get files for that specific day
        """
        nonlocal fname
        logger = get_run_logger()
        a51 = await load_block('a51', fname)
        try:
            if year is None:
                year, mon, _ = get_current_ymd(yesterday=True, strip_zeros=True)
            objects = await a51.list_objects(year=year, mon=mon)
            logger.debug(objects)

            existing_files = []
            fullpath = a51.get_filepath_prefix(year=year, mon=mon)
            if os.path.exists(fullpath):
                existing_files = [os.path.splitext(os.path.basename(f))[0]
                                  for f in os.scandir(fullpath) if f.is_file()]
            logger.debug(existing_files)

            filepath = None
            for obj in objects:
                filename = obj['Key'].replace(os.path.join(a51.key, str(year), str(mon)) + '/',"")
                if not pass_filter(existing_files, filename, year, mon, day):
                    continue
                filepath = await process_object(a51, year, mon, filename)
                logger.info(f"Fetched {obj['Key']}")

            if filepath is None:
                logger.error(f"NOTICE: A51 file for {fname} {year}-{mon} not present, no fetch")
            else:
                logger.debug(exec_rsync(a51))
                logger.info(f"Flow {fname} got new file: {filepath}")
                await update_newfile_block(fname, filepath)
        except Exception:
            msg = '<br/>'.join(traceback.format_exception(*exc_info()))
            logger.error(msg)
            email_message(a51, f"Error in Prefect Flow {fname}", msg)

    infunc.__name__ = fname
    return flow(infunc, name=f"{fname}",
                description="Fetches A51 Archive File from https://cdn.area51.onl/archive/rail/",
                task_runner=SequentialTaskRunner())


prefix_flows = create_flows(flow_generator, ['a51_'])

if __name__ == "__main__":
    if argv[1] == 'all':
        for k, v in prefix_flows.items():
            print(f"\n\n RUNNING {k}")
            asyncio.run(v())
    else:
        # asyncio.run(prefix_flows[argv[1]](year=2022, mon=10))
        asyncio.run(prefix_flows[argv[1]]())
