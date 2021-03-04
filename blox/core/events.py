class NodeEvent:
    pass


class NodePreRename(NodeEvent):
    __slots__ = ('node', 'parent', 'new_name')

    def __init__(self, node, parent, new_name):
        self.node = node
        self.parent = parent
        self.new_name = new_name


class NodePostRename(NodeEvent):
    __slots__ = ('node', 'parent', 'old_name')

    def __init__(self, node, parent, old_name):
        self.node = node
        self.parent = parent
        self.old_name = old_name


class NodePreAttach(NodeEvent):
    __slots__ = ('node', 'parent')

    def __init__(self, node, parent):
        self.node = node
        self.parent = parent


class NodePostAttach(NodeEvent):
    __slots__ = ('node', 'parent')

    def __init__(self, node, parent):
        self.node = node
        self.parent = parent


class NodePreDetach(NodeEvent):
    __slots__ = ('node', 'parent')

    def __init__(self, node, parent):
        self.node = node
        self.parent = parent


class NodePostDetach(NodeEvent):
    __slots__ = ('node', 'parent')

    def __init__(self, node, parent):
        self.node = node
        self.parent = parent


class LinkPreConnect(NodeEvent):
    __slots__ = ('port1', 'port2')

    def __init__(self, port1, port2):
        self.port1 = port1
        self.port2 = port2


class LinkPostConnect(NodeEvent):
    __slots__ = ('port1', 'port2')

    def __init__(self, port1, port2):
        self.port1 = port1
        self.port2 = port2


class LinkPreDisconnect(NodeEvent):
    __slots__ = ('port1', 'port2')

    def __init__(self, port1, port2):
        self.port1 = port1
        self.port2 = port2


class LinkPostDisconnect(NodeEvent):
    __slots__ = ('port1', 'port2')

    def __init__(self, port1, port2):
        self.port1 = port1
        self.port2 = port2
