from __future__ import annotations
import re
from typing import TypeVar, Callable, Optional


def raise_if(cond, exception: Exception):
    if cond:
        raise exception


class const:
    """ A constant value as a function """
    def __init__(self, value):
        self.value = value

    def __call__(self, *args, **kwargs):
        return self.value


def identity(x):
    return x


def instance_check(item, cls):
    return isinstance(item, cls)


def first(pair):
    return pair[0]


def second(pair):
    return pair[1]


T = TypeVar('T')
S = TypeVar('S')


def maybe_fmap(f: Callable[T, S]) -> Callable[Optional[T], Optional[S]]:
    return lambda x: f(x) if x is not None else None


def maybe_bind(x: Optional[T], f: Callable[T, Optional[S]]):
    return f(x) if x is not None else None


def maybe_error(x: Optional[T], exception: Exception) -> T:
    if x is not None:
        return x
    raise exception


def maybe_raise(exception: Optional[Exception]) -> None:
    if exception is not None:
        raise exception


def maybe_or(x: Optional[T], other: T.Any) -> T.Any:
    if x is not None:
        return x
    else:
        return other


class _SingletonWrapper:
    """
    A singleton wrapper class. Its instances would be created
    for each decorated class.
    """

    def __init__(self, cls):
        self.__wrapped__ = cls
        self._instance = None

    def __call__(self, *args, **kwargs):
        """Returns a single instance of decorated class"""
        if self._instance is None:
            self._instance = self.__wrapped__(*args, **kwargs)
        return self._instance


def singleton(cls):
    """
    A singleton decorator. Returns a wrapper objects. A call on that object
    returns a single instance object of decorated class. Use the __wrapped__
    attribute to access decorated class directly in unit tests
    """
    return _SingletonWrapper(cls)


RE_LEGAL_NAME = re.compile('[0-9a-zA-Z_]+')
RE_PORT_RANGE_LETTERS = re.compile('(?P<start>[a-zA-Z])-(?P<end>[a-zA-Z])')
RE_PORT_RANGE_INDICES = re.compile('(?P<prefix>[a-zA-Z]+)(?P<start>[0-9]+)-(?P<end>[0-9]+)')


def assert_identifier(name):
    # Provided name must be a legal python identifier
    if not RE_LEGAL_NAME.match(name):
        raise ValueError(f"Illegal name {name} (must be a legal python identifier)")
    if name.startswith('_') or name.endswith('_'):
        raise ValueError(f"Illegal name {name} (must not start or end with '_')")


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def to_tuple(obj) -> T.Tuple:
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


def fullname(o):
    """
    o.__module__ + "." + o.__class__.__qualname__ is an example in
    this context of H.L. Mencken's "neat, plausible, and wrong."
    Python makes no guarantees as to whether the __module__ special
    attribute is defined, so we take a more circumspect approach.
    Alas, the module name is explicitly excluded from __qualname__
    in Python 3.
    """

    builtins_module = str.__class__.__module__
    if o.__class__.__name__ == 'function':
        module = o.__module__
        name = o.__name__
    else:
        module = o.__class__.__module__
        name = o.__class__.__name__

    # Avoid reporting __builtin__
    if module is None or module == builtins_module:
        return name
    else:
        return f'{module}.{name}'


def compose(*fns):
    """ Functional composition of inputs """

    if len(fns) == 0:
        raise ValueError("At least one function must be provided")

    def composite(*args):
        x = fns[-1](*args)
        for fn in reversed(fns[0:-1]):
            x = fn(x)
        return x

    return composite


def second_or(lst, default):
    if len(lst) > 1:
        return lst[1]
    else:
        return default


def join_not_none(sep: str, iterable):
    return sep.join(filter(None, iterable))


def filter_compose(*fns: T.Callable[[T.Any], bool]):
    """ Composition of filter functions """
    def composite(x):
        for f in fns:
            if not f(x):
                return False
        return True

    return composite


def signature_check(dummy, *args, **kwargs):
    """Checks whether the arguments match the signature of a dummy function by catching a TypeError"""
    try:
        dummy(*args, **kwargs)
        return True

    except TypeError:
        return False
