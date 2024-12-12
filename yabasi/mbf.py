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

import struct
import numpy as np

class MBF_Float:
    """ Microsoft Binary Format float representation
        We try to emulate the (truncating) multiplication of the ancient
        floating-point format.
        See https://en.wikipedia.org/wiki/Microsoft_Binary_Format
    """

    debug = True
    ubit = 1 << 23

    def __init__ (self, sign, exponent, mantissa):
        self.sign = sign
        self.exp  = exponent
        self.mnt  = mantissa
        assert -126 <= self.exp <= 127
    # end def __init__

    def __str__ (self):
        return 'MBF_Float (%d, %d, 0x%x)' % (self.sign, self.exp, self.mnt)
    # end def __str__
    __repr__ = __str__

    def __sub__ (self, other):
        if isinstance (other, (float, np.single, int)):
            other = MBF_Float.from_float (other)
        s = 1 if other.sign == 0 else 0
        return self.__add__ (MBF_Float (s, other.exp, other.mnt))
    # end def __sub__

    @classmethod
    def from_float (cls, f):
        """ Unpack a float into sign, exponent, mantissa
            This uses *single precision*
        >>> print (MBF_Float.from_float (16777215.0))
        MBF_Float (0, 23, 0xffffff)
        >>> print (MBF_Float.from_float (8.0))
        MBF_Float (0, 3, 0x800000)
        >>> print (MBF_Float.from_float (15.0))
        MBF_Float (0, 3, 0xf00000)
        >>> print (MBF_Float.from_float (225.0))
        MBF_Float (0, 7, 0xe10000)
        >>> print (MBF_Float.from_float (0.00007))
        MBF_Float (0, -14, 0x92ccf7)
        >>> print (MBF_Float.from_float (0.0))
        MBF_Float (0, 0, 0x0)
        >>> print (MBF_Float.from_float (-0.5))
        MBF_Float (1, -1, 0x800000)
        >>> print (MBF_Float.from_float (-9.658597e-21))
        MBF_Float (1, -67, 0xb6721c)
        """
        b = struct.pack ('<f', f)
        if b == b'\0\0\0\0' or b == b'\0\0\0\x80':
            return MBF_Float (0, 0, 0)
        sign = int (bool (b [-1] & 0x80))
        exp  = ((b [-1] & 0x7f) << 1) + ((b [-2] & 0x80) >> 7)
        assert exp not in (0, 255)
        exp  = exp - 127
        mnt  = b [0] + (b [1] << 8) + ((b [2] & 0x7f) << 16) + cls.ubit
        return MBF_Float (sign, exp, mnt)
    # end def from_float

    @property
    def _abs (self):
        return (self.exp, self.mnt)
    # end def _abs

    def add (self, other):
        """ Addition: In anticipation of a carry of the highest bit we
            shift by one bit before addition. This doesn't apply when the
            signs are different.
        >>> print ((MBF_Float.from_float (23) + 23).as_float ())
        46.0
        >>> a = MBF_Float (0, 23, 0xffffff)
        >>> print (a.as_float ())
        16777215.0
        >>> print ((a + 1).as_float ())
        16777215.0
        >>> print ((a + 2).as_float ())
        16777216.0
        >>> print ((a - 1).as_float ())
        16777214.0
        >>> print ((a - a).as_float ())
        0.0
        >>> print ((a + a).as_float ())
        33554428.0
        >>> print ((a - 1 - a).as_float ())
        -1.0
        >>> print (MBF_Float.from_float (9.186124e-09).as_float ())
        9.186124e-09
        >>> print ((MBF_Float.from_float (9.186124e-09) + 0.0).as_float ())
        9.186124e-09
        >>> print ((MBF_Float.from_float (0.0) + 9.186124e-09).as_float ())
        9.186124e-09
        >>> print ((MBF_Float.from_float (3.0) - 2.0).as_float ())
        1.0
        """
        if isinstance (other, (float, np.single, int, np.int64)):
            other = MBF_Float.from_float (other)
        if self.mnt == 0:
            return other
        if other.mnt == 0:
            return self
        exdif = abs (self.exp - other.exp)
        a, b  = (self, other) if self._abs > other._abs else (other, self)
        if exdif > 23 or a.sign == b.sign and exdif > 22:
            return a
        s  = a.sign
        bm = b.mnt >> exdif
        if a.sign == b.sign:
            am = a.mnt >> 1
            bm = bm >> 1
            ex = a.exp + 1
            mn = am + bm
        else:
            am = a.mnt
            mn = am - bm
            ex = a.exp
        if mn == 0:
            return MBF_Float (0, 0, 0)
        while (mn & self.ubit) == 0:
            mn <<= 1
            ex -= 1
        if ex < -126:
            return MBF_Float (0, 0, 0)
        if self.debug:
            a = self.as_float ()
            b = other.as_float ()
            v = a + b
            if abs (v - MBF_Float (s, ex, mn).as_float ()) / v >= 0.01:
                import pdb; pdb.set_trace ()
        return MBF_Float (s, ex, mn)
    # end def add
    __add__ = add

    def as_float (self):
        """ Pack sign, exponent, mantissa into IEEE 32-bit float
        >>> mbf = MBF_Float (0, 23, 0xffffff)
        >>> mbf.as_float ()
        16777215.0
        >>> mbf = MBF_Float (0, -3, 0xa00000)
        >>> mbf.as_float ()
        0.15625
        >>> mbf = MBF_Float (1, -3, 0xa00000)
        >>> mbf.as_float ()
        -0.15625
        >>> mbf = MBF_Float (0, 3, 0x800000)
        >>> mbf.as_float ()
        8.0
        >>> mbf = MBF_Float (0, 6, 0x800000)
        >>> mbf.as_float ()
        64.0
        >>> mbf = MBF_Float (0, 0, 0)
        >>> mbf.as_float ()
        0.0
        >>> mbf = MBF_Float (1, -67, 0xb6721c)
        >>> mbf.as_float ()
        -9.658597e-21
        """
        if self.mnt == 0:
            return np.single (0.0)
        assert self.mnt & self.ubit
        exp = self.exp + 127
        b = [0, 0, 0, 0]
        b [0] = self.mnt & 0xff
        b [1] = (self.mnt >>  8) & 0xff
        b [2] = ((self.mnt >> 16) & 0x7f) | ((exp & 1) << 7)
        b [3] = (exp >> 1) | ((self.sign << 7) & 0x80)
        return np.single (struct.unpack ('<f', bytes (b)) [0])
    # end def as_float

    def multiply (self, other):
        """ Multiply two MBF_Float numbers
        >>> a = MBF_Float.from_float (15.)
        >>> print (a.multiply (a).as_float ())
        225.0
        >>> b = MBF_Float.from_float (8.)
        >>> print (b.multiply (b).as_float ())
        64.0
        >>> print (a.multiply (b).as_float ())
        120.0
        >>> a = MBF_Float.from_float (0.00007)
        >>> print (a.multiply (b).as_float ())
        0.00055999996
        >>> print ((b * 0.00007).as_float ())
        0.00055999996
        >>> print (a.multiply (MBF_Float (0, 0, 0)).as_float ())
        0.0
        >>> c = MBF_Float (0, 23, 0xffffff)
        >>> print (c.multiply (c))
        MBF_Float (0, 47, 0xffffe7)
        >>> print (c.multiply (c).as_float ())
        281474560000000.0
        >>> v = 9.584426879882812e-05
        >>> print ((MBF_Float.from_float (v) * v).as_float ())
        9.186124e-09
        """
        if isinstance (other, (float, np.single, int, np.int64)):
            other = MBF_Float.from_float (other)
        if self.mnt == 0 or other.mnt == 0:
            return MBF_Float (0, 0, 0)
        s  = self.sign ^ other.sign
        assert s in (0, 1)
        ex = self.exp + other.exp + 1
        m1 = self.mnt
        r  = 0
        for b in bin (other.mnt)[2:]:
            m1 >>= 1
            if b == '1':
                r += m1
            if m1 == 0:
                break
        if r < self.ubit:
            ex -= 1
            r <<= 1
        if ex < -126:
            return MBF_Float (0, 0, 0)
        if self.debug:
            a = self.as_float ()
            b = other.as_float ()
            v = a * b
            if abs (v - MBF_Float (s, ex, r).as_float ()) / v >= 0.01:
                import pdb; pdb.set_trace ()
        return MBF_Float (s, ex, r)
    # end def multiply
    __mul__ = multiply

    def __truediv__ (self, other):
        """ Convenience method for division
        >>> print ((MBF_Float.from_float (9.0) / 3.0).as_float ())
        2.9999995
        """
        if isinstance (other, self.__class__):
            other = other.as_float ()
        other = 1 / other
        return self * other
    # end def __truediv__

# end class MBF_Float