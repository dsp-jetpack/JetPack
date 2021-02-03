import yaml
from collections import OrderedDict

SCALAR_TAG = yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG


class OrderedDumper(yaml.SafeDumper):
    ''' Extend SafeDumper to handle OrderedDict so content is output in the
    same order it is parsed as.  Also turn off alias rendering for duplicate
    values as aliases are not used elsewhere in Tripleo heat templates, stick
    with upstream pattern'''

    def ignore_aliases(self, data):
        return True


def ordered_map_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())


def literal_representer(dumper, data):
    ''' Pyyaml should do this by default but doesn't for some reason.
    Adding representer to find scalar data containing line feeds and emit
    the correctly formed yaml for block content using literal marker '|'.'''
    _style = None
    if '\n' in data:
        _style = '|'
    return dumper.represent_scalar(SCALAR_TAG, data, style=_style)


def list_representer(dumper, data):
    return dumper.represent_sequence(u'tag:yaml.org,2002:seq', data, False)


OrderedDumper.add_representer(OrderedDict, ordered_map_representer)
OrderedDumper.add_representer(str, literal_representer)
OrderedDumper.add_representer(list, list_representer)


class OrderedLoader(yaml.SafeLoader):
    ''' Overrides default mapping constructor to preserve order
    via OrderedDict '''

    def _construct_yaml_str(self, node):
        # Override the default string handling function
        # to always return unicode objects
        return self.construct_scalar(node)


def construct_mapping(loader, node):
    ''' Use OrderedDict when loading to preserve original order from input
    yaml document.'''

    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                              construct_mapping)
# Upstream heat-common repo does this, forces all scalar types to string.
# Following this pattern in our stuff as well. u'tag:yaml.org,2002:timestamp'
OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG,
                              OrderedLoader._construct_yaml_str)
OrderedLoader.add_constructor(u'tag:yaml.org,2002:timestamp',
                              OrderedLoader._construct_yaml_str)
