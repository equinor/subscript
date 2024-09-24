"""Main function of genertobs"""

import argparse
import logging
from pathlib import Path

from subscript.genertobs_unstable._writers import write_dict_to_ertobs
from subscript.genertobs_unstable.parse_config import (
    generate_data_from_config,
    read_yaml_config,
)


def parse_args():
    """Parse args for genertobs"""
    info_string = "Generates all neccessary files for using observations in ert"
    parser = argparse.ArgumentParser(description=info_string)
    parser.add_argument(
        "config_file",
        help="path to config file, name of this file will be name of generated folder",
        type=str,
    )
    parser.add_argument("--d", help="debug mode", action="store_true")
    return parser.parse_args()


def run(config_path: Path):
    """Generate data from config file

    Args:
        config_path (str): path to genertobs file
        output_folder (str): path to where all results will be stored
    """
    logger = logging.getLogger(__name__ + ".run")
    logger.info("Here is config path %s", config_path)
    config = read_yaml_config(config_path)
    logger.debug("Read config: %s", config)
    config_path = Path(config_path)
    export_folder = (config_path.parent / f"{config_path.stem}_do_not_edit").resolve()

    data = generate_data_from_config(config, config_path.parent)
    logger.debug("Data generated %s", data)
    write_dict_to_ertobs(data, export_folder)
    logger.info("Exported all ert obs results to folder %s", str(export_folder))

    return export_folder


def main():
    """Run the whole shebang"""
    logger = logging.getLogger(__name__ + ".main")
    args = parse_args()
    level = logging.DEBUG if args.d else logging.WARNING
    logging.basicConfig(level=level)
    logger.debug("Have read args %s", args)
    run(args.config_file)


if __name__ == "__main__":
    main()
