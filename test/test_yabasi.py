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

import re
import os
import sys
import inspect
from textwrap import dedent
from yabasi.bas import Interpreter, options, Interpreter_Test

class _Test_Common:

    default_opt = ['']
    regex = re.compile (r'%%For:(.|[\r\n])*%%CreationDate[^\n\r]*\n')

    def run_test (self, expect = None, hook = None, opt = None, capture = None):
        """ Determine caller, get docstring from caller and run
            interpreter with it. Optionally install test hook before
            doing this.
        """
        if opt is None:
            opt = self.default_opt
        args   = options (opt)
        caller = getattr (self, inspect.stack () [1][3])
        prg    = dedent (caller.__doc__).split ('\n')
        t      = self.itest = Interpreter_Test (prg, hook, capture = capture)
        bas    = Interpreter (args, t)
        bas.run ()
        if expect is not None:
            assert t.output.getvalue () == expect
        if capture is not None:
            for typ in ('txt', 'img'):
                attr   = 'cap_' + typ
                result = getattr (t, attr, None)
                if result:
                    if typ == 'img':
                        result = self.regex.sub ('', result)
                    name = caller.__name__.split ('_', 1) [1]
                    fn = os.path.join ('test', 'images', name) + '.' + typ
                    with open (fn) as f:
                        expect = f.read ()
                        with open (fn + '.result', 'w') as fw:
                            fw.write (result)
                        assert result == expect
                    break
            else:
                raise ValueError ('No captured output was found')
    # end def run_test

# end def _Test_Common


class Test_Base (_Test_Common):

    def stack_hook (self, interpreter):
        # assert interpeter and python stacks don't grow
        assert len (interpreter.stack.stack) <= 1
        h = self.itest.stack_height ()
        if self.pystack is None:
            self.pystack = h
        #print (h, self.pystack)
        assert h < self.pystack + 5
    # end def stack_hook

    # Tests start here

    def test_eof (self):
        """
            100 OPEN "/dev/null" FOR INPUT AS #1 LEN=100
            110 PRINT EOF(1)
            120 CLOSE 1
            130 OPEN "test/test_yabasi.py" FOR INPUT AS #1 LEN=20
            140 PRINT EOF(1)
            150 CLOSE 1
            200 OPEN "/dev/null" FOR INPUT AS #1
            210 PRINT EOF(1)
            220 CLOSE 1
        """
        self.run_test ('True\nFalse\nTrue\n')
    # end def test_eof

    def test_multigosub (self):
        """
            10  REM HUHU
            50  PRINT "HALLO"
            100 IF 1 THEN GOSUB 200 : GOSUB 300 : GOSUB 400 : GOTO 800 : PRINT 'notreached'
            110 PRINT "after gosubs, should not be reached"
            120 GOTO 500
            200 PRINT "In 200"
            210 RETURN
            300 PRINT "In 300"
            310 RETURN
            400 PRINT "In 400"
            410 RETURN
            500 GOSUB 200 : GOSUB 300 : GOSUB 400 : GOTO 900
            600 PRINT 'notreached'
            700 END
            800 IF 1 THEN GOSUB 200 : GOSUB 300 : GOSUB 400
            810 PRINT "AFTER second if"
            820 GOTO 500
            900 PRINT "After cmdlist"
            910 GOSUB 200 : GOSUB 300 : GOSUB 400
            920 PRINT "After 2nd cmdlist"
            930 GOTO 700
        """
        gsb = 'In 200\nIn 300\nIn 400\n'
        ret = ( 'HALLO\n' + gsb + gsb + 'AFTER second if\n' + gsb
              + 'After cmdlist\n' + gsb + 'After 2nd cmdlist\n'
              )
        self.run_test (ret)
    # end def test_multigosub

    def test_nested_loop (self):
        """
            100 A%=2
            110 WHILE A%<6 : A%=A%+1 : PRINT A% : FOR K=1 TO 2 : PRINT "K:";K : NEXT K : WEND : PRINT "HUHU"
            120 PRINT "END 1st loop"
            200 A%=3
                WHILE A%<6
                    A%=A%+1
                    PRINT A%
                    FOR K=1 TO 2
                        PRINT "K:";K
                    NEXT K
                WEND
                PRINT "THE END"
        """
        exp = []
        for k in range (3, 7):
            exp.append ('%d\nK:1\nK:2\n' % k)
        exp.append ('HUHU\nEND 1st loop\n')
        for k in range (4, 7):
            exp.append ('%d\nK:1\nK:2\n' % k)
        exp.append ('THE END\n')
        self.run_test (''.join (exp))
    # end def test_nested_loop

    def test_onerr (self):
        """
            100 ON ERROR GOTO 500
            120 OPEN "nonexisting" FOR INPUT AS #1
            130 CLOSE #1
            400 END
            500 PRINT "ERROR"
        """
        self.run_test ('ERROR\n')
    # end def test_onerr

    def test_onerr_resume (self):
        """
            10 ON ERROR GOTO 500
            20 ERRCOUNT=0
            30 NEXT X ' next without for, an error
            40 END
            500 ERRCOUNT = ERRCOUNT + 1
            505 PRINT ERRCOUNT
                ' These are equivalent and re-execute the offending statement
            510 IF ERRCOUNT < 2 THEN RESUME
            520 IF ERRCOUNT < 4 THEN RESUME 0
            530 RESUME NEXT
        """
        self.run_test (' 1\n 2\n 3\n 4\n')
    # end def test_onerr_resume

    def test_ongosub (self):
        """
            10 X%=1
            20 ON X% GOSUB 1000,2000
            30 PRINT "After gosub"
            40 GOTO 2000
            1000 PRINT "In gosub 1000"
            1010 GOSUB 3000
            1020 PRINT "After gosub 3000"
            1030 RETURN
            2000 END
            3000 PRINT "In gosub 3000"
            3010 ON X% GOSUB 4000,2000
            3020 PRINT "After gosub 4000"
            3030 RETURN
            4000 PRINT "In gosub 4000"
            4010 RETURN
        """
        ret  = 'In gosub 1000\nIn gosub 3000\nIn gosub 4000\n'
        ret += 'After gosub 4000\nAfter gosub 3000\nAfter gosub\n'
        self.run_test (ret)
    # end def test_ongosub

    def test_ongoto_ongosub_bounds (self):
        """
            10 X% = 0
            20 ON X% GOTO 100,500
            30 ON X% GOSUB 500,500
            40 X% = 3
            50 ON X% GOTO 100,500
            60 ON X% GOSUB 500,500
            70 PRINT "ByeBye"
            100 END
            500 PRINT "In gosub"
            510 RETURN
        """
        self.run_test ('ByeBye\n')
    # end def test_ongoto_ongosub_bounds

    def test_print_semic (self):
        """
            100 PRINT ;1;2
        """
        self.run_test ('12\n')
    # end def test_print_semic

    def test_skip_next (self):
        """
            1 FOR I=1 TO 2
            2 PRINT I
            3 NEXT I
            5 FOR I=20 TO 19
            6 PRINT I
            7 REM NEXT ZOPPEL
            8 GOTO 50
            9 NEXT I
            10 PRINT CHR$(65)
            40 END
            50 NEXT J
            60 END
        """
        self.run_test ('1\n2\nA\n')
    # end def test_skip_next

    def test_str (self):
        """
            10 DEF FNLSD$(S$)=RIGHT$(S$,LEN(S$)-SGN(SGN(VAL(S$))+1))
            20 PRINT (FNLSD$("10"))
            30 FOR I=-10 TO 10 STEP 10
            40 PRINT "STR:>";STR$(I);"<";
            50 PRINT "LSD>";FNLSD$(STR$(I));"<"
            60 NEXT I
            100 K%=10
            110 PRINT ">";STR$(K%);"<"
            500 END
        """
        r  = '0\nSTR:>-10<LSD>-10<\nSTR:> 0<LSD>0<\nSTR:> 10<LSD>10<\n> 10<\n'
        self.run_test (r)
    # end def test_str

    def test_while (self):
        """
            10 I=0
            20 WHILE I<5
            30 I=I+1
            40 PRINT I
            50 WEND
        """
        self.pystack = None
        self.run_test (' 1\n 2\n 3\n 4\n 5\n', self.stack_hook)
    # end def test_while

    def test_while_single_line (self):
        """
            10 I=0
            20 WHILE I<5: I=I+1: PRINT I: WEND
        """
        self.pystack = None
        self.run_test (' 1\n 2\n 3\n 4\n 5\n', self.stack_hook)
    # end def test_while_single_line

# end class Test_Base

class Test_Graphics (_Test_Common):

    default_opt = ['-S', 'tkinter', '']

    def test_canvas_arc (self):
        """
            10 SCREEN 2,0,0,0
            15 WINDOW (-1, -1)-(1, 1)
            20 CIRCLE (0, 0), .5,,0,3.1415/2
            20000 END
        """
        self.run_test ('', capture = True)
    # end def test_canvas_arc

    def test_canvas_dot (self):
        """
            5 DIM PIC% (8)
            10 SCREEN 2,0,0,0
            15 WINDOW
            30 LINE (1, 1) - (1, 1),,B
            35 GET (0, 0)-(8,8), PIC%
            40 LINE (160,  50) - (160,  50),,B
            50 LINE (320, 100) - (320, 100),,B
            60 LINE (640, 200) - (640, 200),,B
            65 LOCATE 10,10
            70 FOR I=1 TO 8: PRINT PIC%(I);' ': NEXT I
        """
        # HMPF: In this case the dots are not visible in the postscript
        # but they *are* visible in the tkinter canvas. So the canvas
        # postscript export does not export the real thing.
        # We see this when the result is read back from the window with
        # the GET command: It should return all zeros according the
        # postscript version.
        # This is also something to look out for should we ever devise a
        # different method for accessing the canvas pixels.
        self.run_test ('', capture = True)
    # end def test_canvas_dot

    def test_canvas_get (self):
        """
            10 DATA 8,8,16956,15938,16898,60,0,0,0
            20 DIM A9% (8)
            25 DIM B9% (8)
            30 FOR I=0 TO 8: READ A9%(I):NEXT I
            40 '
            50 SCREEN 2,0,0,0
            60 WINDOW
            70 PUT (0, 0), A9%
            80 PUT (0, 200 - 8), A9%
            100 GET (0, 0)-(8, 8),B9%
            150 SCREEN 0,0,0,0
            160 FOR I=0 TO 8: PRINT A9%(I);" ";B9%(I);"," : NEXT I
        """
        self.run_test ('', capture = True)
    # end def test_canvas_get

    def test_canvas_line (self):
        """
            10 SCREEN 2,0,0,0
            15 WINDOW
            20 WINDOW (0, 0)-(1, 1)
            30 LINE (0, 0) - (0.5, 0.5)
        """
        self.run_test ('', capture = True)
    # end def test_canvas_line

    def test_canvas_put (self):
        """
            10 DATA 8,8,16956,15938,16898,60,0,0,0
            20 DIM A9% (8)
            25 DIM B9% (8)
            30 FOR I=0 TO 8: READ A9%(I):NEXT I
            40 '
            50 SCREEN 2,0,0,0
            60 WINDOW
            70 PUT (0, 0), A9%
            80 PUT (0, 200 - 8), A9%
        """
        self.run_test ('', capture = True)
    # end def test_canvas_put

    def test_canvas_text (self):
        """
            10 SCREEN 2,0,0,0
            15 WINDOW
            20 LOCATE 0,0
            30 PRINT "X"
            20 LOCATE 1,1
            30 PRINT "X"
        """
        self.run_test ('', capture = True)
    # end def test_canvas_text

# end class Test_Graphics
