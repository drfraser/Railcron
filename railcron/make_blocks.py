"""
Script to read the configured railcron.yml file and create Prefect Blocks
that can be configured through the UI

Config data always read from the configuration file, not Prefect storage
Therefore existing blocks in storage will be overwritten
"""
import os
import yaml
import pdb

from flows.utils.blocks import *
from flows.utils.misc import load_config


# dynamically generate from utils.block introspection?
block_classes = {
    'hda': 'hda',
    'nrdp': 'nrdfs3',
    'atoc': 'opendata',
    'incidents': 'opendata',
    'sched': 'nrdatafeeds',
    'data': 'nrdatafeeds',
    'a51': 'a51',
    'settings': 'railcron'
}

if __name__ == "__main__":
    config_file = os.getenv('RAILCRON_CFG', '.') + "/railcron.yml"
    with open(config_file, mode="rb") as file:
        config_data = yaml.safe_load(file)
    # for each set of config data
    for block_name in config_data.keys():
        if block_name in ("opendata", "nrdatafeeds"):
            continue
        print(f"Processing {block_name}")
        prefix = block_name.split('_')
        block_type = block_classes[prefix[0]]
        block_class = globals()[block_type.capitalize() + "Block"]
        # this ensures variable substitution etc
        cfg = load_config(config_file, block_name)
        new_block = block_class(**cfg)
        new_block.register_type_and_schema()
        new_block.save(block_name.replace('_', '-'), overwrite=True)
