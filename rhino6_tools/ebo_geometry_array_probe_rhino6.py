# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live 06 EBO v17 head Geometry array descriptor probe.
# READ ONLY: no EBO modification and no OBJ export.
#
# Confirmed from base_lodB.ebo report:
# Geometry object +0xB0/+0xB4/+0xBC/+0xC0 point to descriptors.
# Geometry object +0xC4 and +0xC8 are candidate vertex/index counts.
# This tool validates byte counts, strides, ranges and index interpretations.

import os
import struct
import rhinoscriptsyntax as rs

def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]

def f32(d, o):
    return struct.unpack_from('<f', d, o)[0]

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def dump_hex(d, off, size):
    end = min(len(d), off + size)
    p = off
    while p < end:
        q = min(p + 16, end)
        print('  %08X  %s' % (p, ' '.join('%02X' % ord(d[k]) for k in range(p, q))))
        p = q

def inspect_stream(d, label, desc, expected_count, expected_stride, as_float):
    print('')
    print('[%s STREAM]' % label)
    if desc <= 0 or desc + 12 > len(d):
        print('  descriptor out of range: 0x%X' % desc)
        return None
    byte_count = u32(d, desc)
    stride = u32(d, desc + 4)
    data_off = u32(d, desc + 8)
    print('  descriptor=0x%X bytes=%d (0x%X) stride=%d data=0x%X' %
          (desc, byte_count, byte_count, stride, data_off))
    if data_off + byte_count > len(d):
        print('  ERROR: data range exceeds file')
        return None
    if stride <= 0 or byte_count % stride != 0:
        print('  WARNING: byte_count is not divisible by stride')
    else:
        count = byte_count // stride
        print('  records=%d; expected_count=%d; expected_stride=%d' %
              (count, expected_count, expected_stride))
        print('  count_match=%s stride_match=%s' %
              (str(count == expected_count), str(stride == expected_stride)))
    if as_float and stride in (8, 12, 16):
        n = min(6, byte_count // stride)
        for i in range(n):
            vals = struct.unpack_from('<%df' % (stride // 4), d, data_off + i * stride)
            print('  [%d] %s' % (i, ' '.join('% .7g' % x for x in vals)))
    return (byte_count, stride, data_off)

def inspect_indices(d, desc, expected_count, vertex_count):
    print('')
    print('[INDEX STREAM CANDIDATE]')
    if desc <= 0 or desc + 16 > len(d):
        print('  descriptor out of range: 0x%X' % desc)
        return
    byte_count = u32(d, desc)
    kind = u32(d, desc + 4)
    data_off = u32(d, desc + 8)
    extra = u32(d, desc + 12)
    print('  descriptor=0x%X bytes=%d (0x%X) kind=%d data=0x%X extra=0x%X' %
          (desc, byte_count, byte_count, kind, data_off, extra))
    if data_off + byte_count > len(d):
        print('  ERROR: data range exceeds file')
        return
    available = byte_count // 2
    print('  uint16_available=%d expected_index_count=%d expected_bytes=%d' %
          (available, expected_count, expected_count * 2))
    print('  byte_difference=%d' % (byte_count - expected_count * 2))
    for skip in (0, 2, 4):
        start = data_off + skip
        n = min(expected_count, (data_off + byte_count - start) // 2)
        if n <= 0:
            continue
        vals = list(struct.unpack_from('<%dH' % n, d, start))
        valid = [v for v in vals if v < vertex_count]
        bad = len(vals) - len(valid)
        print('  interpretation start=0x%X skip=%d count=%d min=%d max=%d unique=%d out_of_range=%d' %
              (start, skip, n, min(vals), max(vals), len(set(vals)), bad))
        print('    first 48: %s' % ' '.join(str(v) for v in vals[:48]))
        print('    last 16:  %s' % ' '.join(str(v) for v in vals[-16:]))
        if n % 3 == 0:
            print('    triangle_triplets=%d' % (n // 3))
            degenerate = 0
            for i in range(0, n - 2, 3):
                if vals[i] == vals[i+1] or vals[i] == vals[i+2] or vals[i+1] == vals[i+2]:
                    degenerate += 1
            print('    degenerate_triplets=%d' % degenerate)
    tail_start = data_off + expected_count * 2
    if tail_start < data_off + byte_count:
        print('  trailing bytes after expected indices:')
        dump_hex(d, tail_start, min(16, data_off + byte_count - tail_start))

def main():
    path = rs.OpenFileName('Select NBA Live 06 base Geometry EBO',
                           'EBO files (*.ebo)|*.ebo||')
    if not path:
        print('Cancelled.')
        return
    try:
        d = read_file(path)
        print('')
        print('===== NBA LIVE 06 GEOMETRY ARRAY PROBE =====')
        print('File: %s (%d bytes / 0x%X)' % (os.path.basename(path), len(d), len(d)))
        if len(d) < 0x60 or d[:4] != 'EBO\x00':
            print('Not a recognized EBO file.')
            return
        export_off = u32(d, 28)
        strings_off = u32(d, 32)
        export_count = struct.unpack_from('<H', d, 42)[0]
        found = None
        for i in range(export_count):
            p = export_off + i * 12
            if p + 12 > len(d):
                break
            type_rel, name_rel, data_rel = struct.unpack_from('<IIi', d, p)
            def getstr(off):
                q = strings_off + off
                e = d.find('\x00', q)
                if e < 0:
                    return ''
                return d[q:e].decode('ascii', 'replace')
            typ = getstr(type_rel)
            name = getstr(name_rel)
            target = p + data_rel
            if typ == 'Geometry' and name.lower() == 'headashape':
                found = (name, target)
                break
        if found is None:
            print('No Geometry export named headAShape found. Do not use a Morph EBO.')
            return
        name, obj = found
        if obj + 0x100 > len(d):
            print('Geometry object header truncated.')
            return
        vertex_count = u32(d, obj + 0xC4)
        index_count = u32(d, obj + 0xC8)
        print('Geometry: %s @ 0x%X' % (name, obj))
        print('Candidate vertex_count=%d index_count=%d' % (vertex_count, index_count))
        print('Descriptor pointers: pos=0x%X normal=0x%X uv=0x%X index=0x%X' %
              (u32(d, obj + 0xB0), u32(d, obj + 0xB4),
               u32(d, obj + 0xBC), u32(d, obj + 0xC0)))
        pos = inspect_stream(d, 'POSITION', u32(d, obj + 0xB0),
                             vertex_count, 12, True)
        normal = inspect_stream(d, 'NORMAL', u32(d, obj + 0xB4),
                                 vertex_count, 12, True)
        uv = inspect_stream(d, 'UV', u32(d, obj + 0xBC),
                            vertex_count, 8, True)
        inspect_indices(d, u32(d, obj + 0xC0), index_count, vertex_count)
        print('')
        print('[SUMMARY]')
        print('  Position/normal/UV record counts matching vertex_count is strong structural evidence.')
        print('  Index interpretation remains provisional until topology is checked in Rhino.')
        print('  No OBJ was written; source EBO was opened read-only.')
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
