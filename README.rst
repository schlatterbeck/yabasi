YABASI -- Yet another BASIC Interpreter
=======================================

This is a BASIC interpreter for an old dialect of the language used in
early IBM PCs. It is written in Python. I wrote this over a weekend to
be able to run old MININEC_ code. It has almost no error checking (it
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

.. _MININEC: https://github.com/Kees-PA3KJ/MiniNec
.. _pcbasic: https://robhagemans.github.io/pcbasic/
.. _pymininec: https://github.com/schlatterbeck/pymininec
