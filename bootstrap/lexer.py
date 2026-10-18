"""Zag lexer: splits .zag source into a sequence of tokens.

Zag's lexical conventions:
- Single quotes are characters, double quotes are strings ([]const u8)
- `const?` / `var.` are single tokens (const-safe / declaration-safe), not const + ?
- `$` is a dereference prefix, replacing Zig's `.*`
- Newline is a meaningful token: Zag has no semicolons; a newline is a soft statement terminator
- `//` line comments, `///` doc comments, `/* */` block comments (nestable)
"""

KEYWORDS = frozenset({
    "pub", "fn", "const", "var", "if", "else", "while", "for",
    "return", "break", "continue", "struct", "enum", "union", "class",
    "try", "catch", "defer", "comptime", "inline", "test",
    "export", "extern", "and", "or", "not", "null", "orelse", "using",
    "true", "false", "int", "float", "bool", "string", "void", "type",
})

# Keywords usable in type position
TYPE_KEYWORDS = frozenset({"int", "float", "bool", "string", "void", "type"})

# Two-character operators (matched before single-character)
TWO_CHAR_OPS = ("==", "!=", "<=", ">=", "++", "--", "+=", "-=", "*=", "/=", "%=", "..")

ONE_CHAR_OPS = frozenset("+-*/%=<>!&$|@(){}[],:;.?")

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "0": "\0", "'": "'"}


class LexError(Exception):
    """Lexical error with line and column numbers."""

    def __init__(self, message, line, col):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self):
        return f"{self.line}:{self.col}: {self.message}"


class Token:
    """A lexical token. type is keyword text / operator text / IDENT / INT / FLOAT / STRING / NEWLINE / EOF."""

    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line, col):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []

# ------------------------------------------------------------------ basics
    def _peek(self, offset=0):
        i = self.pos + offset
        if i < len(self.src):
            return self.src[i]
        return ""

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, message):
        raise LexError(message, self.line, self.col)

    def _emit(self, type_, value, line, col):
        self.tokens.append(Token(type_, value, line, col))

# ------------------------------------------------------------------ main loop
    def tokenize(self):
        while self.pos < len(self.src):
            ch = self._peek()
            line, col = self.line, self.col

            if ch in " \t\r":
                self._advance()
            elif ch == "\n":
                self._advance()
                self._emit("NEWLINE", "\n", line, col)
            elif ch == "/" and self._peek(1) == "/":
                self._skip_line_comment()
            elif ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
            elif ch == '"':
                self._read_string(line, col)
            elif ch.isdigit():
                self._read_number(line, col)
            elif ch.isalpha() or ch == "_":
                self._read_ident(line, col)
            else:
                self._read_operator(line, col)

        self._emit("EOF", "", self.line, self.col)
        return self.tokens

# ------------------------------------------------------------------ token kinds
    def _skip_line_comment(self):
        # Both // and /// skip the whole line (doc comment content is not retained)
        while self.pos < len(self.src) and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self):
        start_line, start_col = self.line, self.col
        self._advance()  # /
        self._advance()  # *
        depth = 1
        while depth > 0:
            if self.pos >= len(self.src):
                raise LexError("块注释未闭合", start_line, start_col)
            if self._peek() == "/" and self._peek(1) == "*":
                self._advance()
                self._advance()
                depth += 1
            elif self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                depth -= 1
            else:
                self._advance()

    def _read_string(self, line, col):
        self._advance()  # opening quote
        chars = []
        while True:
            if self.pos >= len(self.src):
                raise LexError("字符串未闭合", line, col)
            ch = self._peek()
            if ch == "\n":
                raise LexError("字符串不能跨行", self.line, self.col)
            if ch == '"':
                self._advance()
                break
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in ESCAPES:
                    chars.append(ESCAPES[esc])
                    self._advance()
                else:
                    raise LexError(f"未知转义序列 \\{esc}", self.line, self.col)
            else:
                chars.append(ch)
                self._advance()
        self._emit("STRING", "".join(chars), line, col)

    def _read_number(self, line, col):
        start = self.pos
        is_float = False

        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            self._advance()
            self._advance()
            if not (self._peek().isdigit() or self._peek() in "abcdefABCDEF_"):
                self._error("非法的十六进制数字")
            while self._peek() and (self._peek() in "0123456789abcdefABCDEF_"):
                self._advance()
            self._emit("INT", self.src[start:self.pos], line, col)
            return

        while self._peek().isdigit() or self._peek() == "_":
            self._advance()

        # Decimal point: must be followed by a digit and must not be the .. range operator
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit() or self._peek() == "_":
                self._advance()

        # Scientific notation 1e5 / 1.5e-3
        if self._peek() in ("e", "E"):
            nxt = self._peek(1)
            if nxt.isdigit() or (nxt in ("+", "-") and self._peek(2).isdigit()):
                is_float = True
                self._advance()
                if self._peek() in ("+", "-"):
                    self._advance()
                while self._peek().isdigit() or self._peek() == "_":
                    self._advance()

        text = self.src[start:self.pos]
        self._emit("FLOAT" if is_float else "INT", text, line, col)

    def _read_ident(self, line, col):
        start = self.pos
        while self._peek() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        word = self.src[start:self.pos]

        # const? — const-safe declaration
        if word == "const" and self._peek() == "?":
            self._advance()
            self._emit("CONSTSAFE", "const?", line, col)
            return
        # var. — declaration-safe declaration
        if word == "var" and self._peek() == ".":
            self._advance()
            self._emit("VARSAFE", "var.", line, col)
            return

        if word in KEYWORDS:
            self._emit(word, word, line, col)
        else:
            self._emit("IDENT", word, line, col)

    def _read_operator(self, line, col):
        two = self.src[self.pos:self.pos + 2]
        if two in TWO_CHAR_OPS:
            self._advance()
            self._advance()
            self._emit(two, two, line, col)
            return
        ch = self._peek()
        if ch in ONE_CHAR_OPS:
            self._advance()
            self._emit(ch, ch, line, col)
            return
        self._error(f"无法识别的字符 {ch!r}")


def tokenize(source):
    """Convenience entry: source -> list of tokens."""
    return Lexer(source).tokenize()
