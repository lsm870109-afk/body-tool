# -*- coding: utf-8 -*-
# NBA Live 06 HEAD MESH RESTORE V16.1
# Rhino 6 / IronPython 2.7
# READ ONLY diagnostic. Reuses the exact V15-verified head-map parser.
# Does NOT guess topology or modify the source EBO.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import Rhino
import scriptcontext as sc
import math
import System

def bval(d,o):
    return int(d[o])

def u16(d,o):
    return bval(d,o) | (bval(d,o+1)<<8)

def u32(d,o):
    return (bval(d,o) | (bval(d,o+1)<<8) |
            (bval(d,o+2)<<16) | (bval(d,o+3)<<24))

def f32(d,o):
    return float(BitConverter.ToSingle(d,o))

def chunk_ranges(d):
    p=u32(d,0x10)
    count=u16(d,0x24)
    out=[]
    for i in range(count):
        if p+0x14>len(d): break
        size=u32(d,p+0x10)
        if size<0x14 or p+size>len(d): break
        out.append((p,p+size))
        p+=size
    return out

def owner_start(ranges,off):
    for s,e in ranges:
        if s<=off<e: return s
    return -1

# This is copied in logic from the successful V15 parser.
def validate_mapping_record(d,off,ranges):
    if off<0 or off+24>len(d): return None
    logical=u32(d,off)
    one=u32(d,off+4)
    rendered=u32(d,off+8)
    pos=u32(d,off+12)
    mp=u32(d,off+16)
    vb=u32(d,off+20)
    if logical!=573 or one!=1 or rendered<3 or rendered>5000: return None
    if mp>len(d)-rendered*2 or pos>len(d)-rendered*12 or vb+12>len(d): return None
    if u32(d,vb+4)!=12 or u32(d,vb)!=rendered*12 or u32(d,vb+8)!=pos: return None
    vals=[u16(d,mp+i*2) for i in range(rendered)]
    if min(vals)!=0 or max(vals)!=572 or len(set(vals))!=573: return None
    return (off,logical,rendered,pos,mp,owner_start(ranges,off),vals)

def find_head_mapping(d):
    ranges=chunk_ranges(d)
    found=[]
    # V15 success confirmed this exact record and data in base_lodB.ebo.
    item=validate_mapping_record(d,0x102B8,ranges)
    if item is not None:
        found.append(item)
    # Scan only if the verified fixed record did not validate.
    if not found:
        for off in range(0,len(d)-24,4):
            item=validate_mapping_record(d,off,ranges)
            if item is not None: found.append(item)
    if len(found)!=1:
        # Print raw fields to distinguish wrong file from parser regression.
        off=0x102B8
        if off+24<=len(d):
            print('MAP_DIAGNOSTIC_AT_0x102B8 logical=%d one=%d rendered=%d pos=0x%X map=0x%X vb=0x%X' %
                  (u32(d,off),u32(d,off+4),u32(d,off+8),u32(d,off+12),u32(d,off+16),u32(d,off+20)))
        raise ValueError('V15-compatible head map validation failed; matches=%d; size=%d' % (len(found),len(d)))
    return found[0]

# Conservative scan only: report index-buffer candidates; do not assume a
# candidate is the actual head topology merely because its values look valid.
def find_index_buffers(d,rendered):
    found=[]
    for off in range(0,len(d)-12,4):
        size=u32(d,off)
        stride=u32(d,off+4)
        ptr=u32(d,off+8)
        if stride!=2 or size<6 or size%2: continue
        if ptr>len(d)-size: continue
        count=size//2
        if count<rendered or count>200000: continue
        vals=[u16(d,ptr+i*2) for i in range(count)]
        if max(vals)!=rendered-1 or len(set(vals))!=rendered: continue
        found.append((off,ptr,size,vals))
    return found

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select the same base_lodB.ebo used successfully in V15'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=False
    if dlg.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    path=dlg.FileName
    d=File.ReadAllBytes(path)
    if len(d)<0x60 or bval(d,0)!=69 or bval(d,1)!=66 or bval(d,2)!=79 or bval(d,3)!=0:
        print('ERROR: invalid EBO file')
        return

    record,logical,rendered,posptr,mapptr,owner,mapping=find_head_mapping(d)
    positions=[]
    for i in range(rendered):
        x=f32(d,posptr+i*12)
        y=f32(d,posptr+i*12+4)
        z=f32(d,posptr+i*12+8)
        if (math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y) or
            math.isnan(z) or math.isinf(z)):
            raise ValueError('Non-finite vertex position at %d' % i)
        positions.append((x,y,z))

    candidates=find_index_buffers(d,rendered)
    print('')
    print('='*76)
    print('V16.1 HEAD INDEX / MESH RESTORE DIAGNOSTIC')
    print('SOURCE=%s' % path)
    print('HEAD_CHUNK=0x%X MAP_RECORD=0x%X' % (owner,record))
    print('LOGICAL_VERTICES=%d RENDERED_VERTICES=%d' % (logical,rendered))
    print('POSITIONS=%d POSITION_BUFFER=0x%X MAP_BUFFER=0x%X' % (len(positions),posptr,mapptr))
    print('INDEX_BUFFER_CANDIDATES=%d' % len(candidates))
    for i,item in enumerate(candidates):
        off,ptr,size,vals=item
        print('CANDIDATE[%d] HEADER=0x%X DATA=0x%X BYTES=%d INDICES=%d MIN=%d MAX=%d UNIQUE=%d' %
              (i,off,ptr,size,len(vals),min(vals),max(vals),len(set(vals))))
    print('TOPOLOGY_STATUS=DIAGNOSTIC_ONLY')
    print('No mesh created: an index candidate must be matched to the EBO geometry metadata before use.')
    print('EBO_SOURCE_MODIFIED=NO')
    print('='*76)

if __name__=='__main__':
    main()
