#!/usr/bin/python3

from ply import lex

class Tokenizer:

    funcs = \
        [ 'ABS'
        , 'ATN'
        , 'COS'
        , 'CVI'
        , 'CVS'
        , 'FRP'
        , 'INT'
        , 'LOG'
        , 'SGN'
        , 'SIN'
        , 'SQR'
        , 'TAB'
        , 'VAL'
        ]
    funcs = dict ((k, k) for k in funcs)

    reserved = \
        [ 'AND'
        , 'APPEND'
        , 'AS'
        , 'CLOSE'
        , 'CLS'
        , 'COLOR'
        , 'CSRLIN'
        , 'DATA'
        , 'DEFINT'
        , 'DEFSNG'
        , 'DIM'
        , 'END'
        , 'ELSE'
        , 'FIELD'
        , 'FOR'
        , 'GET'
        , 'GOSUB'
        , 'GOTO'
        , 'IF'
        , 'INPUT'
        , 'LEN'
        , 'LOCATE'
        , 'LSET'
        , 'MOD'
        , 'NEXT'
        , 'ON'
        , 'OPEN'
        , 'OR'
        , 'OUTPUT'
        , 'PRINT'
        , 'RANDOM'
        , 'READ'
        , 'REM'
        , 'RETURN'
        , 'RSET'
        , 'STEP'
        , 'SYSTEM'
        , 'THEN'
        , 'TO'
        , 'USING'
        , 'WRITE'
        ]
    reserved = dict ((k, k) for k in reserved)

    tokens = \
        [ 'NUMBER'
        , 'STRING_DQ'
        , 'STRING_SQ'
        , 'VAR'
        , 'MINUS'
        , 'PLUS'
        , 'TIMES'
        , 'DIVIDE'
        , 'EXPO'
        , 'LT'
        , 'GT'
        , 'LE'
        , 'GE'
        , 'NE'
        , 'LEFT'
        , 'MID'
        , 'RIGHT'
        , 'CHR'
        , 'STR'
        , 'COMMA'
        , 'SEMIC'
        , 'EQ'
        , 'FHANDLE'
        , 'LPAREN'
        , 'RPAREN'
        , 'COLON'
        ] + list (funcs) + list (reserved)

    t_MINUS   = r'-'
    t_PLUS    = r'\+'
    t_TIMES   = r'\*'
    t_DIVIDE  = r'/'
    t_EXPO    = r'\^'
    t_GT      = r'>'
    t_GE      = r'>='
    t_LT      = r'<'
    t_LE      = r'<='
    t_NE      = r'(<>)|(><)'
    t_LEFT    = r'LEFT[$]'
    t_MID     = r'MID[$]'
    t_RIGHT   = r'RIGHT[$]'
    t_CHR     = r'CHR[$]'
    t_STR     = r'STR[$]'
    t_COMMA   = r','
    t_SEMIC   = r';'
    t_EQ      = r'='
    t_FHANDLE = r'[#][0-9]'
    t_LPAREN  = r'[(]'
    t_RPAREN  = r'[)]'
    t_COLON   = r':'

    t_ignore  = '\n\t '

    def t_NUMBER (self, t):
        r'([0-9]*[.])?[0-9]+([eE][+-]?[0-9]+)?[#!]?'
        v = t.value
        if v.endswith ('#') or v.endswith ('!'):
            if v.endswith ('!'):
                assert v [:-1].isdecimal ()
            v = v [:-1]
        if v.isdecimal ():
            t.value = int (v)
        else:
            t.value = float (v)
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
        r'[A-Z]+[0-9A-Z]*[!%$]?'
        if t.value in self.funcs:
            t.type = self.funcs [t.value]
            return t
        if t.value in self.reserved:
            t.type = self.reserved [t.value]
            return t
        if t.value == 'LEFT$' or t.value == 'RIGHT$' or t.value == 'CHR$':
            t.type = t.value [:-1]
            return t
        if t.value == 'MID$' or t.value == 'STR$':
            t.type = t.value [:-1]
            return t
        return t
    # end def t_VAR

    def t_error (self, t):
        print ("Illegal character '%s'" % t.value [0])
        t.lexer.skip (1)
    # end def t_error

    # END TOKEN DEFINITION

    def __init__ (self, **kw):
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

