import unittest
from core.block import _Block


class TestStructure(unittest.TestCase):

    def setUp(self):
        self.a = _Block(name='a')
        self.b = _Block(name='b')
        self.c = _Block(name='c')
        self.d = _Block(name='d')
        self.e = _Block(name='e')

        self.b.parent = self.a
        self.c.parent = self.a
        self.d.parent = self.c
        self.e.parent = self.c

    def test_contains_instance(self):
        self.assertTrue(self.b in self.a)
        self.assertTrue(self.c in self.a)
        self.assertTrue(self.d in self.c)
        self.assertTrue(self.e in self.c)

    def test_contains_name(self):
        self.assertTrue(self.b.name in self.a)
        self.assertTrue(self.c.name in self.a)
        self.assertTrue(self.d.name in self.c)
        self.assertTrue(self.e.name in self.c)

    def test_access_by_getitem(self):
        self.assertEqual(self.a['c'], self.c)
        self.assertEqual(self.a['c']['e'], self.e)
        self.assertEqual(self.a.blocks['c'], self.c)
        self.assertEqual(self.a.blocks['c']['e'], self.e)

    def test_detach(self):
        self.c.parent = None
        self.assertTrue(self.c not in self.a)
        self.assertTrue(self.c not in self.a.blocks)
        with self.assertRaises(KeyError):
            _ = self.a['c']

        self.assertTrue(self.d in self.c)


class TestConnections(unittest.TestCase):

    def test_in_1out(self):
        r = _Block()
        r.children = _Block('c1'), _Block('c2')
        r['c1'].ports.Out.new('x')
        r['c2'].ports.In.new('x')
        r['c2']['x'] = r['c1']['x']
        self.assertEqual(r['c1']['x'], r['c2']['x'].upstream())
        self.assertTupleEqual(r['c1']['x'].downstream(), (r['c2']['x'],))

    def test_in_2out(self):
        r = _Block()
        r.children = _Block('c1'), _Block('c2'), _Block('c3')
        r['c1'].ports.Out.new('x')
        r['c2'].ports.In.new('x')
        r['c3'].ports.In.new('x')
        r['c2']['x'] = r['c1']['x']
        r['c3']['x'] = r['c1']['x']

        self.assertEqual(r['c1']['x'], r['c2']['x'].upstream())
        self.assertEqual(r['c1']['x'], r['c3']['x'].upstream())
        self.assertSetEqual(set(r['c1']['x'].downstream()), {r['c2']['x'], r['c3']['x']})

    def test_in_1in(self):
        r = _Block()
        r.children = _Block('c'),

        r.ports.In.new('x')
        r['c'].ports.In.new('x')
        r['c']['x'] = r['x']
        self.assertEqual(r['x'], r['c']['x'].upstream())
        self.assertTupleEqual(r['x'].downstream(), (r['c']['x'],))

    # TODO add more tests
