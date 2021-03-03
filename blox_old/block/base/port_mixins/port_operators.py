from __future__ import annotations
import typing as tp

if tp.TYPE_CHECKING:
    from blox_old.block.base.port_base import Port


class PortOperatorMixin:

    def __add__(self, other: tp.Any) -> Port:
        from blox_old.core.block.base import Add
        return Add(In=2, Out=1)(self, other)

    def __radd__(self, other) -> Port:
        from blox_old.core.block.base import Add
        return Add(In=2, Out=1)(other, self)

    def __sub__(self, other: tp.Any) -> Port:
        from blox_old.core.block.base import Sub
        return Sub(In=2, Out=1)(self, other)

    def __rsub__(self, other) -> Port:
        from blox_old.core.block.base import Sub
        return Sub(In=2, Out=1)(other, self)

    def __mul__(self, other: tp.Any) -> Port:
        from blox_old.core.block.base import Mul
        return Mul(In=2, Out=1)(self, other)

    def __rmul__(self, other) -> Port:
        from blox_old.core.block.base import Mul
        return Mul(In=2, Out=1)(other, self)

    def __truediv__(self, other) -> Port:
        from blox_old.core.block.base import TrueDiv
        return TrueDiv(In=2, Out=1)(self, other)

    def __rtruediv__(self, other) -> Port:
        from blox_old.core.block.base import TrueDiv
        return TrueDiv(In=2, Out=1)(other, self)

    def __floordiv__(self, other) -> Port:
        from blox_old.core.block.base import FloorDiv
        return FloorDiv(In=2, Out=1)(self, other)

    def __rfloordiv__(self, other) -> Port:
        from blox_old.core.block.base import FloorDiv
        return FloorDiv(In=2, Out=1)(other, self)

    def __matmul__(self, other) -> Port:
        from blox_old.core.block.base import MatMul
        return MatMul(In=2, Out=1)(self, other)

    def __rmatmul__(self, other) -> Port:
        from blox_old.core.block.base import MatMul
        return MatMul(In=2, Out=1)(other, self)
