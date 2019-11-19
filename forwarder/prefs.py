import os
import sys

from argparse import ArgumentParser
from logging_tool import LoggerFactory
from prefs_loader import Preferences

PREFS_JSON_FILENAME = "forwarder.json"

prefs = None
log_factory = None


def _init():
    global prefs, log_factory
    json_file = "." + os.sep + PREFS_JSON_FILENAME
    parser = ArgumentParser()
    parser.add_argument("-p", "--preferences",
                        dest="preferences", help="JSON Preferences file", type=str)
    args = parser.parse_args()
    if args and args.preferences:
        json_file = args.preferences
    if os.path.exists(json_file) and os.path.isfile(json_file):
        prefs = Preferences(json_file).get_preferences()
        log_factory = LoggerFactory(prefs['logging']['folder'],
                                    prefs['logging']['filename'], prefs['logging']['console_level'],
                                    prefs['logging']['file_level'])
        logger = log_factory.get_new_logger("prefs")
        logger.info("Working with preference logs in {}".format(json_file))
    else:
        if not os.path.exists(json_file):
            print("*** ERROR *** JSON preference file does not exist. Aborting...")
        elif not os.path.isfile(json_file):
            print("*** ERROR *** JSON preference file informed is a folder. Aborting...")
        sys.exit(-1)


_init()
