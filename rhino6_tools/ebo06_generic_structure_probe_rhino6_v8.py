# -*- coding: utf-8 -*-
# NBA Live 06 EBO GENERIC STRUCTURE PROBE V8 - READ ONLY
# Rhino 6 / IronPython 2.7
# Size-independent header and pointer survey. Does not modify the file.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def u32(data, off):
    return struct.unpack('<I', ''.join(chr(int(data[off+i])) for i in range(4)))[0]

def printable(data, start, end):
    out=[]
    i=start
    while i<end:
        if 32 <= int(data[i]) <= 126:
            j=i
            while j<end and 32 <= int(data[j]) <= 126:
                j+=1
            if j-i >= 3:
                s=''.join(chr(int(data[k])) for k in range(i,j))
                out.append((i,s))
            i=j
        else:
            i+=1
    return out

def inspect(path):
    data=File.ReadAllBytes(path)
    size=len(data)
    print('')
    print('='*72)
    print('NBA LIVE 06 EBO GENERIC STRUCTURE PROBE V8 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE=%d (0x%X)' % (size,size))
    if size < 16:
        print('ERROR: file too short for EBO header')
        return

    magic=''.join(chr(int(data[i])) for i in range(4))
    print('MAGIC=%r' % magic)
    print('DWORD @0x04 VERSION/CANDIDATE = 0x%08X (%d)' % (u32(data,4),u32(data,4)))
    print('DWORD @0x08 SIZE/CANDIDATE   = 0x%08X (%d)' % (u32(data,8),u32(data,8)))
    print('DWORD @0x0C                 = 0x%08X (%d)' % (u32(data,12),u32(data,12)))

    print('')
    print('-- FIRST 0x200 BYTES AS DWORDS --')
    lim=min(size,0x200)
    for off in range(0,lim-(lim%4),4):
        if off % 16 == 0:
            print('0x%04X:' % off)
        print(' %08X' % u32(data,off),)

    print('')
    print('-- KNOWN V7 FIELD OFFSETS (WHEN PRESENT) --')
    fields=(0x11C,0x120,0x144,0x148,0x14C,0x16C,0x170,0x174,
            0x194,0x198,0x19C,0x1B0)
    for off in fields:
        if off+4 <= size:
            v=u32(data,off)
            valid='IN_FILE' if v < size else 'OUT_OF_FILE'
            print('0x%04X = 0x%08X (%d) %s' % (off,v,v,valid))
        else:
            print('0x%04X = <not present>' % off)

    print('')
    print('-- ALIGNED DWORDS THAT LOOK LIKE FILE OFFSETS (0x40..0x200) --')
    found=[]
    scan_end=min(size,0x200)
    for off in range(0x10,scan_end-3,4):
        v=u32(data,off)
        if 0x40 <= v < size:
            found.append((off,v))
    for off,v in found:
        print('field 0x%04X -> 0x%X (%d)' % (off,v,v))
    if not found:
        print('(none)')

    print('')
    print('-- PRINTABLE STRINGS IN LAST 0x300 BYTES --')
    start=max(0,size-0x300)
    strings=printable(data,start,size)
    for off,s in strings:
        print('0x%04X: %s' % (off,s))
    if not strings:
        print('(none)')

    print('')
    print('V8 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
    print('='*72)

def main():
    d=OpenFileDialog()
    d.Title='Select NBA Live 06 character EBO'
    d.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    d.Multiselect=False
    if d.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    inspect(d.FileName)

if __name__=='__main__':
    main()
