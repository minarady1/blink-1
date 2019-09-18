from collections import namedtuple
import json
import os
import sys

from halo import Halo

BLINK_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_NAME = 'config.json'

def get_blink_base_path():
    return BLINK_BASE_PATH

def load_config():
    # load config.json, and convert a resulting dict to a namedtuple
    # so that we can access config parameters as attributes, like
    # config.anchors instead of config['anchors'].
    spinner = Halo(text='Loading config')
    spinner.start()

    config_path = os.path.join(get_blink_base_path(), CONFIG_FILE_NAME)

    try:
        with open(config_path) as f:
            config = json.load(
                f,
                object_hook = (
                    lambda d: namedtuple('Config', d.keys())(*d.values())
                )
            )
    except IOError:
        spinner.fail()
        msg = (
            'Cannot load the config file.\n' +
            'Confirm that {} exists and is readable.'.format(config_path)
        )
        sys.exit(msg)

    spinner.succeed('Config is loaded')
    return config
