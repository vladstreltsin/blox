import unittest
from blox.core.block import Block


class TestBlockComposition(unittest.TestCase):

    def setUp(self):
        self.world = Block('world', In='a', Out='b')
        self.world['x'] = Block(In='a', Out='b')
        self.world['y'] = Block(In='a', Out='b')
        self.world['z'] = Block(In='a', Out='b1-2')
        self.world['w'] = Block(In='a1-2', Out='b')

    def test_compose(self):
        x = self.world['x']
        y = self.world['y']

        self.world['Out:b'] = y(x.Out())
        self.assertTrue(self.world['Out:b'].upstream is y.Out())
        self.assertTrue(y['In:a'].upstream is x.Out())

    def test_compose_wildcard(self):
        x = self.world['x']
        y = self.world['y']
        self.world.Out['*'] = y(x.Out())
        self.assertTrue(self.world['Out:b'].upstream is y.Out())
        self.assertTrue(y['In:a'].upstream is x.Out())

    def test_connect_multiple(self):
        self.world['z'].In['*'] = self.world.In()
        self.world['w'].In['*'] = self.world['z'].Out()
        self.world.Out['*'] = self.world['w'].Out()

        self.assertTrue(self.world.Out().upstream is self.world['w'].Out())
        self.assertTrue(self.world['w'].In()[0].upstream is self.world['z'].Out()[0])
        self.assertTrue(self.world['w'].In()[1].upstream is self.world['z'].Out()[1])
        self.assertTrue(self.world['z'].In().upstream is self.world.In())

    def test_compose_multiple(self):
        self.world.Out['*'] = self.world['w'](*self.world['z'](self.world.In()))

        self.assertTrue(self.world.Out().upstream is self.world['w'].Out())
        self.assertTrue(self.world['w'].In()[0].upstream is self.world['z'].Out()[0])
        self.assertTrue(self.world['w'].In()[1].upstream is self.world['z'].Out()[1])
        self.assertTrue(self.world['z'].In().upstream is self.world.In())

    def test_compose_floating_block(self):
        self.world.Out['*'] = Block('x', In='a', Out='b')(self.world.In())
        self.assertTrue('x1' in self.world.blocks)
        self.assertTrue(self.world.Out().upstream is self.world['x1'].Out())
        self.assertTrue(self.world['x1'].In().upstream is self.world.In())

    def test_compose_floating_port(self):
        self.world.Out['*'] = Block('x', In='a1-2', Out='b')(self.world.In(), Block('x', Out='c').Out())
        self.assertTrue('x1' in self.world.blocks)
        self.assertTrue('x2' in self.world.blocks)
        self.assertTrue(self.world['x1'].In()[1].upstream is self.world['x2'].Out())
        self.assertTrue(self.world['x1'].In()[0].upstream is self.world.In())

