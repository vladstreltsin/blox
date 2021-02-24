from __future__ import annotations
from blox.core.block import Block, BlockError, Port
from blox.core.engine import Session, PortPuller
import typing as T
from functools import partial


class Mux(Block):

    def __init__(self, *args, Out=1, **kwargs):
        super(Mux, self).__init__(Out=Out, AuxIn='sel', *args, **kwargs)

        if len(self.Out) != 1:
            raise BlockError(f"Only one output is allowed for a multiplexer. Received {len(self.Out)}")

        self.atomic = True
        self.lock_ports = True

    def propagate(self, session: Session):
        NotImplementedError(f'A {self.__class__.__name__} cannot propagate')

    async def pull(self, port: Port, session: Session) -> T.Any:

        if port not in self:
            raise BlockError(f"Port {port} doesn't belong to the block {self}")

        # For inputs and aux ports use the standard protocol
        if port.auxiliary or port.is_in:
            return await super(Mux, self).pull(port=port, session=session)

        else:

            async def pull_selected(sess, in_ports, selector_port, out_port):

                # Obtain the selector port
                select = await selector_port.pull(session=sess)

                # Set the chosen port
                sess[out_port] = await in_ports[select.value].pull(sess)

            return await PortPuller(coroutine=partial(pull_selected, session, self.In, self.AuxIn(), self.Out()),
                                    out_ports=self.Out).pull(port, session)
