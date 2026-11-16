# -*- coding: utf-8 -*-
# NBA Live 06 MORPH APPLY VALIDATION V14
# Rhino 6 / IronPython 2.7
# READ ONLY. Select base_lodB.ebo, then player Morph EBO files.
# Verifies 573 logical deltas -> 733 rendered head vertices.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import math

def bval(d, o):
    return int(d[o])

def u16(d, o):
    return bval(d,o) | (bval(d,o+1) << 8)

def u32(d, o):
    return (bval(d,o) | (bval(d,o+1) << 8) |
            (bval(d,o+2) << 16) | (bval(d,o+3) << 24))

def f32(d, o):
    return float(BitConverter.ToSingle(d, o))

def cstr(d, o):
    if o < 0 or o >= len(d):
        raise ValueError('string offset outside file')
    chars=[]
    while o < len(d):
        v=bval(d,o)
        if v == 0:
            return ''.join(chars)
        chars.append(chr(v))
        o += 1
    raise ValueError('unterminated string')

def chunk_ranges(d):
    p=u32(d,0x10)
    count=u16(d,0x24)
    out=[]
    for i in range(count):
        if p+0x14 > len(d):
            break
        size=u32(d,p+0x10)
        if size < 0x14 or p+size > len(d):
            break
        out.append((p,p+size))
        p += size
    return out

def owner_start(ranges, off):
    for s,e in ranges:
        if s <= off < e:
            return s
    return -1

def find_head_mapping(d):
    ranges=chunk_ranges(d)
    found=[]
    for off in range(0,len(d)-24,4):
        logical=u32(d,off)
        one=u32(d,off+4)
        rendered=u32(d,off+8)
        pos=u32(d,off+12)
        mp=u32(d,off+16)
        vb=u32(d,off+20)
        if logical != 573 or one != 1 or rendered < 3 or rendered > 5000:
            continue
        if mp > len(d)-rendered*2 or pos > len(d)-rendered*12 or vb+12 > len(d):
            continue
        if u32(d,vb+4) != 12 or u32(d,vb) != rendered*12 or u32(d,vb+8) != pos:
            continue
        vals=[u16(d,mp+i*2) for i in range(rendered)]
        if min(vals) != 0 or max(vals) != 572 or len(set(vals)) != 573:
            continue
        found.append((off,logical,rendered,pos,mp,owner_start(ranges,off)))
    if len(found) != 1:
        raise ValueError('Expected exactly one 573-vertex head mapping; found %d' % len(found))
    return found[0]

def find_coord(d):
    strings=u32(d,0x20)
    chunk=u32(d,0x10)
    found=[]
    for off in range(chunk, min(len(d),chunk+1200)-40, 4):
        rel=u32(d,off)
        if rel >= 4096 or strings+rel >= len(d):
            continue
        try:
            name=cstr(d,strings+rel)
        except:
            continue
        if name != 'coord':
            continue
        fields=[u32(d,off+i*4) for i in range(10)]
        size,payload,aux=fields[3:6]
        if fields[2] != 0 or fields[6] != 1 or fields[7] != 0x3F800000:
            continue
        if fields[8] != 0 or fields[9] != 0:
            continue
        if payload > len(d) or size > len(d)-payload:
            continue
        if aux != 0:
            continue
        if size != 573*3*4:
            continue
        found.append((off,size,payload,aux))
    if len(found) != 1:
        raise ValueError('Expected one dense 573*3 coord stream; found %d' % len(found))
    return found[0]

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select base_lodB.ebo and player Morph EBO files'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=True
    if dlg.ShowDialog() != DialogResult.OK:
        print('Cancelled.')
        return
    paths=list(dlg.FileNames)
    base_path=None
    morph_paths=[]
    for p in paths:
        if p.lower().endswith('base_lodb.ebo'):
            base_path=p
        else:
            morph_paths.append(p)
    if base_path is None:
        print('ERROR: select base_lodB.ebo together with player Morph EBO files.')
        return
    if not morph_paths:
        print('ERROR: select at least one player Morph EBO file.')
        return

    base=File.ReadAllBytes(base_path)
    if len(base)<0x60 or bval(base,0)!=69 or bval(base,1)!=66 or bval(base,2)!=79:
        print('ERROR: invalid base EBO')
        return
    record,logical,rendered,posptr,mapptr,owner=find_head_mapping(base)
    mapping=[u16(base,mapptr+i*2) for i in range(rendered)]
    base_positions=[]
    for i in range(rendered*3):
        base_positions.append(f32(base,posptr+i*4))
    print('')
    print('='*76)
    print('BASE: %s' % base_path)
    print('HEAD_MAP_RECORD=0x%X CHUNK=0x%X LOGICAL=%d RENDERED=%d' %
          (record,owner,logical,rendered))
    print('POSITION_BUFFER=0x%X MAP_BUFFER=0x%X MAP_UNIQUE=%d RANGE=%d..%d' %
          (posptr,mapptr,len(set(mapping)),min(mapping),max(mapping)))
    print('BASE_POSITION_FLOATS=%d FINITE=%s' %
          (len(base_positions),str(not any(math.isnan(x) or math.isinf(x) for x in base_positions))))
    for path in morph_paths:
        try:
            d=File.ReadAllBytes(path)
            hoff,size,payload,aux=find_coord(d)
            delta=[f32(d,payload+i*4) for i in range(573*3)]
            finite=not any(math.isnan(x) or math.isinf(x) for x in delta)
            nonzero=sum(1 for x in delta if abs(x)>0.0000001)
            maxabs=max(abs(x) for x in delta)
            maxmove=0.0
            for ri in range(rendered):
                li=mapping[ri]
                for axis in range(3):
                    v=abs(delta[li*3+axis])
                    if v>maxmove:
                        maxmove=v
            print('')
            print('MORPH: %s' % path)
            print('COORD_HEADER=0x%X PAYLOAD=0x%X SIZE=%d AUX=%d' %
                  (hoff,payload,size,aux))
            print('LOGICAL_DELTAS=573 FLOATS=%d FINITE=%s NONZERO_FLOATS=%d MAX_ABS_DELTA=%.9g' %
                  (len(delta),str(finite),nonzero,maxabs))
            print('RENDERED_VERTICES_RECEIVING_DELTA=%d MAX_COMPONENT_MOVE=%.9g' %
                  (len(mapping),maxmove))
            if not finite:
                print('WARNING: non-finite delta detected')
            else:
                print('APPLY_CHECK=PASS (base position + logical_delta[render_to_logical])')
        except Exception as ex:
            print('')
            print('MORPH ERROR: %s' % path)
            print(str(ex))
    print('')
    print('V14 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
    print('='*76)

if __name__ == '__main__':
    main()
