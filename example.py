from blox.core.block import Block
from blox.core.state import State
from blox.vis.elk import ElkDiagram

world = Block(name='world', In='a1-2', Out='b1-2')
world.Out['*'] = world['In:a1'] + world.In()[1], world.In()[0] - world.In()[1]

print(world.In()[0])
# print(ElkDiagram(world).to_dict())

# state = State()
#
# world = Block(name='world', In='a', Out='b')
#
# world.Out['*'] = world.In()
#
# state[world.In()] = 42
# print(state.compute(world.Out()))

