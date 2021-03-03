class BloxError(Exception):
    pass


class NameCollisionError(BloxError):
    pass


class ChildrenLockError(BloxError):
    pass


class NameLockError(BloxError):
    pass


class UpstreamSizeError(BloxError):
    pass