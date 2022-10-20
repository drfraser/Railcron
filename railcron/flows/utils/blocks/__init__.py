import os

from prefect.blocks.core import Block
from prefect.blocks.system import JSON
from prefect.utilities.asyncutils import sync_compatible

from ..misc import load_config
from .hda import HdaBlock
from .opendata import OpendataBlock
from .nrdatafeeds import NrdatafeedsBlock, Nrdfs3Block
from .a51 import A51Block


@sync_compatible
async def update_newfile_block(flow_tag, newfile):
    """Used to record when a new file has been fetched

       When a flow gets a new file, this block can be used to indicate the
       change from previous file -to- newest file.

       A semaphore of sorts (i.e. (oldfile != newfile) == 1)

       Other flows accessing this block can then be triggered (e.g. to process
       the new file). They MUST update the block when done (oldfile->newfile).

       Args:
           flow_tag: The name of the semaphore
           newfile: The new value of it (e.g. the file path)
    """
    lastfile = None
    try:
        lastfile = await Block.load(f"json/{flow_tag}-lastfile".replace('_','-'))
    except ValueError:
        lastfile = JSON(value={"oldfile": "", "newfile": ""})
    lastfile.value["oldfile"] = lastfile.value["newfile"]
    lastfile.value["newfile"] = newfile
    await lastfile.save(name=f"{flow_tag}-lastfile".replace('_','-'), overwrite=True)


@sync_compatible
async def load_block(block_type, block_name):
    """Gets the specified block from storage or dynamically makes one based on the config file

       Args:
           block_type: Class of the block to load
           block_name: Equivalent to master key in cfg file

       Returns: new block for accessing data
    """
    new_block = None
    block_class = globals()[block_type.capitalize() + "Block"]
    try:
        new_block = await block_class.load(block_name)
    except ValueError:
        cfg_path = os.getenv('FETCH_CFG', '.')
        cfg = load_config(f"{cfg_path}/odfetch.yaml", block_name)
        new_block = block_class(**cfg)
    return new_block
