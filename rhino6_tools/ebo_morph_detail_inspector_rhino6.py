# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# Read-only deep inspector for NBA Live 06 face Morph EBO v17.
# No files are modified.

import os
import struct
import rhinoscriptsyntax as rs

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]

def i32(d, o):
    return struct.unpack_from('<i', d, o)[0]

def f32(d, o):
    return struct.unpack_from('<f', d, o)[0]

def hx(d, o, n):
    end = min(o+n, len(d))
    p = o
    while p < end:
        q = min(p+16, end)
        print('  %08X  %s' % (p, ' '.join('%02X' % ord(d[k]) for k in range(p,q))))
        p = q

def cstr(d, o):
    if o < 0 or o >= len(d):
        return '<OUT_OF_RANGE>'
    e = d.find('\x00', o)
    if e < 0:
        return '<NO_TERMINATOR>'
    return d[o:e].decode('ascii', 'replace')

def main():
    path = rs.OpenFileName('Select face Morph EBO', 'EBO files (*.ebo)|*.ebo||')
    if not path:
        print('Cancelled.')
        return
    d = read_file(path)
    print('')
    print('===== FACE MORPH DETAIL =====')
    print('File: %s (%d bytes / 0x%X)' % (os.path.basename(path), len(d), len(d)))
    if len(d) < 0x60 or d[:4] != 'EBO\x00':
        print('Not EBO v17.')
        return

    strings = u32(d, 32)
    chunk = u32(d, 16)
    export_off = u32(d, 28)
    export_count = struct.unpack_from('<H', d, 42)[0]
    print('Strings table: 0x%X, chunk: 0x%X' % (strings, chunk))
    print('')
    print('[EXPORTS]')
    for i in range(export_count):
        off = export_off + i*12
        tr, nr, dr = struct.unpack_from('<IIi', d, off)
        print('%d: type=%s name=%s target=0x%X' %
              (i, cstr(d, strings+tr), cstr(d, strings+nr), off+dr))

    # This face-only morph chunk's TOC points to the Morph object,
    # target-name array, then four MorphStreamHeader records.
    toc_base = chunk + 0x14
    print('')
    print('[TOC TARGETS]')
    targets = []
    for i in range(7):
        off = toc_base + i*0x10
        flags, usd, count, aligned, rel = struct.unpack_from('<HHIIi', d, off)
        target = off + rel
        targets.append(target)
        print('TOC %d: flags=0x%X usd=%d count=%d aligned=0x%X rel=%d target=0x%X' %
              (i, flags, usd, count, aligned, rel, target))

    print('')
    print('[MORPH OBJECT / NAME ARRAY RAW]')
    for label, off, size in [('Morph object', targets[0], 0x24),
                             ('Target name array', targets[1], 0x20)]:
        print(label + ' @0x%X' % off)
        hx(d, off, size)

    print('')
    print('[FOUR MORPH STREAM HEADERS]')
    for i in range(2,6):
        off = targets[i]
        if off < 0 or off+40 > len(d):
            print('Stream %d header outside file: 0x%X' % (i-2, off))
            continue
        words = struct.unpack_from('<10I', d, off)
        rel_name = words[0]
        name = cstr(d, strings+rel_name) if rel_name else ''
        print('')
        print('Stream %d @0x%X name=%s' % (i-2, off, name))
        for j, value in enumerate(words):
            print('  word[%d] @+0x%02X = 0x%08X (%u)' % (j, j*4, value, value))
        print('  float interpretations: size=%g payload=%g aux=%g scale=%g' %
              (f32(d,off+12), f32(d,off+16), f32(d,off+20), f32(d,off+28)))
        print('  raw header:')
        hx(d, off, 40)

    payload = targets[6]
    payload_size = 10119
    print('')
    print('[I8 PAYLOAD]')
    print('TOC payload starts at 0x%X; declared byte count from TOC=%d (0x%X)' %
          (payload, 10119, 10119))
    if payload >= 0 and payload+payload_size <= len(d):
        print('First 160 bytes:')
        hx(d, payload, 160)
        print('Last 64 bytes:')
        hx(d, payload+payload_size-64, 64)
        print('Payload end exclusive: 0x%X' % (payload+payload_size))
    else:
        print('Payload range outside file.')

    print('')
    print('[FILE TRAILER]')
    if len(d) >= 16:
        hx(d, len(d)-16, 16)
    print('Declared size field: 0x%X; actual size: 0x%X' % (u32(d,8),len(d)))
    print('Read-only inspection complete. No source file changed.')

if __name__ == '__main__':
    main()
