# -*- coding: utf-8 -*-
# NBA Live 06 EBO MORPH HEADER PROBE V12
# Rhino 6 / IronPython 2.7
# READ ONLY. Select base_lodB.ebo and one or more player B EBO files.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def byte_value(d, o):
    return int(d[o])

def u16(d, o):
    return byte_value(d, o) | (byte_value(d, o + 1) << 8)

def u32(d, o):
    return (byte_value(d, o) |
            (byte_value(d, o + 1) << 8) |
            (byte_value(d, o + 2) << 16) |
            (byte_value(d, o + 3) << 24))

def i32(d, o):
    v = u32(d, o)
    if v >= 0x80000000:
        v -= 0x100000000
    return v

def cstr(d, o):
    if o < 0 or o >= len(d):
        raise ValueError('string offset outside file')
    chars = []
    p = o
    while p < len(d):
        v = byte_value(d, p)
        if v == 0:
            return ''.join(chars)
        chars.append(chr(v))
        p += 1
    raise ValueError('unterminated string')

def chunk_ranges(d):
    start = u32(d, 0x10)
    count = u16(d, 0x24)
    out = []
    p = start
    for i in range(count):
        if p + 0x14 > len(d):
            break
        size = u32(d, p + 0x10)
        if size < 0x14 or p + size > len(d):
            break
        out.append((p, p + size))
        p += size
    return out

def owning_chunk(ranges, off):
    for s, e in ranges:
        if s <= off < e:
            return (s, e)
    return None

def read_exports(d, ranges):
    strings = u32(d, 0x20)
    exports = u32(d, 0x1C)
    count = u16(d, 0x2A)
    out = []
    for i in range(count):
        p = exports + i * 12
        if p + 12 > len(d):
            break
        tr = u32(d, p)
        nr = u32(d, p + 4)
        dr = i32(d, p + 8)
        try:
            typ = cstr(d, strings + tr)
            name = cstr(d, strings + nr)
        except:
            continue
        target = p + dr
        owner = owning_chunk(ranges, target)
        out.append((typ, name, p, target, owner))
    return out

def scan_coord_headers(d, start, end):
    strings = u32(d, 0x20)
    found = []
    p = start
    while p + 40 <= end:
        rel = u32(d, p)
        if rel < 0x10000 and strings + rel < len(d):
            try:
                name = cstr(d, strings + rel)
            except:
                name = ''
            if name == 'coord':
                fields = tuple(u32(d, p + j * 4) for j in range(10))
                size, payload, aux = fields[3], fields[4], fields[5]
                valid = (payload <= len(d) and size <= len(d) - payload)
                if fields[6] == 1 and fields[7] == 0x3F800000 and valid:
                    found.append((p, fields))
        p += 4
    return found

def dump_file(path):
    d = File.ReadAllBytes(path)
    print('')
    print('=' * 78)
    print('FILE: %s' % str(path))
    print('SIZE=%d MAGIC=%s VERSION=%d' % (len(d), ' '.join('%02X'%byte_value(d,i) for i in range(4)), u32(d,4)))
    if len(d) < 0x60 or not (byte_value(d,0) == 69 and byte_value(d,1) == 66 and byte_value(d,2) == 79 and byte_value(d,3) == 0):
        print('ERROR: not a supported EBO v17 container')
        return
    print('CHUNKS_OFFSET=0x%X USD=0x%X IMPORTS=0x%X EXPORTS=0x%X STRINGS=0x%X' %
          (u32(d,0x10),u32(d,0x14),u32(d,0x18),u32(d,0x1C),u32(d,0x20)))
    ranges = chunk_ranges(d)
    print('CHUNK_COUNT=%d' % len(ranges))
    for i, (s,e) in enumerate(ranges):
        print('  CHUNK[%d] 0x%X..0x%X SIZE=%d' % (i,s,e,e-s))

    exports = read_exports(d, ranges)
    morphs = [x for x in exports if x[0] == 'Morph']
    geos = [x for x in exports if x[0] == 'Geometry']
    print('EXPORTS: Geometry=%d Morph=%d' % (len(geos),len(morphs)))
    for typ,name,p,target,owner in geos:
        if owner:
            print('  GEO %s export=0x%X target=0x%X chunk=0x%X..0x%X' %
                  (name,p,target,owner[0],owner[1]))
    for typ,name,p,target,owner in morphs:
        if not owner:
            print('  MORPH %s export=0x%X target=0x%X OWNER=NOT_FOUND' % (name,p,target))
            continue
        s,e=owner
        print('')
        print('  MORPH %s export=0x%X target=0x%X chunk=0x%X..0x%X' %
              (name,p,target,s,e))
        headers=scan_coord_headers(d,s,e)
        print('    COORD_HEADERS=%d' % len(headers))
        for h,fields in headers:
            size,payload,aux=fields[3],fields[4],fields[5]
            print('    HEADER=0x%X' % h)
            print('    FIELDS=' + ' '.join('0x%08X'%v for v in fields))
            print('    SIZE=%d (0x%X) PAYLOAD=0x%X AUX=0x%X' % (size,size,payload,aux))
            print('    PAYLOAD_END=0x%X' % (payload+size))
            if aux:
                if aux >= 4 and aux <= len(d):
                    n=u32(d,aux-4)
                    print('    AUX_MINUS_4_DWORD=%d (0x%X)' % (n,n))
                    if aux+n <= len(d):
                        print('    AUX_BYTES_FIRST32=' + ' '.join('%02X'%byte_value(d,j) for j in range(aux,aux+min(32,n))))
            if size <= 100000 and payload+size <= len(d):
                print('    PAYLOAD_FIRST32=' + ' '.join('%02X'%byte_value(d,j) for j in range(payload,payload+min(32,size))))
                print('    PAYLOAD_LAST16 =' + ' '.join('%02X'%byte_value(d,j) for j in range(max(payload,payload+size-16),payload+size)))
            if aux == 0:
                print('    CLASSIFICATION=DENSE_CANDIDATE')
            else:
                print('    CLASSIFICATION=SPARSE_OR_AUX_STREAM_CANDIDATE')
    if not morphs:
        print('  No Morph exports in this file.')
    print('=' * 78)

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select base_lodB.ebo and player B EBO file(s)'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=True
    if dlg.ShowDialog() != DialogResult.OK:
        print('Cancelled.')
        return
    if len(dlg.FileNames) < 2:
        print('Select at least two files: base_lodB.ebo plus player EBO(s).')
        return
    for p in dlg.FileNames:
        dump_file(p)
    print('')
    print('V12 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')

if __name__ == '__main__':
    main()
