"""Zag abstract syntax tree (AST) node definitions.

Every node carries line/col to pinpoint semantic errors to source locations.
Naming: *Decl are declarations, *Stmt are statements, the rest are expressions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============================================================ type nodes
@dataclass
class TypeRef:
    """Named types: int / float / bool / string / void / type / custom struct names."""
    name: str
    line: int = 0
    col: int = 0


@dataclass
class OptionalType:
    """?T — optional type."""
    inner: object
    line: int = 0
    col: int = 0


@dataclass
class ErrorUnionType:
    """!T error union (prefix); when a named error set is used, error_set is non-empty (MyError!int)."""
    inner: object
    error_set: Optional[object] = None
    line: int = 0
    col: int = 0


@dataclass
class ArrayTypeNode:
    """[N]T or []T. size of None means a slice."""
    elem: object
    size: object = None
    line: int = 0
    col: int = 0


@dataclass
class GenericType:
    """Qualified generic type used as a type, e.g. std.List(Token) / std.Map(string, int).

    base is the qualified name ("std.List" / "std.Map"); args are the inner type nodes.
    In expression position the same spelling becomes a Call (constructor) instead.
    """
    base: str
    args: List[object]
    line: int = 0
    col: int = 0


# ============================================================ declarations
@dataclass
class Param:
    name: str
    type: object
    comptime: bool = False   # comptime T: type — compile-time parameter (generics)
    line: int = 0
    col: int = 0


@dataclass
class VarDecl:
    """const / var / const? / var. declaration.

    kind values:
        "const"       — ordinary constant; mutation OR non-use both error
        "var"         — ordinary variable; never mutated errors
        "const_safe"  — const? const-safe; assignment silently discarded
        "var_safe"    — var. declaration-safe; unused/unmutated silently ignored
    """
    kind: str
    name: str
    type: Optional[object]
    value: Optional[object]
    line: int = 0
    col: int = 0
    pub: bool = False


@dataclass
class DestructureDecl:
    """const [a, b] = expr destructuring declaration."""
    kind: str
    targets: List[str]
    value: object
    line: int = 0
    col: int = 0
    pub: bool = False


@dataclass
class FnDecl:
    name: str
    params: List[Param]
    ret_type: Optional[object]
    body: Optional[object]          # extern functions have no body
    pub: bool = False
    inline: bool = False
    export: bool = False
    extern: bool = False
    line: int = 0
    col: int = 0


@dataclass
class StructField:
    name: str
    type: object
    line: int = 0
    col: int = 0


@dataclass
class StructDecl:
    name: str
    fields: List[StructField]
    methods: List["FnDecl"] = field(default_factory=list)
    pub: bool = False
    line: int = 0
    col: int = 0


@dataclass
class EnumVariant:
    name: str
    value: Optional[object] = None
    line: int = 0
    col: int = 0


@dataclass
class EnumDecl:
    name: str
    variants: List[EnumVariant]
    methods: List["FnDecl"] = field(default_factory=list)
    pub: bool = False
    line: int = 0
    col: int = 0


@dataclass
class UnionDecl:
    name: str
    fields: List[StructField]
    methods: List["FnDecl"] = field(default_factory=list)
    pub: bool = False
    line: int = 0
    col: int = 0


@dataclass
class TestDecl:
    name: str
    body: object
    line: int = 0
    col: int = 0


# ============================================================ statements
@dataclass
class Block:
    stmts: List[object]


@dataclass
class ExprStmt:
    expr: object
    line: int = 0
    col: int = 0


@dataclass
class AssignStmt:
    """target op value, op is "=" / "+=" / "-=" / "*=" / "/=" / "%="."""
    target: object
    op: str
    value: object
    line: int = 0
    col: int = 0


@dataclass
class IncDecStmt:
    """target++ / target--."""
    target: object
    op: str
    line: int = 0
    col: int = 0


@dataclass
class ReturnStmt:
    value: Optional[object]
    line: int = 0
    col: int = 0


@dataclass
class IfStmt:
    cond: object
    then_stmt: object
    else_stmt: Optional[object]
    payload: Optional[str] = None   # optional value capture name in if (opt) |val|
    line: int = 0
    col: int = 0


@dataclass
class WhileStmt:
    cond: object
    body: object
    label: Optional[str] = None    # outer: while (...) — loop label
    line: int = 0
    col: int = 0


@dataclass
class ForStmt:
    init: Optional[object]          # VarDecl / AssignStmt / ExprStmt / None
    cond: Optional[object]
    post: Optional[object]          # IncDecStmt / AssignStmt / None
    body: object
    label: Optional[str] = None     # outer: for (...) — loop label
    line: int = 0
    col: int = 0


@dataclass
class DeferStmt:
    body: object
    line: int = 0
    col: int = 0


@dataclass
class ComptimeStmt:
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class BreakStmt:
    label: Optional[str] = None
    line: int = 0
    col: int = 0


@dataclass
class ContinueStmt:
    label: Optional[str] = None
    line: int = 0
    col: int = 0


# ============================================================ expressions
@dataclass
class IntLit:
    value: str
    line: int = 0
    col: int = 0


@dataclass
class FloatLit:
    value: str
    line: int = 0
    col: int = 0


@dataclass
class StringLit:
    value: str
    line: int = 0
    col: int = 0


@dataclass
class BoolLit:
    value: bool
    line: int = 0
    col: int = 0


@dataclass
class NullLit:
    line: int = 0
    col: int = 0


@dataclass
class Ident:
    name: str
    line: int = 0
    col: int = 0


@dataclass
class Binary:
    op: str
    left: object
    right: object
    line: int = 0
    col: int = 0


@dataclass
class ConcatExpr:
    """String concatenation with an explicit allocator: a + b using alloc.

    Lowered to a runtime helper (zag_concat) because Zig string concat needs an allocator.
    """
    left: object
    right: object
    alloc: str                       # allocator identifier name
    line: int = 0
    col: int = 0


@dataclass
class Unary:
    op: str                        # "-" / "!" / "not"
    operand: object
    line: int = 0
    col: int = 0


@dataclass
class Call:
    callee: object
    args: List[object]
    line: int = 0
    col: int = 0


@dataclass
class Index:
    base: object
    index: object
    line: int = 0
    col: int = 0


@dataclass
class SliceExpr:
    base: object
    start: Optional[object]        # None means [..end]
    end: Optional[object]          # None means [start..]
    line: int = 0
    col: int = 0


@dataclass
class Field:
    base: object
    name: str
    line: int = 0
    col: int = 0


@dataclass
class ArrayLit:
    elems: List[object]
    line: int = 0
    col: int = 0


@dataclass
class StructLit:
    type_name: str
    fields: List[Tuple[str, object]]
    line: int = 0
    col: int = 0


@dataclass
class IfExpr:
    cond: object
    then_expr: object
    else_expr: object
    payload: Optional[str] = None   # if (opt) |val| expr else expr
    line: int = 0
    col: int = 0


@dataclass
class TryExpr:
    expr: object
    line: int = 0
    col: int = 0


@dataclass
class CatchExpr:
    expr: object
    capture: Optional[str]         # error name in |err|
    payload: object                # block or expression
    line: int = 0
    col: int = 0


@dataclass
class AddressOf:
    """&expr — take the address."""
    operand: object
    line: int = 0
    col: int = 0


@dataclass
class Deref:
    """$expr — dereference (Zag feature, replaces Zig's .*)."""
    operand: object
    line: int = 0
    col: int = 0


@dataclass
class EnumLit:
    """.name — enum literal."""
    name: str
    line: int = 0
    col: int = 0


@dataclass
class ErrorSetLit:
    """error{ Bad, Worse } — error set (usable as expression or as type)."""
    variants: List[str]
    line: int = 0
    col: int = 0


@dataclass
class BuiltinCall:
    """@sizeOf(T) / @typeName(T) etc., compiler builtin functions."""
    name: str
    args: List[object]
    line: int = 0
    col: int = 0


@dataclass
class ImportExpr:
    """@import("std") / @import("mod.zag")."""
    path: str
    line: int = 0
    col: int = 0


@dataclass
class Program:
    items: List[object]
