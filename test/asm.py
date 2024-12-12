from unicorn  import Uc, UC_ARCH_X86, UC_MODE_16, UcError, x86_const
from keystone import Ks, KS_ARCH_X86, KS_MODE_16, KsError, KS_OPT_SYNTAX_INTEL
from capstone import Cs, CS_ARCH_X86, CS_MODE_16
import unicorn

class GWBasic_Math:

    verbose = False

    def __init__ (self, fn = 'test/math.asm'):
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
        if self.verbose:
            print ('assembled: len = %s' % len (code))
        self.code = bytes (code)

        # Disassemble
        if 0:
            cs = Cs (CS_ARCH_X86, CS_MODE_16)
            asm = list (cs.disasm (code, len (code)))
            for l in asm:
                print (l)
        self.setup ()
    # end def __init__

#    def add (self, num1, num2):
#    # end def add

    def setup (self):
        self.adr = adr = 0x0
        uc  = Uc (UC_ARCH_X86, UC_MODE_16)
        uc.mem_map (adr, 0x200000) # mem @0x0, 2MB
        uc.mem_write (adr, self.code)
        uc.reg_write (x86_const.UC_X86_REG_CS, 0)
        uc.reg_write (x86_const.UC_X86_REG_DS, 0)
        uc.reg_write (x86_const.UC_X86_REG_SS, 2044 >> 8)
        self.uc = uc
    # end def setup

    def int_to_float (self, value):
        self.uc.reg_write (x86_const.UC_X86_REG_DX, value)
        self.uc.emu_start (self.adr, self.adr + len (self.code))
        mem = self.uc.mem_read (0, 16)
        for k in mem:
            print ('%02x' % k)
    # end def int_to_float
# end class GWBasic_Math

if __name__ == '__main__':
    m = GWBasic_Math ()
    m.int_to_float (0x4711)
