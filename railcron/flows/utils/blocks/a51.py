"""Prefect Block for fetching files from A51 archives at
   (https/s3)://cdn.area51.onl/archive/rail/*

# possible paths
# PRE corpus/  --- stops in 2020
# PRE darwin/
# PRE rtppm/   ---
# PRE smart/   ---
# PRE td/
# PRE timetable/   ---
# PRE tps/         ---
# PRE trust/  year/mon1/day1.tbz2 or YYYYMMDD*.xml.gz

"""
import asyncio
from functools import partial
import os
from typing_extensions import Literal

from botocore import UNSIGNED
from botocore.config import Config
from prefect import get_run_logger
from prefect.blocks.core import Block
from prefect_aws import AwsCredentials, AwsClientParameters
from prefect_aws.s3 import s3_list_objects
# from pydantic import Field, validator
import requests

from ..misc import get_current_ymd


class A51Block(Block):
    """
    Block used to fetch files from A51's public archives of NR data
    (https/s3)://cdn.area51.onl/archive/rail/(darwin/trust/td)/{year}/{mon}/{filename}

    Can't use regular S3Block because A51 is a public archive
    Also, support added for way archives are indexed

    Attributes:
        region: AWS region to use (constant)
        bucket: cdn.area51.onl (constant)
        key: rest of path past the bucket part, e.g. archives.rail/darwin/year/mon/
        archive_path: Base of path where to store the downloaded files
                      Full path gets extended with "../year/0-month/"
        filetype: Extension of files to get (blank means all)
        rsync: Command to backup the files with
    """

    _block_type_name = "Network Rail - A51 Archives"
    _description = "Block for getting files from A51's NROD archives: https://cdn.area51.onl/archive/rail/(darwin/trust/td)"

    region: Literal["eu-west-1"] = "eu-west-1"
    # data_url: str = "s3://cdn.area51.onl/archive/rail/"
    bucket: Literal["cdn.area51.onl"] = "cdn.area51.onl"
    key: Literal["archive/rail/darwin/","archive/rail/td/","archive/rail/trust/"] = "archive/rail/darwin/"
    archive_path: str
    filetype: str = None
    rsync: str = None

    # Pydantic's validation features not working with Prefect
    # class Config:
    #     validate_assignment = True

    # @validator('key')
    # def validate_s3_key(cls, val):
    #     if val not in ['archive/rail/darwin/','archive/rail/td/','archiverail/trust/']:
    #         raise ValueError('Key must be of the form "archive/rail/(darwin|td|trust)/"')
    #     return val

    def get_filepath_prefix(self, year=None, mon=None, day=None):
        """Defines scheme by which files are organized under the archive_path"""
        if year is None:
            year, mon, _ = get_current_ymd(yesterday=True, strip_zeros=False)
        return os.path.join(self.archive_path, str(year), str(mon))

    async def get_https_s3_file(self, year, mon, fname, streaming=True):
        """Downloads a file from A51 S3 using https"""
        data_url = f"https://{self.bucket}/{self.key}"
        filepath = os.path.join(data_url, str(year), str(mon), fname)
        loop = asyncio.get_event_loop()
        future1 = loop.run_in_executor(None, partial(requests.get, filepath, stream=streaming))
        resp = await future1  # requests.get(filepath, stream=streaming)
        if resp.status_code not in (200, 201):
            logger = get_run_logger()
            logger.error("Failed to get file from A51 archives")
            logger.error(resp.status_code)
            logger.error(resp.headers)
            logger.error(resp.text)
            raise Exception("Failed to get file from A51 archives")
        return resp

    async def list_objects(self, year, mon):
        """Get list of available objects/files from S3 bucket"""
        prefi = os.path.join(self.key, str(year), str(mon))
        # public S3 repositories require no auth info, e.g. --no-sign-request"
        aws_params = AwsClientParameters(config=Config(signature_version=UNSIGNED))
        objects = await s3_list_objects(bucket=self.bucket,
                        aws_credentials=AwsCredentials(),
                        aws_client_parameters=aws_params,
                        prefix=prefi)
        if self.filetype not in (None, ""):
            objects = [o for o in objects if f".{self.filetype}" in o['Key']]
        return objects
