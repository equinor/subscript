"""Main function of genertobs"""

import logging
import argparse
from pathlib import Path
from subscript.genertobs_unstable.parse_config import (
    read_yaml_config,
    generate_data_from_config,
)
from subscript.genertobs_unstable._writers import (
    write_dict_to_ertobs,
    export_with_dataio,
)


def parse_args():
    """Parse args for genertobs"""
    info_string = "Generates all neccessary files for using observations in ert"
    parser = argparse.ArgumentParser(description=info_string)
    parser.add_argument("config_file", help="path to config file", type=str)
    parser.add_argument("output_folder", help="path to all neccessary files", type=str)
    parser.add_argument(
        "master_config",
        help="Path to file with master metadata (usually contained in the fmu config file)",
        type=str,
    )
    parser.add_argument("--d", help="debug mode", action="store_true")
    return parser.parse_args()


def run(config_path: str, output_folder: str, global_variables):
    """Generate data from config file

    Args:
        config_path (str): path to genertobs file
        output_folder (str): path to where all results will be stored
    """
    logger = logging.getLogger(__name__ + ".run")
    config = read_yaml_config(config_path, validate=True)
    logger.debug("Read config: %s", config)
    data = generate_data_from_config(config, Path(config_path).parent)
    logger.debug("Data generated %s", data)
    write_dict_to_ertobs(data, Path(output_folder))
    global_variables = read_yaml_config(global_variables)
    export_folder = Path(output_folder) / "sumo"
    logger.debug("Exporting observations ready for sumo to %s", str(export_folder))
    export_with_dataio(data, global_variables, export_folder)


def main():
    """Run the whole shebang"""
    logger = logging.getLogger(__name__ + ".main")
    args = parse_args()
    logger.debug("Read args")
    run(args.config_file, args.output_folder, args.global_variables)


if __name__ == "__main__":
    main()
