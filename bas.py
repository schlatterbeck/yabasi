#!/usr/bin/python3

from ply import yacc
from argparse import ArgumentParser
import numpy as np
import re
import sys
import tokenizer
import datetime

def fun_chr (expr):
    expr = int (expr)
    # Don't print formfeed
    if expr == 12:
        return ''
    return chr (expr)
# end def fun_chr

def fun_cvi (s):
    try:
        return int (s)
    except ValueError:
        return 0
# end def fun_cvi

def fun_cvs (s):
    try:
        return float (s)
    except ValueError:
        return 0.0
# end def fun_cvs

def fun_left (expr1, expr2):
    expr2 = int (expr2)
    assert isinstance (expr1, str)
    return expr1 [:expr2]
# end def fun_left

def fun_right (expr1, expr2):
    expr2 = int (expr2)
    assert isinstance (expr1, str)
    return expr1 [-expr2:]
# end def fun_right

#def _fmt_float (v, fmt = '%8f'):
def _fmt_float (v, fmt = '{:#.8g}'):
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
    ' 0 '
    >>> format_float (0.001)
    ' .001 '
    >>> format_float (-0.001)
    '-.001 '
    >>> format_float (2.141428111)
    ' 2.141428 '
    >>> format_float (4.99262212345e-03)
    ' 4.992622E-03 '
    >>> format_float (42.82857111)
    ' 42.82857 '
    >>> format_float (-.9036958111)
    '-.9036958 '
    """
    if v == 0.0:
        return ' 0 '
    e = int (np.floor (np.log10 (np.abs (v))))
    x = _fmt_float (v)
    f = '{:#.7g}'
    if abs (e) > 7 or len (x) >= 7 and abs (e) > 1:
        f = '%12E'
    v = _fmt_float (v, fmt = f)
    if not v.startswith ('-'):
        v = ' ' + v
    v = v + ' '
    return v
# end def format_float

class Interpreter:
    print_special = \
        { ',' : ('++,++', 'COMMA')
        , ';' : ('++;++', 'SEMIC')
        }
    special_by_code = dict \
        ((c [0], c [1]) for c in print_special.values ())
    tabpos = [14, 28, 42, 56]

    def __init__ (self, fn, input = None):
        self.input  = None
        if input:
            self.input = open (input, 'r')
        self.col    = 0
        self.lines  = {}
        self.stack  = []
        self.fors   = {}
        self.files  = {}
        self.data   = []
        self.reclen = {}
        self.fields = {}
        self.defint = {}
        # Variables and dimensioned variables do not occupy the same namespace
        self.var    = {}
        self.dim    = {}
        self.var ['DATE$'] = str (datetime.date.today ())
        self.var ['TIME$'] = datetime.datetime.now ().strftime ('%H:%M:%S')

        self.tokenizer = tokenizer.Tokenizer ()
        self.tokens    = tokenizer.Tokenizer.tokens
        self.parser    = yacc.yacc (module = self)

        with open (fn, 'r') as f:
            for l in f:
                l = l.rstrip ()
                #print (l)
                if l [0] == '\x1a':
                    break
                lineno, r = l.split (None, 1)
                lineno = self.lineno = int (lineno)
                self.tokenizer.lexer.lineno = lineno
                if ' ' in r:
                    a, b = r.split (None, 1)
                    if a == 'REM':
                        self.tokenizer.feed ('REM')
                        r = self.parser.parse (lexer = self.tokenizer)
                        self.insert (r)
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

    def fun_tab (self, expr):
        # We print *at* the tab position
        expr     = int (expr) - 1
        dif      = expr - self.col
        return ' ' * dif
    # end def fun_tab

    def insert (self, r):
        if isinstance (r, list):
            self.lines [self.lineno] = (self.cmd_multi, r)
        else:
            self.lines [self.lineno] = r
    # end def insert

    def run (self):
        self.running = True
        l = self.lineno = self.first
        while self.running and l:
            if self.lineno == self.break_lineno or self.break_lineno == 'all':
                import pdb; pdb.set_trace ()
            self.next = self.nextline.get (l)
            #print ('lineno: %d' % l)
            line = self.lines [l]
            line [0] (*line [1:])
            l = self.lineno = self.next
    # end def run

    def setvar (self, var, value):
        if callable (var):
            var (value)
        else:
            if var.endswith ('%') or var in self.defint:
                value = int (value)
            if not var.endswith ('$'):
                value = float (value)
            self.var [var] = value
    # end def setvar

    # COMMANDS

    def cmd_assign (self, var, expr):
        if callable (expr):
            result = expr ()
        else:
            result = expr
        self.setvar (var, result)
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
        if not isinstance (fhandle, str):
            fhandle = '#%d' % fhandle
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

    def cmd_dim (self, dimlist):
        for v, l in dimlist:
            self.dim [v] = np.zeros (l)
    # end def cmd_dim

    def cmd_end (self):
        self.running = False
    # end def cmd_end

    def cmd_field (self, fhandle, fieldlist):
        self.fields [fhandle] = fieldlist
    # end def cmd_field

    def cmd_for (self, var, frm, to, step = 1):
        frm = frm ()
        to  = to  ()
        if step != 1:
            step = step ()
        self.setvar (var, frm)
        if (step > 0 and frm <= to) or (step < 0 and frm >= to):
            self.fors [var] = [self.next, frm, to, step, frm]
        else:
            # Skip beyond corresponding 'NEXT'
            line = self.lines [self.lineno]
            while line [0] != self.cmd_next or line [1] != var:
                l = self.lineno = self.next
                self.next = self.nextline.get (l)
                line = self.lines [l]
            #print ('\nSkipped to %d' % self.lineno)
    # end def cmd_for

    def cmd_get (self, num):
        fh = '#%d' % num
        fl = self.fields [fh]
        if self.files [fh] is None:
            for l, var in fl:
                self.var [var] = ''
        else:
            r = self.files [fh].read (self.reclen [fh])
            off = 0
            for l, var in fl:
                self.var [var] = r [off:off+l]
                off += l
    # end def cmd_get

    def cmd_gosub (self, nextline):
        self.stack.append (self.next)
        self.next = int (nextline)
    # end def cmd_gosub

    def cmd_goto (self, nextline):
        self.next = int (nextline)
    # end def cmd_goto

    def _cmd_if (self, line_or_cmd):
        if isinstance (line_or_cmd, int):
            self.next = int (line_or_cmd)
        elif isinstance (line_or_cmd, tuple):
            line_or_cmd [0] (*line_or_cmd [1:])
        else:
            for cmd in line_or_cmd:
                cmd [0] (*cmd [1:])
    # end def _cmd_if

    def cmd_if (self, expr, line_or_cmd, line_or_cmd2 = None):
        if expr ():
            self._cmd_if (line_or_cmd)
        elif line_or_cmd2 is not None:
            self._cmd_if (line_or_cmd2)
    # end def cmd_if

    def cmd_input (self, vars, s = ''):
        prompt = s + ': '
        if self.input is not None:
            print (prompt, end = '')
            value = self.input.readline ().rstrip ()
        else:
            value = input (prompt)
        if len (vars) > 1:
            for var, v in zip (vars, value.split (',')):
                self.setvar (var, v)
        else:
            var = vars [0]
            self.setvar (vars [0], value)
    # end def cmd_input

    def cmd_locate (self, num):
        """ Probably positions cursor """
        print ('\r', end = '')
    # end def cmd_locate

    def cmd_multi (self, l):
        """ Multiple commands separated by colon """
        for item in l:
            item [0] (*item [1:])
    # end def cmd_multi

    def cmd_next (self, var):
        fors = self.fors [var]
        # Add step
        fors [-1] += fors [3]
        self.setvar (var, fors [-1])
        #print ('NEXT: %s = %s' % (var, fors [-1]))
        if  (  (fors [3] > 0 and fors [-1] <= fors [2])
            or (fors [3] < 0 and fors [-1] >= fors [2])
            ):
            self.next = fors [0]
        else:
            del self.fors [var]
            #print ('\nNEXT: %s DONE' % (var,))
    # end def cmd_next

    def cmd_ongoto (self, expr, lines):
        expr = int (expr ()) - 1
        self.next = lines [expr]
    # end def cmd_ongoto

    def cmd_open (self, expr, fhandle):
        expr = expr ()
        assert isinstance (expr, str)
        if expr == 'SCRN:':
            self.files [fhandle] = sys.stdout
        else:
            self.files [fhandle] = open (expr, 'w')
    # end def cmd_open

    def cmd_open_read (self, expr, fhandle, len_expr):
        expr = expr ()
        len_expr = int (len_expr ())
        assert isinstance (expr, str)
        try:
            self.files  [fhandle] = open (expr, 'r')
            self.reclen [fhandle] = len_expr
        except FileNotFoundError:
            self.files [fhandle] = None
    # end def cmd_open_read

    def _format_using (self, v):
        f   = []
        s   = 0
        bc  = 0
        ac  = 0
        fmt = []
        for x in v:
            if x == '#':
                if s == 0:
                    bc += 1
                elif s == 1:
                    ac += 1
                else:
                    assert 0
            elif x == '.':
                assert s == 0
                s = 1
            elif x == '^':
                if ac or bc:
                    ln = ac + bc + s
                    f.append ('%%%s.%sf' % (ln, ac))
                    fmt.append (''.join (f))
                    f = []
                ac = bc = 0
            else:
                if ac or bc:
                    ln = ac + bc + s
                    f.append ('%%%s.%sf' % (ln, ac))
                    fmt.append (''.join (f))
                    f = []
                ac = bc = 0
                f.append (x)
        if ac or bc:
            ln = ac + bc + s
            f.append ('%%%s.%sf' % (ln, ac))
            fmt.append (''.join (f))
            f = []
        return fmt
    # end def _format_using

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
                fmt = self._format_using (v)
                continue
            c = self.special_by_code.get (v, None)
            if c is None:
                if fmt:
                    f = fmt.pop (0)
                    v = f % v
                elif isinstance (v, float):
                    v = format_float (v)
                v = str (v)
                self.col += len (v)
                l.append (v)
            elif c == 'COMMA':
                for tb in self.tabpos:
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

    def cmd_read (self, vars):
        for var in vars:
            result = self.data.pop (0)
            self.setvar (var, result)
    # end def cmd_read

    def cmd_rem (self):
        pass
    # end def cmd_rem

    def cmd_return (self):
        self.next = self.stack.pop ()
    # end def cmd_return

    # PRODUCTIONS OF PARSER

    precedence = \
        ( ('left', 'AND', 'OR')
        , ('left', 'LT',  'GT', 'LE', 'GE', 'NE', 'EQ')
        , ('left', 'PLUS',  'MINUS')
        , ('left', 'TIMES', 'DIVIDE', 'MOD')
        , ('left', 'EXPO')
        )

    def p_error (self, p):
        print ("Syntax error in input in line %s!" % self.lineno)
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
                             | dim-statement
                             | end-statement
                             | field-statement
                             | for-statement
                             | get-statement
                             | gosub-statement
                             | goto-statement
                             | if-statement
                             | input-statement
                             | locate-statement
                             | next-statement
                             | ongoto-statement
                             | open-statement
                             | print-statement
                             | read-statement
                             | rem-statement
                             | return-statement

        """
        cmd = p [1][0]
        method = getattr (self, 'cmd_' + cmd.lower ())
        p [0] = (method, *p [1][1:])
    # end def p_stmt

    def p_assignment_statement (self, p):
        """
            assignment-statement : lhs EQ expression
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
            dimrhs : VAR LPAREN intlist RPAREN
        """
        p [0] = (p [1], [a + 1 for a in p [3]])
    # end def p_dimrhs

    def p_empty (self, p):
        'empty :'
        pass
    # end def p_empty

    def p_end_statement (self, p):
        """
            end-statement : END
        """
        p [0] = (p [1], )
    # end def p_end_statement

    def p_expression_literal (self, p):
        """
            expression : literal
        """
        p1 = p [1]
        def x ():
            return p1
        p [0] = x
    # end def p_expression_literal

    def p_expression_function (self, p):
        """
            expression : ABS LPAREN expression RPAREN
                       | ATN LPAREN expression RPAREN
                       | COS LPAREN expression RPAREN
                       | LOG LPAREN expression RPAREN
                       | SGN LPAREN expression RPAREN
                       | SIN LPAREN expression RPAREN
                       | SQR LPAREN expression RPAREN
                       | INT LPAREN expression RPAREN
                       | TAB LPAREN expression RPAREN
                       | CVI LPAREN expression RPAREN
                       | CVS LPAREN expression RPAREN
                       | CHR LPAREN expression RPAREN
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
            expression : LEFT  LPAREN expression COMMA expression RPAREN
                       | RIGHT LPAREN expression COMMA expression RPAREN
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

    def p_expression_paren (self, p):
        """
            expression : LPAREN expression RPAREN
        """
        p [0] = p [2]
    # end def p_expression_paren

    def p_expression_twoop (self, p):
        """
            expression : expression PLUS   expression
                       | expression MINUS  expression
                       | expression TIMES  expression
                       | expression DIVIDE expression
                       | expression MOD    expression
                       | expression GT     expression
                       | expression GE     expression
                       | expression LT     expression
                       | expression LE     expression
                       | expression NE     expression
                       | expression EQ     expression
                       | expression AND    expression
                       | expression OR     expression
                       | expression EXPO   expression
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
            expression : MINUS expression
        """
        p2 = p [2]
        def x ():
            return - p2 ()
        p [0] = x
    # end def p_expression_unaryminus

    def p_expression_var (self, p):
        """
            expression : VAR
        """
        p1 = p [1]
        def x ():
            if p1.endswith ('$'):
                return self.var.get (p1, '')
            elif p1.endswith ('%'):
                return self.var.get (p1, 0)
            else:
                return self.var.get (p1, 0.0)
        p [0] = x
    # end def p_expression_var

    def p_expression_var_complex (self, p):
        """
            expression : VAR LPAREN exprlist RPAREN
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
            exprlist : expression
                     | exprlist COMMA expression
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
            fieldlist : NUMBER AS VAR
                      | fieldlist COMMA NUMBER AS VAR
        """
        if len (p) == 4:
            p [0] = [(p [1], p [3])]
        else:
            p [0] = p [1] + [(p [3], p [5])]
    # end def p_fieldlist

    def p_for_statement (self, p):
        """
            for-statement : FOR VAR EQ expression TO expression
        """
        p [0] = (p [1], p [2], p [4], p [6])
    # end def p_for_statement

    def p_for_statement_step (self, p):
        """
            for-statement : FOR VAR EQ expression TO expression STEP expression
        """
        p [0] = (p [1], p [2], p [4], p [6], p [8])
    # end def p_for_statement_step

    def p_get_statement (self, p):
        """
            get-statement : GET NUMBER
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

    def p_if_statement (self, p):
        """
            if-statement : IF expression THEN NUMBER
                         | IF expression THEN NUMBER ELSE NUMBER
                         | IF expression THEN NUMBER ELSE statement
                         | IF expression THEN statement
                         | IF expression THEN statement ELSE NUMBER
                         | IF expression THEN statement ELSE statement
        """
        if len (p) == 5:
            p [0] = [p [1], p [2], p [4]]
        else:
            p [0] = [p [1], p [2], p [4], p [6]]
    # end def p_if_statement

    def p_if_statement_without_then (self, p):
        """
            if-statement : IF expression GOTO NUMBER
        """
        p [0] = [p [1], p [2], p [4]]
    # end def p_if_statement_without_then

    def p_input_statement (self, p):
        """
            input-statement : INPUT STRING SEMIC VAR
        """
        p [0] = (p [1], [p [4]], p [2])
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
        if len (p) == 2:
            p [0] = p [1]
        else:
            p1 = p [1]
            p3 = p [3]
            def x (v):
                r = [int (k) for k in p3 ()]
                if p1.endswith ('%'):
                    v = int (v)
                elif not p1.endswith ('$'):
                    v = float (v)
                self.dim [p1][*r] = v
            p [0] = x
    # end def p_lhs

    def p_literal (self, p):
        """
            literal : NUMBER
                    | STRING
        """
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

    def p_next_statement (self, p):
        """
            next-statement : NEXT VAR
        """
        p [0] = (p [1], p [2])
    # end def p_next_statement

    def p_ongoto_statement (self, p):
        """
            ongoto-statement : ON expression GOTO intlist
        """
        p [0] = ('ongoto', p [2], p [4])
    # end def p_ongoto_statement

    def p_open_statement (self, p):
        """
            open-statement : OPEN expression FOR OUTPUT AS FHANDLE
        """
        p [0] = (p [1], p [2], p [6])
    # end def p_open_statement

    def p_open_statement_read (self, p):
        """
            open-statement : OPEN expression AS FHANDLE LEN EQ expression
        """
        p [0] = ('open_read', p [2], p [4], p [7])
    # end def p_open_statement_read

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
                      | expression
                      | printlist SEMIC expression
                      | printlist COMMA expression
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
            p2 = self.print_special [p [2]][0]
            def x ():
                return p1 () + [p2]
        else:
            p2 = self.print_special [p [2]][0]
            p3 = p [3]
            def x ():
                return p1 () + [p2, p3]
        p [0] = x
    # end def p_printlist

    def p_printlist_ex_str (self, p):
        """
            printlist : printlist expression STRING
        """
        p1 = p [1]
        p2 = p [2]
        p3 = p [3]
        def x ():
            return p1 () + [p2, p3]
        p [0] = x
    # end def p_printlist_ex_str

    def p_printlist_str_ex (self, p):
        """
            printlist : printlist STRING expression
                      | STRING expression
        """
        p1 = p [1]
        p2 = p [2]
        if len (p) == 3:
            def x ():
                return [p1, p2]
        else:
            p3 = p [3]
            def x ():
                return p1 () + [p2, p3]
        p [0] = x
    # end def p_printlist_str_ex

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

    def p_varlist (self, p):
        """
            varlist : varlist COMMA VAR
                    | VAR
        """
        if len (p) == 2:
            p [0] = [p [1]]
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
    args = cmd.parse_args (argv)
    interpreter = Interpreter (args.program, input = args.input_file)
    interpreter.break_lineno = args.break_line
    interpreter.run ()
# end def main

if __name__ == '__main__':
    main ()
