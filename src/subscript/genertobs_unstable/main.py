"""Main function of genertobs"""

import logging
import argparse
from subscript.genertobs_unstable.parse_config import read_yaml_config


def parse_args():
    """Parse args for genertobs"""
    info_string = "Generates all neccessary files for using observations in ert"
    parser = argparse.ArgumentParser(description=info_string)
    parser.add_argument("config_file", help="path to config file", type=str)
    parser.add_argument("output_folder", help="path to all neccessary files", type=str)
    parser.add_argument("--d", help="debug mode", action="store_true")
    return parser.parse_args()


def main():
    """Run the whole shebang"""
    logger = logging.getLogger(__name__ + ".main")
    args = parse_args()
    config = read_yaml_config(args.conf_file)
    logger.debug(config)


if __name__ == "__main__":
    main()
