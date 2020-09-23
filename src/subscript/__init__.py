import logging

try:
    import pkg_resources

    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    pass


def getLogger(module_name="subscript"):
    """Provide a unified logger for subscript

    In particular, the module names for each tool has
    the module name mentioned twice. Ensure we remove
    the double name, e.g. subscript.csv_merge.csv_merge
    should be mapped to subscript.csv_merge

    Args:
        module_name (str): A suggested name for the logger, usually
            __name__ should be supplied

    Returns:
        A logger object
    """
    logging.basicConfig()  # Ensure at least one handler is available

    if not module_name:
        return logging.getLogger("subscript")

    compressed_name = []
    for elem in module_name.split("."):
        if len(compressed_name) == 0 or elem != compressed_name[-1]:
            compressed_name.append(elem)
    return logging.getLogger(".".join(compressed_name))
