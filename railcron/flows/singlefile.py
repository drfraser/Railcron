"""
Network Rail Datafeeds File Fetching

Generated Prefect Flows that fetch SMART/TPS/Corpus files as well as schedule
related files from the https://datafeeds.networkrail.co.uk/ntrod/ website.
"""
import os
from sys import argv, exc_info
import traceback

from prefect import flow, get_run_logger
from prefect.blocks.core import Block
from prefect.blocks.system import JSON
from prefect.task_runners import SequentialTaskRunner

from utils.blocks import load_block, update_newfile_block
from utils.files import archive_data_to_file, recompress, exec_rsync, file_changed
from utils.misc import create_flows, email_message, get_current_ymd

# Can not use RemoteFileSystem / fsspec to download file due to issues with redirects
# and fsspec expects a standard file system type of logic using file objects things
# e.g https://.../filename.txt

def flow_generator(fname):
    """Generator of flow functions based on configurations in YAML cfg"""

    def infunc():
        nonlocal fname
        logger = get_run_logger()
        nrdf = load_block('nrdatafeeds', fname)
        try:
            file_hash = None
            if fname.startswith("data_"):
                try:
                    file_hash = Block.load(f"json/{fname}-hash".replace('_','-'))
                except ValueError:
                    file_hash = JSON(value={"last_hash": 0})

            data = nrdf.get_datafeeds_file(streaming=True)
            # for data_* and sched_* blocks, always getting data for today
            year, mon, day = get_current_ymd(yesterday=False)
            filename = day + '.' + nrdf.filetype
            filepath_prefix = nrdf.get_filepath_prefix(year, mon, day)
            filepath = archive_data_to_file(data, filepath_prefix, filename)

            if fname.startswith('data_') and not file_changed(fname, filepath, file_hash):
                logger.info("NOTICE: No change in file, so deleting today's")
                os.unlink(filepath)
                return
            if nrdf.settings.recompress:
                filepath = recompress(nrdf, filepath)
            logger.debug(exec_rsync(nrdf))

            logger.info(f"Flow {fname} got new file: {filepath}")
            update_newfile_block(fname, filepath)
        except Exception:
            msg = '<br/>'.join(traceback.format_exception(*exc_info()))
            logger.error(msg)
            email_message(nrdf, f"Error in Prefect Flow {fname}", msg)

    infunc.__name__ = fname
    return flow(infunc, name=f"{fname}", task_runner=SequentialTaskRunner(),
        description="Fetches single files from https://datafeeds.networkrail.co.uk/ntrod/login")


prefix_flows = create_flows(flow_generator, ['sched_', 'data_'])

if __name__ == "__main__":
    if argv[1] == 'all':
        for k, v in prefix_flows.items():
            print(f"\n\n RUNNING {k}")
            v()
    else:
        prefix_flows[argv[1]]()
