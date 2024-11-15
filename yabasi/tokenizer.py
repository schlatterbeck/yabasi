#!/usr/bin/python3
# Copyright (C) 2024 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ****************************************************************************

from ply import lex

class Tokenizer:

    funcs = \
        [ 'ABS'
        , 'ASC'
        , 'ATN'
        , 'COS'
        , 'CSRLIN'
        , 'CVI'
        , 'CVS'
        , 'EOF'
        , 'FIX'
        , 'FRP'
        , 'INSTR'
        , 'INT'
        , 'LOG'
        , 'SGN'
        , 'SIN'
        , 'SQR'
        , 'TAB'
        , 'VAL'
        ]
    funcs = dict ((k, k) for k in funcs)

    strfuncs = \
        [ 'CHR$'
        , 'INKEY$'
        , 'LEFT$'
        , 'MID$'
        , 'MKI$'
        , 'MKS$'
        , 'RIGHT$'
        , 'SPACE$'
        , 'STR$'
        , 'STRING$'
        ]

    reserved = \
        [ 'AND'
        , 'APPEND'
        , 'AS'
        , 'CALL'
        , 'CIRCLE'
        , 'CLOSE'
        , 'CLS'
        , 'COLOR'
        , 'DATA'
        , 'DEF'
        , 'DEFINT'
        , 'DEFSNG'
        , 'DIM'
        , 'END'
        , 'ELSE'
        , 'ERROR'
        , 'FIELD'
        , 'FOR'
        , 'GET'
        , 'GOSUB'
        , 'GOTO'
        , 'IF'
        , 'INPUT'
        , 'KEY'
        , 'KILL'
        , 'LEN'
        , 'LINE'
        , 'LOCATE'
        , 'LSET'
        , 'MOD'
        , 'NEXT'
        , 'NOT'
        , 'ON'
        , 'OPEN'
        , 'OR'
        , 'OUTPUT'
        , 'PRESET'
        , 'PRINT'
        , 'PSET'
        , 'PUT'
        , 'RANDOM'
        , 'READ'
        , 'REM'
        , 'RESET'
        , 'RESTORE'
        , 'RESUME'
        , 'RETURN'
        , 'RSET'
        , 'SCREEN'
        , 'SHELL'
        , 'STEP'
        , 'SYSTEM'
        , 'THEN'
        , 'TO'
        , 'USING'
        , 'WHILE'
        , 'WEND'
        , 'WIDTH'
        , 'WINDOW'
        , 'WRITE'
        , 'XOR'
        ]
    reserved = dict ((k, k) for k in reserved)

    tokens = \
        [ 'COLON'
        , 'COMMA'
        , 'DIVIDE'
        , 'EQ'
        , 'EXPO'
        , 'FHANDLE'
        , 'FNFUNCTION'
        , 'GE'
        , 'GT'
        , 'HEXNUMBER'
        , 'INTDIV'
        , 'LE'
        , 'LPAREN'
        , 'LT'
        , 'MINUS'
        , 'NE'
        , 'NUMBER'
        , 'PLUS'
        , 'QMARK'
        , 'RPAREN'
        , 'SEMIC'
        , 'STRING_DQ'
        , 'STRING_SQ'
        , 'TIMES'
        , 'VAR'
        ] + list (funcs) + list (reserved) + [x [:-1] for x in strfuncs]

    t_COLON   = r':'
    t_COMMA   = r','
    t_DIVIDE  = r'/'
    t_EQ      = r'='
    t_EXPO    = r'\^'
    t_FHANDLE = r'[#]\s*[0-9]'
    t_GE      = r'>='
    t_GT      = r'>'
    t_INTDIV  = r'\\'
    t_LE      = r'<='
    t_LPAREN  = r'[(]'
    t_LT      = r'<'
    t_MINUS   = r'-'
    t_NE      = r'(<>)|(><)'
    t_PLUS    = r'\+'
    t_QMARK   = r'[?]'
    t_RPAREN  = r'[)]'
    t_SEMIC   = r';'
    t_TIMES   = r'\*'

    t_ignore  = '\n\t '

    def t_FNFUNCTION (self, t):
        r'FN[A-Z][0-9A-Z.]*[#%!$]?'
        return t
    # end def t_FNFUNCTION

    def t_HEXNUMBER (self, t):
        r'&h[0-9A-Fa-f]+'
        v = int (t.value [2:], 16)
        t.value = v
        return t
    # end def t_HEXNUMBER

    def t_NUMBER (self, t):
        r'([0-9]*[.]\s*)?[0-9]+([eE][+-]?[0-9]+)?[#%!]?'
        v = t.value
        if v.endswith ('#') or v.endswith ('!') or v.endswith ('%'):
            if v.endswith ('!') or v.endswith('%'):
                assert v [:-1].isdecimal ()
            v = v [:-1]
        if v.isdecimal ():
            t.value = int (v)
        else:
            t.value = float (v.replace (' ', ''))
        return t
    # end def t_NUMBER

    def t_STRING_DQ (self, t):
        r'["][^"]*["]'
        v = t.value.strip ('"')
        t.value = v
        return t
    # end def t_STRING_DQ

    def t_STRING_SQ (self, t):
        r"['][^']*[']"
        v = t.value.strip ("'")
        t.value = v
        return t
    # end def t_STRING_SQ

    def t_VAR (self, t):
        r'[A-Z]+[0-9A-Z.]*[!%$]?'
        if t.value in self.funcs:
            t.type = self.funcs [t.value]
            return t
        if t.value in self.strfuncs:
            t.type = t.value [:-1]
            return t
        if t.value in self.reserved:
            t.type = self.reserved [t.value]
            return t
        return t
    # end def t_VAR

    def t_eof_comment (self, t):
        r"'[^']+$"
        pass
    # end def t_eof_comment

    def t_error (self, t):
        print ("Illegal character '%s'" % t.value [0])
        t.lexer.skip (1)
    # end def t_error

    # END TOKEN DEFINITION

    def __init__ (self, **kw):
        for n in self.strfuncs:
            n = n [:-1]
            setattr (self, 't_' + n, r'%s[$]' % n)
        self.lexer = lex.lex (module = self, **kw)
    # end def __init__

    def feed (self, s):
        self.lexer.input (s)
    # end def feed

    def token (self):
        t = self.lexer.token ()
        #print ('token called: %s' % t)
        return t
    # end def token

# end class Tokenizer

