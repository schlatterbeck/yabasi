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

from ply import yacc
from argparse import ArgumentParser
from io import StringIO
from PIL import Image, ImageTk, ImageGrab
from math import prod
import itertools
import tkinter
import numpy as np
import sys
import os
import datetime
import struct
import copy
import logging
import time
from . import tokenizer

logging.basicConfig \
    ( level    = logging.DEBUG
    , filename = 'parselog.txt'
    , filemode = 'w'
    , format   = '%(filename)10s: %(lineno)5d: %(message)s'
    )
log = logging.getLogger ()

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

def fun_fix (expr):
    return np.trunc (expr)
# end def fun_fix

def fun_fractional_part (expr):
    """ This is used in the first Mininec implementation, probably
        something that the UNIVAC BASIC at the time provided.
        I could not find it in any BASIC function references.
    """
    return expr - int (expr)
# end def fun_fractional_part

def fun_instr (offset, parent, child):
    # Deal with the fact that the *last* element is optional in the
    # grammar rule -- in fact the offset is optional
    if child is None:
        child  = parent
        parent = offset
        offset = None
    if offset is not None:
        offset = int (offset) - 1
    else:
        offset = 0
    return parent.find (child, offset) + 1
# end def fun_instr

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

def fun_space (expr):
    return ' ' * int (expr)
# end def fun_space

def fun_str (expr):
    if isinstance (expr, (float, int)):
        return format_float (expr).rstrip ()
    return str (expr)
# end def fun_str

def fun_string (count, s):
    return chr (s) * int (count)
# end def fun_string

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

class Screen:
    """ Default screen emulation doing essentially nothing
    """

    def __init__ (self, parent, ofile = None):
        self.parent = parent
        self.ofile  = ofile or sys.stdout
    # end def __init__

    # Commands

    def cmd_circle (self, x, y, r, opt):
        pass
    # end def cmd_circle

    def cmd_cls (self, screen = None):
        """ Clear screen """
        pass
    # end def cmd_cls

    def cmd_color (self, exprlist):
        pass
    # end def cmd_color

    def cmd_get_graphics (self, var, e1, e2, e3, e4):
        return 0
    # end def cmd_get_graphics

    def cmd_input (self, prompt):
        return input (prompt)
    # end def cmd_input

    def cmd_key (self, expr1, expr2):
        """ Since we cannot get function key input do nothing
        """
        pass
    # end def cmd_key

    def cmd_line (self, x0, y0, x1, y1, lineopt):
        pass
    # end def cmd_line

    def cmd_locate (self, row, col, ignore = None):
        """ Positions cursor, we just go to start of line """
        print ('\r', end = '')
    # end def cmd_locate

    def cmd_print (self, s, end = None):
        print (s, end = end, file = self.ofile)
    # end def cmd_print

    def cmd_pset (self, x, y):
        pass
    # end def cmd_pset

    def cmd_put_graphics (self, x, y, array, option = None):
        pass
    # end def cmd_put_graphics

    def cmd_screen (self, e1, e2, e3, e4):
        pass
    # end def cmd_screen

    def cmd_width (self, ncols, nrows = None):
        if int (ncols ()) != 80:
            raise NotImplementedError ('Screen width != 80 unsupported')
    # end def cmd_width

    def cmd_window (self, x0, y0, x1, y1, is_screen = False):
        pass
    # end def cmd_window

    # Functions

    def fun_csrlin (self):
        """ Current row of cursor """
        return 0
    # end def fun_csrlin

    def fun_inkey (self):
        """ In the programs we support with the simple screen, INKEY$ is
            used for clearing the input buffer, no need to do this with,
            e.g., cooked terminal mode on Linux. So we always return an
            empty string.
        """
        return ''
    # end def fun_inkey

# end class Screen

class Screen_Tkinter (Screen):
    """ A tkinter based screen emulation
    """

    #   mode width height scale-x scale-y
    screen_mode = dict \
        (( (1,  (320,   200,      1,      1))
         , (2,  (640,   200,      1,      2))
        ))
    # There are more foreground colors supported than this and the
    # colors are probably not correct.
    text_colors = dict \
        (( ( 0, 'black')
         , ( 1, 'blue')
         , ( 2, 'green')
         , ( 3, 'cyan')
         , ( 4, 'red')
         , ( 5, 'magenta')
         , ( 6, 'orange')
         , ( 7, 'grey')
         , (15, 'white')
        ))

    def __init__ (self, parent, ofile = None):
        self.parent    = parent
        self.ofile     = ofile
        self.scr_mode  = 0
        self.win_root  = tkinter.Tk ()
        self.rows      = 25
        self.cols      = 80
        self.cur_row   = 0
        self.cur_col   = 0
        self.text_bg   = 'white'
        self.text_fg   = 'black'
        self.canvas    = None
        self.g_xmul    = 1.0
        self.g_ymul    = 1.0
        self.g_xoff    = 0.0
        self.g_yoff    = 0.0
        self.g_x       = 0.0
        self.g_y       = 0.0
        self.g_images  = []
        self.win_label = tkinter.Label (self.win_root)
        self.win_label.pack ()

        self.win_text = tkinter.Text (self.win_label, font = 'TkFixedFont')
        self.win_text.configure (width  = self.cols)
        self.win_text.configure (height = self.rows)
        self.win_text.configure (state = 'disabled')
        self.clear_text_screen ()
        self.win_text.pack ()
        self.win_root.update ()
        self.keys   = []
        self.funkey = ['', '', '', '', '', '', '', '', '', '']
        self.win_root.bind ("<Key>", self.keyhandler)
    # end def __init__

    def clear_graphics_screen (self):
        if self.canvas:
            self.canvas.delete ('all')
            self.win_root.update ()
        self.g_images = []
        self.cur_row = self.cur_col = 0
        self.win_root.update ()
    # end def clear_graphics_screen

    def clear_text_screen (self):
        self.win_text.configure (state = 'normal')
        self.win_text.delete ('1.0', 'end')
        self.win_text.insert ('end', ' ' * (self.rows * self.cols))
        self.win_text.tag_add ('0', '1.0', '1.%d' % (self.rows * self.cols))
        self.win_text.tag_config \
            ('0', background = self.text_bg, foreground = self.text_fg)
        self.win_text.configure (state = 'disabled')
        self.cur_row = self.cur_col = 0
        self.win_root.update ()
    # end def clear_text_screen

    def get_bufpos (self):
        return self.cur_row * self.cols + self.cur_col
    # end def get_bufpos

    def get_canvas_rectangle (self, x0, y0, x1, y1):
        """ This is a hack: It screen-grabs the rectangle. So if the
            canvas is obscured by another window this will yield very
            interesting special effects.
            There seems to be only a postscript export of the tkinter
            canvas (and this exports the whole thing, meaning it's slow:
            It *does* have a view area (x, y, width, height) but still
            needs to render the whole thing and then extract the area)
            This relies on the canvas having a border of 1, otherwise we
            would need to take it into account
            This returns a boolean numpy array.
        """
        # Not sure if we can somehow find out the width of the canvas border
        xw = self.win_root.winfo_rootx () + self.canvas.winfo_x () + 1
        yw = self.win_root.winfo_rooty () + self.canvas.winfo_y () + 1
        img = ImageGrab.grab (bbox = (xw + x0, yw + y0, xw + x1, yw + y1))
        img = np.array (img.convert ('L')) < 128
        return img
    # end def get_canvas_rectangle

    def init_canvas (self):
        if not self.canvas:
            self.canvas = tkinter.Canvas \
                (self.win_root, width = self.g_width, height = self.g_height)
        self.canvas.pack ()
        self.win_root.update ()
        self.clear_graphics_screen ()
    # end def init_canvas

    def keyhandler (self, event):
        self.keys.append ((event.char, event.keysym))
    # end def keyhandler

    def screen_coords (self, point):
        g_mul = np.array ([self.g_xmul, self.g_ymul])
        g_off = np.array ([self.g_xoff, self.g_yoff])
        return (point * g_mul + g_off).astype (int)
    # end def screen_coords

    # Commands called from outside

    def cmd_circle (self, x, y, r, options):
        x, y, r = (z () for z in (x, y, r))
        n = ['color', 'start', 'end', 'aspect']
        class opt:
            color = start = end = aspect = None
        for name, v in zip (n, options):
            if v is not None:
                setattr (opt, name, v ())
        lh, lo = self.screen_coords (np.array ([x - r, y - r]))
        rh, hi = self.screen_coords (np.array ([x + r, y + r]))
        if opt.start is not None and opt.end is not None:
            start = opt.start / np.pi * 180
            ext   = opt.end / np.pi * 180 - start
            self.canvas.create_arc \
                (lh, hi, rh, lo, start = start, extent = ext, style = 'arc')
        else:
            self.canvas.create_oval (lh, hi, rh, lo)
        self.win_root.update ()
    # end def cmd_circle

    def cmd_cls (self, screen = None):
        """ Clear screen """
        if screen is None:
            if self.scr_mode == 0:
                self.clear_text_screen ()
            else:
                self.clear_graphics_screen ()
        if screen == 0 or screen == 2:
            self.clear_text_screen ()
        if screen == 0 or screen == 1:
            self.clear_graphics_screen ()
    # end def cmd_cls

    def cmd_color (self, exprlist):
        """ Currently only support colors in text mode
            We ignore the third argument (border) if given.
            This would need changes if we allow empty parameters
            (i.e. a comma without an expression before the comma)
        """
        fg = bg = border = None
        params = exprlist ()
        fg = self.text_colors [params [0]]
        if len (params) > 1:
            bg = self.text_colors [params [1]]
        if self.parent.args.enable_text_color and self.scr_mode == 0:
            if fg is not None:
                self.text_fg = fg
            if bg is not None:
                self.text_bg = bg
    # end def cmd_color

    def cmd_get_graphics (self, var, x0, y0, x1, y1):
        """ This currently works only for the graphics mode 2
            with 1 bit per pixel
            Since the result can be ambiguous (the two lines in the
            canvas representing one Basic line may not have the same
            content) we or the K rows/cols representing one Basic line.
        """
        if not self.canvas:
            return
        x0, y0, x1, y1 = (int (x ()) for x in (x0, y0, x1, y1))
        sm = self.screen_mode [self.scr_mode]
        f_x, f_y = sm [2:]
        cx0, cx1 = np.array ([x0, x1]) * f_x
        cy0, cy1 = np.array ([y0, y1]) * f_y
        img = self.get_canvas_rectangle (cx0, cy0, cx1, cy1)
        # Reduce to correct dimension and convert back to bool
        if f_x > 1 or f_y > 1:
            s_y, s_x = img.shape
            shp = (s_y // f_y, f_y, s_x // f_x, f_x)
            img = img.reshape (shp).sum (3).sum (1) > 0
        b   = np.packbits (img).flatten ()
        if prod (b.shape) & 1:
            b = np.append (b, (0,))
        itr = iter (b)
        self.parent.dim [var][0] = x1 - x0
        self.parent.dim [var][1] = y1 - y0
        for n, (b1, b2) in enumerate (zip (itr, itr)):
            self.parent.dim [var][n + 2] = b1 | (b2 << 8)
    # end def cmd_get_graphics

    def cmd_input (self, prompt):
        self.cmd_print (prompt, end = '')
        buf = []
        while True:
            c = self.fun_inkey ()
            if not c:
                time.sleep (.1)
                continue
            if c == '\x08':
                del buf [-1]
                self.cur_col -= 1
                self.cmd_print (' ', end = '')
                self.cur_col -= 1
                continue
            if c == '\n' or c == '\r':
                self.cmd_print ('\n', end = '')
                return ''.join (buf)
            self.cmd_print (c, end = '')
            buf.append (c)
    # end def cmd_input

    def cmd_key (self, expr1, expr2):
        """ Set macro for function key given with first expression
        """
        n = int (expr1 ())
        if 1 <= n <= 10:
            self.funkey [n - 1] = str (expr2 ())
    # end def cmd_key

    def cmd_line (self, x0, y0, x1, y1, lineopt):
        if not self.canvas:
            return
        pt = np.array ([x () if x else None for x in (x0, y0, x1, y1)])
        x1 = pt [-2]
        y1 = pt [-1]
        if pt [0] is None:
            pt [0] = self.g_x
            assert pt [1] is None
            pt [1] = self.g_y
        pt1, pt2 = pt.reshape ((2, 2))
        pt1 = self.screen_coords (pt1)
        pt2 = self.screen_coords (pt2)
        self.g_x = x1
        self.g_y = y1

        if 'B' not in lineopt:
            self.canvas.create_line (*pt1, *pt2)
        else:
            d = {}
            if 'F' in lineopt:
                d.update (fill = 'black')
            self.canvas.create_rectangle (*pt1, *pt2, **d)
        self.win_root.update ()
    # end def cmd_line

    def cmd_locate (self, row = None, col = None, exprlist = None):
        """ Positions cursor """
        if row is not None:
            self.cur_row = int (row ()) - 1
        if col is not None:
            self.cur_col = int (col ()) - 1
    # end def cmd_locate

    def cmd_print (self, s, end = None):
        """ tk row is 1-based, col is 0-based
            Basic row/col is 1-based
            we compute an index into our buffer
        """
        if self.ofile is not None:
            self.ofile.print (s, end = end, file = ofile)
            return
        if self.scr_mode == 0:
            self.cmd_print_text (s, end = end)
        else:
            self.cmd_print_canvas (s, end = end)
    # end def cmd_print

    def cmd_print_canvas (self, s, end = None):
        """ We generally asume non-multiline strings and no text-wrapping
        """
        font = ("Mx437 IBM CGA-2y", 12, "normal")
        scrmode = self.screen_mode [self.scr_mode]
        x = self.cur_col * 8 * scrmode [2] + 1 # scale_x
        y = self.cur_row * 8 * scrmode [3] + 1 # scale_y
        self.canvas.create_text (x, y, text = s, font = font, anchor = 'nw')
        self.cur_col += len (s)
        self.win_root.update ()
    # end def cmd_print_canvas

    def cmd_print_text (self, s, end = None):
        if end is None:
            end = '\n'
        s = s + end
        s = s.encode ('latin1').decode ('cp850')
        s = s.split ('\n')
        e = []
        for k in range (len (s) - 1):
            e.append ('\n')
        e.append (' ')
        for n in range (len (s)):
            v = s [n].split ('\r')
            s [n] = v
            e [n] = '\r' * (len (v) - 1) + e [n]
        e = ''.join (e)

        tlen = self.rows * self.cols
        for n, (p, end) in enumerate (zip (itertools.chain (*s), e)):
            pos  = self.get_bufpos ()
            l    = len (p)
            dl   = pos + l
            wpos = '1.%d' % pos
            epos = '1.%d' % (pos + l)
            self.win_text.configure (state = 'normal')
            self.win_text.delete (wpos, epos)
            self.win_text.insert (wpos, p)
            tn = 'tag_%d' % pos
            self.win_text.tag_add (tn, wpos, epos)
            self.win_text.tag_config \
                (tn, foreground = self.text_fg, background = self.text_bg)
            # compute new cursor position
            # last item does *not* have a newline
            if end == '\r':
                self.cur_col = 0
                self.cur_row = dl // self.cols
            elif end == '\n':
                self.cur_col = 0
                self.cur_row = dl // self.cols + 1
            else:
                self.cur_col = dl % self.cols
                self.cur_row = dl // self.cols
            if self.cur_row > self.rows - 1:
                # Fill to eol
                eol = self.cols - (dl % self.cols)
                self.win_text.insert ('end', ' ' * eol)
                # delete first lines(s)
                ndel = (self.cur_row - self.rows + 1) * self.cols
                assert ndel > 0
                self.win_text.delete ('1.0', '1.%d' % ndel)
                self.cur_row = self.rows - 1
            self.win_text.configure (state = 'disabled')
            self.win_root.update ()
    # end def cmd_print_text

    def cmd_pset (self, x, y):
        """ Only the variant without attribute is implemented.
            Has the effect of changing the current graphics position.
        """
        self.g_x = x ()
        self.g_y = y ()
    # end def cmd_pset

    def cmd_put_graphics (self, x, y, var, method = None):
        """ For now this only works with 1 bit per pixel
        """
        if not self.canvas:
            return
        x, y = (int (z ()) for z in (x, y))
        sm  = self.screen_mode [self.scr_mode]
        f_x = sm [2]
        f_y = sm [3]
        # Canvas seems to start at 1 not 0 at least it drops first row/col
        # if we put it at (0,0). This seems to be a bug of the
        # create_image method. The read-back of get_canvas_rectangle is
        # not affected (and starts with 0)
        # Basic seems to start at 0, at least for -1 pcbasic reports an
        # "Illegal function call".
        cx  = x * f_x + 1
        cy  = y * f_y + 1
        nx  = self.parent.dim [var][0]
        ny  = self.parent.dim [var][1]
        nxu = (nx + 7) // 8 * 8
        shp = (nxu, ny)
        b   = [[w & 0xFF, (w >> 8) & 0xff] for w in self.parent.dim [var][2:]]
        b   = np.array (b, dtype = np.uint8).flatten () [:prod (shp) // 8]
        bit = np.reshape (np.unpackbits (b), shp) < 1
        bit = np.repeat (bit,   f_y, axis = 0)
        bit = np.repeat (bit.T, f_x, axis = 0).T
        if method is None:
            method = 'XOR'
        if method not in ('PSET', 'PRESET'):
            sbit = self.get_canvas_rectangle \
                (cx - 1, cy - 1, cx + nx * f_x - 1, cy + ny * f_y - 1)
            if method == 'XOR':
                bit ^= sbit
            elif method == 'OR':
                bit |= sbit
            elif method == 'AND':
                bit &= sbit
        if method == 'PRESET':
            bit = np.logical_not (bit)
        img = ImageTk.PhotoImage (image = Image.fromarray (bit))
        self.canvas.create_image (cx, cy, anchor = 'nw', image = img)
        # Prevent images to be garbage-collected, tk doesn't keep a ref
        self.g_images.append (img)
        self.win_root.update ()
    # end def cmd_put_graphics

    def cmd_screen (self, e1, e2, e3, e4):
        mode = int (e1 ())
        if mode == 0:
            self.scr_mode = mode
            if self.canvas:
                self.canvas.forget ()
            self.win_label.pack ()
            self.win_root.update ()
            return
        if mode not in self.screen_mode:
            self.parent.raise_error ('Unsupported video mode: %s' % mode)
        self.win_label.forget ()
        self.scr_mode = mode
        sm = self.screen_mode [self.scr_mode]
        self.g_width  = sm [0] * sm [2]
        self.g_height = sm [1] * sm [3]
        self.g_xmul   = sm [2]
        self.g_xoff   = 0
        self.g_ymul   = sm [3]
        self.g_yoff   = 0
        self.init_canvas ()
        self.win_root.update ()
    # end def cmd_screen

    def cmd_width (self, ncols, nrows = None):
        changed = False
        cols = int (ncols ())
        if cols != self.cols:
            self.cols = cols
            self.win_text.configure (state = 'normal')
            self.win_text.configure (width = self.cols)
            changed = True
        if nrows:
            rows = int (nrows ())
            if rows != self.rows:
                self.rows = rows
                self.win_text.configure (state = 'normal')
                self.win_text.configure (height = self.rows)
                changed = True
        if changed:
            self.clear_text_screen ()
        self.win_root.update ()
    # end def cmd_width

    def cmd_window (self, x0, y0, x1, y1, is_screen = False):
        if x0 is not None:
            assert y0 is not None and x1 is not None and y1 is not None
            x0, y0, x1, y1 = (x () for x in (x0, y0, x1, y1))
            self.g_xmul = (1 - self.g_width) / (x0 - x1)
            self.g_xoff = (x0 * self.g_width - x1 * 1) / (x0 - x1)
            ydif = self.g_height - 1
            if is_screen:
                ydif = -ydif
            self.g_ymul = ydif / (y0 - y1)
            self.g_yoff =     (y0 * 1 - y1 * self.g_height) / (y0 - y1)
            if is_screen:
                self.g_yoff = (y0 * self.g_height - y1 * 1) / (y0 - y1)
        else:
            sm = self.screen_mode [self.scr_mode]
            self.g_xmul   = sm [2]
            self.g_xoff   = 0
            self.g_ymul   = sm [3]
            self.g_yoff   = 0
    # end def cmd_window

    # Functions called from outside

    def fun_csrlin (self):
        """ Current row of cursor """
        return self.cur_row + 1
    # end def fun_csrlin

    def fun_inkey (self):
        self.win_root.update ()
        if self.keys:
            v = self.keys.pop (0)
            if len (v [0]) == 0:
                if v [1].startswith ('F'):
                    n = int (v [1][1:])
                    if n - 1 < len (self.funkey):
                        return self.funkey [n - 1]
            else:
                return v [0]
        return ''
    # end def fun_inkey

# end class Screen_Tkinter

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

class Stack_Entry:
    """ We stack FOR/NEXT and IF/ELSE
        While a condition is False we just skip commands but we still
        *do* pick up FOR loops and multi-line IF/ELSE
    """

    def __init__ (self, parent, condition):
        self.parent        = parent
        self.condition     = condition
        self.stack         = None
        self.need_continue = False
    # end def __init__

    def continue_context (self):
        if self.start.cmdidx:
            self.need_continue = True
        else:
            self.start.restore_context ()
    # end def continue_context

    def exec (self):
        self.need_continue = False
        self.parent.exec_cmdlist (self.start.cmdlist, self.start.cmdidx)
    # end def exec

    def set_start (self):
        if self.parent.context:
            self.start = copy.copy (self.parent.context)
            self.start.cmdidx += 1
        else:
            self.start = Context (self.parent)
    # end def set_start

# end class Stack_Entry

class Stack_Entry_For (Stack_Entry):

    def __init__ (self, parent, condition, var, frm, to, step):
        super ().__init__ (parent, condition)
        self.var   = var
        self.frm   = frm
        self.count = frm
        self.to    = to
        self.step  = step
        self.set_start ()
    # end def __init__

    def handle_next (self):
        assert self.parent.stack.top == self
        self.count += self.step
        self.parent.var [self.var] = self.count
        if  (  self.step > 0 and self.count <= self.to
            or self.step < 0 and self.count >= self.to
            ):
            self.continue_context ()
        else:
            self.parent.stack.pop ()
    # end def handle_next

# end class Stack_Entry_For

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

class Stack_Entry_While (Stack_Entry):

    def __init__ (self, parent, condition, expr):
        super ().__init__ (parent, condition)
        self.expr  = expr
        self.set_start ()
    # end def __init__

    def handle_wend (self):
        assert self.parent.stack.top == self
        if self.condition and self.expr ():
            self.continue_context ()
        else:
            self.parent.stack.pop ()
    # end def handle_wend

# end class Stack_Entry_While

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
    if ' ' in x and x.startswith ('#'):
        r = int (x [1:])
        return '#%d' % r
    return x
# end def to_fhandle

class Basic_File:

    def __init__ (self, name, mode = None, reclen = None, binary = False):
        self.name        = name
        self.reclen      = reclen
        self.binary      = binary
        self.mode        = mode
        self.fields      = None
        self.cached_line = None
        self.binmode     = ''
        if self.binary:
            self.binmode = 'b'
        if name == 'SCRN:':
            self.f = sys.stdout
        elif name:
            if mode is None:
                for m in ('r+', 'w'):
                    self.mode = m + self.binmode
                    try:
                        self.f = open (name, self.mode)
                        break
                    except FileNotFoundError:
                        pass
            else:
                self.mode = self.mode + self.binmode
                self.f = open (name, self.mode)
        else:
            self.f = None
    # end def __init__

    def close (self):
        if self.f and self.f != sys.stdout:
            self.f.close ()
    # end def close

    def eof (self):
        if self.binary:
            pos  = self.f.tell ()
            npos = self.f.seek (1, 1)
            if npos == pos:
                return True
            else:
                assert npos - pos == 1
                npos = self.f.seek (-1, 1)
                assert npos == pos
                return False
        else:
            self.cached_line = self.f.readline ()
            if not self.cached_line:
                return True
            return False
    # end def eof

    def readline (self):
        if self.cached_line:
            r = self.cached_line
            self.cached_line = None
            return r
        return self.f.readline ()
    # end def readline

# end class Basic_File

class Interpreter_Test:
    """ This is used for testing: redirecting output, optionally
        redirecting input and passing the program as an iterable.
    """

    def __init__ (self, program, hook = None, input = None):
        self.program = program
        self.hook    = hook
        self.input   = input
        self.output  = StringIO ()
    # end def __init__

    def stack_height (self):
        height = 2
        frame  = sys._getframe (height)
        for height in itertools.count (height):
            frame = frame.f_back
            if not frame:
                return height
    # end def stack_height

# end class Interpreter_Test

class Interpreter:
    print_special = \
        { ',' : ('++,++', 'COMMA')
        , ';' : ('++;++', 'SEMIC')
        }
    special_by_code = dict \
        ((c [0], c [1]) for c in print_special.values ())
    tabpos = [14, 28, 42, 56]

    debug = False

    skip_mode_commands = set \
        (('if_start', 'else', 'endif', 'for', 'next', 'while', 'wend'))

    def __init__ (self, args, test = None):
        self.args   = args
        self.test   = test
        self.input  = None
        self.tab    = args.tab
        if not self.tab:
            self.tab = self.tabpos
        if test is not None and test.input is not None:
            self.input = test.input
        elif args.input_file:
            self.input = open (args.input_file, 'r')
        self.col       = 0
        self.lines     = {}
        self.stack     = Exec_Stack ()
        self.gstack    = [] # gosub
        self.context   = None
        self.files     = {}
        self.data      = []
        self.defint    = {}
        self.err_seen  = False
        # Variables and dimensioned variables do not occupy the same namespace
        self.var       = {}
        self.dim       = {}
        self.flines    = {}
        self.onerr     = None
        self.resume    = None
        self.resume_on = None
        self.var ['DATE$'] = str (datetime.date.today ())
        self.var ['TIME$'] = datetime.datetime.now ().strftime ('%H:%M:%S')

        self.tokenizer = tokenizer.Tokenizer ()
        self.tokens    = tokenizer.Tokenizer.tokens
        self.parser    = yacc.yacc (module = self, debug = True)
        self.data_ptr  = 0
        self.functions = {}
        self.log       = None
        # Only for debugging
        if self.debug:
            self.log = log
        self.ofile = None
        if test is not None:
            self.ofile = test.output
        elif args.output_file:
            self.ofile = open (args.output_file, 'w')
        if self.args.screen == 'tkinter':
            self.screen = Screen_Tkinter (self, self.ofile)
        else:
            self.screen = Screen (self, self.ofile)

        if test is not None:
            self.compile (test.program)
        else:
            with open (args.program, 'r') as f:
                self.compile (f)
        self.break_lineno = None
    # end def __init__

    def __getattr__ (self, name):
        if name.startswith ('cmd_') or name.startswith ('fun_'):
            return getattr (self.screen, name)
        raise AttributeError (name)
    # end def __getattr__

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

    def close_output (self):
        if self.ofile and not self.test:
            self.ofile.close ()
            self.ofile = None
    # end def close_output

    def compile (self, f):
        lineno = self.lineno = sublineno = 0
        for fline, l in enumerate (f):
            l = l.rstrip ()
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
            if not l or r.lstrip ().startswith ("'"):
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
            r = self.parser.parse (lexer = self.tokenizer, debug = self.log)
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
    # end def compile

    def exec_cmdlist (self, cmdlist, idx):
        for i in range (idx, len (cmdlist)):
            cmd = cmdlist [i]
            self.context = Context (self, cmdlist, i)
            cmd [0] (*cmd [1:])
            if self.test and self.test.hook:
                self.test.hook (self)
            # Handle cmdlist continue at top level to avoid stack growth
            if self.stack and self.stack.top.need_continue:
                return
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
        if self.onerr:
            self.next      = self.onerr
            self.resume_on = self.onerr
            self.resume    = (self.lineno, self.sublineno)
            self.onerr     = None
        else:
            self.err_seen = True
        self.context  = None
    # end def raise_error

    def run (self):
        if self.err_seen:
            self.close_output ()
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
            if self.test and self.test.hook:
                self.test.hook (self)
            self.next = self.nextline.get (l)
            line = self.lines [l]
            if line is None:
                self.raise_error ('Uncompiled line')
                self.close_output ()
                return
            name = line [0].__name__.split ('_', 1) [-1]
            if self.exec_condition or name in self.skip_mode_commands:
                try:
                    line [0] (*line [1:])
                except ex as err:
                    self.raise_error (repr (err))
            while self.stack and self.stack.top.need_continue:
                self.stack.top.exec ()
            l = self.next
            if l:
                self.lineno, self.sublineno = l
        self.close_output ()
    # end def run

    # FUNCTIONS which need access to interpreter

    def fun_eof (self, number):
        fhandle = to_fhandle (number)
        return self.files [fhandle].eof ()
    # end def fun_eof

    def fun_fn (self, fname, exprlist):
        """ Temporarily bind function args to values from exprlist then
            call the function, then restore args.
        """
        varlist, expr = self.functions [fname]
        oldval = {}
        for ex, vname in zip (exprlist (), varlist):
            if vname in self.var:
                oldval [vname] = self.var [vname]
            self.var [vname] = ex
        retval = expr ()
        for vname in varlist:
            if vname in oldval:
                self.var [vname] = oldval [vname]
            else:
                del self.var [vname]
        return retval
    # end def fun_fn

    # COMMANDS

    def cmd_assign (self, lhs, expr):
        if callable (expr):
            result = expr ()
        else:
            result = expr
        lhs ().set (result)
    # end def cmd_assign

    def cmd_call (self, var):
        self.raise_error ('CALL not implemented')
    # end def cmd_call

    def cmd_close (self, fhandle = None):
        """ Seems a missing file handle closes all files
            We interpret a missing '#' as the same file as with '#'
        """
        if fhandle is None:
            for fh in self.files:
                self.files [fh].close ()
            self.files = {}
            return
        fhandle = to_fhandle (fhandle)
        if fhandle not in self.files:
            print \
                ( "Warning: Closing unopened file %s" % fhandle
                , file = sys.stderr
                )
            return
        if self.files [fhandle]:
            self.files [fhandle].f.close ()
        del self.files [fhandle]
    # end def cmd_close

    def cmd_deffn (self, fname, varlist, expr):
        self.functions [fname] = (varlist, expr)
    # end def cmd_deffn

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
            dtype = float
            if v.endswith ('$'):
                dtype = object
            elif v.endswith ('%'):
                dtype = int
            self.dim [v] = np.zeros (l, dtype = dtype)
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

    def cmd_error (self, expr):
        self.raise_error ('Error %d' % int (expr ()))
    # end def cmd_error

    def cmd_field (self, fhandle, fieldlist):
        fhandle = to_fhandle (fhandle)
        if fhandle not in self.files:
            self.files [fhandle] = Basic_File (None)
        self.files [fhandle].fields = fieldlist
    # end def cmd_field

    def cmd_for (self, var, frm, to, step = 1):
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
                self.stack.pop ()
        if self.exec_condition:
            self.var [var] = frm
            cond = (step > 0 and frm <= to) or (step < 0 and frm >= to)
        stack_entry = Stack_Entry_For (self, cond, var, frm, to, step)
        self.stack.push (stack_entry)
    # end def cmd_for

    def cmd_get (self, fhandle):
        fh = to_fhandle (fhandle)
        f  = self.files [fh]
        fl = f.fields
        if f.f is None:
            for l, lhs in fl:
                lhs ().set ('')
        else:
            try:
                r = f.f.read (f.reclen)
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

    def _input (self, fhandle, prompt = ''):
        if fhandle is None:
            if self.input is not None:
                value = self.input.readline ().rstrip ()
            else:
                value = self.screen.cmd_input (prompt)
        else:
            value = self.files [fhandle].readline ().rstrip ()
        return value
    # end def _input

    def cmd_input (self, vars, s = '', fhandle = None):
        if fhandle is not None:
            fhandle = to_fhandle (fhandle)
        prompt = s + ': '
        if fhandle is None and self.input is not None:
            self.screen.cmd_print (prompt, end = '')
        value = self._input (fhandle, prompt)
        if fhandle is None and self.input is not None:
            self.screen.cmd_print (value)
        if len (vars) > 1:
            vals = value.split (',')
            while len (vars) > len (vals):
                value = self._input (fhandle)
                vals.extend (value.split (','))
            for lhs, v in zip (vars, vals):
                lhs ().set (v)
        else:
            lhs = vars [0] ()
            lhs.set (value)
    # end def cmd_input

    def cmd_keyoff (self):
        """ Command 'KEY OFF'
            This is supposed to turn off a list of function-key macros
            at the bottom of the screen. We do nothing.
        """
        pass
    # end def cmd_keyoff

    def cmd_kill (self, expr):
        s = expr ()
        if not isinstance (s, str):
            self.raise_error ("Non-string expression")
        try:
            os.unlink (s)
        except FileNotFoundError:
            pass
    # end def cmd_kill

    def cmd_line_input (self, fhandle, lhs):
        file = sys.stdout
        if fhandle is not None:
            file = self.files [fhandle]
        lhs = lhs ()
        lhs.set (file.readline () [:255])
    # end def cmd_line_input

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

    def cmd_onerr_goto (self, nextline):
        nextline = int (nextline)
        if nextline == 0:
            self.onerr  = None
        else:
            self.onerr = (nextline, 0)
        self.resume = None
    # end def cmd_onerr_goto

    def cmd_ongoto (self, expr, lines):
        expr = int (expr ()) - 1
        if expr < 0 or expr > len (lines) - 1:
            return
        self.next = (lines [expr], 0)
    # end def cmd_ongoto

    def cmd_ongosub (self, expr, lines):
        expr = int (expr ()) - 1
        if expr < 0 or expr > len (lines) - 1:
            return
        if self.context:
            self.gstack.append (self.context)
            self.context = None
        else:
            self.gstack.append (Context (self))
        self.next = (lines [expr], 0)
    # end def cmd_ongosub

    def cmd_open (self, expr, forwhat, fhandle, len_expr = None):
        fhandle = to_fhandle (fhandle)
        expr    = expr ()
        if not isinstance (expr, str):
            self.raise_error ('Expect string expression for filename')
            return
        if forwhat is not None:
            forwhat = forwhat.lower ()
        if len_expr is not None:
            len_expr = int (len_expr ())
        assert isinstance (expr, str)
        # The default mode is read/write (used when forwhat is RANDOM)
        mode = None
        if forwhat == 'append':
            mode = 'a'
        if forwhat == 'output':
            mode = 'w'
        elif forwhat == 'input':
            mode = 'r'
        is_bin = len_expr is not None
        try:
            self.files [fhandle] = Basic_File (expr, mode, len_expr, is_bin)
        except IOError as err:
            self.raise_error (err)
    # end def cmd_open

    def cmd_print (self, printlist, fhandle = None, using = False):
        file = None
        fn   = None
        fobj = None
        if fhandle is not None:
            fobj = self.files [fhandle]
            file = fobj.f
            fn   = fobj.name
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
        if file is None or fn == 'SCRN:':
            self.screen.cmd_print (''.join (l), end = end)
        else:
            print (''.join (l), file = file, end = end)
    # end def cmd_print

    def cmd_put (self, fhandle, recno = None):
        fh = to_fhandle (fhandle)
        if recno is not None:
            recno = int (recno)
        if self.files [fh] is not None:
            fobj = self.files [fh]
            fl   = fobj.fields
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
            if len (buf) > fobj.reclen:
                buf = buf [:fobj.reclen]
            if len (buf) < fobj.reclen:
                buf += b' ' * (fobj.reclen - len (buf))
            if recno:
                fobj.f.seek ((recno - 1) * fobj.reclen)
            fobj.f.write (buf)
    # end def cmd_put

    def cmd_read (self, vars):
        for lhs in vars:
            result = self.data [self.data_ptr]
            self.data_ptr += 1
            lhs ().set (result)
    # end def cmd_read

    def cmd_rem (self):
        pass
    # end def cmd_rem

    def cmd_reset (self):
        self.cmd_close ()
    # end def cmd_reset

    def cmd_restore (self, lineno = None):
        if lineno is not None:
            raise NotImplementedError ('RESTORE with line number unsupported')
        self.data_ptr = 0
    # end def cmd_restore

    def cmd_resume (self, nextline):
        if not self.resume:
            self.raise_error ('RESUME without error')
        self.context = None
        if nextline == 'NEXT':
            self.next  = self.nextline.get (self.resume)
        elif nextline == 0:
            self.next  = self.resume
        else:
            self.next  = (int (nextline), 0)
        self.onerr     = self.resume_on
        self.resume    = None
        self.resume_on = None
    # end def cmd_resume

    def cmd_return (self, lineno):
        if not self.gstack:
            self.raise_error ('RETURN without GOSUB')
            return
        next = self.gstack.pop ()
        if lineno is None:
            next.restore_context ()
            if next.cmdlist:
                self.exec_cmdlist (next.cmdlist, next.cmdidx + 1)
        else:
            self.lineno    = lineno
            self.sublineno = 0
            self.next = self.nextline.get ((self.lineno, self.sublineno))
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

    def cmd_shell (self, expr):
        self.raise_error ('Shell command not supported')
    # end def cmd_shell

    def cmd_wend (self):
        errmsg = 'WEND without WHILE'
        if not self.stack:
            self.raise_error (errmsg)
            return
        top = self.stack.top
        if not isinstance (top, Stack_Entry_While):
            self.raise_error (errmsg)
            return
        top.handle_wend ()
    # end def cmd_wend

    def cmd_while (self, expr):
        cond = self.exec_condition
        if self.exec_condition:
            cond = (expr ())
        stack_entry = Stack_Entry_While (self, cond, expr)
        self.stack.push (stack_entry)
    # end def cmd_while

    def cmd_write (self, fhandle, exprs):
        file = sys.stdout
        if fhandle is not None:
            file = self.files [fhandle].f
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
        , ('left', 'TIMES', 'DIVIDE', 'MOD', 'INTDIV')
        , ('left', 'EXPO')
        , ('right', 'UMINUS')
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
                             | call-statement
                             | circle-statement
                             | close-statement
                             | cls-statement
                             | color-statement
                             | data-statement
                             | def-statement
                             | defint-statement
                             | defsng-statement
                             | dim-statement
                             | else-statement
                             | endif-statement
                             | end-statement
                             | error-statement
                             | field-statement
                             | for-statement
                             | get-statement
                             | gosub-statement
                             | goto-statement
                             | if-start-statement
                             | if-statement
                             | input-statement
                             | key-statement
                             | kill-statement
                             | line-statement
                             | line-input-statement
                             | locate-statement
                             | lset-statement
                             | mid-statement
                             | next-statement
                             | onerrgoto-statement
                             | ongosub-statement
                             | ongoto-statement
                             | open-statement
                             | print-statement
                             | pset-statement
                             | put-statement
                             | read-statement
                             | rem-statement
                             | reset-statement
                             | restore-statement
                             | resume-statement
                             | return-statement
                             | rset-statement
                             | shell-statement
                             | screen-statement
                             | wend-statement
                             | while-statement
                             | width-statement
                             | window-statement
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
                          | CLS expr
        """
        # probably clear screen
        e = None
        if len (p) > 2:
            e = p [2]
        p [0] = (p [1], e)
    # end def p_cls_statement

    def p_call_statement (self, p):
        """
            call-statement : CALL VAR
        """
        p [0] = [p [1], p [2]]
    # end def p_call_statement

    def p_circle_opt (self, p):
        """
            circle-opt :
                       | COMMA opt-expr
                       | COMMA opt-expr COMMA opt-expr
                       | COMMA opt-expr COMMA opt-expr COMMA opt-expr
                       | COMMA opt-expr COMMA opt-expr COMMA opt-expr COMMA expr
        """
        p [0] = []
        if len (p) > 2:
            p [0].append (p [2])
        if len (p) > 4:
            p [0].append (p [4])
        if len (p) > 6:
            p [0].append (p [6])
        if len (p) > 8:
            p [0].append (p [8])
    # end def p_circle_opt

    def p_circle_statement (self, p):
        """
            circle-statement : CIRCLE coord COMMA expr circle-opt
        """
        p [0] = [p [1], p [2][0], p [2][1], p [4], p [5]]
    # end def p_circle_statement

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
            color-statement : COLOR exprlist
        """
        p [0] = [p [1], p [2]]
    # end def p_color_statement

    def p_coord (self, p):
        """
            coord : LPAREN expr COMMA expr RPAREN
        """
        p [0] = [p [2], p [4]]
    # end def p_coord

    def p_coord_opt (self, p):
        """
            coord-opt :
                      | coord
        """
        if len (p) == 1:
            p [0] = [None, None]
        else:
            p [0] = p [1]
    # end def p_coord_opt

    def p_data_statement (self, p):
        """
            data-statement : DATA literal-list
        """
        # Must be executed immediately, data can later be read by read commands
        for d in p [2]:
            self.data.append (d)
        p [0] = ('REM',)
    # end def p_data_statement

    def p_def_statement (self, p):
        """
            def-statement : DEF FNFUNCTION LPAREN varlist RPAREN EQ expr
                          | DEF VAR VAR LPAREN varlist RPAREN EQ expr
        """
        if len (p) == 9:
            if p [2] != 'FN':
                self.raise_error ('Invalid DEF FN command')
            p [0] = ['deffn', p [3], p [5], p [8]]
        else:
            p [0] = ['deffn', p [2][2:], p [4], p [7]]
    # end def p_defint_statement

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

    def p_expression_function_0 (self, p):
        """
            expr : INKEY
                 | CSRLIN
        """
        fn = p [1].lower ()
        if fn == 'inkey$':
            fun = self.screen.fun_inkey
        elif fn == 'csrlin':
            fun = self.screen.fun_csrlin
        else:
            assert 0
        def x ():
            return fun ()
        p [0] = x
    # end def p_expression_function_0

    def p_expression_function (self, p):
        """
            expr : ABS   LPAREN expr RPAREN
                 | ASC   LPAREN expr RPAREN
                 | ATN   LPAREN expr RPAREN
                 | CHR   LPAREN expr RPAREN
                 | COS   LPAREN expr RPAREN
                 | CVI   LPAREN expr RPAREN
                 | CVS   LPAREN expr RPAREN
                 | EOF   LPAREN expr RPAREN
                 | FIX   LPAREN expr RPAREN
                 | FRP   LPAREN expr RPAREN
                 | INT   LPAREN expr RPAREN
                 | LEN   LPAREN expr RPAREN
                 | LOG   LPAREN expr RPAREN
                 | MKI   LPAREN expr RPAREN
                 | MKS   LPAREN expr RPAREN
                 | SGN   LPAREN expr RPAREN
                 | SIN   LPAREN expr RPAREN
                 | SPACE LPAREN expr RPAREN
                 | SQR   LPAREN expr RPAREN
                 | STR   LPAREN expr RPAREN
                 | TAB   LPAREN expr RPAREN
                 | VAL   LPAREN expr RPAREN
        """
        fn = p [1].lower ()
        if fn == 'asc':
            fun = ord
        elif fn == 'chr$':
            fun = fun_chr
        elif fn == 'cvi':
            fun = fun_cvi
        elif fn == 'cvs':
            fun = fun_cvs
        elif fn == 'eof':
            fun = self.fun_eof
        elif fn == 'fix':
            fun = fun_fix
        elif fn == 'frp':
            fun = fun_fractional_part
        elif fn == 'int':
            fun = int
        elif fn == 'len':
            fun = len
        elif fn == 'mki$':
            fun = fun_mki
        elif fn == 'mks$':
            fun = fun_mks
        elif fn == 'str$':
            fun = fun_str
        elif fn == 'tab':
            fun = self.fun_tab
        elif fn == 'val':
            fun = float
        elif fn == 'space$':
            fun = fun_space
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
            expr : LEFT   LPAREN expr COMMA expr RPAREN
                 | RIGHT  LPAREN expr COMMA expr RPAREN
                 | STRING LPAREN expr COMMA expr RPAREN
        """
        fn = p [1].lower ()
        if fn == 'left$':
            fun = fun_left
        elif fn == 'right$':
            fun = fun_right
        elif fn == 'string$':
            fun = fun_string
        else:
            assert 0
        p3 = p [3]
        p5 = p [5]
        def x ():
            return fun (p3 (), p5 ())
        p [0] = x
    # end def p_expression_function_2

    def p_expression_function_2_3 (self, p):
        """
            expr : MID   LPAREN expr COMMA expr COMMA expr RPAREN
                 | MID   LPAREN expr COMMA expr RPAREN
                 | INSTR LPAREN expr COMMA expr RPAREN
                 | INSTR LPAREN expr COMMA expr COMMA expr RPAREN
        """
        fn = p [1].lower ()
        if fn == 'mid$':
            fun = fun_mid
        elif fn == 'instr':
            fun = fun_instr
        else:
            assert 0
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

    def p_expression_indexed_array (self, p):
        """
            expr : VAR LPAREN exprlist RPAREN
        """
        p1 = p [1]
        p3 = p [3]
        def x ():
            r = [int (k) for k in p3 ()]
            return self.dim [p1][*r]
        p [0] = x
    # end def p_expression_indexed_array

    def p_expression_literal (self, p):
        """
            expr : literal
        """
        p1 = p [1]
        def x ():
            return p1
        p [0] = x
    # end def p_expression_literal

    def p_expression_not (self, p):
        """
            expr : NOT expr
        """
        p2 = p [2]
        def x ():
            return not (p2 ())
        p [0] = x
    # end def p_expression_not

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
                 | expr INTDIV expr
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
        elif p [2] == '\\':
            def x ():
                return f1 () // f3 ()
        p [0] = x
    # end def p_expression_twoop

    def p_expression_uminus (self, p):
        """
            expr : MINUS expr %prec UMINUS
        """
        p2 = p [2]
        def x ():
            return - p2 ()
        p [0] = x
    # end def p_expression_uminus

    def p_expression_userdefined_function (self, p):
        """
            expr : FNFUNCTION LPAREN exprlist RPAREN
        """
        fn = p [1][2:]
        p3 = p [3]
        def x ():
            return self.fun_fn (fn, p3)
        p [0] = x
    # end def p_expression_userdefined_function

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

    def p_error_statement (self, p):
        """
            error-statement : ERROR expr
        """
        p [0] = (p [1], p [2])
    # end def p_error_statement

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
                          | GET coord MINUS coord COMMA VAR
        """
        if len (p) == 3:
            p [0] = (p [1], p [2])
        else:
            cmd = 'get_graphics'
            p [0] = [cmd, p [6], p [2][0], p [2][1], p [4][0], p [4][1]]
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
                            | INPUT SEMIC varlist-complex
        """
        if len (p) == 4:
            p [0] = (p [1], p [3], '')
        else:
            p [0] = (p [1], p [4], p [2])
    # end def p_input_statement

    def p_input_statement_multi (self, p):
        """
            input-statement : INPUT varlist-complex
                            | INPUT FHANDLE COMMA varlist-complex
        """
        if len (p) == 3:
            p [0] = (p [1], p [2])
        else:
            p [0] = (p [1], p [4], '', p [2])
    # end def p_input_statement_multi

    def p_intlist (self, p):
        """
            intlist : NUMBER
                    | HEXNUMBER
                    | intlist COMMA NUMBER
                    | intlist COMMA HEXNUMBER
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_intlist

    def p_key_statement (self, p):
        """
            key-statement : KEY expr COMMA expr
                          | KEY VAR
        """
        if len (p) == 3:
            if p [2] != 'OFF':
                self.raise_error ('Expected KEY OFF here')
            p [0] = ['keyoff']
        else:
            p [0] = [p [1], p [2], p [4]]
    # end def p_key_statement

    def p_kill_statement (self, p):
        """
            kill-statement : KILL expr
        """
        p [0] = [p [1], p [2]]
    # end def p_kill_statement

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

    def p_line_attr (self, p):
        """
            line-attr :
                      | expr
        """
        if len (p) == 1:
            p [0] = None
        else:
            p [0] = p [1]
    # end def p_line_attr

    def p_line_bf (self, p):
        """
            line-bf :
                    | VAR
                    | VAR VAR
        """
        if len (p) == 1:
            p [0] = None
        elif len (p) == 2:
            if p [1] not in ('B', 'BF'):
                self.raise_error ('Invalid B option: %s' % p [1])
            p [0] = p [1]
        else:
            if p [1] != 'B' or p [2] != 'F':
                self.raise_error ('Invalid B/F option: %s/%s' % tuple (p [1:2]))
            p [0] = 'BF'
    # end def p_line_bf

    def p_line_opt (self, p):
        """
            line-opt :
                     | COMMA line-attr
                     | COMMA line-attr COMMA line-bf
                     | COMMA line-attr COMMA line-bf COMMA expr
        """
        if len (p) == 1:
            p [0] = []
        else:
            p [0] = [p [2]]
            if len (p) > 3:
                p [0].append (p [4])
            if len (p) > 5:
                p [0].append (p [6])
    # end def p_line_opt

    def p_line_statement (self, p):
        """
            line-statement : LINE coord-opt MINUS coord line-opt
        """
        p [0] = [p [1], p [2][0], p [2][1], p [4][0], p [4][1], p [5]]
    # end def p_line_statement

    def p_line_input_statement (self, p):
        """
            line-input-statement : LINE INPUT FHANDLE COMMA lhs
                                 | LINE INPUT SEMIC lhs
        """
        if len (p) == 5:
            p [0] = ['line_input', None, p [4]]
        else:
            p [0] = ['line_input', p [3], p [5]]
    # end def p_line_input_statement

    def p_literal (self, p):
        """
            literal : NUMBER
                    | HEXNUMBER
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
            literal-list : literal-neg
                         | literal-list COMMA literal-neg
        """
        if len (p) == 2:
            p [0] = [p [1]]
        else:
            p [0] = p [1] + [p [3]]
    # end def p_literal_list

    def p_literal_neg (self, p):
        """
            literal-neg : literal
                        | MINUS NUMBER
        """
        if len (p) == 3:
            p [0] = -p [2]
        else:
            p [0] = p [1]
    # end def p_literal_neg

    def p_locate_statement (self, p):
        """
            locate-statement : LOCATE opt-expr COMMA opt-expr
                             | LOCATE opt-expr COMMA opt-expr COMMA exprlist
        """
        if len (p) == 5:
            p [0] = (p [1], p [2], p [4])
        else:
            p [0] = (p [1], p [2], p [4], p [6])
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

    def p_onerror_goto_statement (self, p):
        """
            onerrgoto-statement : ON ERROR GOTO NUMBER
        """
        p [0] = ['onerr_goto', p [4]]
    # end def p_onerror_goto_statement

    def p_ongoto_statement (self, p):
        """
            ongoto-statement : ON expr GOTO intlist
        """
        p [0] = ('ongoto', p [2], p [4])
    # end def p_ongoto_statement

    def p_ongosub_statement (self, p):
        """
            ongosub-statement : ON expr GOSUB intlist
        """
        p [0] = ('ongosub', p [2], p [4])
    # end def p_ongosub_statement

    def p_open_statement (self, p):
        """
            open-statement : OPEN expr FOR OUTPUT AS FHANDLE
                           | OPEN expr FOR APPEND AS FHANDLE
                           | OPEN expr FOR INPUT  AS FHANDLE
                           | OPEN expr FOR RANDOM AS FHANDLE
        """
        p [0] = (p [1], p [2], p [4], p [6])
    # end def p_open_statement

    def p_open_statement_bin (self, p):
        """
            open-statement : OPEN expr AS FHANDLE LEN EQ expr
                           | OPEN expr AS FHANDLE
                           | OPEN expr FOR RANDOM AS FHANDLE LEN EQ expr
                           | OPEN expr FOR OUTPUT AS FHANDLE LEN EQ expr
                           | OPEN expr FOR INPUT  AS FHANDLE LEN EQ expr
        """
        expr = p [2]
        if len (p) == 5:
            fhandle = p [4]
            length  = None
            forwhat = None
        elif len (p) == 8:
            fhandle = p [4]
            length  = p [7]
            forwhat = None
        else:
            fhandle = p [6]
            length  = p [9]
            forwhat = p [4]
        p [0] = (p [1], expr, forwhat, fhandle, length)
    # end def p_open_statement_bin

    def p_optional_expression (self, p):
        """
            opt-expr :
                     | expr
        """
        if len (p) == 1:
            p [0] = None
        else:
            p [0] = p [1]
    # end def p_optional_expression

    def p_print_statement (self, p):
        """
            print-statement : PRINT printlist
                            | PRINT USING printlist
                            | PRINT FHANDLE COMMA printlist
                            | PRINT FHANDLE COMMA USING printlist
                            | QMARK printlist
                            | QMARK USING printlist
                            | QMARK FHANDLE COMMA printlist
                            | QMARK FHANDLE COMMA USING printlist
        """
        if len (p) == 3:
            p [0] = ('PRINT', p [2])
        elif len (p) == 4:
            p [0] = ('PRINT', p [3], None, True)
        elif len (p) == 5:
            p [0] = ('PRINT', p [4], p [2])
        else:
            p [0] = ('PRINT', p [5], p [2], True)
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

    def p_pset_statement (self, p):
        """
            pset-statement : PSET coord
        """
        p [0] = [p [1], p [2][0], p [2][1]]
    # end def p_pset_statement

    def p_put_option (self, p):
        """
            put-option :
                       | COMMA PSET
                       | COMMA PRESET
                       | COMMA AND
                       | COMMA OR
                       | COMMA XOR
        """
        if len (p) == 1:
            p [0] = None
        else:
            p [0] = p [2]
    # end def p_put_option

    def p_put_statement (self, p):
        """
            put-statement : PUT FHANDLE
                          | PUT NUMBER
                          | PUT FHANDLE COMMA NUMBER
                          | PUT NUMBER  COMMA NUMBER
                          | PUT coord COMMA VAR put-option
        """
        if len (p) == 3:
            p [0] = (p [1], p [2])
        elif len (p) == 5:
            p [0] = (p [1], p [2], p [4])
        else:
            p [0] = ('put_graphics', p [2][0], p [2][1], p [4], p [5])
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

    def p_reset_statement (self, p):
        """
            reset-statement : RESET
        """
        p [0] = [p [1]]
    # end def p_reset_statement

    def p_restore_statement (self, p):
        """
            restore-statement : RESTORE NUMBER
                              | RESTORE
        """
        if len (p) == 2:
            p [0] = [p [1], None]
        else:
            p [0] = [p [1], p [2]]
    # end def p_restore_statement

    def p_resume_statement (self, p):
        """
            resume-statement : RESUME NUMBER
                             | RESUME
                             | RESUME NEXT
        """
        p2 = 0
        if len (p) > 2:
            p2 = p [2]
        p [0] = [p [1], p2]
    # end def p_resume_statement

    def p_return_statement (self, p):
        """
            return-statement : RETURN
                             | RETURN NUMBER
        """
        line = None
        if len (p) > 2:
            line = p [2]
        p [0] = [p [1], line]
    # end def p_return_statement

    def p_rset_statement (self, p):
        """
            rset-statement : RSET lhs EQ expr
        """
        p [0] = (p [1], p [2], p [4])
    # end def p_rset_statement

    def p_shell_statement (self, p):
        """
            shell-statement : SHELL expr
        """
        p [0] = (p [1], p [2])
    # end def p_shell_statement

    def p_screen_statement (self, p):
        """
            screen-statement : SCREEN expr COMMA expr COMMA expr COMMA expr
        """
        p [0] = (p [1], p [2], p [4], p [6], p [8])
    # end def p_screen_statement

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

    def p_wend_statement (self, p):
        """
            wend-statement : WEND
        """
        p [0] = [p [1]]
    # end p_wend_statement

    def p_while_statement (self, p):
        """
            while-statement : WHILE expr
        """
        p [0] = [p [1], p [2]]
    # end def p_while_statement

    def p_width_statement (self, p):
        """
            width-statement : WIDTH expr
                            | WIDTH expr COMMA expr
        """
        nrow = None
        if len (p) > 4:
            nrow = p [4]
        p [0] = [p [1], p [2], nrow]
    # end def p_width_statement

    def p_window_statement (self, p):
        """
            window-statement : WINDOW
                             | WINDOW coord MINUS coord
                             | WINDOW SCREEN coord MINUS coord
        """
        if len (p) == 2:
            p [0] = [p [1], None, None, None, None]
        elif len (p) == 5:
            p [0] = [p [1], p [2][0], p [2][1], p [4][0], p [4][1]]
        else:
            p [0] = [p [1], p [3][0], p [3][1], p [5][0], p [5][1], True]
    # end def p_window_statement

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

def options (argv):
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
        ( '-o', '--output-file'
        , help = 'Write output to given file'
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
    cmd.add_argument \
        ( '--enable-text-color'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '-S', '--screen'
        , help    = 'Screen emulation'
        , choices = ('None', 'tkinter')
        , default = 'None'
        )
    args = cmd.parse_args (argv)
    return args
# end def options

def main (argv = sys.argv [1:]):
    args = options (argv)
    interpreter = Interpreter (args)
    interpreter.break_lineno = args.break_line
    interpreter.run ()
# end def main

if __name__ == '__main__':
    main ()
