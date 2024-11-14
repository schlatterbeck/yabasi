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

import inspect
from textwrap import dedent
from yabasi.bas import Interpreter, options, Interpreter_Test

class Test_Base:

    def run_test (self, expect = None, hook = None, opt = None):
        """ Determine caller, get docstring from caller and run
            interpreter with it. Optionally install test hook before
            doing this.
        """
        if opt is None:
            opt = ['']
        args   = options (opt)
        caller = getattr (self, inspect.stack () [1][3])
        prg    = dedent (caller.__doc__).split ('\n')
        t      = Interpreter_Test (prg, hook)
        bas    = Interpreter (args, t)
        bas.run ()
        if expect:
            assert expect == t.output.getvalue ()
    # end def run_test

    def test_while (self):
        """
            10 I=0
            20 WHILE I<5
            30 I=I+1
            40 PRINT I
            50 WEND
        """
        def hook (interpreter):
            # assert stack doesn't grow
            assert len (interpreter.stack.stack) <= 1
        # end def hook
        self.run_test (' 1\n 2\n 3\n 4\n 5\n', hook)
    # end def test_while

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

# end class Test_Base
