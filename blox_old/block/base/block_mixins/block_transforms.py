from __future__ import annotations
from blox_old.exceptions import BlockError, PortError
from blox_old.utils.funcs import maybe_or, camel_to_snake, parse_ports
from functools import partial
from itertools import chain
import typing as tp

if tp.TYPE_CHECKING:
    from blox_old.block.base.port_base import Port


class BlockTransformsMixin:

    @property
    def In(self):
        raise NotImplementedError

    @property
    def Out(self):
        raise NotImplementedError

    @classmethod
    def wrap(cls, **kwargs):
        """ Use this method to convert function definition into block instances """

        def create_block(wrapped_fn) -> cls:

            def block_builder(fn, *, name=None, **fn_kwargs):

                # Obtain the non-keyword arguments of fn - these will serve as input port names
                num_in_ports = fn.__code__.co_argcount
                in_port_names = fn.__code__.co_varnames[0:num_in_ports]

                # Get the Out argument if it is there
                Out = kwargs.pop('Out') if 'Out' in kwargs else None

                default_name = camel_to_snake(fn.__code__.co_name)
                params = dict(name=maybe_or(name, default_name), In=in_port_names)
                params.update(kwargs)

                # Initialize the block with given input ports and the wrapped function name
                block = cls(**params)
                block.auto_rename = True

                # Get the function outputs
                out = fn(*block.In, **fn_kwargs)

                from blox_old.block.base.port_base import Port
                if not isinstance(out, tuple) and not isinstance(out, list) and not isinstance(out, Port):
                    raise BlockError("Wrapped function must return either a single port, a list or a tuple of ports")

                # Make sure out is iterable
                if isinstance(out, Port):
                    out = (out,)

                # Determine the output names
                if Out is None:
                    Out = parse_ports(len(out), default_prefix='o') if not isinstance(out, Port) else 1
                else:
                    Out = parse_ports(Out, default_prefix='o')
                    if len(Out) != len(out):
                        raise BlockError("The number of returned ports doesn't match the specified number of ports")

                for name, port in zip(Out, out):
                    block.Out.new(name)
                    block.Out[name] = port

                return block

            # The decorators returns a function that creates an instance of the block, like a constructor
            return partial(block_builder, wrapped_fn)

        return create_block

    @classmethod
    def pack(cls, blocks, *args, **kwargs) -> None:
        """ Pack provided blocks in a new block of the given class """

        if not blocks:
            raise BlockError("At least one block must be provided")

        # The new block will be added here
        parent = blocks[0].parent

        # All of the blocks must share the same parent
        if not all(blk.parent is parent for blk in blocks):
            raise BlockError("All of the blocks must share the same parent")

        # Store all existing connections
        connections = set()
        for port in chain.from_iterable([blk.ports for blk in blocks]):

            if port.is_in:
                connections.update((ups, port) for ups in port.upstream)
            else:
                connections.update((port, dws) for dws in port.downstream)

        # Create a new block instance and place in under the parent
        block = cls(*args, **kwargs, parent=parent)

        # Move blocks under parent block
        for blk in blocks:
            blk.parent = block

        # Restore connections
        for p1, p2 in connections:
            try:
                p1.feed(p2)

            # If connection adding has failed, it probably means that this is an external connection,
            # therefore we add an intermediate port
            except PortError:

                def add_proxy_from(p):
                    if p.is_in and not p.auxiliary:
                        return block.In.new(f'{p.block.name}_{p.name}')

                    elif p.is_in and p.auxiliary:
                        return block.AuxIn.new(f'{p.block.name}_{p.name}')

                    elif not p.is_in and not p.auxiliary:
                        return block.Out.new(f'{p.block.name}_{p.name}')

                    else:
                        return block.AuxOut.new(f'{p.block.name}_{p.name}')

                # The case when p1 is outside
                if p2.block.parent is block:
                    new_port = add_proxy_from(p2)

                # The case when p2 is outside
                else:
                    # Add new port
                    new_port = add_proxy_from(p1)

                p1.feed(new_port)
                new_port.feed(p2)

        block.ports.sort()

    def __call__(self, *args, **kwargs) -> tp.Union[None, Port, tp.Tuple[Port]]:
        """
        This method allows composing blocks over ports.
        Connects the block's inputs to the provided ports
        """
        from blox_old.block.base.port_section import BlockPortsSection

        # Handle the case when In and Out are passed without ()
        args = list(chain(*map(lambda arg: [arg] if not isinstance(arg, BlockPortsSection) else arg, args)))

        if len(args) + len(kwargs) > len(self.In):
            raise BlockError(f"Too many inputs provided, expected at most: {len(self.In)}, "
                             f"given: {len(args) + len(kwargs)}")

        for port_name, src in chain(zip(self.In.keys(), args), kwargs.items()):
            self.In[port_name] = src

        # Return the output ports
        return self.Out()
