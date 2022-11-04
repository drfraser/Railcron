"""
Network Rail HDA Data Fetching

A Prefect Flow that downloads new HDA related ZIP/CSVs from
https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/
"""
import os
from sys import exc_info
import traceback
import xml.dom.minidom

from prefect import flow, get_run_logger
from prefect.task_runners import SequentialTaskRunner

from utils.blocks import load_block, update_newfile_block
from utils.files import exec_rsync, tar_and_compress, unzip_file
from utils.misc import email_message


# List of new HDA files embedded within a XML chunk in the main HTML page
# So have to parse it and find new files
# thus using RemoteFileSystem not straightforward compared to this function

@flow(name="NR HDA Data", task_runner=SequentialTaskRunner())
def hda_data(debugging=False):
    """Fetches new Historic Delay Attribution CSVs from NR website
       https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/

       List of available files is in a section on the main page
       Gets that section, determines if any entries are new compared to existing list of files
    """
    logger = get_run_logger()
    hda = load_block('hda', 'hda_data')
    try:
        xmldata = hda.get_file()
        thelist = xml.dom.minidom.parseString(xmldata.content)
        all_zips = thelist.getElementsByTagName('Name')
        for x in all_zips: logger.debug(x.firstChild.nodeValue)

        existing_files = []
        if os.path.exists(hda.archive_path):
            filelist = os.walk(hda.archive_path)
            existing_files = [d[0] + '/' + f for d in filelist for f in d[2] if d[2]]
            # originals are .zips so compare to .tar.? files
            existing_files = [
                f.replace(hda.archive_path + '/', "").replace(
                    ".tar" + os.path.splitext(f)[1], ".zip")
                for f in existing_files]
        logger.debug(existing_files)

        zipfile = None
        for hda_node in all_zips:
            zip_name = hda_node.firstChild.nodeValue
            if zip_name not in existing_files:
                logger.info(f"Fetching {zip_name}")
                data = hda.get_file(other_url=hda_node.nextSibling.firstChild.nodeValue, streaming=True)
                zipfile = hda.archive_file(data, zip_name)
                if zipfile.endswith(".zip") and hda.settings.recompress:
                    zipfile = tar_and_compress(hda.settings.recompress, zipfile, unzip_file(zipfile))
            if debugging: break

        if zipfile is not None:
            logger.debug(exec_rsync(hda))
            logger.info(f"Flow hda_data got new file: {zipfile}")
            update_newfile_block("hda_data", zipfile)
    except Exception as err:
        msg = '<br/>'.join(traceback.format_exception(*exc_info()))
        logger.error(msg)
        email_message(hda, "Error in Prefect Flow hda_data", msg)
        raise err


if __name__ == "__main__":
    hda_data(debugging=True)
