class BloxError(Exception):
    pass


class TreeError(BloxError):
    pass


class LoopError(BloxError):
    pass


class NameCollisionError(BloxError):
    pass


class NameLockError(BloxError):
    pass


class BadNameError(BloxError):
    pass


class BlockLockError(BloxError):
    pass


class BlockCompositionError(BloxError):
    pass


class PortConnectionError(BloxError):
    pass


class UnknownError(BloxError):
    pass


class ForbiddenNameError(BloxError):
    pass


class TagMismatchError(BloxError):
    pass


class ComputeError(BloxError):
    pass
