"""Prefect Block for managing access to NR HDA data"""

import os

from prefect import get_run_logger
from prefect.blocks.core import Block
from pydantic import Field
import requests


class HdaBlock(Block):
    """Block used to fetch Historic Delay Attribution files from Network Rail's website
       https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/

       Attributes:
           baseurl: URL of webpage where HDA files are (constant)
           url: Actual URL to access where XML section of HDA files is (constant)
           params:  HTTP params to send in request (constant)
             restype: container
             comp: list
           archive_path: Where to archive the files
           rsync: Command to execute rsync
    """

    _block_type_name = "NR Historic Delay Attributes Files"
    _description = "Configuration data for getting new HDA files"

    baseurl: str = Field("https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/",
                         const=True)
    url: str = Field("https://sacuksprodnrdigital0001.blob.core.windows.net/historic-delay-attribution", const=True)
    params: dict = Field({ 'restype': 'container', 'comp': 'list'}, const=True)
    archive_path: str = None
    rsync: str = None

    def get_file(self, other_url=None, streaming=False):
        """Downloads XML section of HDA CSVs or the zip file"""
        url = self.url if other_url is None else other_url
        params = self.params if other_url is None else None
        resp = requests.get(url, params=params, stream=streaming)
        if resp.status_code not in (200, 201):
            logger = get_run_logger()
            logger.error(f"Could not download {url}")
            logger.error(resp.status_code)
            logger.error(resp.headers)
            logger.error(resp.text)
            raise Exception(f"Could not download {url}")
        return resp

    def archive_file(self, data, zip_name):
        """Save streamed file to subdirectory based on original path"""
        # dir structure on source is copied
        dirpart = zip_name[0: zip_name.index('/')]
        dirpath = os.path.join(self.archive_path, dirpart)
        os.makedirs(dirpath, mode=0o755, exist_ok=True)
        zipfile = os.path.join(self.archive_path, zip_name)
        with open(zipfile, 'wb') as fd:
            for chunk in data.iter_content(chunk_size=100*1024):
                fd.write(chunk)
        return zipfile
