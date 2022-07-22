from __future__ import annotations

from abc import abstractmethod
from typing import Sequence

from public import public

import ibis.expr.rules as rlz
from ibis.common.exceptions import ExpressionError
from ibis.common.grounds import Annotable, Comparable
from ibis.expr.rules import Shape
from ibis.util import UnnamedMarker


@public
class Node(Annotable, Comparable):
    @property
    def args(self):
        return self.__args__

    @property
    def argnames(self):
        return self.__argnames__

    def __equals__(self, other):
        return self.__args__ == other.__args__

    def equals(self, other):
        if not isinstance(other, Node):
            raise TypeError(
                "invalid equality comparison between Node and "
                f"{type(other)}"
            )
        return self.__cached_equals__(other)

    @abstractmethod
    def to_expr(self):
        ...

    # TODO(kszucs): introduce a HasName schema, or NamedValue with a .name
    # abstractproperty
    def resolve_name(self):
        raise ExpressionError(f'Expression is not named: {type(self)}')

    def has_resolved_name(self):
        return False


@public
class Value(Node):
    @property
    @abstractmethod
    def output_dtype(self):
        """
        Ibis datatype of the produced value expression.

        Returns
        -------
        dt.DataType
        """

    @property
    @abstractmethod
    def output_shape(self):
        """
        Shape of the produced value expression.

        Possible values are: "scalar" and "columnar"

        Returns
        -------
        rlz.Shape
        """

    def to_expr(self):
        if self.output_shape is Shape.COLUMNAR:
            return self.output_dtype.column(self)
        else:
            return self.output_dtype.scalar(self)


@public
class Alias(Value):
    arg = rlz.any
    name = rlz.instance_of((str, UnnamedMarker))

    output_shape = rlz.shape_like("arg")
    output_dtype = rlz.dtype_like("arg")

    def has_resolved_name(self):
        return True

    def resolve_name(self):
        return self.name


@public
class Unary(Value):
    """A unary operation."""

    arg = rlz.any

    @property
    def output_shape(self):
        return self.arg.output_shape


@public
class Binary(Value):
    """A binary operation."""

    left = rlz.any
    right = rlz.any

    @property
    def output_shape(self):
        return max(self.left.output_shape, self.right.output_shape)


@public
class NodeList(Node, Sequence[Node]):
    """
    Data structure for grouping arbitrary node objects.
    """

    values = rlz.tuple_of(rlz.instance_of(Node))

    @classmethod
    def __create__(self, *args):
        return super().__create__(values=args)

    @property
    def args(self):
        return self.values

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def __add__(self, other):
        values = self.values + tuple(other)
        return self.__class__(*values)

    def __radd__(self, other):
        values = tuple(other) + self.values
        return self.__class__(*values)

    def to_expr(self):
        import ibis.expr.types as ir

        return ir.List(self)


public(ValueOp=Value, UnaryOp=Unary, BinaryOp=Binary, ValueList=NodeList)
