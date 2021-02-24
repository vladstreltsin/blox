from blox.core.block import AtomicFunction
import time


class Delay(AtomicFunction):

    def __init__(self, delay: float, *args, **kwargs):
        super(Delay, self).__init__(*args, **kwargs, port_map=None, In=1, Out=1)
        self.lock_ports = True
        self.delay = delay

    def fn(self, value):
        time.sleep(self.delay)
        return value
