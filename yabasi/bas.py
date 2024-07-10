#!/usr/bin/python3

from ply import yacc
from argparse import ArgumentParser
import numpy as np
import re
import sys
import datetime
import struct
from . import tokenizer

def fun_chr (expr):
    expr = int (expr)
    # Don't print formfeed
    if expr == 12:
        return ''
    return chr (expr)
# end def fun_chr

def fun_cvi (s):
    if isinstance (s, str):
        s = s.encode ('ascii')
    if isinstance (s, bytes):
        if not len (s):
            return 0
        return struct.unpack ('<h', s)[0]
    try:
        return int (s)
    except ValueError:
        return 0
# end def fun_cvi

def fun_cvs (s):
    if isinstance (s, str):
        s = s.encode ('ascii')
    if isinstance (s, bytes):
        if not len (s):
            return 0
        return struct.unpack ('<f', s)[0]
    try:
        return float (s)
    except ValueError:
        return 0.0
# end def fun_cvs

def fun_fractional_part (expr):
    """ This is used in the first Mininec implementation, probably
        something that the UNIVAC BASIC at the time provided.
        I could not find it in any BASIC function references.
    """
    return expr - int (expr)
# end def fun_fractional_part

def fun_left (expr1, expr2):
    expr2 = int (expr2)
    assert isinstance (expr1, str)
    return expr1 [:expr2]
# end def fun_left

def fun_mid (expr1, expr2, expr3):
    assert isinstance (expr1, str)
    expr2 = int (expr2)
    if expr3 is None:
        return expr1 [expr2 - 1:]
    else:
        expr3 = int (expr3)
        return expr1 [expr2 - 1:expr2 - 1+expr3]
# end def fun_mid

def fun_mki (expr):
    i = int (expr)
    return struct.pack ('<h', i)
# end def fun_mki

def fun_mks (expr):
    f = float (expr)
    return struct.pack ('<f', f)
# end def fun_mks

def fun_right (expr1, expr2):
    expr2 = int (expr2)
    assert isinstance (expr1, str)
    return expr1 [-expr2:]
# end def fun_right

def fun_str (expr):
    if isinstance (expr, float):
        return format_float (expr).rstrip ()
    return str (expr)
# end def fun_str

#def _fmt_float (v, fmt = '%9f'):
def _fmt_float (v, fmt = '{:#.9g}'):
    sign = ''
    if fmt.startswith ('{'):
        x = fmt.format (v).strip ()
    else:
        x = (fmt % v).strip ()
    if x.startswith ('-'):
        sign = '-'
        x = x.lstrip ('-')
    x = x.lstrip ('0')
    x = sign + x
    if '.' in x and not 'e' in x and not 'E' in x:
        x = x.rstrip ('0')
        x = x.rstrip ('.')
    return x
# end def _fmt_float

def format_float (v):
    """ Try to get float formatting right
        (or at least matching to pcbasic)
    >>> format_float (0.0)
    ' 0'
    >>> format_float (0.001)
    ' .001'
    >>> format_float (-0.001)
    '-.001'
    >>> format_float (2.141428111)
    ' 2.1414281'
    >>> format_float (4.99262212345e-03)
    ' .00499262'
    >>> format_float (42.82857111)
    ' 42.828571'
    >>> format_float (-.9036958111)
    '-.90369581'
    >>> format_float (1.700281111E+02)
    ' 170.02811'
    >>> format_float (.0497375)
    ' .0497375'
    >>> format_float (.07958)
    ' .07958'
    >>> format_float (.0099475)
    ' .0099475'
    >>> format_float (-.16039812)
    '-.16039812'
    """
    if v == 0.0:
        return ' 0'
    e = int (np.floor (np.log10 (np.abs (v))))
    x = _fmt_float (v)
    f = '{:#.8g}'
    if -3 <= e <= -1:
        f = '%.8f'
    if abs (e) > 8 or len (x) >= 8 and e < -3:
        f = '%12E'
    v = _fmt_float (v, fmt = f)
    if not v.startswith ('-'):
        v = ' ' + v
    return v
# end def format_float

class Print_Using:
    """ Formatter for USING in a print statement
    >>> p = Print_Using ('###.##    ')
    >>> p.fmt
    ['%6.2f    ']
    >>> p = Print_Using ('       ##.###^^^^')
    >>> p.fmt
    ['       %.4E']
    >>> p = Print_Using ('   ###.##   ')
    >>> p.fmt
    ['   %6.2f   ']
    >>> p = Print_Using ('   ###.##')
    >>> p.fmt
    ['   %6.2f']
    >>> p = Print_Using ('###  ###   ##')
    >>> p.fmt
    ['%3.0f  ', '%3.0f   ', '%2.0f']
    """

    def __init__ (self, formatstring):
        self.f1  = []
        self.f2  = []
        self.s   = 0
        self.bc  = 0
        self.ac  = 0
        self.e   = 0
        self.fmt = []
        self.parse_format (formatstring)
    # end def __init__

    def append_fmt (self):
        if self.ac or self.bc:
            ln = self.ac + self.bc + self.s
            if self.e:
                self.f1.append ('%%.%sE' % (ln - 2))
            else:
                self.f1.append ('%%%s.%sf' % (ln, self.ac))
            self.fmt.append (''.join (self.f1 + self.f2))
        self.ac = self.bc = self.e = self.s = 0
        self.f1 = []
        self.f2 = []
    # end def append_fmt

    def get (self):
        # Formats can be re-used for multiple variables
        if len (self.fmt) > 1:
            f = self.fmt.pop (0)
        else:
            f = self.fmt [0]
        return f
    # end def get

    def parse_format (self, v):
        for x in v:
            if x == '#':
                if self.f2:
                    self.append_fmt ()
                if self.s == 0:
                    self.bc += 1
                elif self.s == 1:
                    self.ac += 1
                else:
                    assert 0
            elif x == '.':
                self.s = 1
            elif x == '^':
                self.e += 1
            else:
                if self.ac > 0 or self.bc > 0:
                    self.f2.append (x)
                else:
                    self.f1.append (x)
        self.append_fmt ()
    # end def parse_format

# end class Print_Using

class Exec_Stack:
    """ Stack holding multiline IF/ELSE and FOR/NEXT info
    """

    def __init__ (self):
        self.stack     = []
        self.xq_cached = None
    # end def __init__

    def __bool__ (self):
        return bool (self.stack)
    # end def __bool__

    def __iter__ (self):
        for entry in reversed (self.stack):
            yield entry
    # end def __iter__

    @property
    def exec_condition (self):
        if self.xq_cached is not None:
            return self.xq_cached
        for stack_entry in self.stack:
            if not stack_entry.condition:
                self.xq_cached = False
                return False
        self.xq_cached = True
        return True
    # end exec_condition

    @property
    def top (self):
        return self.stack [-1]
    # end def top

    def pop (self):
        self.xq_cached = None
        return self.stack.pop ()
    # end def pop

    def push (self, item):
        self.xq_cached = None
        self.stack.append (item)
        item.stack = self
    # end def push

# end class

class Stack_Entry:
    """ We stack FOR/NEXT and IF/ELSE
        While a condition is False we just skip commands but we still
        *do* pick up FOR loops and multi-line IF/ELSE
    """

    def __init__ (self, parent, condition):
        self.parent    = parent
        self.condition = condition
        self.stack     = None
    # end def __init__

# end class Stack_Entry

class Stack_Entry_For (Stack_Entry):

    def __init__ (self, parent, condition, var, frm, to, step):
        super ().__init__ (parent, condition)
        self.var   = var
        self.start = parent.next
        self.frm   = frm
        self.count = frm
        self.to    = to
        self.step  = step
    # end def __init__

    def handle_next (self):
        assert self.parent.stack.top == self
        self.count += self.step
        self.parent.var [self.var] = self.count
        if  (  self.step > 0 and self.count <= self.to
            or self.step < 0 and self.count >= self.to
            ):
            self.parent.next = self.start
        else:
            self.parent.stack.pop ()
            #print ('NEXT pop')
    # end def handle_next

# end class Stack_Entry_For

class Context:
    """ Context of current execution, include line numbers to be able to
        restore execution after a GOSUB.
    """

    def __init__ (self, parent, cmdlist = None, cmdidx = None):
        self.parent  = parent
        self.cmdlist = cmdlist
        self.cmdidx  = cmdidx
        if cmdlist:
            assert cmdidx is not None
            self.current = (parent.lineno, parent.sublineno)
            self.next    = parent.next
        else:
            self.current = (parent.lineno, parent.sublineno)
            self.next    = parent.next
    # end def __init__

    def __str__ (self):
        return \
            ( 'Context: (%d.%d)->(%d.%d) [%s]'
            % (self.current + self.next + (self.cmdidx,))
            )
    # end def __str__
    __repr__ = __str__

    def restore_context (self):
        self.parent.next = self.next
        self.parent.lineno, self.parent.sublineno = self.current
    # end def restore_context

# end class Context

class Stack_Entry_If (Stack_Entry):
    """ Model a multi-line IF/ELSE/END IF
    """

    def __init__ (self, parent, condition):
        super ().__init__ (parent, condition)
        self.else_seen = False
    # end def __init__

    def handle_else (self):
        if self.else_seen:
            self.parent.raise_error ('Duplicate ELSE clause')
            return
        self.else_seen = True
        self.condition = not self.condition
        self.stack.xq_cached = None
    # end def handle_else

# end class Stack_Entry_If

class L_Value:
    def value (self, v):
        if self.name.endswith ('%'):
            v = int (v)
        elif not self.name.endswith ('$'):
            v = float (v)
        return v
    # end def value
# end class L_Value

class L_Value_Var (L_Value):

    def __init__ (self, parent, name):
        self.parent = parent
        self.name   = name
    # end def __init__

    def get (self):
        if self.name not in self.parent.var:
            return None
        return self.parent.var [self.name]
    # end def get

    def set (self, value):
        self.parent.var [self.name] = self.value (value)
    # end def set

# end class L_Value_Var

class L_Value_Dim (L_Value):

    def __init__ (self, parent, dim, expr):
        self.parent = parent
        self.expr   = [int (x) for x in expr]
        self.name   = dim
    # end def __init__

    def get (self):
        if self.name not in self.parent.dim:
            return None
        return self.parent.dim [self.name][*self.expr]
    # end def get

    def set (self, v):
        self.parent.dim [self.name][*self.expr] = self.value (v)
    # end def set

# end class L_Value_Dim

def to_fhandle (x):
    if not isinstance (x, str):
        x = '#%d' % int (x)
    if not x.startswith ('#'):
        x = '#' + x
    return x
# end def to_fhandle

class Interpreter:
    print_special = \
        { ',' : ('++,++', 'COMMA')
        , ';' : ('++;++', 'SEMIC')
        }
    special_by_code = dict \
        ((c [0], c [1]) for c in print_special.values ())
    tabpos = [14, 28, 42, 56]

    skip_mode_commands = set (('if_start', 'else', 'endif', 'for', 'next'))

    def __init__ (self, args):
        self.args   = args
        self.input  = None
        self.tab    = args.tab
        if not self.tab:
            self.tab = self.tabpos
        if args.input_file:
            self.input = open (args.input_file, 'r')
        self.col      = 0
        self.lines    = {}
        self.stack    = Exec_Stack ()
        self.gstack   = [] # gosub
        self.context  = None
        self.files    = {}
        self.data     = []
        self.reclen   = {}
        self.fields   = {}
        self.defint   = {}
        self.err_seen = False
        # Variables and dimensioned variables do not occupy the same namespace
        self.var      = {}
        self.dim      = {}
        self.flines   = {}
        self.var ['DATE$'] = str (datetime.date.today ())
        self.var ['TIME$'] = datetime.datetime.now ().strftime ('%H:%M:%S')

        self.tokenizer = tokenizer.Tokenizer ()
        self.tokens    = tokenizer.Tokenizer.tokens
        self.parser    = yacc.yacc (module = self)

        with open (args.program, 'r') as f:
            lineno = self.lineno = sublineno = 0
            for fline, l in enumerate (f):
                l = l.rstrip ()
                #print (l)
                if l and l [0].isnumeric ():
                    lineno, r = l.split (None, 1)
                    lineno = self.lineno = int (lineno)
                    sublineno = self.sublineno = 0
                else:
                    sublineno += 1
                    self.sublineno = sublineno
                    r = l.lstrip ()
                self.flines [(lineno, sublineno)] = fline + 1
                self.tokenizer.lexer.lineno    = lineno
                self.tokenizer.lexer.sublineno = sublineno
                self.tokenizer.lexer.fline     = fline + 1
                # Newer versions seem to have comments starting with "'"
                # And we now handle empty lines gracefully
                if not l or l.lstrip ().startswith ("'"):
                    self.tokenizer.feed ('REM')
                    p = self.parser.parse (lexer = self.tokenizer)
                    self.insert (p)
                    continue
                if l [0] == '\x1a':
                    break
                if ' ' in r:
                    a, b = r.split (None, 1)
                    if a == 'REM':
                        self.tokenizer.feed ('REM')
                        p = self.parser.parse (lexer = self.tokenizer)
                        self.insert (p)
                        continue
                self.tokenizer.feed (r)
                r = self.parser.parse (lexer = self.tokenizer)
                self.insert (r)
        self.nextline = {}
        self.first    = None
        prev = None
        for l in sorted (self.lines):
            if self.first is None:
                self.first = l
            if prev is not None:
                self.nextline [prev] = l
            prev = l
        self.break_lineno = None
    # end def __init__

    @property
    def exec_condition (self):
        return self.stack.exec_condition
    # end def exec_condition

    @property
    def fline (self):
        if not getattr (self, 'lineno', None):
            return None
        return self.flines [(self.lineno, self.sublineno)]
    # end def fline

    def exec_cmdlist (self, cmdlist, idx):
        for i in range (idx, len (cmdlist)):
            cmd = cmdlist [i]
            self.context = Context (self, cmdlist, i)
            cmd [0] (*cmd [1:])
            # If there was a GOSUB stop execution of cmdlist
            if self.context is None:
                return
        self.context = None
    # end def exec_cmdlist

    def fun_tab (self, expr):
        # We print *at* the tab position
        expr     = int (expr) - 1
        dif      = expr - self.col
        return ' ' * dif
    # end def fun_tab

    def insert (self, r):
        k = (self.lineno, self.sublineno)
        if isinstance (r, list):
            self.lines [k] = (self.cmd_multi, r)
        else:
            self.lines [k] = r
    # end def insert

    def lset_rset_mid_paramcheck (self, lhs, expr):
        if not isinstance (expr, (str, bytes)):
            self.raise_error ('Non-string expression')
            return (None, None)
        if not lhs.name.endswith ('$'):
            self.raise_error ('Non-string variable "%s"' % lhs.name)
            return (None, None)
        return (lhs.get (), expr)
    # end def lset_rset_mid_paramcheck

    def raise_error (self, errmsg):
        print \
            ( 'Error: %s in line %s (%s.%s)'
            % (errmsg, self.fline, self.lineno, self.sublineno)
            , file = sys.stderr
            )
        self.err_seen = True
    # end def raise_error

    def run (self):
        if self.err_seen:
            return
        self.running = True
        l = self.first
        self.lineno, self.sublineno = l
        # Ignore these exceptions and print better error:
        ex = (ZeroDivisionError, ValueError, KeyError, IndexError)
        while self.running and not self.err_seen and l:
            if  (  (self.sublineno == 0 and self.lineno == self.break_lineno)
                or self.break_lineno == 'all'
                ):
                import pdb; pdb.set_trace ()
            self.next = self.nextline.get (l)
            #print ('lineno: %d.%d' % l)
            line = self.lines [l]
            if line is None:
                self.raise_error ('Uncompiled line')
                return
            name = line [0].__name__.split ('_', 1) [-1]
            if self.exec_condition or name in self.skip_mode_commands:
                try:
                    line [0] (*line [1:])
                except ex as err:
                    self.raise_error (err)
            l = self.next
            if l:
                self.lineno, self.sublineno = l
    # end def run

    # COMMANDS

    def cmd_assign (self, lhs, expr):
        if callable (expr):
            result = expr ()
        else:
            result = expr
        lhs ().set (result)
    # end def cmd_assign

    def cmd_close (self, fhandle = None):
        """ Seems a missing file handle closes all files
            We interpret a missing '#' as the same file as with '#'
        """
        if fhandle is None:
            for fh in self.files:
                if self.files [fh] != sys.stdout:
                    self.files [fh].close ()
            self.files = {}
            return
        fhandle = to_fhandle (fhandle)
        if fhandle not in self.files:
            print ("Warning: Closing unopened file %s" % fhandle)
            return
        if self.files [fhandle] and self.files [fhandle] != sys.stdout:
            self.files [fhandle].close ()
        del self.files [fhandle]
    # end def cmd_close

    def cmd_cls (self):
        """ Clear screen? """
        self.col = 0
    # end def cmd_cls

    def cmd_color (self, intlist):
        pass
    # end def cmd_color

    def cmd_defint (self, vars):
        for v in vars:
            self.defint [v] = 1
            self.var [v] = 0
    # end def cmd_defint

    def cmd_defsng (self, vars):
        """ We ignore single precision setting, all is double
        """
        pass
    # end cmd_defsng

    def cmd_dim (self, dimlist):
        for dentry in dimlist:
            v, l = dentry ()
            self.dim [v] = np.zeros (l)
    # end def cmd_dim

    def _ifclause_check (self):
        if not self.stack:
            self.raise_error ('ELSE without IF')
        if not isinstance (self.stack.top, Stack_Entry_If):
            self.raise_error ('ELSE without IF')
        return self.stack.top
    # end def _ifclause_check

    def cmd_else (self):
        top = self._ifclause_check ()
        top.handle_else ()
    # end def cmd_else

    def cmd_end (self):
        """ We treat the 'SYSTEM' command same as 'END'
            In some Basic variants the interpreter stops on END and
            waits for something to completely terminate, we don't do
            this.
        """
        self.running = False
    # end def cmd_end
    cmd_system = cmd_end

    def cmd_endif (self):
        self._ifclause_check ()
        self.stack.pop ()
    # end def cmd_endif

    def cmd_field (self, fhandle, fieldlist):
        self.fields [to_fhandle (fhandle)] = fieldlist
    # end def cmd_field

    def cmd_for (self, var, frm, to, step = 1):
        #print ('FOR command: %s %s' % (var, self.fline))
        frm = frm ()
        to  = to  ()
        if step != 1:
            step = step ()
        cond = self.exec_condition
        # Search backward on stack if we have the same FOR
        found = False
        for n, entry in enumerate (self.stack):
            if not isinstance (entry, Stack_Entry_For):
                break
            if entry.var == var:
                found = True
                break
        if found:
            for k in range (n + 1):
                #print ('POP: %s' % self.stack.top.var)
                self.stack.pop ()
        if self.exec_condition:
            self.var [var] = frm
            cond = (step > 0 and frm <= to) or (step < 0 and frm >= to)
        stack_entry = Stack_Entry_For (self, cond, var, frm, to, step)
        self.stack.push (stack_entry)
    # end def cmd_for

    def cmd_get (self, fhandle):
        fh = to_fhandle (fhandle)
        fl = self.fields [fh]
        if self.files [fh] is None:
            for l, lhs in fl:
                lhs ().set ('')
        else:
            try:
                r = self.files [fh].read (self.reclen [fh])
            except IOError:
                r = b''
            off = 0
            for l, lhs in fl:
                lhs ().set (r [off:off+l])
                off += l
    # end def cmd_get

    def cmd_gosub (self, nextline):
        if self.context:
            self.gstack.append (self.context)
            self.context = None
        else:
            self.gstack.append (Context (self))
        self.next = (int (nextline), 0)
    # end def cmd_gosub

    def cmd_goto (self, nextline):
        self.context = None
        self.next = (int (nextline), 0)
    # end def cmd_goto

    def _cmd_if (self, line_or_cmd):
        if isinstance (line_or_cmd, int):
            self.next = (int (line_or_cmd), 0)
        elif isinstance (line_or_cmd, tuple):
            line_or_cmd [0] (*line_or_cmd [1:])
        else:
            self.exec_cmdlist (line_or_cmd, 0)
    # end def _cmd_if

    def cmd_if (self, expr, line_or_cmd, line_or_cmd2 = None):
        if expr ():
            self._cmd_if (line_or_cmd)
        elif line_or_cmd2 is not None:
            self._cmd_if (line_or_cmd2)
    # end def cmd_if

    def cmd_if_start (self, expr):
        cond = self.exec_condition and expr ()
        self.stack.push (Stack_Entry_If (self, cond))
    # end def cmd_if_start

    def cmd_input (self, vars, s = ''):
        prompt = s + ': '
        if self.input is not None:
            print (prompt, end = '')
            value = self.input.readline ().rstrip ()
            print (value)
        else:
            value = input (prompt)
        if len (vars) > 1:
            for lhs, v in zip (vars, value.split (',')):
                lhs ().set (v)
        else:
            lhs = vars [0] ()
            lhs.set (value)
    # end def cmd_input

    def cmd_locate (self, num):
        """ Probably positions cursor """
        print ('\r', end = '')
    # end def cmd_locate

    def cmd_lset (self, lhs, expr):
        """ According to pcbasic docs lset will do nothing if the
            variable is not defined. But apparently some mininec
            implementations use this with variables undefined. It may be
            a bug in the mininec implementation but we allow undefined
            variables. In case of undefined variables we treat this like
            an assignment.
        """
        lhs = lhs ()
        v, expr = self.lset_rset_mid_paramcheck (lhs, expr ())
        if expr is None:
            return
        if v is None:
            v = ' ' * len (expr)
        if len (expr) < len (v):
            if isinstance (expr, bytes):
                expr += b' ' * (len (v) - len (expr))
            else:
                expr += ' ' * (len (v) - len (expr))
        if len (expr) > len (v):
            expr = expr [:len (v)]
        lhs.set (expr)
    # end def cmd_lset

    def cmd_mid (self, lhs, pos, length, expr):
        lhs = lhs ()
        v, expr = self.lset_rset_mid_paramcheck (lhs, expr ())
        if v is None or expr is None:
            return
        if pos + length > len (v):
            length = len (v) - pos
        if length <= 0:
            return
        if len (expr) > length:
            expr = expr [:length]
        if len (expr) < length:
            length = len (expr)
        lhs.set (v [:pos] + expr + v [pos + length:])
    # end def cmd_lset

    def cmd_multi (self, l):
        """ Multiple commands separated by colon """
        self.exec_cmdlist (l, 0)
    # end def cmd_multi

    def cmd_next (self, var):
        #print ('NEXT command: %s %s' % (var, self.fline))
        if not self.stack:
            self.raise_error ('NEXT without FOR')
            return
        top = self.stack.top
        if not isinstance (top, Stack_Entry_For):
            self.raise_error ('NEXT in unterminated IF statement')
            return
        if top.var != var:
            self.raise_error ('NEXT %s in FOR %s' % (var, top.var))
            return
        top.handle_next ()
    # end def cmd_next

    def cmd_ongoto (self, expr, lines):
        expr = int (expr ()) - 1
        self.next = lines [expr]
    # end def cmd_ongoto

    def cmd_open (self, expr, forwhat, fhandle):
        fhandle = to_fhandle (fhandle)
        expr    = expr ()
        assert isinstance (expr, str)
        if expr == 'SCRN:':
            self.files [fhandle] = sys.stdout
        else:
            open_arg = 'w'
            if forwhat.lower () == 'append':
                open_arg = 'a'
            self.files [fhandle] = open (expr, open_arg)
    # end def cmd_open

    def cmd_open_bin (self, expr, fhandle, len_expr):
        fhandle  = to_fhandle (fhandle)
        expr     = expr ()
        len_expr = int (len_expr ())
        assert isinstance (expr, str)
        try:
            self.files  [fhandle] = open (expr, 'r+b')
            self.reclen [fhandle] = len_expr
        except FileNotFoundError:
            self.files [fhandle] = open (expr, 'wb')
            self.reclen [fhandle] = len_expr
    # end def cmd_open_bin

    def cmd_print (self, printlist, fhandle = None, using = False):
        file = sys.stdout
        if fhandle is not None:
            file = self.files [fhandle]
        l   = []
        c   = None
        fmt = None
        for n, v in enumerate (printlist ()):
            if callable (v):
                v = v ()
            if n == 0 and using:
                fmt = Print_Using (v)
                continue
            c = self.special_by_code.get (v, None)
            if c is None:
                if fmt:
                    f = fmt.get ()
                    v = f % v
                elif isinstance (v, float):
                    v = format_float (v)
                v = str (v)
                self.col += len (v)
                l.append (v)
            elif c == 'COMMA' and not using:
                for tb in self.tab:
                    if self.col >= tb:
                        continue
                    v = ' ' * (tb - self.col)
                    l.append (v)
                    self.col += len (v)
                    break
        end = '\n'
        if c is None:
            self.col = 0
        else:
            end = ''
        print (''.join (l), file = file, end = end)
    # end def cmd_print

    def cmd_put (self, fhandle):
        fh = to_fhandle (fhandle)
        fl = self.fields [fh]
        if self.files [fh] is not None:
            buf = []
            for l, lhs in fl:
                s = lhs ().get ()
                if s is None:
                    s = b''
                if isinstance (s, str):
                    s = s.encode ('ascii')
                if len (s) < l:
                    s += b' ' * (l - len (s))
                if len (s) > l:
                    s = s [:l]
                buf.append (s)
            buf = b''.join (buf)
            if len (buf) > self.reclen [fh]:
                buf = buf [:self.reclen [fh]]
            if len (buf) < self.reclen [fh]:
                buf += b' ' * (self.reclen [fh] - len (buf))
            self.files [fh].write (buf)
    # end def cmd_put

    def cmd_read (self, vars):
        for lhs in vars:
            result = self.data.pop (0)
            lhs ().set (result)
    # end def cmd_read

    def cmd_rem (self):
        pass
    # end def cmd_rem

    def cmd_return (self):
        if not self.gstack:
            self.raise_error ('RETURN without GOSUB')
            return
        next = self.gstack.pop ()
        next.restore_context ()
        if next.cmdlist:
            self.exec_cmdlist (next.cmdlist, next.cmdidx + 1)
    # end def cmd_return

    def cmd_rset (self, lhs, expr):
        """ According to pcbasic docs lset will do nothing if the
            variable is not defined. But apparently some mininec
            implementations use LSET with variables undefined. It may be
            a bug in the mininec implementation but we allow undefined
            variables. In case of undefined variables we treat this like
            an assignment. We make RSET mirror the behavior of LSET.
        """
        lhs = lhs ()
        v, expr = self.lset_rset_mid_paramcheck (lhs, expr ())
        if expr is None:
            return
        if v is None:
            v = ' ' * len (expr)
        if len (expr) < len (v):
            if isinstance (expr, bytes):
                expr = b' ' * (len (v) - len (expr)) + expr
            else:
                expr = ' ' * (len (v) - len (expr)) + expr
        if len (expr) > len (v):
            expr = expr [:len (v)]
        lhs.set (expr)
    # end def cmd_rset

    def cmd_write (self, fhandle, exprs):
        file = sys.stdout
        if fhandle is not None:
            file = self.files [fhandle]
        r    = []
        for ex in exprs ():
            r.append (repr (ex))
        print (','.join (r), end = '\r\n', file = file)
    # end def cmd_write

    # PRODUCTIONS OF PARSER

    precedence = \
        ( ('left', 'AND', 'OR')
        , ('left', 'LT',  'GT', 'LE', 'GE', 'NE', 'EQ')
        , ('left', 'PLUS',  'MINUS')
        , ('left', 'TIMES', 'DIVIDE', 'MOD')
        , ('left', 'EXPO')
        )

    def p_error (self, p):
        print \
            ( "Syntax error in input in input line %s (%s.%s)!"
            % (self.fline, self.lineno, self.sublineno)
            )
    # end def p_error

    def p_start (self, p):
        """
            statement : simple-statement
                      | statement COLON simple-statement
        """
        if len (p) == 2:
            p [0] = p [1]
        else:
            if isinstance (p [1], tuple):
                p [0] = [p [1]] + [p [3]]
            else:
                p [0] = p [1] + [p [3]]
    # end def p_start

    def p_stmt (self, p):
        """
            simple-statement : assignment-statement
                             | close-statement
                             | cls-statement
                             | color-statement
                             | data-statement
                             | defint-statement
                             | defsng-statement
                             | dim-statement
                             | else-statement
                             | endif-statement
                             | end-statement
                             | field-statement
                             | for-statement
                             | get-statement
                             | gosub-statement
                             | goto-statement
                             | if-start-statement
                             | if-statement
                             | input-statement
                             | locate-statement
                             | lset-statement
                             | mid-statement
                             | next-statement
                             | ongoto-statement
                             | open-statement
                             | print-statement
                             | put-statement
                             | read-statement
                             | rem-statement
                             | return-statement
                             | rset-statement
                             | write-statement

        """
        cmd = p [1][0]
        method = getattr (self, 'cmd_' + cmd.lower ())
        p [0] = (method, *p [1][1:])
    # end def p_stmt

    def p_assignment_statement (self, p):
        """
            assignment-statement : lhs EQ expr
        """
        p [0] = ('assign', p [1], p [3])
    # end def p_assignment_statement

    def p_cls_statement (self, p):
        """
            cls-statement : CLS
        """
        # probably clear screen
        p [0] = (p [1],)
    # end def p_cls_statement

    def p_close_statement (self, p):
        """
            close-statement : CLOSE
                            | CLOSE FHANDLE
                            | CLOSE NUMBER
        """
        if len (p) == 2:
            p [0] = (p [1],)
        else:
            p [0] = (p [1], p [2])
    # end def p_close_statement

    def p_color_statement (self, p):
        """
            color-statement : COLOR intlist
        """
        p [0] = [p [1], p [2]]
    # end def p_color_statement

    def p_data_statement (self, p):
        """
            data-statement : DATA literal-list
        """
        # Must be executed immediately, data can later be read by read commands
        for d in p [2]:
            self.data.append (d)
        p [0] = ('REM',)
    # end def p_data_statement

    def p_defint_statement (self, p):
        """
            defint-statement : DEFINT varlist
        """
        p [0] = [p [1], p [2]]
    # end def p_defint_statement

    def p_defsng_statement (self, p):
        """
            defsng-statement : DEFSNG varlist
        """
        p [0] = [p [1], p [2]]
    # end def p_defint_statement

    def p_dim_statement (self, p):
        """
            dim-statement : DIM dimlist
        """
        p [0] = (p [1], p [2])
    # end def p_dim_statement

    def p_dimlist (self, p):
        """
            dimlist : dimrhs
                    | dimlist COMMA dimrhs
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_dimlist

    def p_dimrhs (self, p):
        """
            dimrhs : VAR LPAREN exprlist RPAREN
        """
        p1 = p [1]
        p3 = p [3]
        def x ():
            return (p1, [int (a) + 1 for a in p3 ()])
        p [0] = x
    # end def p_dimrhs

    def p_else (self, p):
        """
            else-statement : ELSE
        """
        p [0] = [p [1]]
    # end def p_else

    def p_empty (self, p):
        'empty :'
        pass
    # end def p_empty

    def p_end_statement (self, p):
        """
            end-statement : END
            end-statement : SYSTEM
        """
        p [0] = (p [1], )
    # end def p_end_statement

    def p_endif_statement (self, p):
        """
            endif-statement : END IF
        """
        p [0] = ['endif']
    # end def p_endif_statement

    def p_expression_literal (self, p):
        """
            expr : literal
        """
        p1 = p [1]
        def x ():
            return p1
        p [0] = x
    # end def p_expression_literal

    def p_expression_function (self, p):
        """
            expr : ABS LPAREN expr RPAREN
                       | ATN LPAREN expr RPAREN
                       | CHR LPAREN expr RPAREN
                       | COS LPAREN expr RPAREN
                       | CVI LPAREN expr RPAREN
                       | CVS LPAREN expr RPAREN
                       | FRP LPAREN expr RPAREN
                       | INT LPAREN expr RPAREN
                       | LOG LPAREN expr RPAREN
                       | MKI LPAREN expr RPAREN
                       | MKS LPAREN expr RPAREN
                       | SGN LPAREN expr RPAREN
                       | SIN LPAREN expr RPAREN
                       | SQR LPAREN expr RPAREN
                       | STR LPAREN expr RPAREN
                       | TAB LPAREN expr RPAREN
                       | VAL LPAREN expr RPAREN
        """
        fn = p [1].lower ()
        if fn == 'int':
            fun = int
        elif fn == 'tab':
            fun = self.fun_tab
        elif fn == 'cvi':
            fun = fun_cvi
        elif fn == 'cvs':
            fun = fun_cvs
        elif fn == 'chr$':
            fun = fun_chr
        elif fn == 'val':
            fun = float
        elif fn == 'str$':
            fun = fun_str
        elif fn == 'frp':
            fun = fun_fractional_part
        elif fn == 'mki$':
            fun = fun_mki
        elif fn == 'mks$':
            fun = fun_mks
        else:
            if fn == 'sgn':
                fn = 'sign'
            if fn == 'sqr':
                fn = 'sqrt'
            if fn == 'atn':
                fn = 'arctan'
            fun = getattr (np, fn)
        p3 = p [3]
        def x ():
            return fun (p3 ())
        p [0] = x
    # end def p_expression_function

    def p_expression_function_2 (self, p):
        """
            expr : LEFT  LPAREN expr COMMA expr RPAREN
                 | RIGHT LPAREN expr COMMA expr RPAREN
        """
        fn = p [1].lower ()
        if fn == 'left$':
            fun = fun_left
        else:
            assert fn == 'right$'
            fun = fun_right
        p3 = p [3]
        p5 = p [5]
        def x ():
            return fun (p3 (), p5 ())
        p [0] = x
    # end def p_expression_function_2

    def p_expression_function_2_3 (self, p):
        """
            expr : MID LPAREN expr COMMA expr COMMA expr RPAREN
                 | MID LPAREN expr COMMA expr RPAREN
        """
        fn = p [1].lower ()
        assert fn == 'mid$'
        fun = fun_mid
        p3 = p [3]
        p5 = p [5]
        if len (p) < 8:
            p7 = None
        else:
            p7 = p [7]
        def x ():
            if p7 is not None:
                return fun (p3 (), p5 (), p7 ())
            return fun (p3 (), p5 (), None)
        p [0] = x
    # end def p_expression_function_3

    def p_expression_paren (self, p):
        """
            expr : LPAREN expr RPAREN
        """
        p [0] = p [2]
    # end def p_expression_paren

    def p_expression_twoop (self, p):
        """
            expr : expr PLUS   expr
                 | expr MINUS  expr
                 | expr TIMES  expr
                 | expr DIVIDE expr
                 | expr MOD    expr
                 | expr GT     expr
                 | expr GE     expr
                 | expr LT     expr
                 | expr LE     expr
                 | expr NE     expr
                 | expr EQ     expr
                 | expr AND    expr
                 | expr OR     expr
                 | expr EXPO   expr
        """
        f1 = p [1]
        f3 = p [3]
        if p [2] == '+':
            def x ():
                return f1 () + f3 ()
        elif p [2] == '-':
            def x ():
                return f1 () - f3 ()
        elif p [2] == '*':
            def x ():
                return f1 () * f3 ()
        elif p [2] == '/':
            def x ():
                return f1 () / f3 ()
        elif p [2] == 'MOD':
            def x ():
                return f1 () % f3 ()
        elif p [2] == '>':
            def x ():
                return f1 () > f3 ()
        elif p [2] == '>=':
            def x ():
                return f1 () >= f3 ()
        elif p [2] == '<':
            def x ():
                return f1 () < f3 ()
        elif p [2] == '<=':
            def x ():
                return f1 () <= f3 ()
        elif p [2] == '<>' or p [2] == '><':
            def x ():
                return f1 () != f3 ()
        elif p [2] == '=':
            def x ():
                return f1 () == f3 ()
        elif p [2] == 'AND':
            def x ():
                return (f1 () and f3 ())
        elif p [2] == 'OR':
            def x ():
                return (f1 () or f3 ())
        elif p [2] == '^':
            def x ():
                return f1 () ** f3 ()
        p [0] = x
    # end def p_expression_twoop

    def p_expression_unaryminus (self, p):
        """
            expr : MINUS expr
        """
        p2 = p [2]
        def x ():
            return - p2 ()
        p [0] = x
    # end def p_expression_unaryminus

    def _var_helper (self, p1):
        default = 0.0
        if p1.endswith ('$'):
            default = ''
        elif p1.endswith ('%'):
            default = 0
        def x ():
            return self.var.get (p1, default)
        return x
    # end def _var_helper

    def p_expression_var (self, p):
        """
            expr : VAR
        """
        p1 = p [1]
        p [0] = self._var_helper (p1)
    # end def p_expression_var

    def p_expression_var_complex (self, p):
        """
            expr : VAR LPAREN exprlist RPAREN
        """
        p1 = p [1]
        p3 = p [3]
        def x ():
            r = [int (k) for k in p3 ()]
            return self.dim [p1][*r]
        p [0] = x
    # end def p_expression_var_complex

    def p_exprlist (self, p):
        """
            exprlist : expr
                     | exprlist COMMA expr
        """
        p1 = p [1]
        if len (p) == 2:
            def x ():
                return [p1 ()]
        else:
            p3 = p [3]
            def x ():
                return p1 () + [p3 ()]
        p [0] = x
    # end def p_exprlist

    def p_field_statement (self, p):
        """
            field-statement : FIELD FHANDLE COMMA fieldlist
        """
        p [0] = (p [1], p [2], p [4])
    # end def p_field_statement

    def p_fieldlist (self, p):
        """
            fieldlist : NUMBER AS lhs
                      | fieldlist COMMA NUMBER AS lhs
        """
        if len (p) == 4:
            p [0] = [(p [1], p [3])]
        else:
            p [0] = p [1] + [(p [3], p [5])]
    # end def p_fieldlist

    def p_for_statement (self, p):
        """
            for-statement : FOR VAR EQ expr TO expr
        """
        p [0] = (p [1], p [2], p [4], p [6])
    # end def p_for_statement

    def p_for_statement_step (self, p):
        """
            for-statement : FOR VAR EQ expr TO expr STEP expr
        """
        p [0] = (p [1], p [2], p [4], p [6], p [8])
    # end def p_for_statement_step

    def p_get_statement (self, p):
        """
            get-statement : GET FHANDLE
                          | GET NUMBER
        """
        p [0] = (p [1], p [2])
    # end def p_get_statement

    def p_goto_statement (self, p):
        """
            goto-statement : GOTO NUMBER
        """
        p [0] = [p [1], p [2]]
    # end def p_goto_statement

    def p_gosub_statement (self, p):
        """
            gosub-statement : GOSUB NUMBER
        """
        p [0] = [p [1], p [2]]
    # end def p_gosub_statement

    def p_if_start (self, p):
        """
            if-start-statement : IF expr THEN
        """
        p [0] = ['if_start', p [2]]
    # end def p_if_start

    def p_if_statement (self, p):
        """
            if-statement : IF expr THEN NUMBER
                         | IF expr THEN NUMBER ELSE NUMBER
                         | IF expr THEN NUMBER ELSE statement
                         | IF expr THEN statement
                         | IF expr THEN statement ELSE NUMBER
                         | IF expr THEN statement ELSE statement
        """
        if len (p) == 5:
            p [0] = [p [1], p [2], p [4]]
        else:
            p [0] = [p [1], p [2], p [4], p [6]]
    # end def p_if_statement

    def p_if_statement_without_then (self, p):
        """
            if-statement : IF expr GOTO NUMBER
        """
        p [0] = [p [1], p [2], p [4]]
    # end def p_if_statement_without_then

    def p_input_statement (self, p):
        """
            input-statement : INPUT STRING_SQ SEMIC varlist-complex
                            | INPUT STRING_DQ SEMIC varlist-complex
        """
        p [0] = (p [1], p [4], p [2])
    # end def p_input_statement

    def p_input_statement_multi (self, p):
        """
            input-statement : INPUT varlist-complex
        """
        p [0] = (p [1], p [2])
    # end def p_input_statement_multi

    def p_intlist (self, p):
        """
            intlist : NUMBER
                    | intlist COMMA NUMBER
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_intlist

    def p_lhs (self, p):
        """
            lhs : VAR
                | VAR LPAREN exprlist RPAREN
        """
        p1 = p [1]
        if len (p) == 2:
            def x ():
                return L_Value_Var (self, p1)
        else:
            p3 = p [3]
            def x ():
                r = [int (k) for k in p3 ()]
                return L_Value_Dim (self, p1, r)
        p [0] = x
    # end def p_lhs

    def p_literal (self, p):
        """
            literal : NUMBER
                    | STRING_DQ
                    | STRING_SQ
        """
        copro = '{math co-processor}'
        if isinstance (p [1], str) and copro in p [1]:
            p [0] = p [1].replace (copro, '*******************')
        else:
            p [0] = p [1]
    # end def p_literal

    def p_literal_list (self, p):
        """
            literal-list : literal
                         | literal-list COMMA literal
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_literal_list

    def p_locate_statement (self, p):
        """
            locate-statement : LOCATE CSRLIN COMMA NUMBER
        """
        p [0] = (p [1], p [4])
    # end def p_locate_statement

    def p_lset_statement (self, p):
        """
            lset-statement : LSET lhs EQ expr
        """
        p [0] = (p [1], p [2], p [4])
    # end def p_lset_statement

    def p_mid_statement (self, p):
        """
            mid-statement : MID LPAREN lhs COMMA expr COMMA expr RPAREN EQ expr
                          | MID LPAREN lhs COMMA expr RPAREN EQ expr
        """
        if len (p) == 9:
            p [0] = (p [1], p [3], p [5], None, p [8])
        else:
            p [0] = (p [1], p [3], p [5], p [7], p [10])
    # end def p_mid_statement

    def p_next_statement (self, p):
        """
            next-statement : NEXT VAR
        """
        p [0] = (p [1], p [2])
    # end def p_next_statement

    def p_ongoto_statement (self, p):
        """
            ongoto-statement : ON expr GOTO intlist
        """
        p [0] = ('ongoto', p [2], p [4])
    # end def p_ongoto_statement

    def p_open_statement (self, p):
        """
            open-statement : OPEN expr FOR OUTPUT AS FHANDLE
                           | OPEN expr FOR APPEND AS FHANDLE
        """
        p [0] = (p [1], p [2], p [4], p [6])
    # end def p_open_statement

    def p_open_statement_bin (self, p):
        """
            open-statement : OPEN expr AS FHANDLE LEN EQ expr
                           | OPEN expr FOR RANDOM AS FHANDLE LEN EQ expr
        """
        expr = p [2]
        if len (p) == 8:
            fhandle = p [4]
            length  = p [7]
        else:
            fhandle = p [6]
            length  = p [9]
        p [0] = ('open_bin', expr, fhandle, length)
    # end def p_open_statement_bin

    def p_print_statement (self, p):
        """
            print-statement : PRINT printlist
                            | PRINT FHANDLE COMMA printlist
                            | PRINT FHANDLE COMMA USING printlist
        """
        if len (p) == 3:
            p [0] = (p [1], p [2])
        elif len (p) == 5:
            p [0] = (p [1], p [4], p [2])
        else:
            p [0] = (p [1], p [5], p [2], True)
    # end def p_print_statement

    def p_printlist (self, p):
        """
            printlist : empty
                      | expr
                      | printlist SEMIC expr
                      | printlist COMMA expr
                      | printlist expr
                      | printlist SEMIC
                      | printlist COMMA
        """
        p1 = p [1]
        if len (p) == 2:
            def x ():
                if p1 is None:
                    return []
                return [p1]
        elif len (p) == 3:
            if p [2] == ';' or p [2] == ',':
                p2 = self.print_special [p [2]][0]
                def x ():
                    return p1 () + [p2]
            else:
                # Two expressions are equivalent to a left-out semicolon
                px = self.print_special [';'][0]
                p2 = p [2]
                def x ():
                    return p1 () + [px, p2]
        else:
            p2 = self.print_special [p [2]][0]
            p3 = p [3]
            def x ():
                return p1 () + [p2, p3]
        p [0] = x
    # end def p_printlist

    def p_put_statement (self, p):
        """
            put-statement : PUT FHANDLE
                          | PUT NUMBER
        """
        p [0] = (p [1], p [2])
    # end def p_put_statement

    def p_read_statement (self, p):
        """
            read-statement : READ varlist-complex
        """
        p [0] = (p [1], p [2])
    # end def p_read_statement

    def p_rem_statement (self, p):
        """
            rem-statement : REM
        """
        p [0] = [p [1]]
    # end def p_rem_statement

    def p_return_statement (self, p):
        """
            return-statement : RETURN
        """
        p [0] = [p [1]]
    # end def p_return_statement

    def p_rset_statement (self, p):
        """
            rset-statement : RSET lhs EQ expr
        """
        p [0] = (p [1], p [2], p [4])
    # end def p_rset_statement

    def p_varlist (self, p):
        """
            varlist : varlist COMMA VAR
                    | varlist MINUS VAR
                    | VAR
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            if p [2] == '-':
                var = p [1][-1]
                if len (var) > 1:
                    self.raise_error ('Variable name "%s" too long' % var)
                    p [0] = p [1]
                    return
                if len (p [3]) > 1:
                    self.raise_error ('Variable name "%s" too long' % p [3])
                    p [0] = p [1]
                    return
                l   = p [1][:]
                s   = ord (var)
                e   = ord (p [3])
                for i in range (e - s):
                    l.append (chr (s + i + 1))
                p [0] = l
            else:
                p [0] = p [1] + [p [3]]
    # end def p_varlist

    def p_varlist_complex (self, p):
        """
            varlist-complex : varlist-complex COMMA lhs
                            | lhs
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_varlist_complex

    def p_write (self, p):
        """
            write-statement : WRITE FHANDLE COMMA exprlist
                            | WRITE exprlist
        """
        if len (p) == 5:
            p [0] = [p [1], p [2], p [4]]
        else:
            p [0] = [p [1], None, p [4]]
    # end def p_write

# end class Interpreter

def main (argv = sys.argv [1:]):
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( 'program'
        , help = 'Basic program to run'
        )
    cmd.add_argument \
        ( '-i', '--input-file'
        , help = 'Read input from file instead of stdin'
        )
    cmd.add_argument \
        ( '-L', '--break-line'
        , help = 'Line in basic where to stop in (python-) debugger'
        , type = int
        )
    cmd.add_argument \
        ( '-t', '--tab'
        , help    = 'Indicate tab position, can specified multiple times'
        , type    = int
        , action  = 'append'
        , default = []
        )
    args = cmd.parse_args (argv)
    interpreter = Interpreter (args)
    interpreter.break_lineno = args.break_line
    interpreter.run ()
# end def main

if __name__ == '__main__':
    main ()
