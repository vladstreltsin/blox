import unittest
from blox.core.block import Block
from blox.core.port import Port
from blox.etc.errors import PortConnectionError


class TestPortConnect(unittest.TestCase):

    def setUp(self):
        self.x = Block(name='x')
        self.y = self.x.blocks['y'] = Block()
        self.z = self.x.blocks['z'] = Block()
        self.w = self.z.blocks['w'] = Block()

        self.x.In['p'] = Port()
        self.x.Out['p'] = Port()
        self.y.In['p'] = Port()
        self.y.Out['p'] = Port()
        self.z.In['p'] = Port()
        self.z.Out['p'] = Port()
        self.w.In['p'] = Port()
        self.w.Out['p'] = Port()

    def test_connect_x_in_to_y_in(self):
        self.y.In['p'] = self.x.In['p']
        self.assertTrue(self.y.In['p'] in self.x.In['p'].downstream)

    def test_connect_y_in_to_x_in(self):
        with self.assertRaises(PortConnectionError):
            self.x.In['p'] = self.y.In['p']

    def test_connect_x_in_to_y_in_downstream(self):
        self.x.In['p'].downstream.add(self.y.In['p'])
        self.assertTrue(self.y.In['p'] in self.x.In['p'].downstream)

    def test_connect_y_in_to_x_in_downstream(self):
        with self.assertRaises(PortConnectionError):
            self.y.In['p'].downstream.add(self.x.In['p'])

    def test_connect_x_in_to_x_out(self):
        self.x.Out['p'] = self.x.In['p']
        self.assertTrue(self.x.Out['p'] in self.x.In['p'].downstream)

    # A self loop of a floating block
    def test_connect_x_out_to_x_in(self):
        with self.assertRaises(PortConnectionError):
            self.x.In['p'] = self.x.Out['p']

    def test_connect_y_in_to_y_out(self):
        self.y.Out['p'] = self.y.In['p']
        self.assertTrue(self.y.Out['p'] in self.y.In['p'].downstream)

    # Self loop
    def test_connect_y_out_to_y_in(self):
        self.y.In['p'] = self.y.Out['p']
        self.assertTrue(self.y.In['p'] in self.y.Out['p'].downstream)

    # Illegal connections
    def test_connect_x_in_to_y_out(self):
        with self.assertRaises(PortConnectionError):
            self.y.Out['p'] = self.x.In['p']

    def test_connect_y_out_to_x_in(self):
        with self.assertRaises(PortConnectionError):
            self.x.In['p'] = self.y.Out['p']

    def test_connect_y_in_to_x_out(self):
        with self.assertRaises(PortConnectionError):
            self.x.Out['p'] = self.y.In['p']

    def test_connect_x_out_to_y_in(self):
        with self.assertRaises(PortConnectionError):
            self.y.In['p'] = self.x.Out['p']

    def test_connect_y_in_to_z_out(self):
        with self.assertRaises(PortConnectionError):
            self.z.Out['p'] = self.y.In['p']

    def test_connect_y_in_to_z_in(self):
        with self.assertRaises(PortConnectionError):
            self.z.In['p'] = self.y.In['p']

    def test_connect_y_out_to_z_out(self):
        with self.assertRaises(PortConnectionError):
            self.z.Out['p'] = self.y.Out['p']

    def test_connect_y_out_to_z_in(self):
        self.z.In['p'] = self.y.Out['p']
        self.assertTrue(self.z.In['p'] in self.y.Out['p'].downstream)

    # Connecting between incompatible levels
    def test_connect_x_in_to_w_in(self):
        with self.assertRaises(PortConnectionError):
            self.w.In['p'] = self.x.In['p']

    def test_connect_x_in_to_w_out(self):
        with self.assertRaises(PortConnectionError):
            self.w.Out['p'] = self.x.In['p']

    def test_connect_x_out_to_w_in(self):
        with self.assertRaises(PortConnectionError):
            self.w.In['p'] = self.x.Out['p']

    def test_connect_x_out_to_w_out(self):
        with self.assertRaises(PortConnectionError):
            self.w.Out['p'] = self.x.Out['p']

    def test_connect_y_in_to_w_in(self):
        with self.assertRaises(PortConnectionError):
            self.w.In['p'] = self.y.In['p']

    def test_connect_y_in_to_w_out(self):
        with self.assertRaises(PortConnectionError):
            self.w.Out['p'] = self.y.In['p']

    def test_connect_y_out_to_w_in(self):
        with self.assertRaises(PortConnectionError):
            self.w.In['p'] = self.y.Out['p']

    def test_connect_y_out_to_w_out(self):
        with self.assertRaises(PortConnectionError):
            self.w.Out['p'] = self.y.Out['p']


class TestPortAppend(unittest.TestCase):

    def setUp(self):
        self.x = Block(name='x')
        self.y = self.x.blocks['y'] = Block()
        self.z = self.x.blocks['z'] = Block()
        self.w = self.z.blocks['w'] = Block()

        self.x.In['p'] = Port()
        self.x.Out['p'] = Port()
        self.y.In['p'] = Port()
        self.y.Out['p'] = Port()
        self.z.In['p'] = Port()
        self.z.Out['p'] = Port()
        self.w.In['p'] = Port()
        self.w.Out['p'] = Port()

    def add_x_in(self):
        self.x.In['q'] = Port()
        self.x.Out['p'] = self.x.In['q']
        self.assertTrue(self.x.Out['p'] in self.x.In['q'].downstream)

    def add_x_out(self):
        self.x.Out['q'] = Port()
        self.x.Out['q'] = self.x.In['p']
        self.assertTrue(self.x.Out['q'] in self.x.In['p'].downstream)


class TestPortDelete(unittest.TestCase):

    def setUp(self):
        self.x = Block(name='x')
        self.y = self.x.blocks['y'] = Block()
        self.z = self.x.blocks['z'] = Block()
        self.w = self.z.blocks['w'] = Block()

        self.x.In['p'] = Port()
        self.x.Out['p'] = Port()
        self.y.In['p'] = Port()
        self.y.Out['p'] = Port()
        self.z.In['p'] = Port()
        self.z.Out['p'] = Port()
        self.w.In['p'] = Port()
        self.w.Out['p'] = Port()

        self.y.In['p'] = self.x.In['p']
        self.y.Out['p'] = self.y.In['p']
        self.z.In['p'] = self.y.Out['p']
        self.w.In['p'] = self.z.In['p']
        self.w.Out['p'] = self.w.In['p']
        self.z.Out['p'] = self.w.Out['p']
        self.x.Out['p'] = self.z.Out['p']

    def test_remove_w(self):
        self.w.parent = None
        self.assertTrue(len(self.z.In['p'].downstream) == 0)
        self.assertTrue(self.z.Out['p'].upstream is None)
        self.assertTrue(len(self.w.Out['p'].downstream) == 0)
        self.assertTrue(self.w.In['p'].upstream is None)

    def test_remove_z(self):
        self.z.parent = None
        self.assertTrue(len(self.y.Out['p'].downstream) == 0)
        self.assertTrue(self.x.In['p'].upstream is None)
        self.assertTrue(self.w.In['p'] in self.z.In['p'].downstream)
        self.assertTrue(self.z.Out['p'] in self.w.Out['p'].downstream)

    def steal_upstream(self):
        self.y.In['q'] = Port()


