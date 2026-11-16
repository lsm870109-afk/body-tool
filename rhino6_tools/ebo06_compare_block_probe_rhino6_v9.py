# -*- coding: utf-8 -*-
# NBA Live 06 EBO COMPARE BLOCK PROBE V9 - READ ONLY
# Rhino 6 / IronPython 2.7
# Select two or more EBO files. No source bytes are modified.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def bval(data, i):
    return int(data[i])

def u32(data, off):
    return struct.unpack('<I', ''.join(chr(bval(data, off+i)) for i in range(4)))[0]

def f32(data, off):
    return struct.unpack('<f', ''.join(chr(bval(data, off+i)) for i in range(4)))[0]

def hexline(data, start, end):
    vals=[]
    for i in range(start, min(end, start+32)):
        vals.append('%02X' % bval(data,i))
    return ' '.join(vals)

def float_stats(data, start, end):
    count=(end-start)//4
    vals=[]
    finite=0
    zeros=0
    nz=0
    mn=None
    mx=None
    for i in range(count):
        v=f32(data,start+i*4)
        vals.append(v)
        if v == v and abs(v) != float('inf'):
            finite+=1
            if v == 0.0:
                zeros+=1
            else:
                nz+=1
            if mn is None or v<mn: mn=v
            if mx is None or v>mx: mx=v
    if mn is None:
        return count,finite,zeros,nz,None,None
    return count,finite,zeros,nz,mn,mx

def inspect(path):
    data=File.ReadAllBytes(path)
    size=len(data)
    print('')
    print('='*76)
    print('FILE: %s' % str(path))
    print('SIZE=%d (0x%X)' % (size,size))
    if size < 0x1B4:
        print('ERROR: too short for known metadata fields')
        return

    print('MAGIC=%r VERSION=%d' % (''.join(chr(bval(data,i)) for i in range(4)),u32(data,4)))
    print('COORD_BYTES=0x%X COORD_START=0x%X' % (u32(data,0x11C),u32(data,0x120)))
    print('COORD_COUNT_IF_FLOAT3=%d' % (u32(data,0x11C)//12))

    specs=[
        ('BLOCK_A',0x148,0x14C,0x144),
        ('BLOCK_B',0x170,0x174,0x16C)
    ]
    for name,so,eo,lo in specs:
        start=u32(data,so)
        end=u32(data,eo)
        length=u32(data,lo)
        print('')
        print('-- %s --' % name)
        print('START_FIELD@0x%04X=0x%X END_FIELD@0x%04X=0x%X LENGTH_FIELD@0x%04X=0x%X' % (so,start,eo,end,lo,length))
        if start < size and end <= size and end >= start:
            span=end-start
            print('SPAN=%d (0x%X) LENGTH_PLUS_4=%d MATCH=%s' % (span,span,length+4,str(span==length+4)))
            print('FIRST32: %s' % hexline(data,start,min(end,start+32)))
            print('LAST32 : %s' % hexline(data,max(start,end-32),end))
            if span >= 4:
                print('FIRST_DWORD=0x%08X (%d)' % (u32(data,start),u32(data,start)))
            if span >= 4 and span % 4 == 0:
                st=float_stats(data,start,end)
                print('AS_FLOATS count=%d finite=%d zeros=%d nonzero=%d min=%s max=%s' %
                      (st[0],st[1],st[2],st[3],str(st[4]),str(st[5])))
                print('FIRST_FLOATS:')
                for j in range(min(16,st[0])):
                    print('  %03d @0x%X = %.10g' % (j,start+j*4,f32(data,start+j*4)))
        else:
            print('INVALID RANGE FOR THIS FILE')

    print('')
    print('-- MORPH-RELATED TAIL STRINGS --')
    for term in ('Morph','MorphTargetNameArray','MorphStreamHeader','MorphData','ByteArray','headAShape_morphs','coord','normal','colour'):
        needle=term
        raw=''.join(chr(bval(data,i)) for i in range(size))
        pos=raw.find(needle)
        print('%s : %s' % (term,('0x%X' % pos) if pos>=0 else 'NOT FOUND'))

    print('='*76)

def main():
    d=OpenFileDialog()
    d.Title='Select two or more NBA Live 06 EBO files'
    d.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    d.Multiselect=True
    if d.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    if len(d.FileNames)<2:
        print('Please select at least two EBO files.')
        return
    for p in d.FileNames:
        inspect(p)
    print('')
    print('V9 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')

if __name__=='__main__':
    main()
