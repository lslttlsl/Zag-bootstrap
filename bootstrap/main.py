#!/usr/bin/env python3
"""Zag compiler command-line entry point.

Usage (run from the project root):
    python -m src.main examples/example.zag                # compile to .zig
    python -m src.main examples/example.zag -o out.zig     # specify output
    python -m src.main examples/example.zag --run          # compile and run immediately
    python -m src.main examples/example.zag --test         # compile and run tests
    python -m src.main examples/example.zag --ast          # print the AST only

Also runnable directly: python src/main.py examples/example.zag
"""

import argparse
import os
import subprocess
import sys
from dataclasses import fields, is_dataclass

try:
    from .lexer import Lexer, LexError
    from .parser import Parser, ParseError
    from .codegen import CodeGen, ZagError
except ImportError:  # run directly as a script
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bootstrap.lexer import Lexer, LexError
    from bootstrap.parser import Parser, ParseError
    from bootstrap.codegen import CodeGen, ZagError


# ============================================================ AST printing (for debugging)
def dump_ast(node, indent=0):
    pad = "  " * indent
    if is_dataclass(node):
        name = type(node).__name__
        simple = []
        children = []
        for f in fields(node):
            v = getattr(node, f.name)
            if isinstance(v, (int, bool, str)) or v is None:
                simple.append(f"{f.name}={v!r}")
            else:
                children.append((f.name, v))
        head = f"{pad}{name}(" + ", ".join(simple) + ")"
        print(head)
        for fname, v in children:
            print(f"{pad}  .{fname}:")
            if isinstance(v, list):
                for item in v:
                    dump_ast(item, indent + 2)
            else:
                dump_ast(v, indent + 2)
    elif isinstance(node, list):
        for item in node:
            dump_ast(item, indent)
    else:
        print(f"{pad}{node!r}")


# ============================================================ compilation
def compile_file(input_path, show_ast=False):
    """Compiles a single .zag file; returns (zig source, list of .zag imports to compile)."""
    with open(input_path, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse_program()

    if show_ast:
        dump_ast(ast)

    source_dir = os.path.dirname(os.path.abspath(input_path))
    codegen = CodeGen(os.path.basename(input_path), source_dir)
    zig_code = codegen.generate(ast)
    return zig_code, codegen.pending_imports


def compile_project(input_path, output_path, show_ast=False):
    """Compiles the entry file and recursively compiles every .zag module it imports."""
    visited = set()

    def _compile(src_path, out_path):
        real = os.path.abspath(src_path)
        if real in visited:
            return
        visited.add(real)

        zig_code, pending = compile_file(src_path, show_ast)

        out_dir = os.path.dirname(os.path.abspath(out_path))
        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(zig_code)
        print(f"[zag] {src_path} -> {out_path}")

        src_dir = os.path.dirname(os.path.abspath(src_path))
        for raw_path, _ in pending:
            dep_src = os.path.join(src_dir, raw_path)
            dep_out = os.path.join(
                out_dir, os.path.splitext(os.path.basename(raw_path))[0] + ".zig")
            if os.path.exists(dep_src):
                _compile(dep_src, dep_out)
            else:
                print(f"[zag] 警告: 找不到导入的模块 {raw_path}", file=sys.stderr)

    _compile(input_path, output_path)


# ============================================================ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="zag",
        description="Zag compiler — compiles the Zag language to Zig source")
    ap.add_argument("input", help="Zag source file (.zag)")
    ap.add_argument("-o", "--output",
                        help="Output .zig path (defaults to same directory and name as input)")
    ap.add_argument("--run", action="store_true",
                        help="Run immediately with zig run after generation")
    ap.add_argument("--test", action="store_true",
                        help="Run tests with zig test after generation")
    ap.add_argument("--zig", default=os.environ.get("ZIG", "zig"),
                        help="Path to the zig executable (defaults to PATH lookup, or env var ZIG)")
    ap.add_argument("--ast", action="store_true",
                        help="Print the AST and exit (for debugging)")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"zag: error: 文件不存在: {args.input}", file=sys.stderr)
        return 1

    output = args.output or (os.path.splitext(args.input)[0] + ".zig")

    try:
        compile_project(args.input, output, show_ast=args.ast)
    except (LexError, ParseError, ZagError) as e:
        print(f"zag: error: {args.input}: {e}", file=sys.stderr)
        return 1

    if args.run:
        cmd = [args.zig, "run", output]
        print(f"[zag] 运行: {' '.join(cmd)}")
        return subprocess.run(cmd).returncode
    if args.test:
        cmd = [args.zig, "test", output]
        print(f"[zag] 测试: {' '.join(cmd)}")
        return subprocess.run(cmd).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
