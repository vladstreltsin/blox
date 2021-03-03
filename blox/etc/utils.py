import re
from collections import UserDict
from events import Events
import re
import typing as tp


RE_LEGAL_NAME = re.compile('[0-9a-zA-Z_]+')
RE_PORT_RANGE_LETTERS = re.compile('(?P<start>[a-zA-Z])-(?P<end>[a-zA-Z])')
RE_PORT_RANGE_INDICES = re.compile('(?P<prefix>[a-zA-Z]+)(?P<start>[0-9]+)-(?P<end>[0-9]+)')


def get_dynamic_attribute(obj, name: str, default=None):
    """ Returns the property with the given name. Sets it if doesn't exist """
    if not hasattr(obj, name):
        setattr(obj, name, default)
    return getattr(obj, name)


def set_dynamic_attribute(obj, name, value):
    setattr(obj, name, value)


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def to_tuple(obj) -> tp.Tuple:
    if obj is None:
        return ()
    if isinstance(obj, str):
        return obj,
    else:
        return tuple(obj)


def parse_ports(obj, default_prefix):

    if isinstance(obj, int):
        prefix = default_prefix
        return tuple(f"{prefix}{n}" for n in range(1, obj+1))

    elif isinstance(obj, str):
        match = RE_PORT_RANGE_LETTERS.match(obj)
        if match:
            start = match['start']
            end = match['end']

            if ord(end) < ord(start):
                raise ValueError(f"The specified range {obj} is empty")
            return tuple(f"{chr(c)}" for c in range(ord(start), ord(end)+1))

        match = RE_PORT_RANGE_INDICES.match(obj)
        if match:
            prefix = match['prefix']
            start = int(match['start'])
            end = int(match['end'])

            if end < start:
                raise ValueError(f"The specified range {obj} is empty")
            return tuple(f"{prefix}{n}" for n in range(start, end + 1))

        return to_tuple(obj)

    return to_tuple(obj)


def remove_trailing_digits(s):
    # Remove trailing digits from the child's name
    m = re.compile('(.*?)([0-9]+)$').match(s)
    if m:
        return m.group(1)
    return s
