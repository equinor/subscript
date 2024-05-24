"""Upload observations to sumo"""

import logging
from pathlib import Path, PosixPath
import argparse
from typing import Union, List
import yaml
from fmu.dataio import ExportData
from fmu.sumo.uploader import SumoConnection
from fmu.sumo.uploader._sumofile import SumoFile
from fmu.sumo.uploader._fileonjob import FileOnJob
from fmu.sumo.uploader._upload_files import upload_files
import pyarrow as pa
import pyarrow.feather as pf
import pyarrow.parquet as pq


def yaml_load(file_name: Union[str, PosixPath]) -> dict:
    """Load yaml config file into dict

    Args:
        file_name (str): name of yaml file

    Returns:
        dict: the read results
    """
    logger = logging.getLogger(__file__ + ".yaml_load")
    config = {}
    try:
        with open(file_name, "r", encoding="utf-8") as yam:
            config = yaml.safe_load(yam)
    except OSError:
        logger.warning("Cannot open file, will return empty dict")
    return config


def generate_metadata(obj: Union[str, PosixPath], case_path: str) -> dict:
    """Generate full metadata from preprocessed files

    Args:
        obj (Object): table object
        case_path (str): path to ert case

    Returns:
        dict: the metadata
    """
    logger = logging.getLogger(__name__ + ".generate_metadata")
    if not obj.is_file():
        raise TypeError(f"Expecting file, but what is passed is {type(obj)}")
    config = {"model": {"name": "ff", "revision": "undefined"}}
    exd = ExportData(config=config, casepath=case_path, fmu_context="case")
    metadata = exd.generate_metadata(obj)
    logger.debug("Generated metadata: %s", metadata)
    return metadata


def table_to_bytes(table: Union[str, PosixPath]):
    """Return table as bytestring

    Args:
        table_file (str): the file containing table to convert
    Returns:
        bytes: table as bytestring
    """
    logger = logging.getLogger(__name__ + ".tablefile_to_bytes")
    sink = pa.BufferOutputStream()
    logger.debug("Writing %s to sink", table)
    pq.write_table(table, sink)
    byte_string = sink.getvalue().to_pybytes()
    logger.debug("Returning bytestring with size %s", len(byte_string))
    return byte_string


def table_2_bytestring(table: Union[str, PosixPath]) -> bytes:
    """Convert pa.table to bytestring

    Args:
        table_file (str): the file containing table to convert

    Returns:
        bytest: the bytes string
    """
    bytestring = table_to_bytes(table)
    return bytestring


def make_sumo_file(file_path: Union[str, PosixPath], case_path: str) -> SumoFile:
    """Make SumoFile for given file containing object

    Args:
        file_path (Union[str, PosixPath]): path to given file
        config_path (Union[str, PosixPath]): path to config file
        case_path (str): path to given ert case

    Returns:
        SumoFile: File containing blob and metadata ready for shipping
    """
    logger = logging.getLogger(__name__ + ".make_sumo_file")
    logger.debug("Making sumo file with %s", file_path)
    metadata = generate_metadata(file_path, case_path)
    logger.debug("Metadata generated")
    bytestring = table_to_bytes(pf.read_table(file_path))
    logger.debug("Bytestring created")

    sumo_file = FileOnJob(bytestring, metadata)
    sumo_file.path = metadata["file"]["relative_path"]
    sumo_file.metadata_path = ""
    return sumo_file


def prepare_sumo_files(
    preprocessed_folder: Union[str, PosixPath],
    case_path: str,
):
    """Prepare all preprocessed files as list of SumoFiles

    Args:
        preprocessed_folder (Union[str, PosixPath]): path to folder for preprocessed data
        case_path (str): path to given ert case

    Returns:
        list: list of SumoFiles
    """
    logger = logging.getLogger(__name__ + ".prepare_sumo_files")
    sumo_files = []
    preprocessed_folder = Path(preprocessed_folder)
    table_files = preprocessed_folder.glob(r"**/*.arrow")
    for table_file in table_files:
        logger.debug("File %s", table_file)
        if table_file.name.startswith("."):
            continue
        sumo_files.append(make_sumo_file(table_file, case_path))
    logger.debug("Prepared %s files", len(sumo_files))
    return sumo_files


def sumo_upload(files: List[SumoFile], parent_id: str, env: str = "prod"):
    """Upload files to sumo

    Args:
        files (list): should contain only SumoFile objects
        parent_id (str): uuid of parent object
        connection (str): client to upload with
    """
    logger = logging.getLogger(__name__ + ".nodisk_upload")
    logger.info("%s files to upload", len(files))
    logger.debug("Uploading to parent %s", parent_id)
    if len(files) > 0:
        connection = SumoConnection(env=env)
        status = upload_files(files, parent_id, connection)
        print("Status after upload: ", end="\n--------------\n")
        for state, obj_status in status.items():
            print(f"{state}: {len(obj_status)}")
    else:
        logger.info("No passed files, nothing to do here")


def get_case_meta(case_path: Union[str, PosixPath]) -> dict:
    """Get case metadata

    Args:
        case_path (Union[str, PosixPath]): path to case

    Returns:
        dict: the case metadata dictionary
    """
    logger = logging.getLogger(__name__ + ".get_case_meta")
    case_meta_path = Path(case_path) / "share/metadata/fmu_case.yml"
    logger.debug("Case meta path: %s", case_meta_path)
    case_meta = yaml_load(case_meta_path)
    logger.info("Case meta: %s", case_meta)
    return case_meta


def get_case_uuid(case_path: Union[str, PosixPath]) -> str:
    """Get case uuid from case metadata file

    Args:
        case_path (str): path to case

    Returns:
        str: the case uuid
    """
    logger = logging.getLogger(__name__ + ".get_case_uuid")
    case_meta = get_case_meta(case_path)
    uuid = case_meta["fmu"]["case"]["uuid"]
    logger.info("Case uuid: %s", uuid)
    return uuid


def parse_args() -> argparse.Namespace:
    """Parse arguments

    Returns:
        argparse.Namespace: namespace containing input arguments
    """
    description = "Read preprocessed observation data and connects to an ert case"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("case_path", type=str, help="Path to ert case")
    parser.add_argument(
        "preprocessed_folder",
        type=str,
        help="Path to folder with preprocessed observations",
    )
    parser.add_argument(
        "--fmuconfig_path",
        type=str,
        help="Directly specify path to fmuconfig file, relative to ert config path",
        default="../../fmuconfig/output/global_variables.yml",
    )
    parser.add_argument(
        "--env", type=str, help="Environment to upload to", default="prod"
    )
    parser.add_argument("--d", help="Enable debug mode", action="store_true")
    return parser.parse_args()


def run(args):
    if args.d:
        logging.basicConfig(level="DEBUG")

    logger = logging.getLogger(__name__ + ".run")
    logger.info("Will upload observations to sumo")
    sumo_upload(
        prepare_sumo_files(args.preprocessed_folder, args.case_path),
        get_case_uuid(args.case_path),
        args.env,
    )
    logger.info("Done!")


def main():
    """Run the whole shebang"""
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
