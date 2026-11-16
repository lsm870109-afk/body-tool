# -*- coding: utf-8 -*-
# NBA Live 06 BASE MORPH MAP PROBE V13
# Rhino 6 / IronPython 2.7
# READ ONLY. Select base_lodB.ebo only.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def bval(d, o):
    return int(d[o])

def u16(d, o):
    return bval(d,o) | (bval(d,o+1) << 8)

def u32(d, o):
    return (bval(d,o) | (bval(d,o+1) << 8) |
            (bval(d,o+2) << 16) | (bval(d,o+3) << 24))

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

def geometry_names(d):
    strings=u32(d,0x20)
    exports=u32(d,0x1C)
    count=u16(d,0x2A)
    out={}
    for i in range(count):
        p=exports+i*12
        if p+12 > len(d):
            break
        tr=u32(d,p)
        nr=u32(d,p+4)
        dr=u32(d,p+8)
        try:
            typ=cstr(d,strings+tr)
            name=cstr(d,strings+nr)
        except:
            continue
        if typ == 'Geometry':
            target=p+dr
            own=owner_start(chunk_ranges(d),target)
            out.setdefault(own,[]).append(name)
    return out

def scan_maps(d, ranges):
    found=[]
    for off in range(0,len(d)-24,4):
        logical=u32(d,off)
        one=u32(d,off+4)
        rendered=u32(d,off+8)
        posptr=u32(d,off+12)
        mapptr=u32(d,off+16)
        vb=u32(d,off+20)
        if one != 1 or logical < 16 or rendered < 3:
            continue
        if logical > 100000 or rendered > 100000:
            continue
        if mapptr > len(d)-rendered*2:
            continue
        if posptr > len(d)-rendered*12:
            continue
        if vb+12 > len(d):
            continue
        vbsize=u32(d,vb)
        vbstride=u32(d,vb+4)
        vbptr=u32(d,vb+8)
        if vbstride != 12 or vbsize != rendered*12 or vbptr != posptr:
            continue
        vals=[]
        for j in range(rendered):
            vals.append(u16(d,mapptr+j*2))
        if not vals or max(vals) >= logical:
            continue
        own=owner_start(ranges,off)
        found.append({
            'off':off,'logical':logical,'rendered':rendered,
            'posptr':posptr,'mapptr':mapptr,'vb':vb,
            'owner':own,'mapping':vals
        })
    return found

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select base_lodB.ebo'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=False
    if dlg.ShowDialog() != DialogResult.OK:
        print('Cancelled.')
        return
    path=dlg.FileName
    d=File.ReadAllBytes(path)
    print('')
    print('='*76)
    print('FILE: %s' % path)
    print('SIZE=%d MAGIC=%02X %02X %02X %02X VERSION=%d' %
          (len(d),bval(d,0),bval(d,1),bval(d,2),bval(d,3),u32(d,4)))
    if len(d)<0x60 or bval(d,0)!=69 or bval(d,1)!=66 or bval(d,2)!=79 or bval(d,3)!=0:
        print('ERROR: unsupported EBO file')
        return
    ranges=chunk_ranges(d)
    names=geometry_names(d)
    candidates=scan_maps(d,ranges)
    print('CHUNKS=%d MAP_CANDIDATES=%d' % (len(ranges),len(candidates)))
    groups={}
    for x in candidates:
        key=(x['owner'],x['logical'])
        groups.setdefault(key,[]).append(x)
    complete=[]
    for key,segs in groups.items():
        union=set()
        for seg in segs:
            union.update(seg['mapping'])
        if len(union)==key[1] and min(union)==0 and max(union)==key[1]-1:
            complete.append((key,segs,union))
    print('COMPLETE_MAPPING_GROUPS=%d' % len(complete))
    ranked=[]
    for key,segs,union in complete:
        chunk_name=','.join(names.get(key[0],[]))
        total=sum(x['rendered'] for x in segs)
        role=3 if 'head' in chunk_name.lower() else (1 if 'baseplyr' in chunk_name.lower() else 0)
        ranked.append((role,key[1],total,key,segs,chunk_name))
    ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
    for idx,item in enumerate(ranked):
        role,logical,total,key,segs,chunk_name=item
        print('')
        print('GROUP[%d] GEOMETRY=%s CHUNK=0x%X LOGICAL=%d RENDERED=%d SEGMENTS=%d' %
              (idx,chunk_name,key[0],logical,total,len(segs)))
        for si,x in enumerate(segs):
            vals=x['mapping']
            print('  SEG[%d] RECORD=0x%X RENDERED=%d POS=0x%X MAP=0x%X VB=0x%X MAP_MIN=%d MAP_MAX=%d UNIQUE=%d' %
                  (si,x['off'],x['rendered'],x['posptr'],x['mapptr'],x['vb'],min(vals),max(vals),len(set(vals))))
        if idx==0:
            ordered=[]
            for x in segs:
                ordered.extend(x['mapping'])
            print('  SELECTED_TOTAL_RENDERED=%d UNIQUE_LOGICAL=%d' % (len(ordered),len(set(ordered))))
            print('  FIRST_40_MAP=' + ','.join(str(v) for v in ordered[:40]))
            print('  LAST_20_MAP=' + ','.join(str(v) for v in ordered[-20:]))
    if not ranked:
        print('NO COMPLETE MAPPING GROUP FOUND')
    print('')
    print('V13 COMPLETE. READ ONLY; SOURCE FILE NOT MODIFIED.')
    print('='*76)

if __name__ == '__main__':
    main()
