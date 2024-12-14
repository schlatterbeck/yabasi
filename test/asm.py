import struct
from unicorn  import Uc, UC_ARCH_X86, UC_MODE_16, UcError, x86_const
from keystone import Ks, KS_ARCH_X86, KS_MODE_16, KsError, KS_OPT_SYNTAX_INTEL
from capstone import Cs, CS_ARCH_X86, CS_MODE_16
import unicorn

# This seems to work only when run inside the test framework
# (Unless we explicitly set PYTHONPATH)
from yabasi.mbf import MBF_Float

class GWBasic_Math:
    # FIXME: These are the addresses of functions we want to call.
    # They should really be retrieved from the assembler but found no
    # way to do this.
    flt   = 0x2ec
    fmuls = 0x10b
    fadds = 0x1ba

    def __init__ (self, fn = 'test/math.asm', verbose = 0, debug = False):
        self.verbose = verbose
        self.debug   = debug
        lines = []
        with open (fn) as f:
            for line in f:
                line = line.rstrip ()
                if line.lstrip ().startswith ('SUBTTL'):
                    line = ''
                try:
                    a, b = line.split (';', 1)
                    line = a
                except ValueError:
                    pass
                lines.append (line)
        self.asm = '\n'.join (lines) + '\n'

        ks = Ks (KS_ARCH_X86, KS_MODE_16)
        ks.syntax = KS_OPT_SYNTAX_INTEL
        try:
            code, _ = ks.asm (self.asm)
        except KsError as err:
            count = err.get_asm_count ()
            print ('Error: %s' % err)
            if count is not None:
                print ('compiled %s instructions' % count)
            exit (23)
        if self.verbose > 1:
            print ('assembled: len = %s' % len (code))
        self.code    = bytes (code)
        self.calladr = len (self.code) - 7
        asm = self.disassemble (self.code)
        self.idict = {}
        for a in asm:
            s = str (a)
            pos, bin, s = s.split (None, 3)[1:]
            pos = int (pos, 16) - len (self.code)
            s   = ('0x%04x %s' % (pos, s)).rstrip ('>').rstrip ()
            self.idict [pos] = (s, bin)
        if self.verbose > 1:
            for n in sorted (self.idict):
                print ('0x%04x: %s' % (n, self.idict [n]))
    # end def __init__

    def add (self, num1, num2):
        """ The given two numbers are MBF_Float.
            We set up the call to $FADDS.
            Then we put the first number int BXDX and the second one
            into the FAC.
            The result is in the FAC and is returned as an MBF_Float.
        """
        self.setup ()
        num = struct.unpack ('>HH', num1.as_mbf ())
        if self.verbose:
            print ('BX:%04x DX:%04x' % num)
        self.uc.reg_write (x86_const.UC_X86_REG_BX, num [0])
        if self.verbose:
            print ('BH:%02x' % self.uc.reg_read (x86_const.UC_X86_REG_BH))
            print ('BL:%02x' % self.uc.reg_read (x86_const.UC_X86_REG_BL))
        self.uc.reg_write (x86_const.UC_X86_REG_DX, num [1])
        self.uc.mem_write (10, num2.as_mbf ())
        if self.verbose:
            print (' '.join ('%02x' % k for k in self.uc.mem_read (6, 10)))
        self.setup_call (self.fadds)
        self.uc.reg_write (x86_const.UC_X86_REG_SP, 0)
        self.uc.emu_start (self.adr, self.adr + len (self.code))
        if self.verbose:
            print (' '.join ('%02x' % k for k in self.uc.mem_read (6, 10)))
        return self.to_mbf ()
    # end def add

    def debug_hook (self, uc, address, size, user_data):
        print (self.idict [address][0])
        ax = self.uc.reg_read (x86_const.UC_X86_REG_AX)
        bx = self.uc.reg_read (x86_const.UC_X86_REG_BX)
        cx = self.uc.reg_read (x86_const.UC_X86_REG_CX)
        dx = self.uc.reg_read (x86_const.UC_X86_REG_DX)
        print ('  AX: %04x BX: %04x CX: %04x DX: %04x' % (ax, bx, cx, dx))
        di = self.uc.reg_read (x86_const.UC_X86_REG_DI)
        si = self.uc.reg_read (x86_const.UC_X86_REG_SI)
        bp = self.uc.reg_read (x86_const.UC_X86_REG_BP)
        print ('  DI: %04x SI: %04x BP: %04x' % (di, si, bp))
        fl = self.uc.reg_read (x86_const.UC_X86_REG_FLAGS)
        fl = bin (fl) [2:]
        fl = '0' * (16 - len (fl)) + fl
        fl = fl.replace ('', '  ').rstrip ()
        print ('  U  U  U  U OF DF IF TF SF ZF  U AF  U PF  U CF')
        print (fl)
    # end def debug_hook

    def debug_disassemble (self):
        asm = self.disassemble ()
        print (asm [0])
        for l in asm [-2:]:
            print (l)
    # end def debug_disassemble

    def disassemble (self, code = None):
        cs   = Cs (CS_ARCH_X86, CS_MODE_16)
        if code is None:
            code = self.uc.mem_read (0, len (self.code))
        # Avoid misleading disassembler with data
        code = code [:6] + bytes (10) + code [16:]
        return list (cs.disasm (code, len (code)))
    # end def disassemble

    def int_to_float (self, value):
        self.setup ()
        self.setup_call (self.flt)
        self.uc.reg_write (x86_const.UC_X86_REG_DX, value)
        self.uc.reg_write (x86_const.UC_X86_REG_SP, 0)
        self.uc.emu_start (self.adr, self.adr + len (self.code))
        return self.to_mbf ()
    # end def int_to_float

    def mul (self, num1, num2):
        self.setup ()
        num = struct.unpack ('>HH', num1.as_mbf ())
        if self.verbose:
            print ('BX:%04x DX:%04x' % num)
        self.uc.reg_write (x86_const.UC_X86_REG_BX, num [0])
        self.uc.reg_write (x86_const.UC_X86_REG_DX, num [1])
        self.uc.mem_write (10, num2.as_mbf ())
        if self.verbose:
            print (' '.join ('%02x' % k for k in self.uc.mem_read (6, 10)))
        self.setup_call (self.fmuls)
        self.uc.reg_write (x86_const.UC_X86_REG_SP, 0)
        self.uc.emu_start (self.adr, self.adr + len (self.code))
        if self.verbose:
            print (' '.join ('%02x' % k for k in self.uc.mem_read (6, 10)))
        return self.to_mbf ()
    # end def mul

    def setup_call (self, adr):
        b = b'\x66\xe8' + struct.pack ('<l', adr - (self.calladr + 6))
        self.uc.mem_write (self.calladr, b)
        #self.debug_disassemble ()
    # end def setup_call

    def setup (self):
        self.adr = adr = 0x0
        uc  = Uc (UC_ARCH_X86, UC_MODE_16)
        uc.mem_map (adr, 0x200000) # mem @0x0, 2MB
        uc.mem_write (adr, self.code)
        uc.reg_write (x86_const.UC_X86_REG_CS, 0)
        uc.reg_write (x86_const.UC_X86_REG_DS, 0)
        uc.reg_write (x86_const.UC_X86_REG_SS, 0x1000000 >> 8)
        # Single-step hook
        if self.debug:
            uc.hook_add (unicorn.UC_HOOK_CODE, self.debug_hook)
        self.uc = uc
    # end def setup

    def to_mbf (self):
        fac  = self.uc.mem_read (10, 4)
        #print (fac)
        exp  = fac [0] - 128 - 1
        if exp == -129:
            return MBF_Float (0, 0, 0)
        sign = int (bool (fac [1] & 0x80))
        mnt  = (((fac [1] & 0x7f) | 0x80) << 16) + (fac [2] << 8) + fac [3]
        #print (sign, exp, mnt)
        return MBF_Float (sign, exp, mnt)
    # end def to_mbf

# end class GWBasic_Math

if __name__ == '__main__':
    import sys
    from argparse import ArgumentParser
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( '-v', '--verbose'
        , action  = 'count'
        , help    = 'Verbose reporting including disassembler listing'
        , default = 0
        )
    cmd.add_argument \
        ( '-D', '--debug'
        , action = 'store_true'
        , help   = 'Debugging with visited assembler lines'
        )
    args = cmd.parse_args (sys.argv [1:])
    m = GWBasic_Math (verbose = args.verbose, debug = args.debug)
    #r = m.int_to_float (0x4711)
    #print (r.as_float ())
    #r = m.add (MBF_Float.from_float (0.0), MBF_Float.from_float (4.0))
    #print (r.as_float ())
    #r = m.add (MBF_Float.from_float (4.0), MBF_Float.from_float (0.0))
    #print (r.as_float ())
    #r = m.add (MBF_Float.from_float (4.0), MBF_Float.from_float (8.0))
    #print (r.as_float ())
    #r = m.add (MBF_Float.from_float (8.0), MBF_Float.from_float (4.0))
    #print (r.as_float ())
    #r = m.int_to_float (0x4711)
    #print (r.as_float ())
    #r = m.add (MBF_Float (0, 23, 0xffffff), MBF_Float.from_float (-16777214.0))
    #print (r.as_float ())
    a = MBF_Float (0, 23, 0xffffff)
    r = m.mul (a, a)
    #a = MBF_Float (0, 23, 0xffffff)
    #b = MBF_Float.from_float (-1.0)
    #r = m.add (a, b)
    #print (r.as_float ())
