# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live .EBO / .O binary diagnostic reader
# Read-only: this script never modifies the selected source file.

import os
import struct
import rhinoscriptsyntax as rs

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def hx(data, start, count):
    return ' '.join('%02X' % ord(data[i]) for i in range(start, min(start + count, len(data))))

def strings(data, min_len=4, limit=60):
    found, buf, start = [], [], 0
    for i in range(len(data)):
        n = ord(data[i])
        if 32 <= n <= 126:
            if not buf:
                start = i
            buf.append(chr(n))
        else:
            if len(buf) >= min_len:
                found.append((start, ''.join(buf)))
                if len(found) >= limit:
                    return found
            buf = []
    if len(buf) >= min_len and len(found) < limit:
        found.append((start, ''.join(buf)))
    return found

def print_header(data, path):
    print('')
    print('===== FILE =====')
    print(os.path.basename(path))
    print('Bytes: %d (0x%X)' % (len(data), len(data)))
    print('First 128 bytes:')
    for p in range(0, min(128, len(data)), 16):
        print('%08X  %s' % (p, hx(data, p, 16)))
    print('Readable strings:')
    ss = strings(data)
    if not ss:
        print('(none)')
    for off, s in ss:
        print('0x%X  %s' % (off, s))

def inspect_ebo(data):
    print('')
    print('===== EBO CHECK =====')
    if data:
        print('First byte candidate: 0x%02X' % ord(data[0]))
    # Sample-specific candidate observed previously for damilicB.ebo.
    # It is NOT a universal EBO specification.
    off = 0x1BC
    count = 573 * 3
    size = count * 4
    print('Known sample candidate: offset 0x1BC, 573 XYZ float32 values (%d bytes)' % size)
    if len(data) >= off + size:
        vals = struct.unpack_from('<%df' % count, data, off)
        finite = True
        for v in vals:
            if v != v or abs(v) > 1.0e20:
                finite = False
                break
        if finite:
            xs, ys, zs = vals[0::3], vals[1::3], vals[2::3]
            print('Candidate float block is present and finite.')
            print('X: %.7f .. %.7f' % (min(xs), max(xs)))
            print('Y: %.7f .. %.7f' % (min(ys), max(ys)))
            print('Z: %.7f .. %.7f' % (min(zs), max(zs)))
            print('WARNING: on the previously examined sample this block was coordinate DELTAS, not confirmed absolute geometry.')
        else:
            print('Candidate block contains implausible float values.')
    else:
        print('File is shorter than this sample-specific candidate block.')
    print('Full EBO chunk decoding and safe export are NOT implemented.')

def inspect_o(data):
    print('')
    print('===== O FILE CHECK =====')
    print('Previously examined .o sample contained a 40-byte vertex record:')
    print('XYZ float32 at +0, unknown +12, normal float32 at +16,')
    print('unknown/marker +28, UV float32 at +32.')
    print('This layout is sample-specific; the vertex-section offset is not yet known.')
    print('File size modulo 40: %d' % (len(data) % 40))
    print('Float interpretations at file offset 0 (diagnostic only):')
    for base in (0, 40, 80):
        if base + 40 <= len(data):
            xyz = struct.unpack_from('<3f', data, base)
            nrm = struct.unpack_from('<3f', data, base + 16)
            uv = struct.unpack_from('<2f', data, base + 32)
            print('%08X XYZ=(%.6f, %.6f, %.6f) N=(%.5f, %.5f, %.5f) UV=(%.5f, %.5f)' %
                  (base, xyz[0], xyz[1], xyz[2], nrm[0], nrm[1], nrm[2], uv[0], uv[1]))
    print('The .o container and vertex block must be decoded before extracting geometry.')

def main():
    path = rs.OpenFileName('Select NBA Live .EBO or .O file',
        'NBA Live binary (*.ebo;*.o)|*.ebo;*.o|EBO (*.ebo)|*.ebo|O (*.o)|*.o||')
    if not path:
        print('Cancelled.')
        return
    try:
        data = read_file(path)
        print_header(data, path)
        ext = os.path.splitext(path)[1].lower()
        if ext == '.ebo':
            inspect_ebo(data)
        elif ext == '.o':
            inspect_o(data)
        else:
            print('Unsupported extension: ' + ext)
        print('')
        print('Read-only inspection finished. No source file was changed.')
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
