from blox2.messengernode import Message
from enum import Enum


class ChildRenameMessage(Message):

    def __init__(self, child, new_name):
        super(ChildRenameMessage, self).__init__(pass_on=False)
        self.child = child
        self.new_name = new_name


class ChangeType(Enum):
    PRE_ATTACH = 0,
    POST_ATTACH = 1,
    PRE_DETACH = 2,
    POST_DETACH = 3


class ChildChangeMessage(Message):

    def __init__(self, child, change_type):
        super(ChildChangeMessage).__init__(pass_on=False)
        self.child = child
        self.change_type = ChangeType[change_type.upper()]


class PortStreamDisconnect(Message):

    def __init__(self, port):
        super(PortStreamDisconnect, self).__init__(pass_on=False)
        self.port = port
