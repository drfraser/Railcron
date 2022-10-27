"""Prefect Block for managing access to National Rail Opendata services"""

import gzip
import json
import os
from typing_extensions import Literal

from prefect import get_run_logger
from prefect.blocks.core import Block
from pydantic import Field, SecretStr
import requests

from ..misc import get_current_ymd


class OpendataBlock(Block):
    """Block used to fetch files from National Rail's Opendata service
       Accounts can be managed through https://opendata.nationalrail.co.uk/

       Attributes:
           username: Username for logging into https://opendata.nationalrail.co.uk/
           password: Password
           auth_url: URL used to fetch an authentication token (constant)
           data_url: URL to use to fetch data file - based on service being accessed
           archive_path: Where to save file to the file system
           rsync: Optional command to invoke rsync to backup files
           filetype: Extension of the fetched file
    """

    _block_type_name = "National Rail OD Files"
    _description = "Block for getting National Rail Open Data files from https://opendata.nationalrail.co.uk/"

    username: str
    password: SecretStr
    auth_url: Literal["https://opendata.nationalrail.co.uk/authenticate"] = "https://opendata.nationalrail.co.uk/authenticate"
    data_url: str
    archive_path: str
    filetype: str
    rsync: str = None

    # no get_filepath_prefix() defined because of need to do specific things when saving a file

    def authenticate(self):
        """Logs into NR Opendata site and gets a token"""
        resp = requests.post(self.auth_url,
                             headers={ "Content-Type": "application/x-www-form-urlencoded" },
                             data=f"username={self.username}&password={self.password.get_secret_value()}")
        if resp.status_code not in (200, 201):
            logger = get_run_logger()
            logger.error("Could not authenticate with NR Opendata")
            logger.error(resp.status_code)
            logger.error(resp.headers)
            logger.error(resp.text)
            raise Exception("Could not authenticate with NR Opendata")
        return json.loads(resp.text)

    def get_file(self, auth_data, streaming=False):
        """Downloads a file from NR Opendata site"""
        headers = {
           "Content-Type": "application/json",
           "X-Auth-Token": auth_data['token']
        }
        resp = requests.get(self.data_url, headers=headers, data="", stream=streaming)
        if resp.status_code not in (200, 201):
            logger = get_run_logger()
            logger.error("Failed to get file from NR Opendata")
            logger.error(resp.status_code)
            logger.error(resp.headers)
            logger.error(resp.text)
            raise Exception("Failed to get file from NR Opendata")
        return resp

    def archive_atoc(self, data):
        """Archives the ATOC ZIP file received from NR Opendata"""
        cyear, cmon, _ = get_current_ymd()
        os.makedirs(os.path.join(self.archive_path, cyear, cmon), mode=0o755, exist_ok=True)
        # get name of PKZIP file from headers - if it exists already, do not save it
        filename = data.headers['Content-Disposition'].split('"')[1]   # get the RJTTF*.ZIP part
        filepath = os.path.join(self.archive_path, cyear, cmon, filename)
        if not os.path.isfile(filepath):
            with open(filepath, 'wb') as fd:
                for chunk in data.iter_content(chunk_size=100*1024):
                    fd.write(chunk)
        return filepath

    def archive_incidents(self, data, thehour):
        """Archives the gzipped XML file received from the NR Incidents stream

           Note: the filename template is {thehour}.incidents.gz
        """
        cyear, cmon, cday = get_current_ymd()
        os.makedirs(os.path.join(self.archive_path, cyear, cmon, cday), mode=0o755, exist_ok=True)
        filepath = os.path.join(self.archive_path, cyear, cmon, cday,
                                f"{thehour}.incidents." + self.filetype)
        with gzip.open(filepath, 'wt', encoding='utf8') as fd:
            fd.write(data.text)
        return filepath
