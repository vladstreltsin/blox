from blox.core.compute import AtomicFunction
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


class UnaryOperator(AtomicFunction):

    OPS = {
        'neg': '__neg__',
        'pos': '__pos__',
        'abs': '__abs__',
        'invert': '__invert__',
    }

    def __init__(self, op):
        super(UnaryOperator, self).__init__(name=op.lower(), In=['in'], Out=['out'])
        self.op = self.OPS[op.lower()]

    def callback(self, ports, meta):
        return getattr(ports['in'], self.op)()


class BinaryOperator(AtomicFunction):

    OPS = {
        'add': '__add__',
        'sub': '__sub__',
        'mul': '__mul__',
        'matmul': '__matmul__',
        'truediv': '__truediv__',
        'floordiv': '__floordiv__',
        'mod': '__mod__',
        'divmod': '__divmod__',
        'pow': '__pow__',
        'lshift': '__lshift__',
        'rshift': '__rshift__',
        'and': '__and__',
        'xor': '__xor__',
        'or': '__or__'
    }

    def __init__(self, op):
        super(BinaryOperator, self).__init__(name=op.lower(), In=['in1', 'in2'], Out=['out'])
        self.op = self.OPS[op.lower()]

    def callback(self, ports, meta):
        return getattr(ports['in1'], self.op)(ports['in2'])


# class GetOperator(AtomicFunction):
#
#     def __init__(self):
#         super(GetOperator, self).__init__(name='get', In=['in', 'sel'], Out=['out'])
#
#
# class ApplyOperator(AtomicFunction):
#     def __init__(self):
#         super(ApplyOperator, self).__init__(name='apply', In=['func', 'in'], Out=['out'])


class Const(AtomicFunction):

    def __init__(self, value):
        super(Const, self).__init__(name=None, Out='out')
        self._value = value

    def callback(self, ports, meta):
        return self._value
