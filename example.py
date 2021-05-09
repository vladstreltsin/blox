from blox.core.block import Block
from blox.core.compute import Computable
from blox.core.state import State
from blox.vis.elk import ElkDiagram

world = Computable(name='world', In=('a', 'b'), Out=('c', 'd', 'e'))
p1 = world.In['a'] + world.In['b']
p2 = world.In['a'] - world.In['b']
world.Out['c'] = p1
world.Out['d'] = p2
world.Out['e'] = p2 * (-(p1 * p2) + p1 + world.In['a'])

state = State()
state[world.In['a']] = 2
state[world.In['b']] = 4


print(state(world.Out['c']))
print(state(world.Out['d']))
print(state(world.Out['e']))

