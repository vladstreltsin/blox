class PortOperatorsMixin:
    """ Allow operations between ports """

    @staticmethod
    def _make_port(other):
        """ Convert non-port values to Const blocks """
        from blox.core.port import Port
        from blox.core.special import Const
        if not isinstance(other, Port):
            return Const(value=other).Out()
        else:
            return other

    def __add__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('add')(self, self._make_port(other))

    def __sub__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('sub')(self, self._make_port(other))

    def __mul__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('mul')(self, self._make_port(other))

    def __matmul__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('matmul')(self, self._make_port(other))

    def __truediv__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('truediv')(self, self._make_port(other))

    def __floordiv__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('floordiv')(self, self._make_port(other))

    def __mod__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('mod')(self, self._make_port(other))

    def __divmod__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('divmod')(self, self._make_port(other))

    def __pow__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('pow')(self, self._make_port(other))

    def __lshift__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('lshift')(self, self._make_port(other))

    def __rshift__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('rshift')(self, self._make_port(other))

    def __and__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('and')(self, self._make_port(other))

    def __xor__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('xor')(self, self._make_port(other))

    def __or__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('or')(self, self._make_port(other))

    def __radd__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('add')(self._make_port(other), self)

    def __rsub__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('sub')(self._make_port(other), self)

    def __rmul__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('mul')(self._make_port(other), self)

    def __rmatmul__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('matmul')(self._make_port(other), self)

    def __rtruediv__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('truediv')(self._make_port(other), self)

    def __rfloordiv__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('floordiv')(self._make_port(other), self)

    def __rmod__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('mod')(self._make_port(other), self)

    def __rdivmod__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('divmod')(self._make_port(other), self)

    def __rpow__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('pow')(self._make_port(other), self)

    def __rlshift__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('lshift')(self._make_port(other), self)

    def __rrshift__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('rshift')(self._make_port(other), self)

    def __rand__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('and')(self._make_port(other), self)

    def __rxor__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('xor')(self._make_port(other), self)

    def __ror__(self, other):
        from blox.core.special import BinaryOperator
        return BinaryOperator('or')(self._make_port(other), self)

    # Unary operators
    def __neg__(self):
        from blox.core.special import UnaryOperator
        return UnaryOperator('neg')(self)

    def __pos__(self):
        from blox.core.special import UnaryOperator
        return UnaryOperator('pos')(self)

    def __abs__(self):
        from blox.core.special import UnaryOperator
        return UnaryOperator('abs')(self)

    def __invert__(self):
        from blox.core.special import UnaryOperator
        return UnaryOperator('invert')(self)

    # Functional operators

    # def __getitem__(self, item):
    #     from blox.core.special import GetOperator
    #     return GetOperator()(self, self._make_port(item))
    #
    # def __call__(self, item):
    #     from blox.core.special import ApplyOperator
    #     return ApplyOperator()(self, self._make_port(item))
