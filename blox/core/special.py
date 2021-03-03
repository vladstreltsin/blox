from blox.core.block import Block
from enum import Enum


class BinaryOps(Enum):
    ADD = 0,
    SUB = 1,
    MUL = 2,
    MATMUL = 3,
    TRUEDIV = 4,
    FLOORDIV = 5,
    MOD = 5,
    DIVMOD = 6,
    POW = 7,
    LSHIFT = 8,
    RSHIFT = 9,
    AND = 10,
    XOR = 11,
    OR = 12


class UnaryOps(Enum):
    NEG = 0,
    POS = 1,
    ABS = 2,
    INVERT = 3,


class UnaryOperator(Block):

    def __init__(self, op):
        super(UnaryOperator, self).__init__(name=op.lower(), In=['in'], Out=['out'])
        self.op = UnaryOps[op.upper()]


class BinaryOperator(Block):

    def __init__(self, op):
        super(BinaryOperator, self).__init__(name=op.lower(), In=['in1', 'in2'], Out=['out'])
        self.op = BinaryOps[op.upper()]


class GetOperator(Block):
    def __init__(self):
        super(GetOperator, self).__init__(name='get', In=['in', 'sel'], Out=['out'])


class ApplyOperator(Block):
    def __init__(self):
        super(ApplyOperator, self).__init__(name='apply', In=['func', 'in'], Out=['out'])


class Const(Block):

    def __init__(self, value):
        super(Const, self).__init__(name=None, Out='out')
        self._value = value
