from __future__ import annotations
import asyncio
import threading
from anytree import NodeMixin
from blox_old.core.block.base import Port, _Block, _BlockPortsSection
from blox_old.utils import maybe_error, maybe_raise
import uuid
import typing as T
from itertools import chain
from more_itertools import prepend
from scalpl import Cut
from concurrent.futures import Future
from collections import OrderedDict
from blox_old.maybe import Something, Nothing
from concurrent.futures import ThreadPoolExecutor
import loky
from blox_old.core.engine.device import BlockDevice, DefaultDevice

import uvloop
uvloop.install()


def _parse_port(port: T.Union[Port, _BlockPortsSection]) -> Port:
    if isinstance(port, _BlockPortsSection):
        if len(port) != 1:
            raise SessionError("Exactly one port must be provided")
        return port()

    return port


class EngineError(Exception):
    pass


class SessionError(Exception):
    pass


class PortData:

    __slots__ = ['__value', '__device']

    def __init__(self, value, device):
        self.__value = value
        self.__device = device

    @property
    def value(self):
        return self.__value

    @property
    def device(self):
        return self.__device

    def to(self, device: BlockDevice):
        """ Moves port data to another device if needed """
        if device is not self.device:
            return self.__class__(value=self.device.move(self.value, device), device=device)
        else:
            return self

    async def ato(self, device: BlockDevice):
        """ Moves port data to another device if needed asynchronously """
        if device is not self.device:
            value = await self.device.amove(self.value, device)
            return self.__class__(value=value, device=device)
        else:
            return self

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value}, device={self.device})"

    def __call__(self):
        return self.value


class _SessionTasks:

    def __init__(self, _session: Session):
        self.__data = dict()
        self.__session = _session

    @property
    def session(self):
        return self.__session

    @property
    def engine(self):
        return self.__session.engine

    def __assert_thread(self):
        if threading.current_thread() != self.engine.thread:
            raise SessionError("Can only be called from the Engine's thread")

    def __getitem__(self, port: T.Union[Port, _BlockPortsSection]):
        self.__assert_thread()
        port = _parse_port(port)
        return self.__data[port]

    def __setitem__(self, port: T.Union[Port, _BlockPortsSection], value: T.Awaitable):
        self.__assert_thread()
        port = _parse_port(port)
        if port in self.__data:
            raise SessionError(f"Port {port} already has an associated task")
        self.__data[port] = value

    def __contains__(self, port: T.Union[Port, _BlockPortsSection]):
        self.__assert_thread()
        port = _parse_port(port)
        return port in self.__data

    def __delitem__(self, port: T.Union[Port, _BlockPortsSection]):
        self.__assert_thread()
        port = _parse_port(port)
        del self.__data[port]


class Session(NodeMixin):

    def __init__(self, engine: T.Optional[Engine]=None, guid: T.Optional[uuid.UUID]=None, save_memory: bool=False,
                 tag: T.Optional[str] = None):

        # Here port data will be stored
        self._data = dict()

        # Here we'll store events that signal that a given port was computed in a given session
        self.events = dict()

        # Here asyncio futures will be stored for each port
        self._tasks = _SessionTasks(_session=self)

        # Assign a global unique id to the session
        self._guid = guid or uuid.uuid4()

        # The engine to which the session is bound
        self._engine = engine

        # Cleanup intermediate ports on propagate
        self.save_memory = save_memory

        # An optional identifier string for the session
        # TODO: this should be given its own class
        self._tag = tag

    @property
    def tag(self):
        return self._tag

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, value: Engine):
        """ Set the engine for self and all sub-sessions """
        self._engine = value
        for child in self.children:
            child.engine = value

    @property
    def tasks(self):
        return self._tasks

    def keys(self):
        return self._data.keys()

    def value(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def clear(self):
        self._data.clear()

    def update(self, other: Session):
        """ Updates current session data with data from another session with the same guid """
        if self.guid != other.guid:
            SessionError("Session GUID mismatch")

        # Session has .keys() method so we can update using the dict update method
        self._data.update(other)

        other_children = OrderedDict((child_sess.guid, child_sess) for child_sess in other.children)

        # Merge children
        for child in self.children:
            if child.guid in other_children:
                other_child = other_children.pop(child.guid)
                child.update(other_child)

        # Add new children
        for other_guid, other_child in other_children.items():
            child = self.spawn_session(guid=other_guid)
            child.update(other_child)

    def spawn_session(self, detach=False, *args, **kwargs) -> Session:
        session = Session(*args, **kwargs, engine=self.engine, save_memory=self.save_memory)
        session.parent = self if not detach else None
        return session

    @property
    def guid(self):
        return self._guid

    def __getitem__(self, port: T.Union[Port, _BlockPortsSection]) -> PortData:
        port = _parse_port(port)
        if port not in self:
            raise SessionError(f"Getting the value of a unset port {port}")

        value: PortData = self._data[port]
        if value.device is not port.device:
            self._data[port] = value.to(port.device)

        return self._data[port]

    def __setitem__(self, port: T.Union[Port, _BlockPortsSection], value):
        port = _parse_port(port)

        if not isinstance(value, PortData):
            value = PortData(value=value, device=DefaultDevice())
        self._data[port] = value.to(port.device)

    def __contains__(self, port: T.Union[Port, _BlockPortsSection]):
        port = _parse_port(port)
        return port in self._data

    def __delitem__(self, port: T.Union[Port, _BlockPortsSection]):
        port = _parse_port(port)
        del self._data[port]
        if port in self.events:
            del self.events[port]

    def __call__(self, port: Port, timeout=None):
        maybe_error(self.engine, SessionError(f"Session is not bound to any Engine"))
        return self.engine(session=self, port=port, timeout=timeout)

    async def aget(self, port: T.Union[Port, _BlockPortsSection]) -> T.Union[Something, Nothing]:
        port = _parse_port(port)

        # This is the case when the port was already computed
        if port in self:
            return Something(self[port])

        # This is the case when the port is being computed
        if port in self.tasks:
            task = self.tasks[port]
            await task
            return Something(task.result())

        return Nothing()

    def maybe_delete(self, port: Port):
        if self.save_memory:
            del self[port]


class PortPuller:

    __slots__ = ['_coroutine', '_out_ports']

    def __init__(self, coroutine, out_ports: T.Iterable[Port]):
        self._coroutine = coroutine
        self._out_ports = list(out_ports)

    async def pull(self, port: Port, session: Session):
        port = _parse_port(port)

        if port not in session:

            # If the port is already being computed, wait until it is done
            if port in session.events:
                await session.events[port]

            else:
                # Lock all involved ports
                for p in self._out_ports:
                    session.events[p] = asyncio.Event()

                # Run the coroutine
                await self._coroutine()

                # Release all involved ports and make sure they were indeed set
                for p in self._out_ports:

                    if p not in session:
                        raise SessionError(f"Port {p} wasn't set by the coroutine, although it should have been")

                    session.events[p].set()

        return session[port]


class Engine:

    def __init__(self, max_threads=None, max_processes=None, stop_timeout=1.5, save_memory=False):

        # The event loop that runs things in this world
        # We run the event loop in another thread much like in https://github.com/alex-sherman/unsync
        self.__loop = asyncio.new_event_loop()

        self.__thread = None
        self.__agents = set()
        self.__max_threads = max_threads
        self.__max_processes = max_processes

        self.__process_pool = None
        self.__thread_pool = None
        self.stop_timeout = stop_timeout

        self.save_memory = save_memory

    @property
    def thread(self):
        return self.__thread

    def __thread_target(self):
        self.loop.run_forever()

    # A context manager that starts the event loop
    def __enter__(self):

        # self.__process_pool = ProcessPoolExecutor(max_workers=self.__max_processes).__enter__()
        self.__process_pool = loky.get_reusable_executor(max_workers=self.__max_processes).__enter__()
        self.__thread_pool = ThreadPoolExecutor(max_workers=self.__max_threads).__enter__()

        # It is absolutely crucial that no exception be thrown here, otherwise we get a deadlock!!
        self.__thread = threading.Thread(target=self.__thread_target)
        self.thread.start()

        return self

    def __stop_event_loop(self):
        """ Gracefully stops the event loop. """

        # Try terminating gracefully
        try:

            # Stop all running agents
            for agent in self.__agents:
                agent.stop()

            self.__agents.clear()

            # Cancel all active tasks in the event loop
            def cancel_tasks():
                for task in asyncio.all_tasks():
                    task.cancel()

            self.loop.call_soon_threadsafe(cancel_tasks)

            # Wait until all tasks (except has_active_tasks, which is itself a task)
            # complete to terminate the event loop
            async def has_active_tasks():
                return len(list(filter(lambda x: x is not asyncio.current_task(), asyncio.all_tasks())))

            while asyncio.run_coroutine_threadsafe(has_active_tasks(), loop=self.loop).result():
                pass

        # Even if something bad happens in the way, we want to be sure to kill the event loop so not to get stuck
        finally:
            # Shutdown the event loop
            self.loop.call_soon_threadsafe(self.loop.stop)

    def __exit__(self, exc_type, exc_val, exc_tb):

        # Gracefully stop the event loop
        self.__stop_event_loop()

        # Wait for the event loop to terminate gracefully
        self.thread.join()
        # self.__thread = None

        self.__process_pool.__exit__(exc_type, exc_val, exc_tb)
        self.__thread_pool.__exit__(exc_type, exc_val, exc_tb)

    @property
    def loop(self):
        return self.__loop

    def fetch_future(self, port: Port, session: Session) -> Future:
        """ Obtain a port's value by pulling on it (done asynchronously).
        Returns a concurrent.futures.Future object """

        if not self.loop.is_running():
            raise EngineError("The Engine's event loop is not running")

        if threading.current_thread() == self.__thread:
            raise EngineError("Cannot be called from the ambient thread")

        # Submit the pull task to the event loop end get a future object
        future = asyncio.run_coroutine_threadsafe(port.pull(session), loop=self.loop)

        return future

    def __call__(self, port: Port, session: Session, timeout=None):
        """ Use fetch_future to obtain the port's value and return the result. Re-raise any exception """

        future = self.fetch_future(port=port, session=session)

        # See if any exception was thrown and re-raise it

        maybe_raise(future.exception(timeout=timeout))

        return future.result(timeout=timeout).value

    def spawn_session(self, *args, **kwargs) -> Session:
        return Session(*args, **kwargs, engine=self, save_memory=self.save_memory)

    def create_task(self, *args, **kwargs):
        return self.loop.create_task(*args, **kwargs)

    def run_coroutine_threadsafe(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def register_agent(self, queue):
        self.__agents.add(queue)

    async def run_in_thread_pool(self, callback) -> None:
        result = await self.loop.run_in_executor(self.__thread_pool, callback)
        return result

    async def run_in_process_pool(self, callback) -> None:
        result = await self.loop.run_in_executor(self.__process_pool, callback)
        return result


# TODO session tags should also be exported
def export_sessions(block: _Block, *sessions: Session, export_children=True) -> T.Dict[uuid.UUID, T.Any]:
    """ Exports the given sessions to a nested dict, maintaining session hierarchy. The port names are
    exported relative to the given block.

    Returns nested dict of the form {UUID:
                                        {'data':
                                            {
                                                <port1 relative path>: value1,
                                                <port1 relative path>: value2, ...
                                            }
                                         'children' : {UUID: ...}}
     """

    dct = OrderedDict()

    # Get the ports (either given or from block's descendants including block)
    # ports = chain(*map(lambda blk: blk.ports, prepend(block,
    #                                                   filter(lambda x: isinstance(x, _Block), block.descendants))))
    ports = chain(*map(lambda blk: blk.ports, prepend(block, block.blocks.descendants)))
    ports = set(ports)

    for session in sessions:

        sess_dct = dct[session.guid] = dict(data={}, children=OrderedDict())

        # Store ports' data using their relative names (rel_name returns None if port is not a descendant of block)
        sess_dct['data'] = {maybe_error(port.rel_name(block),
                                        SessionError(f"Port {port} is not a descendant of block {block}")):
                            session[port] for port in ports & set(session.keys())}

        # Export the children sessions
        if export_children:
            sess_dct['children'] = export_sessions(block, *session.children, export_children=export_children)

        # Remove child sessions without data (works recursively)
        if not sess_dct['data'] and not sess_dct['children']:
            del dct[session.guid]

    return dct


def import_sessions(block: _Block, export_dict: T.Dict[uuid.UUID, T.Any]) -> T.Tuple[Session]:

    # This provides a nested dict attribute access
    block_dict = Cut({block.name: block}, sep=_Block.separator)

    sessions = []
    for guid, sess_dict in export_dict.items():

        session = Session(guid=guid)

        # Set port values
        for rel_name, value in sess_dict['data'].items():

            # Get the port (using the nested path access) and set its value in the current session
            try:
                port = block_dict[rel_name]
            except KeyError:
                raise SessionError(f"Relative port path {rel_name} is not understood relative to block {block}")

            session[port] = value

        # Get the children recursively
        session.children = import_sessions(block, sess_dict['children'])
        sessions.append(session)

    return tuple(sessions)


