.. |--| unicode:: U+2013   .. en dash

Yabasi |--| Yet another BASIC Interpreter
=========================================

:Author: Ralf Schlatterbeck <rsc@runtux.com>

This is a BASIC interpreter for an old dialect of the language used in
early IBM PCs |--| and, in fact even earlier incarnations of BASIC that
existed on a UNIVAC (according to [1]_ the code there |--| which can be
run with Yabasi |--| ran on a UNIVAC).

It is written in Python. I wrote this over a weekend to
be able to run old MININEC_ code (the linked version of MININEC_
contains some small fixes). It has almost no error checking (it
relies on the code being correct not trying to aid you in writing a new
program in BASIC, I think the world does not need new code in BASIC). If
you're looking for a working BASIC interpreter, look at the pcbasic_
implementation, it is also in Python but faithfully reproduces the
memory limitations of the machines at the time. And it seems to use
single-precision floating point numbers. This is why I wrote my own
interpreter: I needed to compare computations in double precision and I
could not fit some examples into the limited memory of pcbasic_.

I'm probably not going to put much work into improving this code, it has
achieved the purpose: Running (and debugging in Python) old MININEC_
code to allow me to compare the computations in BASIC to my
re-implementation of MININEC_ in Python, pymininec_.

But in fact the code can now run more than the publicly available
version of MININEC_ and implements some of the basic binary file I/O
mechanisms of the time.

Changes
-------

Version 1.0: More fixes

This version has a lot of fixes that go beyond just running MININEC_, it
can now be used to read binary files (MININEC_ used a pre-processor
script to create a binary representation of an antenna geometry) and it
can run programs without a line number on every line.

- We no longer require line numbers on every line
- Handle multi-line ``IF``/``END IF``
- Dynamic ``DIM`` statements
- Binary File I/O with ``GET``/``PUT``, note that a file is opened for
  binary if a record length is specified, this probably should change at
  some time to just convert everything written to a file from python's
  string representation where necessary and open all files in binary
  mode. We use the default in Basic of opening a file read/write, so
  don't be surprised if a file opened for reading which doesn't exist is
  created with zero length.
- Conversion of int and float from/to strings |--| in python the strings
  are represented as bytes objects |--| these are the functions ``MKI$``,
  ``MKS$`` and fixes to ``CVI`` and ``CVS``
- Bug-fix when a ``GOSUB`` is not the last statement in a list of
  statements (e.g. in ``IF`` *expr* ``THEN`` *list-of-statements*), this
  did not execute the ``GOSUB`` previously

Version 0.3: Fix rules for printlist

The syntax of parameters to the ``PRINT`` statement can either use a
semicolon (or a comma) to separate expressions or just put the
expressions together without a separator. The latter had some quite
ad-hoc rules and I've removed many of them, the result removes a
reduce/reduce conflict...

Version 0.2: First working (released) version

.. [1] Alfredo J. Julian, James C. Logan, and John W. Rockway.
    Mininec: A mini-numerical electromagnetics code. Technical Report
    NOSC TD 516, Naval Ocean Systems Center (NOSC), San Diego,
    California, September 1982. Available as ADA121535_


.. _MININEC: https://github.com/schlatterbeck/MiniNec
.. _pcbasic: https://robhagemans.github.io/pcbasic/
.. _pymininec: https://github.com/schlatterbeck/pymininec
.. _ADA121535: https://apps.dtic.mil/sti/pdfs/ADA121535.pdf
