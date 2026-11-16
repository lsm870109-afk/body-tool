# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V7 - READ ONLY
# Rhino 6 / IronPython 2.7
# Checks the byte-counted blocks inferred from V5/V6.
# Does not decode or modify the source file.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def by(data, off):
    return int(data[off])

def u32(data, off):
    return struct.unpack('<I', ''.join(chr(by(data, off+i)) for i in range(4)))[0]

def f32(data, off):
    return struct.unpack('<f', ''.join(chr(by(data, off+i)) for i in range(4)))[0]

def dump_bytes(data, start, count, label):
    end = min(start+count, len(data))
    print('')
    print('-- %s: 0x%X..0x%X (%d bytes) --' % (label, start, end, end-start))
    for pos in range(start, end, 16):
        stop = min(pos+16, end)
        print('0x%04X: %s' % (pos, ' '.join('%02X' % by(data,i) for i in range(pos,stop))))

def byte_block(data, header, expected, label):
    actual = u32(data, header)
    start = header + 4
    end = min(start + expected, len(data))
    vals = [by(data, i) for i in range(start, end)]
    print('')
    print('-- %s --' % label)
    print('HEADER @0x%X = %d (0x%X)' % (header, actual, actual))
    print('PAYLOAD @0x%X EXPECTED=%d ACTUAL=%d END=0x%X' % (start, expected, len(vals), end))
    if vals:
        print('MIN=%d MAX=%d UNIQUE=%d' % (min(vals), max(vals), len(set(vals))))
        counts = {}
        for v in vals:
            counts[v] = counts.get(v,0)+1
        ranked = sorted([(n,v) for v,n in counts.items()], reverse=True)
        print('FREQUENCY:')
        for n,v in ranked[:24]:
            print('  %02X : %d' % (v,n))
        print('FIRST 96:')
        for i in range(0, min(96,len(vals)), 16):
            print('  %04d: %s' % (i, ' '.join('%02X' % v for v in vals[i:i+16])))
        print('LAST 32:')
        start_i = max(0,len(vals)-32)
        for i in range(start_i,len(vals),16):
            print('  %04d: %s' % (i, ' '.join('%02X' % v for v in vals[i:i+16])))
    return start, end

def float_block(data, start, count, label):
    print('')
    print('-- %s --' % label)
    print('START=0x%X FLOATS=%d BYTES=%d' % (start,count,count*4))
    vals = [f32(data,start+i*4) for i in range(count)]
    for group in (3,4):
        print('GROUP SIZE %d: full_groups=%d remainder=%d' % (group,count//group,count%group))
    print('INDEXED QUADS (first 24):')
    for i in range(min(24,count//4)):
        k=i*4
        print('  Q%03d @0x%X: %.8g %.8g %.8g %.8g' % (i,start+k*4,vals[k],vals[k+1],vals[k+2],vals[k+3]))
    print('INDEXED TRIPLES (first 24):')
    for i in range(min(24,count//3)):
        k=i*3
        print('  T%03d @0x%X: %.8g %.8g %.8g' % (i,start+k*4,vals[k],vals[k+1],vals[k+2]))
    print('NONZERO COUNT=%d' % sum(1 for v in vals if v != 0.0))

def tiny_float_region(data, start, end, label):
    count=(end-start)//4
    vals=[f32(data,start+i*4) for i in range(count)]
    print('')
    print('-- %s --' % label)
    print('FLOATS=%d NONZERO=%d' % (count,sum(1 for v in vals if v != 0.0)))
    if vals:
        print('MIN=%.9g MAX=%.9g' % (min(vals),max(vals)))
        print('FIRST 32:')
        for i in range(min(32,len(vals))):
            print('  %03d @0x%X = %.9g' % (i,start+i*4,vals[i]))

def inspect(path):
    data=File.ReadAllBytes(path)
    size=len(data)
    print('')
    print('='*72)
    print('NBA LIVE 06 MORPH STREAM PROBE V7 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE=%d (0x%X)' % (size,size))
    if size < 0x453C or by(data,0)!=69 or by(data,1)!=66 or by(data,2)!=79 or by(data,3)!=0:
        print('ERROR: unexpected EBO file')
        return

    # V5 alignment: count header is four bytes before the V6 candidate payload offset.
    start_a,end_a=byte_block(data,0x3C68,248,'248-BYTE BLOCK AT 0x3C68')
    print('BLOCK A END=0x%X; NEXT FLOAT BLOCK=0x3D70; GAP=%d bytes' % (end_a,0x3D70-end_a))
    dump_bytes(data,end_a,0x3D70-end_a,'BLOCK A PADDING / ALIGNMENT')

    float_block(data,0x3D70,404,'FLOAT BLOCK 0x3D70..0x43C0')
    byte_block(data,0x43C0,163,'163-BYTE BLOCK AT 0x43C0')
    dump_bytes(data,0x43C0+4+163,0x4474-(0x43C0+4+163),'BYTES AFTER 163-BYTE PAYLOAD TO 0x4474')
    dump_bytes(data,0x4474,0x449C-0x4474,'0x4474 METADATA-LIKE REGION')

    tiny_float_region(data,0x1CA4,0x1FC4,'TINY FLOAT REGION 0x1CA4..0x1FC4')
    tiny_float_region(data,0x1FC4,0x3C68,'TINY FLOAT REGION 0x1FC4..0x3C68')

    print('')
    print('-- METADATA POINTER/LENGTH PAIRS (RAW) --')
    for off in (0x11C,0x120,0x144,0x148,0x14C,0x16C,0x170,0x174,0x194,0x198,0x19C,0x1B0):
        print('0x%04X = 0x%08X (%d)' % (off,u32(data,off),u32(data,off)))

    print('')
    print('V7 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
    print('='*72)

def main():
    d=OpenFileDialog()
    d.Title='Select NBA Live 06 character Morph EBO'
    d.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    d.Multiselect=False
    if d.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    inspect(d.FileName)

if __name__=='__main__':
    main()
