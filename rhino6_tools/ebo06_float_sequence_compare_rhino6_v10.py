# -*- coding: utf-8 -*-
# NBA Live 06 EBO FLOAT SEQUENCE COMPARISON V10 - READ ONLY
# Rhino 6 / IronPython 2.7
# Select two EBO files. Compares complete float sequences and trailing byte streams.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def byte_at(d,i):
    return int(d[i])

def u32(d,o):
    return struct.unpack('<I',''.join(chr(byte_at(d,o+i)) for i in range(4)))[0]

def f32(d,o):
    return struct.unpack('<f',''.join(chr(byte_at(d,o+i)) for i in range(4)))[0]

def float_list(d,start,end):
    n=(end-start)//4
    return [f32(d,start+i*4) for i in range(n)]

def same_float(a,b):
    return struct.pack('<f',a)==struct.pack('<f',b)

def compare_seq(name,a,b):
    n=min(len(a),len(b))
    same=0
    prefix=0
    prefix_open=True
    first=[]
    for i in range(n):
        eq=same_float(a[i],b[i])
        if eq: same+=1
        if prefix_open and eq:
            prefix+=1
        else:
            prefix_open=False
        if not eq and len(first)<12:
            first.append((i,a[i],b[i]))
    print('')
    print('-- %s FLOAT SEQUENCE --' % name)
    print('A_COUNT=%d B_COUNT=%d COMMON_INDEX_COUNT=%d' % (len(a),len(b),n))
    print('EXACT_EQUAL_AT_SAME_INDEX=%d / %d (%.2f%%)' % (same,n,(100.0*same/n if n else 0)))
    print('EXACT_COMMON_PREFIX=%d floats' % prefix)
    print('FIRST_DIFFERENCES:')
    for i,x,y in first:
        print('  index %d: A=%.10g B=%.10g' % (i,x,y))
    if not first:
        print('  none in common range')

def inspect_pair(pa,pb):
    da=File.ReadAllBytes(pa)
    db=File.ReadAllBytes(pb)
    print('')
    print('='*78)
    print('A: %s (%d bytes)' % (str(pa),len(da)))
    print('B: %s (%d bytes)' % (str(pb),len(db)))
    if len(da)<0x1B4 or len(db)<0x1B4:
        print('ERROR: one file is too short')
        return
    # Block A starts at 0x148 pointer and ends at 0x14C pointer.
    # Block B starts at 0x170 pointer and ends at 0x174 pointer.
    ranges=[]
    for label,so,eo in [('BLOCK_A',0x148,0x14C),('BLOCK_B',0x170,0x174)]:
        sa=u32(da,so); ea=u32(da,eo)
        sb=u32(db,so); eb=u32(db,eo)
        print('')
        print('%s A_RANGE=0x%X..0x%X B_RANGE=0x%X..0x%X' % (label,sa,ea,sb,eb))
        if ea<sa or eb<sb or ea>len(da) or eb>len(db):
            print('INVALID RANGE')
            continue
        # Exclude final 4-byte length field from float sequence.
        fa_end=ea-4
        fb_end=eb-4
        if fa_end>=sa and fb_end>=sb:
            aa=float_list(da,sa,fa_end)
            bb=float_list(db,sb,fb_end)
            compare_seq(label,aa,bb)
        print('TRAILER_LENGTH_A=%d (0x%X) TRAILER_LENGTH_B=%d (0x%X)' %
              (u32(da,ea-4),u32(da,ea-4),u32(db,eb-4),u32(db,eb-4)))
        print('FOLLOWING_PAYLOAD_A_START=0x%X' % ea)
        print('FOLLOWING_PAYLOAD_B_START=0x%X' % eb)
        print('PAYLOAD_A_FIRST32=%s' % ' '.join('%02X'%byte_at(da,i) for i in range(ea,min(ea+32,len(da)))))
        print('PAYLOAD_B_FIRST32=%s' % ' '.join('%02X'%byte_at(db,i) for i in range(eb,min(eb+32,len(db)))))
        ranges.append((label,sa,ea,sb,eb))
    print('')
    print('V10 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
    print('='*78)

def main():
    d=OpenFileDialog()
    d.Title='Select exactly two NBA Live 06 EBO files'
    d.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    d.Multiselect=True
    if d.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    if len(d.FileNames)!=2:
        print('Please select exactly two EBO files.')
        return
    inspect_pair(d.FileNames[0],d.FileNames[1])

if __name__=='__main__':
    main()
