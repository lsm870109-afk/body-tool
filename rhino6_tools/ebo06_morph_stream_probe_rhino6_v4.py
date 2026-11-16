# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V4 - READ ONLY
# Rhino 6 / IronPython 2.7
# Focus: MorphStreamHeader fields and streams after the 573-vertex coord block.
# Does not modify the selected EBO.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def read_file(path):
    return File.ReadAllBytes(path)

def byte_string(data, offset, count):
    parts = []
    for index in range(count):
        parts.append(chr(int(data[offset + index])))
    return ''.join(parts)

def get_u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        return None
    return struct.unpack('<H', byte_string(data, offset, 2))[0]

def get_u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<I', byte_string(data, offset, 4))[0]

def get_i32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<i', byte_string(data, offset, 4))[0]

def get_f32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<f', byte_string(data, offset, 4))[0]

def hex_value(value):
    if value is None:
        return '--------'
    return '0x%08X' % value

def print_word_table(data, start, end, title):
    print('')
    print('-- ' + title + ' --')
    pos = start
    limit = min(end, len(data))
    while pos + 4 <= limit:
        uval = get_u32(data, pos)
        ival = get_i32(data, pos)
        fval = get_f32(data, pos)
        print('0x%04X  u32=%10u  i32=%11d  f32=% .9g  %s' % (pos, uval, ival, fval, hex_value(uval)))
        pos += 4

def print_hex(data, start, end, title):
    print('')
    print('-- ' + title + ' --')
    pos = start
    limit = min(end, len(data))
    while pos < limit:
        count = min(16, limit - pos)
        hex_parts = []
        text_parts = []
        for index in range(count):
            value = int(data[pos + index])
            hex_parts.append('%02X' % value)
            if value >= 32 and value <= 126:
                text_parts.append(chr(value))
            else:
                text_parts.append('.')
        print('%08X  %-47s  %s' % (pos, ' '.join(hex_parts), ''.join(text_parts)))
        pos += count

def inspect(path):
    data = read_file(path)
    size = len(data)
    print('')
    print('=' * 76)
    print('NBA LIVE 06 MORPH STREAM PROBE V4 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE: %d (0x%X)' % (size, size))

    if size < 0x40:
        print('ERROR: file too small')
        return
    if int(data[0]) != 69 or int(data[1]) != 66 or int(data[2]) != 79 or int(data[3]) != 0:
        print('ERROR: EBO magic not found')
        return

    print('EBO version=%d size_field=%d' % (get_u32(data, 4), get_u32(data, 8)))
    print('HEADER POINTERS:')
    for off in (0x10, 0x14, 0x18, 0x1C, 0x20):
        value = get_u32(data, off)
        print('  0x%02X -> %s (%d)' % (off, hex_value(value), value))

    print_hex(data, 0x60, 0x1BC, 'DESCRIPTOR AND STREAM HEADER BYTES')
    print_word_table(data, 0x60, 0x1BC, 'DESCRIPTOR / STREAM HEADER DWORD VIEW')

    coord_start = get_u32(data, 0x120)
    coord_size = get_u32(data, 0x11C)
    print('')
    print('COORD HEADER CANDIDATE: start=%s size=%s' % (hex_value(coord_start), coord_size))
    if coord_start is not None and coord_size is not None:
        print('COORD END: %s' % hex_value(coord_start + coord_size))
        print('COORD SIZE / 12: %s' % str(float(coord_size) / 12.0))

    print_word_table(data, 0x1BC, min(size, 0x2BC), 'WORDS AT AND AFTER COORD STREAM START')
    print_hex(data, 0x1C80, min(size, 0x1E00), 'COORD STREAM END AND FOLLOWING BYTES')

    print_word_table(data, 0x1C98, min(size, 0x1D98), 'POSSIBLE NEXT STREAM HEADER / DATA')
    print_hex(data, 0x1D80, min(size, 0x2000), 'FOLLOWING STREAM RAW BYTES')

    print_word_table(data, 0x4380, min(size, 0x44C0), 'TAIL METADATA DWORD VIEW')
    print_hex(data, 0x43A0, min(size, 0x44C0), 'TAIL METADATA RAW BYTES')

    print('')
    print('STRING MARKERS:')
    markers = ('Morph', 'MorphTargetNameArray', 'MorphStreamHeader', 'MorphData', 'ByteArray', 'headAShape_morphs', 'coord', 'normal', 'uv', 'colour')
    for marker in markers:
        needle = marker
        found = -1
        for pos in range(0, size - len(needle) + 1):
            if byte_string(data, pos, len(needle)) == needle:
                found = pos
                break
        if found >= 0:
            print('  %-24s  0x%04X' % (marker, found))
        else:
            print('  %-24s  not found' % marker)

    print('')
    print('READ ONLY COMPLETE. NO SOURCE BYTES WERE CHANGED.')
    print('=' * 76)

def main():
    dialog = OpenFileDialog()
    dialog.Title = 'Select NBA Live 06 character Morph EBO'
    dialog.Filter = 'EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dialog.Multiselect = False
    result = dialog.ShowDialog()
    if result != DialogResult.OK:
        print('Cancelled.')
        return
    try:
        inspect(dialog.FileName)
    except Exception as error:
        import traceback
        print('V4 ERROR: %s' % repr(error))
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
