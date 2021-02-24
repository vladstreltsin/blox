from __future__ import annotations
from blox.core.engine import Session, export_sessions, import_sessions, PortData, PortPuller
from blox.core._block import _Block, Port, BlockError
from blox.utils import maybe_or, camel_to_snake, fullname
import typing as T
from abc import abstractmethod
from blox.utils import maybe_error, maybe_bind
from functools import partial
from enum import Enum
from functools import update_wrapper


class BlockRuntimeError(RuntimeError):
    pass


class Block(_Block):
    """ This class allows to actually run blocks in sessions """

    def __init__(self, *args, **kwargs):
        super(Block, self).__init__(*args, **kwargs)

    async def pull(self, port: Port, session: Session) -> T.Any:
        """ The default pull policy is asynchronously pulling on the downstream and setting own value """

        if port not in self:
            raise BlockError(f"Port {port} does't belong to the block {self}")

        if port in session:
            return session[port]

        # Compute the port by pulling on the upstream
        async def upstream_pull(p, sess):
            upstream = maybe_error(p.upstream(), BlockError(f"Port {p} is pulled but has no upstream. "
                                                            f"Did you forget to set it?"))
            sess[p] = await upstream.pull(sess)

        result = await PortPuller(coroutine=partial(upstream_pull, p=port, sess=session),
                                  out_ports=[port]).pull(port, session)

        return result

    def push(self, port: Port, session: Session) -> None:
        """ The default push policy is writing own's value on the downstream """

        if port not in self:
            raise BlockError(f"Port {port} doesn't belong to the block {self}")

        # Obtain current value
        value = session[port]

        # Propagate it to downstream
        for dws in port.downstream:
            session[dws] = value

        # Delete unused ports in memory saving regime
        session.maybe_delete(port)

    def propagate(self, session: Session) -> None:
        """ The default propagation policy.
        1. Push inputs
        2. for each child in topologically sorted order - propagate (recursively) and push outputs
        3. Make sure outputs we set
        """

        # Push all inputs
        for port in self.In:
            port.push(session)

        # Propagate essential children (in topological order)
        for child in self.blocks.essential_sorted():
            child.propagate(session)

            for port in child.Out:
                port.push(session)

    async def async_propagate(self, session: Session, executor=None) -> None:
        """ Calls propagate asynchronously, optionally in a remote executor """

        # Get the executor type (defaults to None)
        # executor = maybe(executor).bind(lambda x: FunctionExecutorType[x.upper()]).or_else(None)
        executor = maybe_bind(executor, lambda x: FunctionExecutorType[x.upper()])

        # In this case the method will run in the executor's thread pool "as is"
        if executor is FunctionExecutorType.THREAD:
            await session.engine.run_in_thread_pool(partial(self.propagate, session=session))

        # In this case we "pack" the task and send it to the process pool executor, then merge the
        # computed sessions back in
        elif executor is FunctionExecutorType.PROCESS:
            sess_dict = await session.engine.run_in_process_pool(_ProcessExecutorPropagate(block=self,
                                                                                           session=session))
            session.update(*import_sessions(block=self, export_dict=sess_dict))

        else:
            self.propagate(session=session)

    def map(self, *args, **kwargs):
        """ Uses the block as if it were a function. """

        session = Session(save_memory=True)
        if len(args) > len(self.In):
            raise BlockError(f"Block {self} has {len(self.In)} inputs but provided with "
                             f"{len(args)} non-keyword arguments")

        for n, value in enumerate(args):
            port = self.In[n]
            session[port] = value

        for name, value in kwargs.items():
            port = self.ports[name]
            if port in session:
                BlockError(f"Block {self} got multiple values for port {port}")

            session[port] = value

        # Compute the outputs
        self.propagate(session)

        # Get the result
        result = tuple(session[port].value for port in self.Out)
        return result[0] if len(result) == 1 else result

    def wrap_value(self, value):
        return PortData(value=value, device=self.device)


class _ProcessExecutorPropagate:
    """ Wrapper class for propagation tasks to be performed in an executor """

    def __init__(self, block: Block, session: Session):
        self._block = block
        self._session = session

    @property
    def block(self):
        return self._block

    @property
    def session(self):
        return self._session

    def __getstate__(self):
        odict = self.__dict__.copy()

        # Sessions will be sent through their export dict
        del odict['_session']
        odict['_export_dict'] = export_sessions(self._block, self._session)

        return odict

    def __setstate__(self, state):

        # Fix side effects of circular pickling
        block = state.pop('_block').fix_pickle()

        # Get the exported session dict
        export_dict = state.pop('_export_dict')
        session, = import_sessions(block, export_dict)

        # Update the state dict
        self.__dict__.update(state)
        self.__dict__['_block'] = block
        self.__dict__['_session'] = session

    def __call__(self):
        # Compute block's outputs, note that we run here without an Engine, since no async stuff will be done here
        self.block.propagate(self.session)

        # Return exported dict
        return export_sessions(self.block, self.session)


class FunctionExecutorType(Enum):
    THREAD = 0,
    PROCESS = 1


class Function(Block):
    """ Upon output pulling, first get the inputs and then use the propagate method """

    def __init__(self, *args, executor=None, **kwargs):
        super(Function, self).__init__(*args, **kwargs)

        # Where the propagate method will run upon pull
        self.__executor = None
        self.executor = executor

    @property
    def executor(self):
        return maybe_bind(self.__executor, lambda x: x.name)

    @executor.setter
    def executor(self, value):
        self.__executor = maybe_bind(value, lambda x: FunctionExecutorType[x.upper()])

    # async def pull(self, port: Port, session: Session) -> T.Any:
    #
    #     if port not in self:
    #         raise BlockError(f"Port {port} doesn't belong to the block {self}")
    #
    #     # For inputs and aux ports use the standard protocol
    #     if port.auxiliary or port.is_in:
    #         return await super(Function, self).pull(port=port, session=session)
    #
    #     # Wait if the port is already being computed
    #     result: T.Union[Something, Nothing] = await session.aget(port)
    #     if result.is_some():
    #         return result.value
    #
    #     # This is the central task that collects the inputs and sets the outputs
    #     async def gather_and_propagate():
    #         await asyncio.gather(*[x.pull(session) for x in self.In])
    #         await self.async_propagate(session=session, executor=self.executor)
    #
    #     # propagate_task = session.engine.create_task(async_propagate())
    #     propagate_task = session.engine.create_task(gather_and_propagate())
    #
    #     # These are the secondary tasks that 'lock' output ports
    #     async def get_port(x):
    #         # the async_propagate() method sets the outputs so once it completes
    #         # session should contain the port's value
    #         await propagate_task
    #         return session[x]
    #
    #     # Add port getter tasks
    #     for p in self.Out:
    #         session.tasks[p] = session.engine.create_task(get_port(p))
    #
    #     # Wait until the tasks complete, set outputs and erase tasks
    #     for p in self.Out:
    #         await session.tasks[p]
    #         session[p] = session.tasks[p].result()
    #         del session.tasks[p]
    #
    #
    #     return session[port]

    async def pull(self, port: Port, session: Session) -> T.Any:

        if port not in self:
            raise BlockError(f"Port {port} doesn't belong to the block {self}")

        # For inputs and aux ports use the standard protocol
        if port.auxiliary or port.is_in:
            return await super(Function, self).pull(port=port, session=session)

        else:
            # This is the central task that collects the inputs and sets the outputs
            async def gather_and_propagate(in_ports, sess, exc):
                # await asyncio.gather(*[x.pull(sess) for x in in_ports])
                for x in in_ports:
                    await x.pull(sess)
                await self.async_propagate(session=sess, executor=exc)

            result = await PortPuller(coroutine=partial(gather_and_propagate,
                                                        in_ports=list(self.In),
                                                        sess=session,
                                                        exc=self.executor),
                                      out_ports=self.Out).pull(port, session)

            return result


class AtomicFunction(Function):
    """ The propagate method is realized with a given function """

    def __init__(self, *args, port_map: T.Optional[T.Dict[str, str]] = None, **kwargs):
        super(AtomicFunction, self).__init__(*args, **kwargs)
        self.__port_map = None
        self.port_map = port_map        # Called via the setter
        self.atomic = True

    @property
    def port_map(self):
        return self.__port_map

    @port_map.setter
    def port_map(self, value: T.Optional[T.Dict[str, str]]):
        value = value or {}
        assert isinstance(value, dict)
        self.__port_map = value

    def propagate(self, session: Session):
        try:

            # Obtain the arguments and the keyword arguments for the function
            kwargs = {arg_name: session[self.In[port_name]].value
                      for port_name, arg_name in self.port_map.items()}
            args = [session[self.In[port_name]].value
                    for port_name in self.In.keys() if port_name not in self.port_map]

            result = self._call_fn(*args, **kwargs)

            # Memory maintenance
            for port in self.In:
                session.maybe_delete(port)

            if len(self.Out) == 1:
                session[self.Out()] = self.wrap_value(value=result)

            else:
                if len(self.Out) != len(result):
                    raise BlockError(f"In Function {self}: expected {len(self.Out)} outputs, got {len(result)}")

                for out_port, value in zip(self.Out, result):
                    session[out_port] = self.wrap_value(value=value)

        except Exception as e:
            raise BlockRuntimeError(f"Exception thrown during propagation of block {self}") from e

    def _call_fn(self, *args, **kwargs):
        # TODO add here support for parallel processing
        # Determine whether one of the inputs is an
        result = self.fn(*args, **kwargs)
        return result

    @abstractmethod
    def fn(self, *args, **kwargs) -> T.Any:
        pass

    @classmethod
    def wrap(cls, **kwargs):
        raise NotImplementedError


class Lambda(AtomicFunction):

    def __init__(self, fn: T.Callable, *args, In=1, Out=1, **kwargs):
        super(Lambda, self).__init__(*args, **kwargs, In=In, Out=Out)
        self.__fn = fn

    def fn(self, *args, **kwargs):
        return self.__fn(*args, **kwargs)

    @classmethod
    def wrap(cls, **kwargs):
        """ Use this method to convert regular python function into a Lambda block instance """

        def create_block(wrapped_fn) -> cls:

            def block_builder(fn, *, name=None, **fn_kwargs):

                # Obtain the non-keyword arguments of fn - these will serve as input port names
                num_in_ports = fn.__code__.co_argcount
                in_port_names = fn.__code__.co_varnames[0:num_in_ports]

                default_name = camel_to_snake(fn.__code__.co_name)
                params = dict(name=maybe_or(name, default_name), In=in_port_names)
                params.update(kwargs)

                # Initialize the block with given input ports and the wrapped function name
                block = cls(fn=partial(fn, **fn_kwargs), **params)

                return block

            update_wrapper(wrapper=block_builder, wrapped=wrapped_fn)

            # The decorators returns a function that creates an instance of the block, like a constructor
            return partial(block_builder, wrapped_fn)

        return create_block


class Add(AtomicFunction):
    def fn(self, x, y):
        return x + y


class Mul(AtomicFunction):
    def fn(self, x, y):
        return x * y


class Sub(AtomicFunction):
    def fn(self, x, y):
        return x - y


class TrueDiv(AtomicFunction):
    def fn(self, x, y):
        return x / y


class FloorDiv(AtomicFunction):
    def fn(self, x, y):
        return x // y


class MatMul(AtomicFunction):
    def fn(self, x, y):
        return x @ y


class Const(Function):

    def __init__(self, value, *args, **kwargs):
        super(Const, self).__init__(*args, **kwargs, In=(), Out=1)
        self.value = value
        self.lock_ports = True
        self.atomic = True

    def propagate(self, session):
        session[self.Out()] = self.wrap_value(value=self.value)

    def set(self, value):
        self.value = value


class NoDefault:
    _instance = None

    def __new__(cls, *args, **kwargs):
        cls._instance = maybe_or(cls._instance, super().__new__(cls, *args, **kwargs))
        return cls._instance


class Src(Function):
    """ Sources are a nice way to set up the inputs to a system. """

    def __init__(self, default=NoDefault(), *args, **kwargs):
        super(Src, self).__init__(*args, **kwargs, In=(), Out=1)
        self.default = default
        self.lock_ports = True
        self.atomic = True

    def propagate(self, session: Session):

        # Sets the default value in case one is given
        if self.Out() not in session and self.default is not NoDefault():
            session[self.Out()] = self.wrap_value(value=self.default)

    def set(self, session: Session, value):
        session[self.Out()] = self.wrap_value(value=value)


class Sink(Function):
    """ Sinks serve as the endpoints of systems. They provide the 'get' method that pulls on the input and
    returns the result """

    def __init__(self, *args, **kwargs):
        super(Sink, self).__init__(*args, **kwargs, In=1, Out=())
        self.lock_ports = True
        self.atomic = True

    def get(self, session):
        return session(self.In()).value

