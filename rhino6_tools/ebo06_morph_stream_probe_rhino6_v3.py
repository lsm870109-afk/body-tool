# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V3 - READ ONLY
# Rhino 6 / IronPython 2.7
# Fresh file: no bytearray, no FileStream.Read, no multiline continuations.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def get_bytes(path):
    return File.ReadAllBytes(path)

def bstr(data, offset, count):
    out = []
    for i in range(count):
        out.append(chr(int(data[offset + i])))
    return ''.join(out)

def u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<I', bstr(data, offset, 4))[0]

def i32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<i', bstr(data, offset, 4))[0]

def f32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<f', bstr(data, offset, 4))[0]

def hex32(value):
    if value is None:
        return '--------'
    return '0x%08X' % value

def ascii_text(data, start, count):
    chars = []
    end = min(len(data), start + count)
    for pos in range(start, end):
        value = int(data[pos])
        if value >= 32 and value <= 126:
            chars.append(chr(value))
        else:
            chars.append('.')
    return ''.join(chars)

def dump_bytes(data, start, count, title):
    end = min(len(data), start + count)
    print('')
    print('-- ' + title + ' --')
    pos = start
    while pos < end:
        n = min(16, end - pos)
        values = []
        for j in range(n):
            values.append('%02X' % int(data[pos + j]))
        line_hex = ' '.join(values)
        line_ascii = ascii_text(data, pos, n)
        print('%08X  %-47s  %s' % (pos, line_hex, line_ascii))
        pos += n

def dump_words(data, start, end):
    print('')
    print('-- METADATA WORDS --')
    pos = start
    while pos + 4 <= min(end, len(data)):
        uv = u32(data, pos)
        sv = i32(data, pos)
        fv = f32(data, pos)
        print('0x%04X  u32=%10u  i32=%11d  f32=% .9g  hex=%s' % (pos, uv, sv, fv, hex32(uv)))
        pos += 4

def scan_strings(data, start, end):
    print('')
    print('-- PRINTABLE STRINGS --')
    pos = start
    end = min(end, len(data))
    while pos < end:
        value = int(data[pos])
        if value >= 32 and value <= 126:
            run_start = pos
            while pos < end:
                value = int(data[pos])
                if value < 32 or value > 126:
                    break
                pos += 1
            if pos - run_start >= 3:
                print('0x%04X  %s' % (run_start, ascii_text(data, run_start, pos - run_start)))
        else:
            pos += 1

def inspect_file(path):
    data = get_bytes(path)
    size = len(data)
    print('')
    print('=' * 72)
    print('NBA LIVE 06 MORPH STREAM PROBE V3 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE: %d bytes (0x%X)' % (size, size))

    if size < 0x40:
        print('ERROR: File is too small.')
        return

    if int(data[0]) != 69 or int(data[1]) != 66 or int(data[2]) != 79 or int(data[3]) != 0:
        print('ERROR: EBO magic not found.')
        print('FIRST BYTES: ' + ascii_text(data, 0, 4))
        return

    version = u32(data, 4)
    size_field = u32(data, 8)
    print('MAGIC: EBO OK')
    print('VERSION: %d' % version)
    print('SIZE FIELD: %d' % size_field)

    print('')
    print('-- HEADER POINTERS --')
    for off in (0x10, 0x14, 0x18, 0x1C, 0x20):
        value = u32(data, off)
        if value is None:
            print('0x%02X: unavailable' % off)
        else:
            state = 'IN FILE' if value < size else 'OUTSIDE FILE'
            print('0x%02X -> 0x%X (%d) %s' % (off, value, value, state))

    dump_bytes(data, 0x60, 0x160, 'DESCRIPTOR / MORPH METADATA')
    dump_words(data, 0xE0, 0x1BC)

    start = 0x1BC
    count = 573
    byte_count = count * 12
    finish = start + byte_count
    print('')
    print('-- 573 x FLOAT3 CANDIDATE --')
    print('START: 0x%X' % start)
    print('BYTE COUNT: %d (0x%X)' % (byte_count, byte_count))
    print('END: 0x%X' % finish)

    if finish <= size:
        mins = [None, None, None]
        maxs = [None, None, None]
        finite = 0
        for n in range(count):
            for axis in range(3):
                value = f32(data, start + n * 12 + axis * 4)
                if value == value and abs(value) < 1.0e20:
                    finite += 1
                    if mins[axis] is None or value < mins[axis]:
                        mins[axis] = value
                    if maxs[axis] is None or value > maxs[axis]:
                        maxs[axis] = value
        print('FINITE COMPONENTS: %d / %d' % (finite, count * 3))
        print('X RANGE: % .9g .. % .9g' % (mins[0], maxs[0]))
        print('Y RANGE: % .9g .. % .9g' % (mins[1], maxs[1]))
        print('Z RANGE: % .9g .. % .9g' % (mins[2], maxs[2]))
        print('FIRST 12 RECORDS:')
        for n in range(12):
            off = start + n * 12
            x = f32(data, off)
            y = f32(data, off + 4)
            z = f32(data, off + 8)
            print('#%03d  % .9g  % .9g  % .9g' % (n, x, y, z))
        print('LAST 4 RECORDS:')
        for n in range(count - 4, count):
            off = start + n * 12
            x = f32(data, off)
            y = f32(data, off + 4)
            z = f32(data, off + 8)
            print('#%03d  % .9g  % .9g  % .9g' % (n, x, y, z))
    else:
        print('Candidate data range is outside this file.')

    scan_strings(data, max(0, size - 0x500), size)

    if finish < size:
        dump_bytes(data, finish, min(0x100, size - finish), 'BYTES AFTER FLOAT3 CANDIDATE')

    print('')
    print('READ ONLY COMPLETE. SOURCE FILE WAS NOT MODIFIED.')
    print('=' * 72)

def main():
    dialog = OpenFileDialog()
    dialog.Title = 'Select NBA Live 06 character EBO'
    dialog.Filter = 'EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dialog.Multiselect = False
    result = dialog.ShowDialog()
    if result != DialogResult.OK:
        print('Cancelled.')
        return
    selected_path = dialog.FileName
    try:
        inspect_file(selected_path)
    except Exception as error:
        import traceback
        print('PROBE V3 ERROR: %s' % repr(error))
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
