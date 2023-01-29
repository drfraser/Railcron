"""
National Rail Data Portal S3 Based Data File Fetching

Generated Prefect Flows that fetch DARWIN timetable related files as
well as nrdp-v16-logs related files (location, reference, logs)
from NRDP's S3 repositories.
"""
import asyncio
from sys import argv, exc_info, modules
import traceback

from prefect import flow, get_run_logger
from prefect.task_runners import SequentialTaskRunner
from prefect_aws.s3 import s3_download, s3_list_objects

from utils.blocks import load_block, update_newfile_block
from utils.files import archive_data_to_file, async_recompress, async_exec_rsync
from utils.misc import get_current_ymd, create_flows, email_message

# S3 objects in lists
# {'Key': 'darwin_direct/20220727092930_PP.log.gz',
#  'LastModified': datetime.datetime(2022, 7, 27, 8, 30, 2, tzinfo=tzutc()),
#  'ETag': '"127ed5aba74a15ef3e5f0e297af5962c"',
#  'Size': 13240, 'StorageClass': 'STANDARD'},

def flow_generator(fname):
    """Generator of flow functions based on configurations in YAML cfg"""

    async def infunc(year: int = None, mon: int = None, day: int = None):
        nonlocal fname
        logger = get_run_logger()
        nrdf = await load_block('nrdfs3', fname)
        try:
            if year is None:
                year, mon, day = get_current_ymd(yesterday=(nrdf.filter == 'yesterdays'))
            aws_creds = nrdf.get_credentials()
            # deal with any S3 path / prefix requirements
            prefi = nrdf.key
            # If y/m/d not explicitly specified, then flow gets either today's
            # file or yesterday's as determined by the filter set in the Block
            if nrdf.date_in_key:
                # have to worry about subdirectories?
                mons = str(mon) if int(mon) > 9 else "0" + str(int(mon))
                prefi += f"{year}/{year}{mons}/"

            objects = await s3_list_objects(bucket=nrdf.bucket,
                                            aws_credentials=aws_creds,
                                            prefix=prefi)
            logger.debug(objects)

            filepath = None
            for obj in objects:
                if nrdf.filter:
                    to_filter = (not (obj['LastModified'].year == int(year) and
                                      obj['LastModified'].month == int(mon) and
                                      obj['LastModified'].day == int(day)))
                    if to_filter:
                        continue
                filename = obj['Key'].replace(prefi, "")
                if filename == "": continue

                logger.info(f"Getting new file {filename}")
                fdata = await s3_download(bucket=nrdf.bucket, key=obj['Key'],
                                          aws_credentials=aws_creds)
                if int(mon) < 10: mon = "0" + str(int(mon))
                if int(day) < 10: day = "0" + str(int(day))
                # assumption of files do not already exist - check?
                filepath_prefix = nrdf.get_filepath_prefix(year, mon, day)
                filepath = archive_data_to_file(fdata, filepath_prefix, filename,
                                                streaming=False)
                if nrdf.settings.recompress:
                    filepath = await async_recompress(nrdf, filepath)

            if filepath is not None:
                output = await async_exec_rsync(nrdf)
                if output: logger.debug(output)
                logger.info(f"Flow {fname} got new file: {filepath}")
                await update_newfile_block(fname, filepath)
        except Exception as err:
            msg = '<br/>'.join(traceback.format_exception(*exc_info()))
            logger.error(msg)
            email_message(nrdf, f"Error in Prefect Flow {fname}", msg)
            raise err

    infunc.__name__ = fname
    return flow(infunc, name=f"{fname}",
                description="Fetches data from NRDP S3 repositories",
                task_runner=SequentialTaskRunner())


prefix_flows = create_flows(flow_generator, ['nrdp_'])
for k, v in prefix_flows.items(): setattr(modules[__name__], k, v)

if __name__ == "__main__":
    if argv[1] == 'all':
        for k, v in prefix_flows.items():
            # testing nrdp_logs involves many files
            # if 'logs' in k: continue
            print(f"\n\n RUNNING {k}")
            asyncio.run(v())
    else:
        # asyncio.run(prefix_flows[argv[1]](year=2022, mon=10, day=16))
        asyncio.run(prefix_flows[argv[1]]())
