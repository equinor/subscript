# -*- coding: utf-8 -*-
"""Loading nested config files"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path
from collections import OrderedDict
import io

try:
    file_types = (file, io.IOBase)
except NameError:
    file_types = (io.IOBase,)

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from xtgeo.common import XTGeoDialog

xtg = XTGeoDialog()
logger = xtg.functionlogger(__name__)


class YamlXLoader(yaml.Loader):
    """Class for making it possible to use nested YAML files.

    Code is borrowed from David Hall (but extended later):
    https://davidchall.github.io/yaml-includes.html
    """

    # pylint: disable=too-many-ancestors

    def __init__(self, stream, ordered=False):
        self._ordered = ordered  # for OrderedDict
        self._root = os.path.split(stream.name)[0]
        super(YamlXLoader, self).__init__(stream)

        YamlXLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            YamlXLoader.construct_mapping,
        )

        YamlXLoader.add_constructor("!include", YamlXLoader.include)
        YamlXLoader.add_constructor("!import", YamlXLoader.include)
        YamlXLoader.add_constructor("!include_from", YamlXLoader.include_from)
        # if root:
        #     self.root = root
        # elif isinstance(self.stream, file_types):
        #     self.root = os.path.dirname(self.stream.name)
        # else:
        #     self.root = os.path.curdir

    def include(self, node):
        """Include method"""

        result = None
        if isinstance(node, yaml.ScalarNode):
            result = self.extract_file(self.construct_scalar(node))

        elif isinstance(node, yaml.SequenceNode):
            result = []
            for filename in self.construct_sequence(node):
                result += self.extract_file(filename)

        elif isinstance(node, yaml.MappingNode):
            result = {}
            for knum, val in self.construct_mapping(node).items():
                result[knum] = self.extract_file(val)

        else:
            print("Error:: unrecognised node type in !include statement")
            raise yaml.constructor.ConstructorError

        return result

    def include_from(self, node):
        """The include_from method, which parses parts of another YAML.

        E.g.
        dates: !include_from /private/jriv/tmp/global_config.yml::global.DATES
        diffdates: !include_from tests/yaml/global_config.yml::global.DIFFDATES

        In the first case, it will read the ['global']['DATES'] values

        The files must have full path (abs or relative)
        """

        result = None
        oldroot = self._root

        if isinstance(node, yaml.ScalarNode):
            filename, val = self.construct_scalar(node).split("::")
            result = yaml.safe_load(open(filename, "r"))
            self._root = oldroot

            fields = val.strip().split(".")
            for ilev, field in enumerate(fields):
                if field in set(result.keys()):
                    logger.info("Level %s key, field name is %s", ilev + 1, field)
                    result = result[field]
                else:
                    logger.critical(
                        "Level %s key, field name not found %s", ilev + 1, field
                    )
                    raise yaml.constructor.ConstructorError
            return result

        else:
            print("Error:: unrecognised node type in !include_from statement")
            raise yaml.constructor.ConstructorError

        return result

    def extract_file(self, filename):
        """Extract file method"""

        filepath = os.path.join(self._root, filename)
        with open(filepath, "r") as yfile:
            return yaml.load(yfile, YamlXLoader)

    # from https://gist.github.com/pypt/94d747fe5180851196eb
    # but changed mapping to OrderedDict
    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                "Expected a mapping node, but found %s" % node.id,
                node.start_mark,
            )

        mapping = dict()
        if self._ordered:
            mapping = OrderedDict()

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError(
                    "While constructing a mapping",
                    node.start_mark,
                    "found unacceptable key (%s)" % exc,
                    key_node.start_mark,
                )
            # check for duplicate keys
            if key in mapping:
                raise ConstructorError(
                    "Found duplicate key <{}> ... {}".format(key, key_node.start_mark)
                )
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


# cf https://stackoverflow.com/questions/528281/\
#    how-can-i-include-a-yaml-file-inside-another
class YLoader(yaml.Loader):
    """
    yaml.YLoader subclass handles "!include path/to/foo.yml" directives in
    config files.  When constructed with a file object,
    the root path for includes defaults to the directory
    containing the file, otherwise to the current
    working directory. In either case, the root path can be overridden by the
    `root` keyword argument.

    When an included file F contain its own !include directive, the path is
    relative to F's location.

    Example:
        YAML file /home/frodo/one-ring.yml:
            ---
            Name: The One Ring
            Specials:
                - resize-to-wearer
            Effects:
                - !include path/to/invisibility.yml

        YAML file /home/frodo/path/to/invisibility.yml:
            ---
            Name: invisibility
            Message: Suddenly you disappear!

        Loading:
            data = YLoader(open('/home/frodo/one-ring.yml', 'r')).get_data()

        Result:
            {'Effects': [{'Message': 'Suddenly you disappear!', 'Name':
                'invisibility'}], 'Name': 'The One Ring', 'Specials':
                ['resize-to-wearer']}

    """

    def __init__(self, *args, **kwargs):
        super(YLoader, self).__init__(*args, **kwargs)
        self.add_constructor("!include", self._include)
        if "root" in kwargs:
            self.root = kwargs["root"]
        elif isinstance(self.stream, file_types):
            self.root = os.path.dirname(self.stream.name)
        else:
            self.root = os.path.curdir

    def _include(self, loader, node):
        oldroot = self.root
        filename = os.path.join(self.root, loader.construct_scalar(node))
        self.root = os.path.dirname(filename)
        data = yaml.load(open(filename, "r"))
        self.root = oldroot
        return data
