from blox.core.block import Block
from blox.core.compute import Computable
from blox.core.state import State
from blox.vis.elk import ElkDiagram

world = Computable(name='world', In='a1-2', Out='b')
p = world.In()[0] + world.In()[1]
q = world.In()[0] * world.In()[1]
r = p + q + world.In()[0]
t = r + q
world.Out['*'] = t

state = State()
state[world.In()[0]] = 4
state[world.In()[1]] = 2
print(state.compute(world.Out()))
# world.propagate(state)
# print(state[world.Out()])
# x = state.compute(world.Out())

# print(world.toposort._changed)
# world['a'] = Block()
# print(world.toposort._changed)
# world.toposort._sort()
# print(world.toposort._changed)
# print(ElkDiagram(world).to_dict())

# state = State()
#
# world = Block(name='world', In='a', Out='b')
#
# world.Out['*'] = world.In()
#
# state[world.In()] = 42
# print(state.compute(world.Out()))

