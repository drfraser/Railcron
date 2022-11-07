"""Prefect Block for managing generic Railcron settings"""

from typing import Optional   #, TypedDict
from typing_extensions import Literal  #, TypedDict

from prefect.blocks.core import Block
# from prefect.blocks.system import JSON
# from pydantic import SecretStr


# Using this to deal with Pydantic/Prefect UI issues would be too fine-grained
# and clunky from a user POV (too many screens to deal with)
# class EmailInfoBlock(Block):
#     _block_type_name = "Railcron Email Settings"
#     _description = "Block for managing Railcron's email functionality"
#
#     MAIL_FROM: Optional[str]
#     MAIL_TO: Optional[str]
#     MAIL_CC: Optional[str]
#     MAIL_BCC: Optional[str]
#     MAIL_LOGIN: Optional[str]
#     MAIL_PWD: Optional[str] = None  # issue if SecretStr - not useful really either
#     MAIL_SRV: Optional[str]
#     MAIL_TYPE: Literal['SSL','STARTTLS','INSECURE'] = None
#     MAIL_PORT: Optional[int]


class RailcronBlock(Block):
    """Block used to store Railcron generic settings

       Attributes:
           recompress:   If original data is to be recompressed, e.g. zip or gzip to xz
                         Blank to disable, otherwise name of compression utility
                         Maximum compression by default
                         Only xz, gzip, bzip2, zstd supported

           BACKUP_HOST:  Used in rsync command to backup files
           BACKUP_ROOT:  Set these to blank to disable rsync

           MAIL_FROM:     Set this as blank to disable flow related emails
           MAIL_TO:       If localhost mail server used, e.g. ssmtp or msmtp
           MAIL_CC:       Then it must be configured to utilize 'mail' cmd
           MAIL_BCC:      cc and bcc are optional

           MAIL_LOGIN:    These to send mail thru a server (not sendmail)
           MAIL_PWD:      Set all to blank to disable
           MAIL_SRV:      All these settings must be defined otherwise
           MAIL_TYPE:     Prefect's SSL, STARTTLS, or INSECURE
           MAIL_PORT:     465, 25, 587, 993...
    """

    _block_type_name = "Railcron Generic Settings"
    _description = "Block for managing Railcron's email, rsync, and compression functionality"

    recompress: Literal['bzip2', 'gzip', 'xz', 'zstd'] = None
    BACKUP_HOST: Optional[str]
    BACKUP_ROOT: Optional[str]
    MAIL_FROM: Optional[str]
    MAIL_TO: Optional[str]
    MAIL_CC: Optional[str]
    MAIL_BCC: Optional[str]
    MAIL_LOGIN: Optional[str]
    MAIL_PWD: Optional[str]
    MAIL_SRV: Optional[str]
    MAIL_TYPE: Literal['SSL','STARTTLS','INSECURE'] = None
    MAIL_PORT: Optional[int]

    #   too many screens in Prefect UI
    # email: EmailInfoBlock
    #   Issues with Prefect UI - freeform entry of keys, no way to set intial value?
    # email: dict
    #   Schema problems, EmailSettings needs to be a block?
    # email: TypedDict('EmailSettings',
    #   MAIL_FROM=str,
    #   MAIL_TO=str,
    #   MAIL_CC=str,
    #   MAIL_BCC=str,
    #   MAIL_LOGIN=str,
    #   MAIL_PWD=str,
    #   MAIL_SRV=str,
    #   MAIL_TYPE=Literal['SSL','STARTTLS','INSECURE'],
    #   MAIL_PORT=int)
