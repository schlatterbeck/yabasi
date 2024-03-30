#!/usr/bin/python3

from ply import yacc
import numpy as np
import re
import sys
import tokenizer


class Interpreter:

    def __init__ (self, fn):
        self.lines  = {}
        self.stack  = []
        self.fors   = {}
        self.files  = {}
        self.data   = []
        self.reclen = {}
        self.var    = {}

        self.tokenizer = tokenizer.Tokenizer ()
        self.tokens    = tokenizer.Tokenizer.tokens
        self.parser    = yacc.yacc (module = self)

        with open (fn, 'r') as f:
            for l in f:
                l = l.rstrip ()
                print (l)
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
    # end def __init__

    def insert (self, r):
        if isinstance (r, list):
            self.lines [self.lineno] = (self.cmd_multi, r)
        else:
            self.lines [self.lineno] = r
    # end def insert

    def run (self):
        self.running = True
        l = self.first
        while self.running:
            self.next = self.nextline [l]
            line = self.lines [l]
            line [0] (*line [1:])
            l = self.next
    # end def run

    # COMMANDS

    def cmd_assign (self, var, expr):
        if callable (expr):
            result = expr ()
        else:
            result = expr
        if callable (var):
            var (result)
        else:
            self.var [var] = result
    # end def cmd_assign

    def cmd_close (self, fhandle = None):
        """ Seems a missing file handle closes all files
            We interpret a missing '#' as the same file as with '#'
        """
        if fhandle is None:
            for fh in self.files:
                self.files [fh].close ()
            self.files = {}
            return
        if not isinstance (fhandle, str):
            fhandle = '#%d' % fhandle
        self.files [fhandle].close ()
        del self.files [fhandle]
    # end def cmd_close

    def cmd_cls (self):
        """ Clear screen? """
        pass
    # end def cmd_cls

    def cmd_color (self, intlist):
        pass
    # end def cmd_color

    def cmd_defint (self, vars):
        for v in vars:
            self.var [v] = 0
    # end def cmd_defint

    def cmd_dim (self, dimlist):
        for v, l in dimlist:
            self.var [v] = np.zeros (l)
    # end def cmd_dim

    def cmd_end (self):
        self.running = False
    # end def cmd_end

    def cmd_field (self, fhandle, fieldlist):
        raise NotImplementedError ('"FIELD" Not yet implemented')
    # end def cmd_field

    def cmd_for (self, var, frm, to, step = 1):
        frm = frm ()
        to  = to  ()
        if step != 1:
            step = step ()
        self.fors [var] = [self.next, frm, to, step, frm]
    # end def cmd_for

    def cmd_get (self, num):
        raise NotImplementedError ('"GET" not yet implemented')
    # end def cmd_get

    def cmd_gosub (self, nextline):
        self.stack.append (self.next)
        self.next = int (nextline)
    # end def cmd_gosub

    def cmd_goto (self, nextline):
        self.next = int (nextline)
    # end def cmd_goto

    def cmd_if (self, expr, line_or_cmd, line_or_cmd2 = None):
        if expr ():
            if isinstance (line_or_cmd, int):
                self.next = int (line_or_cmd)
            else:
                line_or_cmd ()
        elif line_or_cmd2 is not None:
            if isinstance (line_or_cmd2, int):
                self.next = int (line_or_cmd2)
            else:
                line_or_cmd2 ()
    # end def cmd_if

    def cmd_input (self, vars, s = ''):
        for v in vars:
            if callable (v):
                v (input (s))
            else:
                self.var [var] = input (s)
            s = ''
    # end def cmd_input

    def cmd_locate (self, num):
        """ Probably positions cursor """
        print ('\r', end = '')
    # end def cmd_locate

    def cmd_multi (self, l):
        """ Multiple commands separated by colon """
        for item in l:
            l [0] (l [1:])
    # end def cmd_multi

    def cmd_next (self, var):
        fors = self.fors [var]
        # Add step
        fors [-1] += fors [3]
        self.next = fors [0]
    # end def cmd_next

    def cmd_ongoto (self, expr, lines):
        expr = int (expr ()) - 1
        self.next = lines [expr]
    # end def cmd_ongoto

    def cmd_open (self, expr, fhandle):
        expr = expr ()
        assert isinstance (expr, str)
        self.files [fhandle] = open (expr, 'w')
    # end def cmd_open

    def cmd_open_read (self, expr, fhandle, len_expr):
        expr = expr ()
        len_expr = int (len_expr ())
        assert isinstance (expr, str)
        self.files  [fhandle] = open (expr, 'r')
        self.reclen [fhandle] = len_expr
    # end def cmd_open_read

    def cmd_print (self, printlist, fhandle = None):
        f = sys.stdout
        if fhandle is not None:
            f = self.files [fhandle]
        print (''.join (str (s) for s in printlist ()), file = f)
    # end def cmd_print

    def cmd_read (self, vars):
        for var in vars:
            result = self.data.pop ()
            if callable (var):
                var (result)
            else:
                self.var [var] = result
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
        #import pdb;pdb.set_trace ()
        cmd = p [1][0]
        method = getattr (self, 'cmd_' + cmd.lower ())
        p [0] = (method, *p [1][1:])
    # end def p_stmt

    def p_assignment_statement (self, p):
        """
            assignment-statement : lhs EQ expression
        """
        p [0] = ['assign', p [1], p [3]]
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
        for d in p [1]:
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
        p [0] = (p [1], p [3])
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
        def x ():
            return p [1]
        p [0] = x
    # end def p_expression_literal

    def p_expression_function (self, p):
        """
            expression : ABS LPAREN expression RPAREN
                       | COS LPAREN expression RPAREN
                       | LOG LPAREN expression RPAREN
                       | SGN LPAREN expression RPAREN
                       | SIN LPAREN expression RPAREN
                       | SQR LPAREN expression RPAREN
                       | INT LPAREN expression RPAREN
        """
        fn = p [1].lower ()
        if fn == 'int':
            fun = int
        else:
            if fn == 'sgn':
                fn = 'sign'
            if fn == 'sqr':
                fn = 'sqrt'
            fun = getattr (np, fn)
        def x ():
            return fun (p [3] ())
        p [0] = x
    # end def p_expression_function

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
        def x ():
            return - p [2] ()
        p [0] = x
    # end def p_expression_unaryminus

    def p_expression_var (self, p):
        """
            expression : VAR
        """
        def x ():
            return self.var [p [1]]
        p [0] = x
    # end def p_expression_var

    def p_expression_var_complex (self, p):
        """
            expression : VAR LPAREN exprlist RPAREN
        """
        p1 = p [1]
        p3 = p [3]
        def x ():
            r = [int (k ()) for k in p3 ()]
            return self.var [p1][r]
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
                return [p1]
        else:
            p3 = p [3]
            def x ():
                return [p1] + p3
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
            return p [1]
        else:
            def x (v):
                r = [int (k) for k in p [3] ()]
                self.var [p [1]][r] = v
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
        if len (p) == 2:
            p [0] = (p [1], [])
        elif len (p) == 3:
            p [0] = (p [1], p [2])
        elif len (p) == 5:
            p [0] = (p [1], p [4], p [2])
        else:
            p [0] = (p [1], p [4], p [2], True)
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
        if len (p) == 2:
            def x ():
                return [p [1] ()]
        elif len (p) == 3:
            def x ():
                return [p [1] ()]
        else:
            def x ():
                return p [1] () + [p [3] ()]
        p [0] = x
    # end def p_printlist

    def p_printlist_ex_str (self, p):
        """
            printlist : printlist expression STRING
                      | expression STRING
        """
        if len (p) == 3:
            def x ():
                return [p [2] (), p [3]]
        else:
            def x ():
                return p [1] () + [p [2] (), p [3]]
        p [0] = x
    # end def p_printlist_ex_str

    def p_printlist_str_ex (self, p):
        """
            printlist : printlist STRING expression
                      | STRING expression
        """
        if len (p) == 3:
            def x ():
                return [p [2], p [3] ()]
        else:
            def x ():
                return p [1] () + [p [2], p [3] ()]
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
        elif len (p) == 5:
            p [0] = p [1] + [p [3]]
    # end def p_varlist_complex

# end class Interpreter

if __name__ == '__main__':
    interpreter = Interpreter (sys.argv [1])
    interpreter.run ()
