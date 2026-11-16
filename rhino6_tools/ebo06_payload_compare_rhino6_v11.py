# -*- coding: utf-8 -*-
# NBA Live 06 EBO PAYLOAD COMPARISON V11 - READ ONLY
# Rhino 6 / IronPython 2.7
# Select two EBO files. Compares complete variable-length byte payloads.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def bv(d,i):
    return int(d[i])

def u32(d,o):
    return struct.unpack('<I',''.join(chr(bv(d,o+i)) for i in range(4)))[0]

def f32(d,o):
    return struct.unpack('<f',''.join(chr(bv(d,o+i)) for i in range(4)))[0]

def raw_bytes(d,s,e):
    return [bv(d,i) for i in range(s,e)]

def longest_prefix(a,b):
    n=min(len(a),len(b))
    i=0
    while i<n and a[i]==b[i]:
        i+=1
    return i

def longest_suffix(a,b):
    n=min(len(a),len(b))
    i=0
    while i<n and a[len(a)-1-i]==b[len(b)-1-i]:
        i+=1
    return i

def compare_bytes(label,a,b):
    n=min(len(a),len(b))
    eq=0
    first=[]
    for i in range(n):
        if a[i]==b[i]:
            eq+=1
        elif len(first)<20:
            first.append((i,a[i],b[i]))
    p=longest_prefix(a,b)
    s=longest_suffix(a,b)
    print('')
    print('-- %s --' % label)
    print('A_BYTES=%d B_BYTES=%d COMMON_LENGTH=%d' % (len(a),len(b),n))
    print('SAME_BYTE_AT_SAME_OFFSET=%d/%d (%.2f%%)' % (eq,n,(100.0*eq/n if n else 0)))
    print('IDENTICAL_PREFIX=%d bytes IDENTICAL_SUFFIX=%d bytes' % (p,s))
    print('FIRST_DIFFERENCES:')
    for x,y,z in first:
        print('  +0x%X: A=%02X B=%02X' % (x,y,z))
    if not first:
        print('  none')
    print('A_FIRST64: %s' % ' '.join('%02X'%x for x in a[:64]))
    print('B_FIRST64: %s' % ' '.join('%02X'%x for x in b[:64]))
    print('A_LAST32 : %s' % ' '.join('%02X'%x for x in a[-32:]))
    print('B_LAST32 : %s' % ' '.join('%02X'%x for x in b[-32:]))
    # 16-bit interpretation is diagnostic only, not an asserted format.
    if len(a)>=2 and len(b)>=2:
        wa=[a[i] | (a[i+1]<<8) for i in range(0,len(a)-1,2)]
        wb=[b[i] | (b[i+1]<<8) for i in range(0,len(b)-1,2)]
        wn=min(len(wa),len(wb))
        we=sum(1 for i in range(wn) if wa[i]==wb[i])
        print('AS_U16_DIAGNOSTIC: A=%d words B=%d words same_index=%d/%d' % (len(wa),len(wb),we,wn))

def compare_float(label,da,sa,ea,db,sb,eb):
    na=(ea-sa)//4
    nb=(eb-sb)//4
    n=min(na,nb)
    eq=0
    first=[]
    for i in range(n):
        aa=f32(da,sa+i*4)
        bb=f32(db,sb+i*4)
        if struct.pack('<f',aa)==struct.pack('<f',bb):
            eq+=1
        elif len(first)<16:
            first.append((i,aa,bb))
    print('')
    print('-- %s FLOATS --' % label)
    print('A=%d B=%d SAME_INDEX_EXACT=%d/%d (%.2f%%)' % (na,nb,eq,n,(100.0*eq/n if n else 0)))
    print('FIRST_DIFFERENCES:')
    for i,a,b in first:
        print('  %d: %.10g / %.10g' % (i,a,b))

def inspect(pa,pb):
    da=File.ReadAllBytes(pa)
    db=File.ReadAllBytes(pb)
    print('')
    print('='*78)
    print('A: %s (%d)' % (str(pa),len(da)))
    print('B: %s (%d)' % (str(pb),len(db)))
    if len(da)<0x1B4 or len(db)<0x1B4:
        print('ERROR: file too short')
        return

    # Float payloads, excluding the 4-byte length immediately after each block.
    a0=u32(da,0x148); a1=u32(da,0x14C)
    b0=u32(db,0x148); b1=u32(db,0x14C)
    c0=u32(da,0x170); c1=u32(da,0x174)
    d0=u32(db,0x170); d1=u32(db,0x174)

    compare_float('BLOCK_A_FLOATS',da,a0,a1-4,db,b0,b1-4)
    compare_float('BLOCK_B_FLOATS',da,c0,c1-4,db,d0,d1-4)

    # The length DWORD is at end-4; the payload starts at end.
    la=u32(da,a1-4); lb=u32(db,b1-4)
    pa0=a1; pb0=b1
    compare_bytes('BLOCK_A_BYTE_PAYLOAD',raw_bytes(da,pa0,min(pa0+la,len(da))),raw_bytes(db,pb0,min(pb0+lb,len(db))))

    lc=u32(da,c1-4); ld=u32(db,d1-4)
    pc0=c1; pd0=d1
    compare_bytes('BLOCK_B_BYTE_PAYLOAD',raw_bytes(da,pc0,min(pc0+lc,len(da))),raw_bytes(db,pd0,min(pd0+ld,len(db))))

    print('')
    print('V11 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
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
    inspect(d.FileNames[0],d.FileNames[1])

if __name__=='__main__':
    main()
