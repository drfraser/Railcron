"""Prefect Blocks for managing access to Network Rail Datafeeds services"""
import os
from typing_extensions import Literal

from prefect import get_run_logger
from prefect.blocks.core import Block
from prefect_aws import AwsCredentials
from pydantic import Field, SecretStr
import requests

from ..misc import get_current_ymd, get_day_of_week


class NrdatafeedsBlock(Block):
    """Block used to store configuration for getting files from NR Datafeeds

       Accounts can be managed through https://datafeeds.networkrail.co.uk/ntrod/login

       Attributes:
           username: Username for logging into https://datafeeds.networkrail.co.uk/ntrod/login
           password: Password
           data_url: URL from which to get the file
           params: Dictionary of params to send with request
           archive_path: Path where to store saved files
           filetype: Extension of files to get
           rsync: Command to use to backup files
    """

    _block_type_name = "Network Rail Datafeeds Files"
    _description = "Block for getting Network Rail files (SMART, TPS, schedules) from https://datafeeds.networkrail.co.uk/"

    username: str
    password: SecretStr
    data_url: str
    params: dict
    archive_path: str
    filetype: str
    rsync: str = None

    def get_filepath_prefix(self, year=None, mon=None, day=None):
        """Defines scheme by which files are organized under the archive_path"""
        if year is None:
            year, mon, _ = get_current_ymd(yesterday=False, strip_zeros=False)
        return os.path.join(self.archive_path, str(year), str(mon))

    def get_datafeeds_file(self, streaming=False):
        """Downloads a file from NR Datafeeds site"""
        # deal with day related variables in filename
        the_day = get_day_of_week(yesterday=True)
        if 'day' in self.params:
            self.params['day'] = self.params['day'].replace("{theday}", the_day)
        resp = requests.get(self.data_url,
                         params=self.params,
                         auth=(self.username, self.password.get_secret_value()),
                         stream=streaming)
        if resp.status_code not in (200, 201):
            logger = get_run_logger()
            logger.error("Failed to get file from NR Datafeeds")
            logger.error(resp.status_code)
            logger.error(resp.headers)
            logger.error(resp.text)
            raise Exception("Failed to get file from NR Datafeeds")
        return resp



class Nrdfs3Block(Block):
    """Block for accessing NR Datafeeds S3 based services

       Do not want to use individual saved AwsCredentials Blocks as
       parts of these blocks because they generally are not reused

       Attributes:
           aws_access_key_id: AWS configuration info
           aws_secret_access_key:
           region_name:
           # data_url:  s3://bucket/key/extensions
           bucket: Name of S3 bucket
           key: Constant static part of key
           date_in_key: Boolean to indicate if /{year}/{year}{mon}/ part of full key
           archive_path: Filesystem path where to store files
           filetype: Extension of files to download
           filter: Name of filter to use when downloading files
           rsync: Command to use to backup files
    """

    _block_type_name = "NR Datafeeds (S3 based)"
    _description = "Block for getting Network Rail's S3 based files (DARWIN logs, Location data)"

    aws_access_key_id: str
    aws_secret_access_key: SecretStr
    region_name: str
    # data_url: s3://nrdp-v16-logs/logs/{yyear}/{yyear}{ymon}/
    bucket: str
    key: str # = Field(None, regex=".*/$")
    date_in_key: bool    # true only for logs
    archive_path: str
    filetype: str
    filter: Literal["todays", "yesterdays"] = None
    rsync: str = None

    def get_filepath_prefix(self, year=None, mon=None, day=None):
        """Defines scheme by which files are organized under the archive_path"""
        return os.path.join(self.archive_path, str(year), str(mon), str(day))

    def get_credentials(self):
        """Creates an AwsCredentials out of AWS information"""
        return AwsCredentials(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name
        )
