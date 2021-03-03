import unittest
from blox.core.block import Block
from blox.core.special import BinaryOps


class TestOperators(unittest.TestCase):

    def setUp(self):
        self.world = Block(name='world', In='a1-2', Out='b1-2')

    def test_add(self):
        self.world.Out['*'] = self.world.In()[0] + self.world.In()[1], self.world.In()[0] - self.world.In()[1]
        self.assertTrue(self.world.Out()[0].upstream.block.op is BinaryOps.ADD)
        self.assertTrue(self.world.Out()[1].upstream.block.op is BinaryOps.SUB)

