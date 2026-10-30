#!/usr/bin/env python3
"""Mini interpréteur PostScript : exécute un EPS et relève chacun de ses tracés.

Le fichier n'est pas rastérisé : chaque fill / eofill / stroke est relevé comme
un tracé en coordonnées de page (points), avec sa couleur, son épaisseur et la
position, dans le texte source, de l'instruction qui l'a déclenché. C'est ce qui
permet ensuite de modifier un tracé précis.

Seul un sous-ensemble du langage est géré (procédures, dictionnaires, matrices,
tracés, couleurs, polices factices) : les EPS « simples » tels que ceux de cairo
ou d'Inkscape passent ; les textes ne sont pas dessinés et les images ne sont
représentées que par leur cadre.
"""

import base64
import colorsys
import math
import re

WHITESPACE = "\0\t\n\f\r "
DELIMITERS = "()<>[]{}/%"

INT_RE = re.compile(r"[+-]?\d+$")
REAL_RE = re.compile(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$|[+-]?\d+[eE][+-]?\d+$")
RADIX_RE = re.compile(r"(\d+)#([0-9A-Za-z]+)$")

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class PSError(Exception):
    pass


class _Exit(Exception):
    pass


class _Stop(Exception):
    pass


class _Quit(Exception):
    pass


class Name:
    __slots__ = ("name", "exe")

    def __init__(self, name, exe=True):
        self.name, self.exe = name, exe

    def __repr__(self):
        return self.name if self.exe else "/" + self.name


class PSString:
    __slots__ = ("data", "exe")

    def __init__(self, data=b"", exe=False):
        self.data, self.exe = bytearray(data), exe

    def text(self):
        return self.data.decode("latin-1")


class PSArray(list):
    """Tableau PostScript ; exe=True pour une procédure."""
    exe = False


def make_proc(items):
    p = PSArray(items)
    p.exe = True
    return p


class Op:
    __slots__ = ("name", "fn")

    def __init__(self, name, fn):
        self.name, self.fn = name, fn

    def __repr__(self):
        return "--" + self.name + "--"


class PSFile:
    """« currentfile », éventuellement filtré. `state` est partagé par la chaîne de filtres."""

    def __init__(self, state, filters=()):
        self.state, self.filters = state, list(filters)


class Mark:
    def __repr__(self):
        return "-mark-"


class Save:
    __slots__ = ("depth",)

    def __init__(self, depth):
        self.depth = depth


MARK = Mark()
END = object()  # « } » rencontré par le lecteur


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def key(obj):
    """Clé de dictionnaire : un nom et la chaîne de même texte sont équivalents."""
    if isinstance(obj, Name):
        return obj.name
    if isinstance(obj, PSString):
        return obj.text()
    return obj


def parse_number(word):
    if INT_RE.match(word):
        v = int(word)
        return v if -2 ** 31 <= v < 2 ** 31 else float(v)
    if REAL_RE.match(word):
        return float(word)
    m = RADIX_RE.match(word)
    if m and 2 <= int(m.group(1)) <= 36:
        try:
            return int(m.group(2), int(m.group(1)))
        except ValueError:
            return None
    return None


def type_name(v):
    if isinstance(v, bool):
        return "booleantype"
    if isinstance(v, int):
        return "integertype"
    if isinstance(v, float):
        return "realtype"
    if isinstance(v, Name):
        return "nametype"
    if isinstance(v, PSString):
        return "stringtype"
    if isinstance(v, PSArray):
        return "arraytype"
    if isinstance(v, dict):
        return "dicttype"
    if isinstance(v, Op):
        return "operatortype"
    if isinstance(v, Mark):
        return "marktype"
    if isinstance(v, PSFile):
        return "filetype"
    if isinstance(v, Save):
        return "savetype"
    return "nulltype"


# --- Matrices (convention PostScript : [x y 1] · M) ---------------------------

def mat_mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def mat_inv(m):
    a, b, c, d, e, f = m
    det = a * d - b * c
    if det == 0:
        raise PSError("matrice non inversible")
    return (d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det)


def apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def apply_delta(m, x, y):
    return m[0] * x + m[2] * y, m[1] * x + m[3] * y


def arc_curves(cx, cy, r, a1, a2, clockwise):
    """Découpe un arc en courbes de Bézier d'au plus 90°, en espace utilisateur."""
    if clockwise:
        while a2 > a1:
            a2 -= 360
    else:
        while a2 < a1:
            a2 += 360
    total = a2 - a1
    n = max(1, math.ceil(abs(total) / 90 - 1e-9))
    step = math.radians(total / n)
    k = 4 / 3 * math.tan(step / 4)
    a = math.radians(a1)
    start = (cx + r * math.cos(a), cy + r * math.sin(a))
    curves = []
    for _ in range(n):
        b = a + step
        curves.append(((cx + r * (math.cos(a) - k * math.sin(a)), cy + r * (math.sin(a) + k * math.cos(a))),
                       (cx + r * (math.cos(b) + k * math.sin(b)), cy + r * (math.sin(b) - k * math.cos(b))),
                       (cx + r * math.cos(b), cy + r * math.sin(b))))
        a = b
    return start, curves


def cmyk_to_rgb(c, m, y, k):
    return tuple(max(0.0, min(1.0, (1 - v) * (1 - k))) for v in (c, m, y))


# --- Lecteur ------------------------------------------------------------------

class Scanner:
    def __init__(self, text, resolve):
        self.text, self.pos, self.resolve = text, 0, resolve

    def line(self, pos=None):
        return self.text.count("\n", 0, self.pos if pos is None else pos) + 1

    def next(self):
        """Lit l'objet suivant : (objet, début, fin), ou None en fin de texte."""
        text, n, i = self.text, len(self.text), self.pos
        while i < n:
            if text[i] in WHITESPACE:
                i += 1
            elif text[i] == "%":
                i = self._skip_comment(i)
            else:
                break
        if i >= n:
            self.pos = n
            return None

        start, ch = i, text[i]
        if ch == "(":
            obj, i = self._string(i)
        elif text.startswith("<~", i):
            end = text.find("~>", i + 2)
            if end == -1:
                raise PSError("chaîne ASCII85 non terminée")
            try:
                data = base64.a85decode(text[i + 2:end].encode("latin-1"),
                                        ignorechars=b" \t\n\r\v\f\0")
            except ValueError:
                data = b""
            obj, i = PSString(data), end + 2
        elif text.startswith("<<", i) or text.startswith(">>", i):
            obj, i = Name(text[i:i + 2]), i + 2
        elif ch == "<":
            end = text.find(">", i + 1)
            if end == -1:
                raise PSError("chaîne hexadécimale non terminée")
            digits = re.sub(r"\s", "", text[i + 1:end])
            try:
                data = bytes.fromhex(digits + "0" * (len(digits) % 2))
            except ValueError:
                raise PSError("chaîne hexadécimale invalide") from None
            obj, i = PSString(data), end + 1
        elif ch in "[]":
            obj, i = Name(ch), i + 1
        elif ch == "{":
            self.pos = i + 1
            items = []
            while True:
                tok = self.next()
                if tok is None:
                    raise PSError("« { » sans « } »")
                if tok[0] is END:
                    break
                items.append(tok[0])
            obj, i = make_proc(items), self.pos
        elif ch == "}":
            obj, i = END, i + 1
        elif ch in ")>":
            raise PSError(f"caractère inattendu « {ch} »")
        else:
            j = i + 1 if ch == "/" else i
            immediate = ch == "/" and j < n and text[j] == "/"
            if immediate:
                j += 1
            k = j
            while k < n and text[k] not in WHITESPACE and text[k] not in DELIMITERS:
                k += 1
            word, i = text[j:k], k
            if ch == "/":
                obj = self.resolve(word) if immediate else Name(word, exe=False)
            else:
                num = parse_number(word)
                obj = num if num is not None else Name(word)
        self.pos = i
        return obj, start, i

    def _skip_comment(self, i):
        text = self.text
        end = text.find("\n", i)
        end = len(text) if end == -1 else end + 1
        if i and text[i - 1] not in "\r\n":
            return end
        comment = text[i:end]
        m = re.match(r"%%BeginBinary:\s*(\d+)", comment)
        if m:
            return end + int(m.group(1))
        m = re.match(r"%%BeginData:\s*(\d+)(?:\s+\w+)?(?:\s+(Bytes|Lines))?", comment)
        if m:
            count = int(m.group(1))
            if m.group(2) != "Lines":
                return end + count
            for _ in range(count):
                nl = text.find("\n", end)
                end = len(text) if nl == -1 else nl + 1
        return end

    def _string(self, i):
        text, n = self.text, len(self.text)
        out, depth, i = bytearray(), 1, i + 1
        escapes = {"n": 10, "r": 13, "t": 9, "b": 8, "f": 12, "\\": 92, "(": 40, ")": 41}
        while i < n:
            c = text[i]
            if c == "\\":
                i += 1
                c = text[i] if i < n else ""
                if c in escapes:
                    out.append(escapes[c])
                elif c in "01234567" and c:
                    m = re.match(r"[0-7]{1,3}", text[i:])
                    out.append(int(m.group(0), 8) & 255)
                    i += len(m.group(0)) - 1
                elif c == "\r":
                    if text.startswith("\n", i + 1):
                        i += 1
                elif c != "\n":
                    out += c.encode("latin-1", "replace")
            elif c == "(":
                depth += 1
                out.append(40)
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return PSString(out), i + 1
                out.append(41)
            else:
                out += c.encode("latin-1", "replace")
            i += 1
        raise PSError("chaîne non terminée")


# --- État graphique et tracés relevés -----------------------------------------

class GState:
    def __init__(self):
        self.ctm = IDENTITY
        self.path = []        # segments en coordonnées de page
        self.point = None     # point courant (page)
        self.start = None     # début du sous-tracé courant
        self.rgb = (0.0, 0.0, 0.0)
        self.spot = None      # nom du ton direct courant, s'il y en a un
        self.space = PSArray([Name("DeviceGray", False)])
        self.linewidth = 1.0
        self.font = None

    def copy(self):
        g = GState.__new__(GState)
        g.__dict__.update(self.__dict__)
        g.path = list(self.path)
        return g


class Paint:
    """Un tracé peint : kind vaut fill, eofill, stroke, rectfill, rectstroke ou image."""

    def __init__(self, kind, segments, gs, span):
        self.kind = kind
        self.segments = segments
        self.rgb = gs.rgb
        self.spot = gs.spot
        self.scale = math.sqrt(abs(gs.ctm[0] * gs.ctm[3] - gs.ctm[1] * gs.ctm[2])) or 1.0
        self.width = gs.linewidth * self.scale
        self.span = span          # (début, fin) de l'instruction source qui a peint
        self.editable = False     # renseigné par interpret()


# --- Opérateurs -----------------------------------------------------------------

OPERATORS = {}


def operator(*names):
    def deco(fn):
        for n in names:
            OPERATORS[n] = fn
        return fn
    return deco


def popper(count):
    """Opérateur sans effet visible qui consomme `count` opérandes."""
    def fn(ps):
        for _ in range(count):
            ps.pop()
    return fn


for _name, _count in {
    "setlinecap": 1, "setlinejoin": 1, "setmiterlimit": 1, "setflat": 1, "setstrokeadjust": 1,
    "setoverprint": 1, "setsmoothness": 1, "setcolorrendering": 1, "sethalftone": 1,
    "settransfer": 1, "setblackgeneration": 1, "setundercolorremoval": 1, "setscreen": 3,
    "setcolortransfer": 4, "setcolorscreen": 12, "setpagedevice": 1, "setuserparams": 1,
    "setsystemparams": 1, "setdevparams": 2, "setglobal": 1, "setpacking": 1, "srand": 1,
    "setfont": 1, "selectfont": 2, "undefinefont": 1, "show": 1, "ashow": 3, "widthshow": 4,
    "awidthshow": 6, "kshow": 2, "xshow": 2, "yshow": 2, "xyshow": 2, "glyphshow": 1,
    "cshow": 2, "charpath": 2, "shfill": 1, "setcachedevice": 6, "setcharwidth": 2,
    "setcachedevice2": 10, "print": 1, "=": 1, "==": 1, "undefineresource": 2,
    "resourceforall": 4, "setobjectformat": 1, "setvmthreshold": 1, "setucacheparams": 1,
}.items():
    OPERATORS[_name] = popper(_count)

for _name in ("showpage", "copypage", "erasepage", "flush", "pstack", "stack", "initclip",
              "flattenpath", "reversepath", "strokepath", "clippath", "clip", "eoclip",
              "nulldevice", "ucache", "bind"):
    OPERATORS[_name] = lambda ps: None

for _name, _value in {"currentoverprint": False, "currentflat": 1.0, "currentlinecap": 0,
                      "currentlinejoin": 0, "currentmiterlimit": 10.0, "currentstrokeadjust": False,
                      "currentglobal": False, "currentpacking": False, "rand": 0, "rrand": 0,
                      "usertime": 0, "realtime": 0, "countexecstack": 0, "bytesavailable": -1,
                      "languagelevel": 2}.items():
    OPERATORS[_name] = (lambda v: lambda ps: ps.push(v))(_value)


# Pile

@operator("pop")
def _pop(ps):
    ps.pop()


@operator("exch")
def _exch(ps):
    b, a = ps.pop(), ps.pop()
    ps.push(b)
    ps.push(a)


@operator("dup")
def _dup(ps):
    v = ps.pop()
    ps.push(v)
    ps.push(v)


@operator("copy")
def _copy(ps):
    top = ps.pop()
    if is_num(top):
        n = int(top)
        if n < 0 or n > len(ps.stack):
            raise PSError("copy : pile trop courte")
        if n:
            ps.stack.extend(ps.stack[-n:])
    elif isinstance(top, PSArray):
        src = ps.pop()
        top[:len(src)] = src
        ps.push(PSArray(top[:len(src)]))
    elif isinstance(top, dict):
        top.update(ps.pop())
        ps.push(top)
    elif isinstance(top, PSString):
        src = ps.pop()
        top.data[:len(src.data)] = src.data
        ps.push(PSString(top.data[:len(src.data)]))
    else:
        raise PSError("copy : opérande invalide")


@operator("index")
def _index(ps):
    n = ps.pop_int()
    if n < 0 or n >= len(ps.stack):
        raise PSError("index : pile trop courte")
    ps.push(ps.stack[-1 - n])


@operator("roll")
def _roll(ps):
    j, n = ps.pop_int(), ps.pop_int()
    if n < 0 or n > len(ps.stack):
        raise PSError("roll : pile trop courte")
    if n:
        seg = ps.stack[-n:]
        j %= n
        ps.stack[-n:] = seg[n - j:] + seg[:n - j]


@operator("clear")
def _clear(ps):
    ps.stack.clear()


@operator("count")
def _count(ps):
    ps.push(len(ps.stack))


@operator("mark", "[", "<<")
def _mark(ps):
    ps.push(MARK)


@operator("cleartomark", "pdfmark")
def _cleartomark(ps):
    ps.to_mark()


@operator("counttomark")
def _counttomark(ps):
    for i, v in enumerate(reversed(ps.stack)):
        if v is MARK:
            ps.push(i)
            return
    raise PSError("counttomark : pas de marque")


@operator("]")
def _array_end(ps):
    ps.push(PSArray(ps.to_mark()))


@operator(">>")
def _dict_end(ps):
    items = ps.to_mark()
    if len(items) % 2:
        raise PSError(">> : nombre impair d'éléments")
    ps.push({key(items[i]): items[i + 1] for i in range(0, len(items), 2)})


# Arithmétique

def _int_or_float(v):
    if isinstance(v, int) and not -2 ** 31 <= v < 2 ** 31:
        return float(v)
    return v


def binary(fn):
    def op(ps):
        b, a = ps.pop_num(), ps.pop_num()
        ps.push(_int_or_float(fn(a, b)))
    return op


OPERATORS["add"] = binary(lambda a, b: a + b)
OPERATORS["sub"] = binary(lambda a, b: a - b)
OPERATORS["mul"] = binary(lambda a, b: a * b)


@operator("div")
def _div(ps):
    b, a = ps.pop_num(), ps.pop_num()
    if b == 0:
        raise PSError("division par zéro")
    ps.push(a / b)


@operator("idiv", "mod")
def _idiv(ps):
    b, a = ps.pop_int(), ps.pop_int()
    if b == 0:
        raise PSError("division par zéro")
    q = abs(a) // abs(b) * (1 if (a >= 0) == (b >= 0) else -1)
    ps.push(q if ps.current_op == "idiv" else a - b * q)


def unary(fn, keep_int=False):
    """Fonction d'un nombre ; keep_int : un entier reste inchangé (ceiling, round...)."""
    def op(ps):
        v = ps.pop_num()
        ps.push(v if keep_int and isinstance(v, int) else float(fn(v)))
    return op


OPERATORS["neg"] = lambda ps: ps.push(_int_or_float(-ps.pop_num()))
OPERATORS["abs"] = lambda ps: ps.push(_int_or_float(abs(ps.pop_num())))
OPERATORS["sqrt"] = unary(lambda v: math.sqrt(max(v, 0)))
OPERATORS["sin"] = unary(lambda v: math.sin(math.radians(v)))
OPERATORS["cos"] = unary(lambda v: math.cos(math.radians(v)))
OPERATORS["ln"] = unary(lambda v: math.log(v))
OPERATORS["log"] = unary(lambda v: math.log10(v))
OPERATORS["ceiling"] = unary(lambda v: float(math.ceil(v)), keep_int=True)
OPERATORS["floor"] = unary(lambda v: float(math.floor(v)), keep_int=True)
OPERATORS["round"] = unary(lambda v: float(math.floor(v + 0.5)), keep_int=True)
OPERATORS["truncate"] = unary(lambda v: float(math.trunc(v)), keep_int=True)


@operator("atan")
def _atan(ps):
    den, num = ps.pop_num(), ps.pop_num()
    ps.push(math.degrees(math.atan2(num, den)) % 360)


@operator("exp")
def _exp(ps):
    e, b = ps.pop_num(), ps.pop_num()
    ps.push(float(b) ** e)


@operator("cvi")
def _cvi(ps):
    v = ps.pop()
    if isinstance(v, PSString):
        v = parse_number(v.text().strip())
    if not is_num(v):
        raise PSError("cvi : nombre attendu")
    ps.push(int(math.trunc(v)))


@operator("cvr")
def _cvr(ps):
    v = ps.pop()
    if isinstance(v, PSString):
        v = parse_number(v.text().strip())
    if not is_num(v):
        raise PSError("cvr : nombre attendu")
    ps.push(float(v))


# Comparaisons et logique

def _same(a, b):
    if is_num(a) and is_num(b):
        return a == b
    if isinstance(a, (Name, PSString)) and isinstance(b, (Name, PSString)):
        return key(a) == key(b)
    if isinstance(a, bool) and isinstance(b, bool):
        return a == b
    return a is b


OPERATORS["eq"] = lambda ps: ps.push(_same(ps.pop(), ps.pop()))
OPERATORS["ne"] = lambda ps: ps.push(not _same(ps.pop(), ps.pop()))


def compare(fn):
    def op(ps):
        b, a = ps.pop(), ps.pop()
        if isinstance(a, PSString) and isinstance(b, PSString):
            a, b = bytes(a.data), bytes(b.data)
        elif not (is_num(a) and is_num(b)):
            raise PSError("comparaison : nombres ou chaînes attendus")
        ps.push(fn(a, b))
    return op


OPERATORS["gt"] = compare(lambda a, b: a > b)
OPERATORS["ge"] = compare(lambda a, b: a >= b)
OPERATORS["lt"] = compare(lambda a, b: a < b)
OPERATORS["le"] = compare(lambda a, b: a <= b)


def logical(fn_bool, fn_int):
    def op(ps):
        b, a = ps.pop(), ps.pop()
        if isinstance(a, bool) and isinstance(b, bool):
            ps.push(fn_bool(a, b))
        elif isinstance(a, int) and isinstance(b, int):
            ps.push(fn_int(a, b))
        else:
            raise PSError("opération logique : booléens ou entiers attendus")
    return op


OPERATORS["and"] = logical(lambda a, b: a and b, lambda a, b: a & b)
OPERATORS["or"] = logical(lambda a, b: a or b, lambda a, b: a | b)
OPERATORS["xor"] = logical(lambda a, b: a != b, lambda a, b: a ^ b)


@operator("not")
def _not(ps):
    v = ps.pop()
    ps.push(not v if isinstance(v, bool) else ~v)


@operator("bitshift")
def _bitshift(ps):
    s, v = ps.pop_int(), ps.pop_int()
    ps.push(v << s if s >= 0 else v >> -s)


# Contrôle

@operator("exec")
def _exec(ps):
    ps.execute(ps.pop())


@operator("if")
def _if(ps):
    p, cond = ps.pop_proc(), ps.pop_bool()
    if cond:
        ps.execute(p)


@operator("ifelse")
def _ifelse(ps):
    p2, p1, cond = ps.pop_proc(), ps.pop_proc(), ps.pop_bool()
    ps.execute(p1 if cond else p2)


@operator("for")
def _for(ps):
    p, limit, inc, init = ps.pop_proc(), ps.pop_num(), ps.pop_num(), ps.pop_num()
    as_int = all(isinstance(v, int) for v in (limit, inc, init))
    v = init if as_int else float(init)
    try:
        while (inc > 0 and v <= limit) or (inc < 0 and v >= limit) or (inc == 0 and ps.tick()):
            ps.push(v)
            ps.execute(p)
            v += inc
    except _Exit:
        pass


@operator("repeat")
def _repeat(ps):
    p, n = ps.pop_proc(), ps.pop_int()
    try:
        for _ in range(n):
            ps.execute(p)
    except _Exit:
        pass


@operator("loop")
def _loop(ps):
    p = ps.pop_proc()
    try:
        while True:
            ps.execute(p)
    except _Exit:
        pass


@operator("forall")
def _forall(ps):
    p, obj = ps.pop_proc(), ps.pop()
    if isinstance(obj, PSArray):
        items = [(v,) for v in list(obj)]
    elif isinstance(obj, dict):
        items = [(Name(k, False) if isinstance(k, str) else k, v) for k, v in list(obj.items())]
    elif isinstance(obj, PSString):
        items = [(b,) for b in bytes(obj.data)]
    else:
        raise PSError("forall : tableau, dictionnaire ou chaîne attendu")
    try:
        for values in items:
            for v in values:
                ps.push(v)
            ps.execute(p)
    except _Exit:
        pass


@operator("exit")
def _exit(ps):
    raise _Exit()


@operator("stop")
def _stop(ps):
    raise _Stop()


@operator("stopped")
def _stopped(ps):
    p = ps.pop()
    try:
        ps.execute(p)
    except (_Stop, PSError):
        ps.push(True)
    else:
        ps.push(False)


@operator("quit")
def _quit(ps):
    raise _Quit()


# Types et conversions

OPERATORS["type"] = lambda ps: ps.push(Name(type_name(ps.pop()), exe=False))


def _with_exe(obj, exe):
    if isinstance(obj, Name):
        return Name(obj.name, exe)
    if isinstance(obj, PSArray):
        a = PSArray(obj)
        a.exe = exe
        return a
    if isinstance(obj, PSString):
        s = PSString(obj.data, exe)
        return s
    return obj


OPERATORS["cvx"] = lambda ps: ps.push(_with_exe(ps.pop(), True))
OPERATORS["cvlit"] = lambda ps: ps.push(_with_exe(ps.pop(), False))
@operator("xcheck")
def _xcheck(ps):
    v = ps.pop()
    ps.push(isinstance(v, Op) or bool(getattr(v, "exe", False)))


OPERATORS["rcheck"] = OPERATORS["wcheck"] = lambda ps: (ps.pop(), ps.push(True))
OPERATORS["gcheck"] = OPERATORS["scheck"] = lambda ps: (ps.pop(), ps.push(False))
for _name in ("readonly", "executeonly", "noaccess"):
    OPERATORS[_name] = lambda ps: None


@operator("cvn")
def _cvn(ps):
    s = ps.pop()
    ps.push(Name(s.text(), s.exe) if isinstance(s, PSString) else s)


def _to_text(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v).rstrip("0").rstrip(".") if "e" not in repr(v) else repr(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, (Name, PSString)):
        return key(v)
    if isinstance(v, Op):
        return v.name
    return "--nostringval--"


@operator("cvs")
def _cvs(ps):
    buf, v = ps.pop(), ps.pop()
    data = _to_text(v).encode("latin-1", "replace")
    buf.data[:len(data)] = data
    ps.push(PSString(data))


@operator("cvrs")
def _cvrs(ps):
    buf, radix, v = ps.pop(), ps.pop_int(), ps.pop_num()
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n = int(v) & 0xFFFFFFFF if v < 0 else int(v)
    out = ""
    while True:
        n, r = divmod(n, radix)
        out = digits[r] + out
        if not n:
            break
    data = out.encode()
    buf.data[:len(data)] = data
    ps.push(PSString(data))


# Tableaux, dictionnaires, chaînes

@operator("array")
def _array(ps):
    ps.push(PSArray([None] * ps.pop_int()))


@operator("astore")
def _astore(ps):
    arr = ps.pop()
    n = len(arr)
    if n > len(ps.stack):
        raise PSError("astore : pile trop courte")
    arr[:] = ps.stack[len(ps.stack) - n:]
    del ps.stack[len(ps.stack) - n:]
    ps.push(arr)


@operator("aload")
def _aload(ps):
    arr = ps.pop()
    ps.stack.extend(arr)
    ps.push(arr)


@operator("length")
def _length(ps):
    v = ps.pop()
    if isinstance(v, PSString):
        ps.push(len(v.data))
    elif isinstance(v, Name):
        ps.push(len(v.name))
    else:
        ps.push(len(v))


@operator("get")
def _get(ps):
    idx, obj = ps.pop(), ps.pop()
    if isinstance(obj, dict):
        if key(idx) not in obj:
            raise PSError(f"get : clé inconnue {key(idx)}")
        ps.push(obj[key(idx)])
    elif isinstance(obj, PSString):
        ps.push(obj.data[int(idx)])
    else:
        ps.push(obj[int(idx)])


@operator("put")
def _put(ps):
    val, idx, obj = ps.pop(), ps.pop(), ps.pop()
    if isinstance(obj, dict):
        obj[key(idx)] = val
    elif isinstance(obj, PSString):
        obj.data[int(idx)] = int(val) & 255
    else:
        obj[int(idx)] = val


@operator("getinterval")
def _getinterval(ps):
    n, i, obj = ps.pop_int(), ps.pop_int(), ps.pop()
    if isinstance(obj, PSString):
        ps.push(PSString(obj.data[i:i + n]))
    else:
        a = PSArray(obj[i:i + n])
        a.exe = obj.exe
        ps.push(a)


@operator("putinterval")
def _putinterval(ps):
    src, i, obj = ps.pop(), ps.pop_int(), ps.pop()
    if isinstance(obj, PSString):
        obj.data[i:i + len(src.data)] = src.data
    else:
        obj[i:i + len(src)] = src


@operator("string")
def _string(ps):
    ps.push(PSString(b"\0" * ps.pop_int()))


@operator("search", "anchorsearch")
def _search(ps):
    seek, s = ps.pop(), ps.pop()
    data, pat = bytes(s.data), bytes(seek.data)
    i = data.find(pat)
    if ps.current_op == "anchorsearch" and i != 0:
        i = -1
    if i == -1:
        ps.push(s)
        ps.push(False)
        return
    if ps.current_op == "search":
        ps.push(PSString(data[i + len(pat):]))
        ps.push(PSString(pat))
        ps.push(PSString(data[:i]))
    else:
        ps.push(PSString(data[len(pat):]))
        ps.push(PSString(pat))
    ps.push(True)


@operator("dict")
def _dict(ps):
    ps.pop_int()
    ps.push({})


@operator("begin")
def _begin(ps):
    d = ps.pop()
    if not isinstance(d, dict):
        raise PSError("begin : dictionnaire attendu")
    ps.dstack.append(d)


@operator("end")
def _end(ps):
    if len(ps.dstack) <= 3:
        raise PSError("end : pile de dictionnaires vide")
    ps.dstack.pop()


@operator("def")
def _def(ps):
    v, k = ps.pop(), ps.pop()
    ps.dstack[-1][key(k)] = v


@operator("load")
def _load(ps):
    ps.push(ps.lookup(key(ps.pop())))


@operator("store")
def _store(ps):
    v, k = ps.pop(), key(ps.pop())
    for d in reversed(ps.dstack):
        if k in d:
            d[k] = v
            return
    ps.dstack[-1][k] = v


@operator("known")
def _known(ps):
    k, d = ps.pop(), ps.pop()
    ps.push(key(k) in d)


@operator("where")
def _where(ps):
    k = key(ps.pop())
    for d in reversed(ps.dstack):
        if k in d:
            ps.push(d)
            ps.push(True)
            return
    ps.push(False)


@operator("undef")
def _undef(ps):
    k, d = ps.pop(), ps.pop()
    d.pop(key(k), None)


OPERATORS["currentdict"] = lambda ps: ps.push(ps.dstack[-1])
OPERATORS["countdictstack"] = lambda ps: ps.push(len(ps.dstack))
OPERATORS["maxlength"] = lambda ps: (ps.pop(), ps.push(1000))
OPERATORS["cleardictstack"] = lambda ps: ps.dstack.__delitem__(slice(3, None))
OPERATORS["internaldict"] = lambda ps: (ps.pop(), ps.push(ps.internal))
OPERATORS["currentpagedevice"] = lambda ps: ps.push({})
OPERATORS["currentuserparams"] = lambda ps: ps.push({})
OPERATORS["vmstatus"] = lambda ps: [ps.push(v) for v in (0, 0, 10 ** 7)]


@operator("save")
def _save(ps):
    ps.push(Save(len(ps.gstack)))
    ps.gstack.append(ps.gs.copy())


@operator("restore")
def _restore(ps):
    s = ps.pop()
    if isinstance(s, Save) and s.depth < len(ps.gstack):
        del ps.gstack[s.depth + 1:]
        ps.gs = ps.gstack.pop()


# État graphique

@operator("gsave")
def _gsave(ps):
    ps.gstack.append(ps.gs.copy())


@operator("grestore")
def _grestore(ps):
    if ps.gstack:
        ps.gs = ps.gstack.pop()


@operator("grestoreall")
def _grestoreall(ps):
    if ps.gstack:
        ps.gs = ps.gstack[0]
        ps.gstack.clear()


@operator("initgraphics")
def _initgraphics(ps):
    ps.gs = GState()


@operator("setlinewidth")
def _setlinewidth(ps):
    ps.gs.linewidth = abs(ps.pop_num())


OPERATORS["currentlinewidth"] = lambda ps: ps.push(ps.gs.linewidth)


@operator("setdash")
def _setdash(ps):
    ps.pop_num()
    ps.pop()


OPERATORS["currentdash"] = lambda ps: (ps.push(PSArray()), ps.push(0))


# Couleurs

def _set_rgb(ps, rgb, space, spot=None):
    ps.gs.rgb = tuple(max(0.0, min(1.0, float(v))) for v in rgb)
    ps.gs.space = PSArray([Name(space, False)]) if isinstance(space, str) else space
    ps.gs.spot = spot


@operator("setgray")
def _setgray(ps):
    g = ps.pop_num()
    _set_rgb(ps, (g, g, g), "DeviceGray")


@operator("setrgbcolor")
def _setrgbcolor(ps):
    _set_rgb(ps, ps.pop_nums(3), "DeviceRGB")


@operator("setcmykcolor")
def _setcmykcolor(ps):
    _set_rgb(ps, cmyk_to_rgb(*ps.pop_nums(4)), "DeviceCMYK")


@operator("sethsbcolor")
def _sethsbcolor(ps):
    _set_rgb(ps, colorsys.hsv_to_rgb(*ps.pop_nums(3)), "DeviceRGB")


@operator("currentgray")
def _currentgray(ps):
    r, g, b = ps.gs.rgb
    ps.push(0.3 * r + 0.59 * g + 0.11 * b)


OPERATORS["currentrgbcolor"] = lambda ps: [ps.push(v) for v in ps.gs.rgb]


@operator("currentcmykcolor")
def _currentcmykcolor(ps):
    c, m, y = (1 - v for v in ps.gs.rgb)
    k = min(c, m, y)
    for v in ((c - k) / (1 - k), (m - k) / (1 - k), (y - k) / (1 - k)) if k < 1 else (0, 0, 0):
        ps.push(v)
    ps.push(k)


@operator("findcmykcustomcolor")
def _findcmykcustomcolor(ps):
    name = ps.pop()
    ps.push(PSArray(ps.pop_nums(4) + [name]))


@operator("setcustomcolor")
def _setcustomcolor(ps):
    tint, arr = ps.pop_num(), ps.pop()
    _set_rgb(ps, cmyk_to_rgb(*(v * tint for v in arr[:4])), "DeviceCMYK", key(arr[4]))


def _space_name(space):
    if isinstance(space, PSArray):
        return key(space[0]) if space else "DeviceGray"
    return key(space)


def _components(space):
    name = _space_name(space)
    if name in ("DeviceRGB", "CalRGB", "Lab"):
        return 3
    if name == "DeviceCMYK":
        return 4
    if name == "DeviceN":
        return len(space[1])
    if name == "ICCBased":
        return int(space[1].get("N", 3)) if isinstance(space[1], dict) else 3
    return 1


@operator("setcolorspace")
def _setcolorspace(ps):
    space = ps.pop()
    if not isinstance(space, PSArray):
        space = PSArray([space])
    name = _space_name(space)
    ps.gs.space = space
    if name in ("Separation", "DeviceN"):
        ps.set_color(space, [1.0] * _components(space))
    elif name not in ("Pattern",):
        ps.set_color(space, [0.0] * _components(space) if name != "DeviceCMYK" else [0, 0, 0, 1])


@operator("setcolor")
def _setcolor(ps):
    space = ps.gs.space
    if _space_name(space) == "Pattern":
        ps.pop()  # dictionnaire du motif
        _set_rgb(ps, (0.5, 0.5, 0.5), space)
        return
    ps.set_color(space, ps.pop_nums(_components(space)))


@operator("setpattern")
def _setpattern(ps):
    ps.pop()
    _set_rgb(ps, (0.5, 0.5, 0.5), "Pattern")


OPERATORS["currentcolorspace"] = lambda ps: ps.push(ps.gs.space)
OPERATORS["currentcolor"] = lambda ps: [ps.push(v) for v in ps.gs.rgb]


# Matrices

def _matrix_operand(ps):
    if ps.stack and isinstance(ps.stack[-1], PSArray) and not ps.stack[-1].exe and len(ps.stack[-1]) == 6:
        return ps.pop()
    return None


def _store_matrix(arr, m):
    arr[:] = [float(v) for v in m]
    return arr


OPERATORS["matrix"] = lambda ps: ps.push(PSArray(IDENTITY))
OPERATORS["identmatrix"] = lambda ps: ps.push(_store_matrix(ps.pop(), IDENTITY))
OPERATORS["defaultmatrix"] = OPERATORS["identmatrix"]
OPERATORS["currentmatrix"] = lambda ps: ps.push(_store_matrix(ps.pop(), ps.gs.ctm))


@operator("setmatrix")
def _setmatrix(ps):
    ps.gs.ctm = ps.pop_matrix()


@operator("initmatrix")
def _initmatrix(ps):
    ps.gs.ctm = IDENTITY


@operator("concat")
def _concat(ps):
    ps.gs.ctm = mat_mul(ps.pop_matrix(), ps.gs.ctm)


@operator("concatmatrix")
def _concatmatrix(ps):
    dst, m2, m1 = ps.pop(), ps.pop_matrix(), ps.pop_matrix()
    ps.push(_store_matrix(dst, mat_mul(m1, m2)))


@operator("invertmatrix")
def _invertmatrix(ps):
    dst, m = ps.pop(), ps.pop_matrix()
    ps.push(_store_matrix(dst, mat_inv(m)))


def matrix_op(build, count):
    def op(ps):
        dst = _matrix_operand(ps)
        m = build(*ps.pop_nums(count))
        if dst is not None:
            ps.push(_store_matrix(dst, m))
        else:
            ps.gs.ctm = mat_mul(m, ps.gs.ctm)
    return op


OPERATORS["translate"] = matrix_op(lambda tx, ty: (1.0, 0.0, 0.0, 1.0, tx, ty), 2)
OPERATORS["scale"] = matrix_op(lambda sx, sy: (sx, 0.0, 0.0, sy, 0.0, 0.0), 2)
OPERATORS["rotate"] = matrix_op(lambda a: (math.cos(math.radians(a)), math.sin(math.radians(a)),
                                           -math.sin(math.radians(a)), math.cos(math.radians(a)), 0.0, 0.0), 1)


def transform_op(fn, inverse):
    def op(ps):
        m = _matrix_operand(ps)
        m = m if m is not None else ps.gs.ctm
        x, y = ps.pop_nums(2)
        for v in fn(mat_inv(m) if inverse else m, x, y):
            ps.push(v)
    return op


OPERATORS["transform"] = transform_op(apply, False)
OPERATORS["itransform"] = transform_op(apply, True)
OPERATORS["dtransform"] = transform_op(apply_delta, False)
OPERATORS["idtransform"] = transform_op(apply_delta, True)


# Tracés

@operator("newpath")
def _newpath(ps):
    ps.gs.path, ps.gs.point = [], None


@operator("moveto")
def _moveto(ps):
    ps.move_to(apply(ps.gs.ctm, *ps.pop_nums(2)))


@operator("rmoveto")
def _rmoveto(ps):
    dx, dy = apply_delta(ps.gs.ctm, *ps.pop_nums(2))
    x, y = ps.current_point()
    ps.move_to((x + dx, y + dy))


@operator("lineto")
def _lineto(ps):
    p = apply(ps.gs.ctm, *ps.pop_nums(2))
    ps.current_point()
    ps.gs.path.append(("L", p))
    ps.gs.point = p


@operator("rlineto")
def _rlineto(ps):
    dx, dy = apply_delta(ps.gs.ctm, *ps.pop_nums(2))
    x, y = ps.current_point()
    ps.gs.path.append(("L", (x + dx, y + dy)))
    ps.gs.point = (x + dx, y + dy)


@operator("curveto")
def _curveto(ps):
    v = ps.pop_nums(6)
    ps.current_point()
    ps.curve_to(*(apply(ps.gs.ctm, v[i], v[i + 1]) for i in (0, 2, 4)))


@operator("rcurveto")
def _rcurveto(ps):
    v = ps.pop_nums(6)
    x, y = ps.current_point()
    pts = []
    for i in (0, 2, 4):
        dx, dy = apply_delta(ps.gs.ctm, v[i], v[i + 1])
        pts.append((x + dx, y + dy))
    ps.curve_to(*pts)


@operator("closepath")
def _closepath(ps):
    if ps.gs.point is not None:
        ps.gs.path.append(("Z",))
        ps.gs.point = ps.gs.start


@operator("arc", "arcn")
def _arc(ps):
    cx, cy, r, a1, a2 = ps.pop_nums(5)
    start, curves = arc_curves(cx, cy, r, a1, a2, ps.current_op == "arcn")
    m = ps.gs.ctm
    if ps.gs.point is None:
        ps.move_to(apply(m, *start))
    else:
        p = apply(m, *start)
        ps.gs.path.append(("L", p))
        ps.gs.point = p
    for c in curves:
        ps.curve_to(*(apply(m, *pt) for pt in c))


@operator("arct", "arcto")
def _arct(ps):
    x1, y1, _x2, _y2, _r = ps.pop_nums(5)
    ps.current_point()
    p = apply(ps.gs.ctm, x1, y1)
    ps.gs.path.append(("L", p))
    ps.gs.point = p
    if ps.current_op == "arcto":
        for v in (x1, y1, x1, y1):
            ps.push(v)


@operator("currentpoint")
def _currentpoint(ps):
    for v in apply(mat_inv(ps.gs.ctm), *ps.current_point()):
        ps.push(v)


@operator("pathbbox")
def _pathbbox(ps):
    pts = [pt for seg in ps.gs.path for pt in seg[1:]]
    if not pts:
        raise PSError("pathbbox : pas de tracé courant")
    inv = mat_inv(ps.gs.ctm)
    user = [apply(inv, *pt) for pt in pts]
    xs, ys = [p[0] for p in user], [p[1] for p in user]
    for v in (min(xs), min(ys), max(xs), max(ys)):
        ps.push(v)


@operator("rectclip")
def _rectclip(ps):
    ps.pop_rects()
    ps.gs.path, ps.gs.point = [], None


# Peinture

@operator("fill", "eofill", "stroke")
def _paint(ps):
    if any(seg[0] != "M" for seg in ps.gs.path):
        ps.record(ps.current_op, ps.gs.path)
    ps.gs.path, ps.gs.point = [], None


@operator("rectfill", "rectstroke")
def _rectpaint(ps):
    if ps.current_op == "rectstroke":
        _matrix_operand(ps)
    m, segs = ps.gs.ctm, []
    for x, y, w, h in ps.pop_rects():
        corners = [apply(m, *p) for p in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
        segs += [("M", corners[0])] + [("L", c) for c in corners[1:]] + [("Z",)]
    if segs:
        ps.record(ps.current_op, segs)


@operator("image", "imagemask", "colorimage")
def _image(ps):
    kind = ps.current_op
    top = ps.pop()
    if isinstance(top, dict):
        w, h = top.get("Width", 0), top.get("Height", 0)
        bpc = top.get("BitsPerComponent", 1)
        ncomp = 1 if kind == "imagemask" else _components(ps.gs.space)
        src = top.get("DataSource")
        sources = list(src) if top.get("MultipleDataSources") else [src]
        if top.get("MultipleDataSources"):
            ncomp = 1
    elif kind == "colorimage":
        ncomp = int(top)
        multi = ps.pop_bool()
        sources = [ps.pop() for _ in range(ncomp if multi else 1)][::-1]
        if multi:
            ncomp = 1
        ps.pop()
        bpc, h, w = ps.pop_int(), ps.pop_int(), ps.pop_int()
    else:
        sources = [top]
        ps.pop()
        bpc = 1 if kind == "imagemask" else ps.pop_int()
        if kind == "imagemask":
            ps.pop()
        h, w = ps.pop_int(), ps.pop_int()
        ncomp = 1
    nbytes = (int(w) * int(bpc) * ncomp + 7) // 8 * int(h)
    for src in sources:
        ps.skip_image_data(src, nbytes)
    m = ps.gs.ctm
    corners = [apply(m, *p) for p in ((0, 0), (1, 0), (1, 1), (0, 1))]
    ps.record("image", [("M", corners[0])] + [("L", c) for c in corners[1:]] + [("Z",)])


# Polices (factices : le texte n'est pas dessiné)

def _dummy_font(name="Courier"):
    return {"FontName": Name(name, False), "FontType": 1, "FontMatrix": PSArray([0.001, 0, 0, 0.001, 0, 0]),
            "FontBBox": PSArray([0, 0, 1000, 1000]), "Encoding": PSArray([Name(".notdef", False)] * 256)}


@operator("findfont")
def _findfont(ps):
    name = key(ps.pop())
    ps.push(ps.fonts.get(name) or _dummy_font(name))


@operator("definefont")
def _definefont(ps):
    font, name = ps.pop(), key(ps.pop())
    ps.fonts[name] = font
    ps.push(font)


@operator("composefont")
def _composefont(ps):
    ps.pop()
    ps.pop()
    name = key(ps.pop())
    ps.fonts[name] = _dummy_font(name)
    ps.push(ps.fonts[name])


OPERATORS["scalefont"] = OPERATORS["makefont"] = lambda ps: ps.pop()
OPERATORS["currentfont"] = OPERATORS["rootfont"] = lambda ps: ps.push(_dummy_font())
OPERATORS["stringwidth"] = lambda ps: (ps.pop(), ps.push(0.0), ps.push(0.0))
OPERATORS["findencoding"] = lambda ps: (ps.pop(), ps.push(PSArray([Name(".notdef", False)] * 256)))


# Ressources

@operator("defineresource")
def _defineresource(ps):
    category, instance, k = key(ps.pop()), ps.pop(), key(ps.pop())
    ps.resources.setdefault(category, {})[k] = instance
    ps.push(instance)


@operator("findresource")
def _findresource(ps):
    category, k = key(ps.pop()), key(ps.pop())
    if k in ps.resources.get(category, {}):
        ps.push(ps.resources[category][k])
    elif category == "Font":
        ps.push(ps.fonts.get(k) or _dummy_font(k))
    elif category == "Encoding":
        ps.push(PSArray([Name(".notdef", False)] * 256))
    else:
        raise PSError(f"ressource introuvable : {k} ({category})")


@operator("resourcestatus")
def _resourcestatus(ps):
    category, k = key(ps.pop()), key(ps.pop())
    if k in ps.resources.get(category, {}):
        ps.push(0)
        ps.push(0)
        ps.push(True)
    else:
        ps.push(False)


@operator("execform")
def _execform(ps):
    form = ps.pop()
    ps.push(form)
    ps.execute(form["PaintProc"])


@operator("makepattern")
def _makepattern(ps):
    ps.pop()


# Fichiers

@operator("currentfile")
def _currentfile(ps):
    ps.push(PSFile({"consumed": False}))


@operator("filter")
def _filter(ps):
    name = key(ps.pop())
    if name == "SubFileDecode":
        ps.pop()
        ps.pop()
    elif ps.stack and isinstance(ps.stack[-1], dict):
        ps.pop()
    src = ps.pop()
    if isinstance(src, PSFile):
        ps.push(PSFile(src.state, src.filters + [name]))
    else:
        ps.push(PSFile({"consumed": True}, [name]))


@operator("closefile", "flushfile")
def _closefile(ps):
    f = ps.pop()
    if isinstance(f, PSFile) and f.filters and not f.state["consumed"]:
        ps.skip_filtered(f)


@operator("status")
def _status(ps):
    v = ps.pop()
    ps.push(isinstance(v, PSFile))


@operator("readhexstring", "readstring", "readline")
def _readstring(ps):
    buf, f = ps.pop(), ps.pop()
    sc, n = ps.scanner, len(buf.data)
    if not isinstance(f, PSFile) or f.filters:
        raise PSError(f"{ps.current_op} : seule la lecture directe de currentfile est gérée")
    if ps.current_op == "readhexstring":
        digits, i = [], sc.pos
        while len(digits) < 2 * n and i < len(sc.text) and sc.text[i] != ">":
            if sc.text[i] in "0123456789abcdefABCDEF":
                digits.append(sc.text[i])
            i += 1
        data = bytes.fromhex("".join(digits) + "0" * (len(digits) % 2))
    elif ps.current_op == "readstring":
        i = sc.pos + n
        data = sc.text[sc.pos:i].encode("latin-1")
    else:
        end = sc.text.find("\n", sc.pos)
        end = len(sc.text) if end == -1 else end
        data = sc.text[sc.pos:end].rstrip("\r").encode("latin-1")[:n]
        i = end + 1
    sc.pos = i
    buf.data[:len(data)] = data
    ps.push(PSString(data))
    ps.push(len(data) == n or ps.current_op == "readline")


@operator("eexec")
def _eexec(ps):
    """Saute la partie chiffrée d'une police Type 1 (jusqu'aux 512 zéros)."""
    ps.pop()
    sc = ps.scanner
    i = sc.text.find("0" * 64, sc.pos)
    if i == -1:
        raise PSError("eexec : fin de la partie chiffrée introuvable")
    while i < len(sc.text) and sc.text[i] in "0\r\n\t ":
        i += 1
    sc.pos = i
    if ps.stack and isinstance(ps.stack[-1], dict):
        font = ps.pop()
        ps.fonts[key(font.get("FontName", Name("?")))] = font
    ps.push(MARK)


@operator("file", "run", "deletefile", "renamefile")
def _file(ps):
    raise PSError(f"{ps.current_op} : accès aux fichiers non géré")


# --- Interpréteur ---------------------------------------------------------------

class Interpreter:
    def __init__(self, max_steps=20_000_000):
        sysd = {n: Op(n, fn) for n, fn in OPERATORS.items()}
        self.userdict, globald = {}, {}
        sysd.update({"true": True, "false": False, "null": None, "systemdict": sysd,
                     "userdict": self.userdict, "globaldict": globald, "statusdict": {},
                     "errordict": {}, "$error": {}, "version": PSString(b"3010"),
                     "product": PSString(b"eps_interpreteur"),
                     "StandardEncoding": PSArray([Name(".notdef", False)] * 256),
                     "ISOLatin1Encoding": PSArray([Name(".notdef", False)] * 256)})
        self.dstack = [sysd, globald, self.userdict]
        self.stack, self.gstack = [], []
        self.gs = GState()
        self.fonts, self.resources, self.internal = {}, {}, {}
        self.paints = []
        self.span = None
        self.scanner = None
        self.current_op = None
        self.steps, self.max_steps = 0, max_steps

    # Pile
    def push(self, v):
        self.stack.append(v)

    def pop(self):
        if not self.stack:
            raise PSError(f"{self.current_op} : pile vide")
        return self.stack.pop()

    def pop_num(self):
        v = self.pop()
        if not is_num(v):
            raise PSError(f"{self.current_op} : nombre attendu, trouvé {type_name(v)}")
        return v

    def pop_nums(self, n):
        return [self.pop_num() for _ in range(n)][::-1]

    def pop_int(self):
        return int(self.pop_num())

    def pop_bool(self):
        v = self.pop()
        if not isinstance(v, bool):
            raise PSError(f"{self.current_op} : booléen attendu, trouvé {type_name(v)}")
        return v

    def pop_proc(self):
        v = self.pop()
        if not isinstance(v, (PSArray, Op, Name)):
            raise PSError(f"{self.current_op} : procédure attendue, trouvé {type_name(v)}")
        return v

    def pop_matrix(self):
        v = self.pop()
        if not isinstance(v, PSArray) or len(v) != 6 or not all(is_num(x) for x in v):
            raise PSError(f"{self.current_op} : matrice attendue")
        return tuple(float(x) for x in v)

    def pop_rects(self):
        top = self.pop()
        if isinstance(top, PSArray):
            vals = [float(v) for v in top]
            return [vals[i:i + 4] for i in range(0, len(vals) - 3, 4)]
        self.push(top)
        return [self.pop_nums(4)]

    def to_mark(self):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] is MARK:
                items = self.stack[i + 1:]
                del self.stack[i:]
                return items
        raise PSError(f"{self.current_op} : pas de marque")

    # Exécution
    def tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise PSError("exécution trop longue (boucle infinie ?)")
        return True

    def lookup(self, name):
        for d in reversed(self.dstack):
            if name in d:
                return d[name]
        raise PSError(f"nom inconnu : {name}")

    def _immediate(self, name):
        return self.lookup(name)

    def execute(self, obj):
        self.tick()
        if isinstance(obj, Op):
            previous, self.current_op = self.current_op, obj.name
            try:
                obj.fn(self)
            finally:
                self.current_op = previous
        elif isinstance(obj, Name) and obj.exe:
            self.execute(self.lookup(obj.name))
        elif isinstance(obj, PSArray) and obj.exe:
            for item in obj:
                if isinstance(item, (Name, Op)) and getattr(item, "exe", True):
                    self.execute(item)
                else:
                    self.push(item)
        elif isinstance(obj, PSString) and obj.exe:
            raise PSError("exécution d'une chaîne non gérée")
        else:
            self.push(obj)

    def run(self, text):
        self.scanner = Scanner(text, self._immediate)
        try:
            while True:
                tok = self.scanner.next()
                if tok is None:
                    break
                obj, start, end = tok
                if obj is END:
                    raise PSError("« } » sans « { »")
                self.span = (start, end)
                if isinstance(obj, Name) and obj.exe:
                    self.execute(obj)
                else:
                    self.push(obj)
        except _Quit:
            pass
        except (_Exit, _Stop):
            raise PSError(f"ligne {self.scanner.line()} : exit/stop hors d'une boucle") from None
        except PSError as e:
            raise PSError(f"ligne {self.scanner.line()} : {e}") from None
        except RecursionError:
            raise PSError(f"ligne {self.scanner.line()} : récursion trop profonde") from None
        except (IndexError, KeyError, TypeError, ValueError, AttributeError,
                ZeroDivisionError, OverflowError) as e:
            raise PSError(f"ligne {self.scanner.line()} : opérande invalide pour "
                          f"{self.current_op or '?'} ({e})") from None

    # Tracés et couleurs
    def current_point(self):
        if self.gs.point is None:
            raise PSError(f"{self.current_op} : pas de point courant")
        return self.gs.point

    def move_to(self, p):
        self.gs.path.append(("M", p))
        self.gs.point = self.gs.start = p

    def curve_to(self, p1, p2, p3):
        self.gs.path.append(("C", p1, p2, p3))
        self.gs.point = p3

    def set_color(self, space, comps):
        name = _space_name(space)
        if name in ("DeviceGray", "CalGray") or (name == "ICCBased" and len(comps) == 1):
            _set_rgb(self, (comps[0],) * 3, space)
        elif name in ("DeviceRGB", "CalRGB", "Lab", "ICCBased") and len(comps) == 3:
            _set_rgb(self, comps, space)
        elif name == "DeviceCMYK" or (name == "ICCBased" and len(comps) == 4):
            _set_rgb(self, cmyk_to_rgb(*comps), space)
        elif name in ("Separation", "DeviceN"):
            spot = key(space[1]) if name == "Separation" else None
            alt, tint = space[2], space[3]
            depth = len(self.stack)
            for c in comps:
                self.push(c)
            self.execute(tint)
            alt_comps = [float(v) for v in self.stack[depth:]]
            del self.stack[depth:]
            alt = alt if isinstance(alt, PSArray) else PSArray([alt])
            self.set_color(alt, alt_comps)
            self.gs.space, self.gs.spot = space, spot
        elif name == "Indexed":
            base, lookup = space[1], space[3]
            base = base if isinstance(base, PSArray) else PSArray([base])
            n, i = _components(base), int(comps[0])
            if isinstance(lookup, PSString):
                vals = [b / 255 for b in lookup.data[i * n:(i + 1) * n]]
            else:
                depth = len(self.stack)
                self.push(i)
                self.execute(lookup)
                vals = [float(v) for v in self.stack[depth:]]
                del self.stack[depth:]
            self.set_color(base, vals or [0.0] * n)
            self.gs.space = space
        else:
            _set_rgb(self, (0.5, 0.5, 0.5), space)

    def record(self, kind, segments):
        self.paints.append(Paint(kind, list(segments), self.gs, self.span))

    def skip_image_data(self, src, nbytes):
        """Avance le lecteur au-delà des données d'image intégrées au fichier."""
        if isinstance(src, PSFile):
            if src.state["consumed"]:
                return
            if src.filters:
                self.skip_filtered(src)
            else:
                self._skip_whitespace_char()
                self.scanner.pos += nbytes
                src.state["consumed"] = True
        elif isinstance(src, PSArray) and src.exe:
            names = {item.name for item in src if isinstance(item, Name)}
            if "currentfile" not in names:
                return
            if "readhexstring" in names:
                sc, count, i = self.scanner, 0, self.scanner.pos
                while count < 2 * nbytes and i < len(sc.text) and sc.text[i] != ">":
                    count += sc.text[i] in "0123456789abcdefABCDEF"
                    i += 1
                sc.pos = i
            elif "readstring" in names:
                self._skip_whitespace_char()
                self.scanner.pos += nbytes
            else:
                raise PSError("données d'image lues par une procédure non gérée")

    def skip_filtered(self, f):
        sc, first = self.scanner, f.filters[0]
        terminator = {"ASCII85Decode": "~>", "A85": "~>", "ASCIIHexDecode": ">", "AHx": ">"}.get(first)
        if terminator is None:
            raise PSError(f"données d'image avec le filtre {first} non gérées")
        end = sc.text.find(terminator, sc.pos)
        if end == -1:
            raise PSError("fin des données d'image introuvable")
        sc.pos = end + len(terminator)
        f.state["consumed"] = True

    def _skip_whitespace_char(self):
        sc = self.scanner
        if sc.text.startswith("\r\n", sc.pos):
            sc.pos += 2
        elif sc.pos < len(sc.text) and sc.text[sc.pos] in WHITESPACE:
            sc.pos += 1


EDITABLE_KINDS = ("fill", "eofill", "stroke", "rectstroke")


def interpret(text):
    """Exécute le texte PostScript : renvoie (tracés, message d'erreur ou None).

    En cas d'erreur, les tracés relevés avant elle sont tout de même renvoyés.
    Un tracé est « editable » si l'instruction source qui l'a peint n'en peint
    aucun autre : on peut alors la modifier sans toucher au reste.
    """
    ps = Interpreter()
    error = None
    try:
        ps.run(text)
    except PSError as e:
        error = str(e)
    per_span = {}
    for p in ps.paints:
        per_span[p.span] = per_span.get(p.span, 0) + 1
    for p in ps.paints:
        p.editable = p.kind in EDITABLE_KINDS and p.span is not None and per_span[p.span] == 1
    return ps.paints, error


def bounding_box(text):
    """BoundingBox de l'en-tête DSC (HiRes de préférence), ou None."""
    for pattern in (r"^%%HiResBoundingBox:\s*([-\d.eE+]+(?:\s+[-\d.eE+]+){3})",
                    r"^%%BoundingBox:\s*([-\d.eE+]+(?:\s+[-\d.eE+]+){3})"):
        m = re.search(pattern, text, re.M)
        if m:
            x0, y0, x1, y1 = (float(v) for v in m.group(1).split())
            if x1 > x0 and y1 > y0:
                return x0, y0, x1, y1
    return None
