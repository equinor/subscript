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
    generate_preprocessed_hook,
)


def parse_args():
    """Parse args for genertobs"""
    info_string = "Generates all neccessary files for using observations in ert"
    parser = argparse.ArgumentParser(description=info_string)
    parser.add_argument("config_file", help="path to config file", type=str)
    parser.add_argument(
        "output_folder", help="path to write all result files", type=str
    )
    parser.add_argument(
        "master_config_file",
        help="Path to file with master metadata (usually contained in the fmu config file)",
        type=str,
    )
    parser.add_argument("--d", help="debug mode", action="store_true")
    return parser.parse_args()


def run(config_path: str, output_folder: str, master_config_file):
    """Generate data from config file

    Args:
        config_path (str): path to genertobs file
        output_folder (str): path to where all results will be stored
    """
    logger = logging.getLogger(__name__ + ".run")
    output_folder = Path(output_folder).resolve()
    config = read_yaml_config(config_path, validate=True)
    logger.debug("Read config: %s", config)
    data = generate_data_from_config(config, Path(config_path).parent)
    logger.debug("Data generated %s", data)
    write_dict_to_ertobs(data, Path(output_folder))
    master_config = read_yaml_config(master_config_file)
    export_folder = Path(output_folder)
    logger.info("Exporting observations ready for sumo to %s", str(export_folder))
    export_path = export_with_dataio(data, master_config, export_folder)
    logger.info(export_path)
    generate_preprocessed_hook(export_path, output_folder)


def main():
    """Run the whole shebang"""
    logger = logging.getLogger(__name__ + ".main")
    args = parse_args()
    if args.d:
        logging.basicConfig(level=logging.DEBUG)
    logger.debug("Have read args %s", args)
    run(args.config_file, args.output_folder, args.master_config_file)


if __name__ == "__main__":
    main()
