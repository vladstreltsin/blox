class Message:

    def __init__(self, pass_on=False):
        self.pass_on = pass_on


class MessengerNodeMixin:
    """ Implements a node that can send messages to its parent """

    @property
    def parent(self):
        raise NotImplementedError

    def handle_message(self, message):
        """ This method must be implemented """
        pass

    def send_message(self, message):
        """ Sending a message to the parent by calling its recv() method"""
        if not isinstance(message, Message):
            raise TypeError(f"A message must be of type {Message.__name__}")

        if self.parent is not None:
            self.parent.recv(message)

    def recv_message(self, message):
        if not isinstance(message, Message):
            raise TypeError(f"A message must be of type {Message.__name__}")

        self.handle_message(message)

        if message.pass_on:
            self.send_message(message)
