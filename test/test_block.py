import unittest
from blox.core.block import Block
from blox.etc.errors import NameCollisionError


class TestBlockAttachDetach(unittest.TestCase):

    def setUp(self):
        """ Setup the structure:  y -> x <- z """
        self.x = Block()
        self.x.name = 'x'
        self.x.blocks['y'] = self.y = Block()
        self.x.blocks['z'] = self.z = Block()

    def test_blocks_list(self):
        self.assertListEqual(list(self.x.blocks), [self.y, self.z])

    def test_blocks_contain_blocks(self):
        self.assertTrue(self.y in self.x.blocks)
        self.assertTrue(self.z in self.x.blocks)

    def test_blocks_contain_names(self):
        self.assertTrue(self.y.name in self.x.blocks)
        self.assertTrue(self.z.name in self.x.blocks)

    def test_blocks_not_contain(self):
        z = Block()     # This block must not be in self.x.blocks even though it as the same name
        z.name = 'z'
        self.assertTrue(z not in self.x.blocks)

    def test_name_collision(self):
        z = Block()
        z.name = 'z'
        with self.assertRaises(NameCollisionError):
            z.parent = self.x

    def test_setitem(self):
        self.x.blocks['u'] = Block()
        self.assertTrue('u' in self.x.blocks)

    def test_delitem(self):
        del self.x.blocks['y']
        self.assertTrue(len(self.x.blocks) == 1)
        self.assertTrue('y' not in self.x.blocks)


class TestBlockRename(unittest.TestCase):

    def setUp(self):
        """ Setup the structure:  y -> x <- z """
        self.x = Block()
        self.x.name = 'x'
        self.x.blocks['y'] = self.y = Block()
        self.x.blocks['z'] = self.z = Block()

    def test_rename_root(self):
        self.x.name = 'xxx'
        self.assertTrue(self.x.name == 'xxx')

    def test_rename_child(self):
        self.y.name = 'yyy'
        self.assertTrue(self.y.name == 'yyy')
        self.assertTrue('yyy' in self.x.blocks)
        self.assertTrue(self.x.blocks['yyy'] is self.y)

    def test_bad_rename_child(self):
        with self.assertRaises(NameCollisionError):
            self.y.name = 'z'

    def test_bad_rename_two_children(self):
        self.y.name = 'new_name'
        with self.assertRaises(NameCollisionError):
            self.z.name = 'new_name'

    def test_bad_rename_after_remove(self):
        self.y.name = 'new_name'
        self.y.parent = None
        self.z.name = 'new_name'
        with self.assertRaises(NameCollisionError):
            self.y.parent = self.x
