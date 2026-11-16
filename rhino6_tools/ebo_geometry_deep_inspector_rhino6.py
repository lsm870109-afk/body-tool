# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live 06 EBO v17 Geometry deep diagnostic (READ ONLY)
# Focus: locate and characterize headAShape data without guessing its semantics.
# This script does NOT modify the source EBO and does NOT export an OBJ yet.

import os
import struct
import rhinoscriptsyntax as rs

def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]

def i32(d, o):
    return struct.unpack_from('<i', d, o)[0]

def f32(d, o):
    return struct.unpack_from('<f', d, o)[0]

def hx(d, o, n):
    end = min(o + n, len(d))
    p = o
    while p < end:
        q = min(p + 16, end)
        print('  %08X  %s' % (p, ' '.join('%02X' % ord(d[k]) for k in range(p, q))))
        p = q

def cstr(d, o):
    if o < 0 or o >= len(d):
        return '<OUT_OF_RANGE>'
    e = d.find('\x00', o)
    if e < 0:
        return '<NO_TERMINATOR>'
    return d[o:e].decode('ascii', 'replace')

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def plausible_float(v):
    return (v == v and abs(v) < 1.0e7)

def print_float_window(d, off, size, max_rows=24):
    end = min(off + size, len(d))
    if off < 0 or off + 4 > end:
        return
    count = (end - off) // 4
    shown = min(count, max_rows * 4)
    vals = struct.unpack_from('<%df' % shown, d, off)
    print('  float32 view (%d values; first %d shown):' % (count, shown))
    for i in range(0, shown, 4):
        row = vals[i:i+4]
        print('    +0x%04X: %s' % (i*4, ' '.join('% .7g' % x for x in row)))

def scan_float_runs(d, start, end, min_values=12):
    # Report long contiguous runs of finite, moderate float32 values.
    runs = []
    p = start
    run_start = None
    run_count = 0
    while p + 4 <= end:
        v = f32(d, p)
        good = plausible_float(v)
        if good:
            if run_start is None:
                run_start = p
                run_count = 0
            run_count += 1
        else:
            if run_start is not None and run_count >= min_values:
                runs.append((run_start, run_count))
            run_start = None
            run_count = 0
        p += 4
    if run_start is not None and run_count >= min_values:
        runs.append((run_start, run_count))
    # Merge adjacent runs separated by a single non-float word is intentionally avoided.
    print('')
    print('[LONG FLOAT32 CANDIDATE RUNS]')
    if not runs:
        print('  No long runs found with current conservative filter.')
    for off, count in runs[:80]:
        vals = struct.unpack_from('<%df' % count, d, off)
        mn, mx = min(vals), max(vals)
        print('  0x%X  values=%d bytes=0x%X range=[%.6g, %.6g]' %
              (off, count, count*4, mn, mx))
    if len(runs) > 80:
        print('  ... %d additional runs omitted' % (len(runs)-80))

def parse_exports(d):
    # EBO v17 header offsets established from the supplied base_lodB.ebo inspection.
    if len(d) < 0x60 or d[:4] != 'EBO\x00':
        print('Not a recognized EBO v17 header.')
        return None
    version = u32(d, 4)
    declared = u32(d, 8)
    chunk = u32(d, 16)
    export_off = u32(d, 28)
    strings_off = u32(d, 32)
    export_count = u16(d, 42)
    print('[EBO HEADER]')
    print('  version=%d declared_size=0x%X actual_size=0x%X' % (version, declared, len(d)))
    print('  chunk=0x%X exports=0x%X count=%d strings=0x%X' %
          (chunk, export_off, export_count, strings_off))
    if version != 17:
        print('  WARNING: expected v17; continuing with cautious export parsing.')
    if export_off >= len(d) or strings_off >= len(d):
        print('  Header offsets outside file; stop.')
        return None
    exports = []
    print('')
    print('[EXPORT TABLE]')
    for i in range(export_count):
        p = export_off + i * 12
        if p + 12 > len(d):
            print('  Export table truncated at entry %d.' % i)
            break
        type_rel, name_rel, data_rel = struct.unpack_from('<IIi', d, p)
        typ = cstr(d, strings_off + type_rel)
        name = cstr(d, strings_off + name_rel)
        target = p + data_rel
        valid = (0 <= target < len(d))
        print('  %02d type=%s name=%s target=0x%X %s' %
              (i, typ, name, target, 'OK' if valid else 'OUT_OF_RANGE'))
        exports.append((typ, name, target))
    return exports

def inspect_geometry(d, target, name):
    print('')
    print('===== GEOMETRY OBJECT: %s @ 0x%X =====' % (name, target))
    if target < 0 or target + 0x100 > len(d):
        print('Object header is outside file or truncated.')
        return
    print('[RAW OBJECT HEADER: 0x100 bytes]')
    hx(d, target, 0x100)
    print('')
    print('[32-BIT WORD MAP]')
    print('  Relative offset | uint32 | int32 | float32 | pointer-in-file?')
    for rel in range(0, 0x100, 4):
        p = target + rel
        uv = u32(d, p)
        iv = i32(d, p)
        fv = f32(d, p)
        ptr = ('YES' if 0 < uv < len(d) else '')
        print('  +0x%03X          0x%08X %11d % .7g %s' % (rel, uv, iv, fv, ptr))
    print('')
    print('[KNOWN / CANDIDATE FIELDS]')
    # These are observed offsets from one inspected headAShape sample.
    # Values are printed as raw fields, not asserted to be vertex counts.
    for rel in (0x00,0x10,0x18,0x3C,0x44,0x7C,0x98,0xA0,0xA8,
                0xB0,0xB4,0xB8,0xBC,0xC0,0xC4,0xC8,0xD0,0xD4,
                0xD8,0xDC,0xE0,0xE4,0xE8,0xEC,0xF0,0xFC):
        p = target + rel
        if p + 4 > len(d):
            continue
        v = u32(d, p)
        extra = ''
        if rel in (0x00,0x10,0xD8,0xE0,0xE4):
            extra = ' string=' + cstr(d, strings_base + v) if 'strings_base' in globals() else ''
        print('  +0x%03X = 0x%08X (%u)%s' % (rel, v, v, extra))
    # Inspect every distinct pointer-looking value in the header, plus known targets.
    candidates = []
    for rel in range(0, 0x100, 4):
        v = u32(d, target + rel)
        if target < v < len(d) and v not in candidates:
            candidates.append(v)
    print('')
    print('[POINTER TARGET PREVIEWS]')
    for off in candidates[:36]:
        print('  target 0x%X:' % off)
        hx(d, off, 48)
    print('')
    print('[KNOWN HEAD SHAPE CANDIDATE OFFSETS]')
    for off in (0xC8D4, 0xC91C, 0xEB94, 0x1029C, 0x10330,
                0x10340, 0x10D60, 0x113A0, 0x13618, 0x145E8, 0x14608):
        if off >= len(d):
            continue
        print('  @0x%X:' % off)
        hx(d, off, 64)
        print_float_window(d, off, 64, 4)

def main():
    path = rs.OpenFileName('Select NBA Live 06 base Geometry EBO',
                           'EBO files (*.ebo)|*.ebo||')
    if not path:
        print('Cancelled.')
        return
    try:
        d = read_file(path)
        print('')
        print('===== NBA LIVE 06 GEOMETRY DEEP INSPECTOR =====')
        print('File: %s (%d bytes / 0x%X)' % (os.path.basename(path), len(d), len(d)))
        exports = parse_exports(d)
        if exports is None:
            return
        found = []
        for typ, name, target in exports:
            if name.lower() == 'headashape' or ('head' in name.lower() and 'shape' in name.lower()):
                found.append((name, target))
        if not found:
            print('')
            print('No head*Shape export found. Available exports are listed above.')
        for name, target in found:
            inspect_geometry(d, target, name)
        # Scan the region beginning at the first head geometry through the file end.
        if found:
            first = min(x[1] for x in found)
            scan_float_runs(d, first, len(d))
        print('')
        print('===== IMPORTANT =====')
        print('This is a read-only diagnostic. Pointer targets and float runs are candidates,')
        print('not yet proven vertex/UV/normal/index arrays. No OBJ was written.')
        print('Next step is to use the resulting report to prove array descriptors and strides.')
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
