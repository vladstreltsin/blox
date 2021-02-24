from .block import Block, Port, BlockError
from .engine import Session, Engine, PortPuller
import asyncio
import typing as T
from ..utils import maybe_or, identity
from ..maybe import Something, Nothing, maybe
import threading
import time
from functools import partial


class GeneratorError(Exception):
    pass


# class GeneratorTask:
#
#     __slots__ = ['sessions', 'task']
#
#     def __init__(self, sessions: T.List[Session], task: asyncio.Task):
#         self.sessions = sessions
#         self.task = task


# class Generator(Block):
#     """ A block that always pulls on its input ports maintaining a queue of values """
#
#     def __init__(self,
#                  queue_size,
#                  batch_sampler: T.Iterable,
#                  keep_sessions=True,
#                  task_delay=0.00,
#                  stop_timeout=5.,
#                  collate_fn=None,
#                  *args, **kwargs):
#         super(Generator, self).__init__(*args, **kwargs, In='data', AuxOut='key')
#         self.lock_ports = True
#         self.atomic = True
#
#         self.__queue = None
#         self.__produce_task = None
#         self.__queue_size = queue_size
#         self.__engine = None
#         self.__collate_fn = maybe_or(collate_fn, identity)
#         self.__batch_sampler = batch_sampler
#
#         self.task_delay = task_delay
#         self.stop_timeout = stop_timeout
#         self.keep_sessions = keep_sessions
#
#         # Lock port names because we refer to them explicitly
#         self.key.lock_name = True
#
#     def propagate(self, session):
#         raise NotImplementedError(f'A {self.__class__.__name__} cannot propagate')
#
#     @property
#     def qsize(self):
#         return maybe(self.__queue).qsize().or_else(0)
#
#     @property
#     def engine(self) -> T.Optional[Engine]:
#         return self.__engine
#
#     @property
#     def batch_sampler(self):
#         return self.__batch_sampler
#
#     def __batch_sampler_gen(self):
#         """ Yields samples from the batch sampler indefinitely """
#         while True:
#             yield from self.batch_sampler
#
#     def __start(self, session):
#         """ Start the queue. Will be run by the first output pull from the Engine thread """
#         self.__engine = session.engine
#         if threading.current_thread() != self.engine.thread:
#             raise GeneratorError("Queue start must be run from the engine thread")
#         if self.running:
#             raise GeneratorError("Queue is already running")
#
#         self.__queue = asyncio.Queue(maxsize=self.__queue_size, loop=session.engine.loop)
#
#         # Start the production task
#         self.__produce_task = self.engine.create_task(self.__produce())
#         self.__engine.register_agent(self)
#
#     def stop(self):
#         """ Stop the queue. Will be run from the main thread """
#         if threading.current_thread() == self.engine.thread:
#             raise GeneratorError("Queue stop can't be run from the engine thread")
#         if not self.running:
#             raise GeneratorError("Queue is already stopped")
#
#         self.__produce_task.cancel()
#
#         # Empty the queue and cancel all tasks still inside it
#         while True:
#             try:
#                 sampler_task = self.__queue.get_nowait()
#                 sampler_task.task.cancel()
#                 self.__queue.task_done()
#
#             except asyncio.QueueEmpty:
#                 break
#
#         self.__produce_task = None
#
#     @property
#     def running(self):
#         return self.__produce_task is not None
#
#     async def __produce(self):
#         """ A task that spawns pull tasks to fill up the queue """
#
#         # TODO: Exceptions here are not propagated and everything stalls
#
#         async def pull_batch(session_list):
#             value = await asyncio.gather(*[self.In[0].pull(s) for s in session_list])
#             return value
#
#         for key_batch in self.__batch_sampler_gen():
#
#             # Creates a batch of sessions, each with a key from the key_batch and pulls on all of them in parallel
#             sessions = []
#             for key in key_batch:
#                 sess = self.engine.spawn_session()
#                 sess[self.AuxOut()] = key
#                 sessions.append(sess)
#
#             task = self.engine.create_task(pull_batch(tuple(sessions)))
#
#             # Put the task on the queue and maybe wait a little to be nice to others
#             await self.__queue.put(GeneratorTask(sessions=sessions, task=task))
#             await asyncio.sleep(self.task_delay)
#
#         # We should never get here because the loop should run indefinitely
#         raise GeneratorError("Generator Exhausted")
#
#     async def pull(self, port: Port, session: Session):
#
#         if port not in self:
#             raise BlockError(f"Port {port} does't belong to the block {self}")
#
#         # Input port and aux port are pulled normally
#         if port.is_in or port.auxiliary:
#             return await super(Generator, self).pull(port, session=session)
#
#         # The output port is special
#         # Start the queue if it wasn't running
#         if not self.running:
#             self.__start(session)
#
#         if session.engine is not self.engine:
#             raise GeneratorError("Session is bound to a different engine")
#
#         # Try getting the port's value if it was computed or is being computed
#         result: T.Union[Something, Nothing] = await session.aget(port)
#         if result.is_some():
#             return result.value
#
#         async def pull_queue():
#
#             generator_task: GeneratorTask = await self.__queue.get()
#             await generator_task.task
#
#             self.__queue.task_done()  # Signal the queue that pulled task is completed
#
#             # Unpack the task
#             sessions = generator_task.sessions
#             task = generator_task.task
#
#             # Attach sub-session to the parent if sub-sessions are to be kept
#             if self.keep_sessions:
#                 for sess in sessions:
#                     sess.parent = session
#
#             # Get the values from the task result
#             data = [x.value for x in task.result()]
#
#             # When there is just one output port the data goes "as is"
#             if len(self.Out) == 1:
#                 for sess, d in zip(sessions, data):
#                     sess[port] = d
#
#             # When there are multiple output ports we distribute the values either using dictionary keys
#             # when data is a dictionary or by the output port numbers
#             else:
#                 for sess, d in zip(sessions, data):
#                     if not hasattr(d, '__len__'):
#                         raise GeneratorError(f"Data has no __len__ but generator has "
#                                              f"more than one output port")
#                     if len(d) != len(self.Out):
#                         raise GeneratorError(f"Data size ({len(d)}) doesn't match the "
#                                              f"expected number of outputs ({len(self.Out)})")
#
#                     # Convert d to a dictionary if it isn't already
#                     if not isinstance(d, dict):
#                         d = {n: x for n, x in enumerate(d)}
#
#                     # Set output ports
#                     for n, x in d.items():
#                         sess[self.Out[n]] = x
#
#             return sessions
#
#         pull_queue_task = session.engine.create_task(pull_queue())
#
#         # This task will compute the data for each port
#         async def get_port(p):
#             sessions = await pull_queue_task
#             value = self.__collate_fn([sess[p].value for sess in sessions])
#             return value
#
#         # Lock the ports with the tasks
#         for out_port in self.Out:
#             session.tasks[out_port] = session.engine.create_task(get_port(out_port))
#
#         # Wait until the tasks complete, set outputs and erase tasks
#
#         for out_port in self.Out:
#
#             await session.tasks[out_port]
#             session[out_port] = session.tasks[out_port].result()
#             del session.tasks[out_port]
#
#         return session[port]
#

class Generator(Block):
    """ A block that always pulls on its input ports maintaining a queue of values """

    def __init__(self,
                 queue_size,
                 batch_sampler: T.Iterable,
                 keep_sessions=True,
                 task_delay=0.00,
                 stop_timeout=5.,
                 collate_fn=None,
                 *args, **kwargs):
        super(Generator, self).__init__(*args, **kwargs, In='data', AuxOut='key')
        self.lock_ports = True
        self.atomic = True

        self.__queue = None
        self.__produce_task = None
        self.__queue_size = queue_size
        self.__engine = None
        self.__collate_fn = maybe_or(collate_fn, identity)
        self.__batch_sampler = batch_sampler

        self.task_delay = task_delay
        self.stop_timeout = stop_timeout
        self.keep_sessions = keep_sessions

        # Lock port names because we refer to them explicitly
        self.key.lock_name = True

    def propagate(self, session):
        raise NotImplementedError(f'A {self.__class__.__name__} cannot propagate')

    @property
    def qsize(self):
        return maybe(self.__queue).qsize().or_else(0)

    @property
    def engine(self) -> T.Optional[Engine]:
        return self.__engine

    @property
    def batch_sampler(self):
        return self.__batch_sampler

    def __batch_sampler_gen(self):
        """ Yields samples from the batch sampler indefinitely """
        while True:
            yield from self.batch_sampler

    def __start(self, session):
        """ Start the queue. Will be run by the first output pull from the Engine thread """
        self.__engine = session.engine
        if threading.current_thread() != self.engine.thread:
            raise GeneratorError("Queue start must be run from the engine thread")
        if self.running:
            raise GeneratorError("Queue is already running")

        self.__queue = asyncio.Queue(maxsize=self.__queue_size, loop=session.engine.loop)

        # Start the production task
        self.__produce_task = self.engine.create_task(self.__produce())
        self.__engine.register_agent(self)

    def stop(self):
        """ Stop the queue. Will be run from the main thread """
        if threading.current_thread() == self.engine.thread:
            raise GeneratorError("Queue stop can't be run from the engine thread")
        if not self.running:
            raise GeneratorError("Queue is already stopped")

        self.__produce_task.cancel()

        # Empty the queue and cancel all tasks still inside it
        while True:
            try:
                _ = self.__queue.get_nowait()
                # sampler_task.task.cancel()
                self.__queue.task_done()

            except asyncio.QueueEmpty:
                break

        self.__produce_task = None

    @property
    def running(self):
        return self.__produce_task is not None

    async def __produce(self):
        """ A task that spawns pull tasks to fill up the queue """

        # TODO: Exceptions here are not propagated and everything stalls

        async def pull_batch(session_list):
            # for s in session_list:
            #     await self.In().pull(s)
            # return await asyncio.gather(*[self.In().pull(s) for s in session_list])
            return [await self.In().pull(s) for s in session_list]

        for key_batch in self.__batch_sampler_gen():

            # Creates a batch of sessions, each with a key from the key_batch and pulls on all of them in parallel
            sessions = []
            for key in key_batch:
                sess = self.engine.spawn_session()
                sess[self.AuxOut()] = key
                sessions.append(sess)

            # Pull the batch and put the results on the queue
            results = await pull_batch(sessions)
            await self.__queue.put((sessions, results))

            # await asyncio.sleep(self.task_delay)

        # We should never get here because the loop should run indefinitely
        raise GeneratorError("Generator Exhausted")

    # async def pull(self, port: Port, session: Session):
    #
    #     if port not in self:
    #         raise BlockError(f"Port {port} does't belong to the block {self}")
    #
    #     # Input port and aux port are pulled normally
    #     if port.is_in or port.auxiliary:
    #         return await super(Generator, self).pull(port, session=session)
    #
    #     # The output port is special
    #     # Start the queue if it wasn't running
    #     if not self.running:
    #         self.__start(session)
    #
    #     if session.engine is not self.engine:
    #         raise GeneratorError("Session is bound to a different engine")
    #
    #     # Try getting the port's value if it was computed or is being computed
    #     result: T.Union[Something, Nothing] = await session.aget(port)
    #     if result.is_some():
    #         return result.value
    #
    #     async def pull_queue():
    #
    #         generator_task: GeneratorTask = await self.__queue.get()
    #         await generator_task.task
    #
    #         self.__queue.task_done()  # Signal the queue that pulled task is completed
    #
    #         # Unpack the task
    #         sessions = generator_task.sessions
    #         task = generator_task.task
    #
    #         # Attach sub-session to the parent if sub-sessions are to be kept
    #         if self.keep_sessions:
    #             for sess in sessions:
    #                 sess.parent = session
    #
    #         # Get the values from the task result
    #         data = [x.value for x in task.result()]
    #
    #         # When there is just one output port the data goes "as is"
    #         if len(self.Out) == 1:
    #             for sess, d in zip(sessions, data):
    #                 sess[port] = d
    #
    #         # When there are multiple output ports we distribute the values either using dictionary keys
    #         # when data is a dictionary or by the output port numbers
    #         else:
    #             for sess, d in zip(sessions, data):
    #                 if not hasattr(d, '__len__'):
    #                     raise GeneratorError(f"Data has no __len__ but generator has "
    #                                          f"more than one output port")
    #                 if len(d) != len(self.Out):
    #                     raise GeneratorError(f"Data size ({len(d)}) doesn't match the "
    #                                          f"expected number of outputs ({len(self.Out)})")
    #
    #                 # Convert d to a dictionary if it isn't already
    #                 if not isinstance(d, dict):
    #                     d = {n: x for n, x in enumerate(d)}
    #
    #                 # Set output ports
    #                 for n, x in d.items():
    #                     sess[self.Out[n]] = x
    #
    #         return sessions
    #
    #     pull_queue_task = session.engine.create_task(pull_queue())
    #
    #     # This task will compute the data for each port
    #     async def get_port(p):
    #         sessions = await pull_queue_task
    #         value = self.__collate_fn([sess[p].value for sess in sessions])
    #         return value
    #
    #     # Lock the ports with the tasks
    #     for out_port in self.Out:
    #         session.tasks[out_port] = session.engine.create_task(get_port(out_port))
    #
    #     # Wait until the tasks complete, set outputs and erase tasks
    #
    #     for out_port in self.Out:
    #
    #         await session.tasks[out_port]
    #         session[out_port] = session.tasks[out_port].result()
    #         del session.tasks[out_port]
    #
    #     return session[port]
    #
    #
    async def pull(self, port: Port, session: Session):

        if port not in self:
            raise BlockError(f"Port {port} does't belong to the block {self}")

        # Input port and aux port are pulled normally
        if port.is_in or port.auxiliary:
            return await super(Generator, self).pull(port, session=session)

        # The output port is special
        # Start the queue if it wasn't running
        if not self.running:
            self.__start(session)

        if session.engine is not self.engine:
            raise GeneratorError("Session is bound to a different engine")

        async def pull_from_queue(obj, sess, queue, collate_fn):

            # Get a value from the queue
            sessions, result = await queue.get()
            queue.task_done()

            # Attach sub-session to the parent if sub-sessions are to be kept
            if obj.keep_sessions:
                for s in sessions:
                    s.parent = sess

            # Strip off the PortData object
            data = [x.value for x in result]

            # When there is just one output port the data goes "as is"
            if len(obj.Out) == 1:
                for s, d in zip(sessions, data):
                    s[obj.Out()] = d

            # When there are multiple output ports we distribute the values either using dictionary keys
            # when data is a dictionary or by the output port numbers
            else:
                for s, d in zip(sessions, data):
                    if not hasattr(d, '__len__'):
                        raise GeneratorError(f"Data has no __len__ but generator has "
                                             f"more than one output port")
                    if len(d) != len(obj.Out):
                        raise GeneratorError(f"Data size ({len(d)}) doesn't match the "
                                             f"expected number of outputs ({len(obj.Out)})")

                    # Convert d to a dictionary if it isn't already
                    if not isinstance(d, dict):
                        d = {n: x for n, x in enumerate(d)}

                    # Set output ports on the child sessions
                    for n, x in d.items():
                        s[obj.Out[n]] = x

            # Set the output ports on the calling session
            for p in obj.Out:
                sess[p] = collate_fn([s[p].value for s in sessions])

        return await PortPuller(partial(pull_from_queue, obj=self, sess=session, queue=self.__queue,
                                        collate_fn=self.__collate_fn), out_ports=self.Out).pull(port, session)

        # # Try getting the port's value if it was computed or is being computed
        # result: T.Union[Something, Nothing] = await session.aget(port)
        # if result.is_some():
        #     return result.value
        #
        # async def pull_queue():
        #
        #     generator_task: GeneratorTask = await self.__queue.get()
        #     await generator_task.task
        #
        #     self.__queue.task_done()  # Signal the queue that pulled task is completed
        #
        #     # Unpack the task
        #     sessions = generator_task.sessions
        #     task = generator_task.task
        #
        #     # Attach sub-session to the parent if sub-sessions are to be kept
        #     if self.keep_sessions:
        #         for sess in sessions:
        #             sess.parent = session
        #
        #     # Get the values from the task result
        #     data = [x.value for x in task.result()]
        #
        #     # When there is just one output port the data goes "as is"
        #     if len(self.Out) == 1:
        #         for sess, d in zip(sessions, data):
        #             sess[port] = d
        #
        #     # When there are multiple output ports we distribute the values either using dictionary keys
        #     # when data is a dictionary or by the output port numbers
        #     else:
        #         for sess, d in zip(sessions, data):
        #             if not hasattr(d, '__len__'):
        #                 raise GeneratorError(f"Data has no __len__ but generator has "
        #                                      f"more than one output port")
        #             if len(d) != len(self.Out):
        #                 raise GeneratorError(f"Data size ({len(d)}) doesn't match the "
        #                                      f"expected number of outputs ({len(self.Out)})")
        #
        #             # Convert d to a dictionary if it isn't already
        #             if not isinstance(d, dict):
        #                 d = {n: x for n, x in enumerate(d)}
        #
        #             # Set output ports
        #             for n, x in d.items():
        #                 sess[self.Out[n]] = x
        #
        #     return sessions
        #
        # pull_queue_task = session.engine.create_task(pull_queue())
        #
        # # This task will compute the data for each port
        # async def get_port(p):
        #     sessions = await pull_queue_task
        #     value = self.__collate_fn([sess[p].value for sess in sessions])
        #     return value
        #
        # # Lock the ports with the tasks
        # for out_port in self.Out:
        #     session.tasks[out_port] = session.engine.create_task(get_port(out_port))
        #
        # # Wait until the tasks complete, set outputs and erase tasks
        #
        # for out_port in self.Out:
        #
        #     await session.tasks[out_port]
        #     session[out_port] = session.tasks[out_port].result()
        #     del session.tasks[out_port]
        #
        # return session[port]

