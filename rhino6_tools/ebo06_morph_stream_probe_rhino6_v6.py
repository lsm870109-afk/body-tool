# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V6 - READ ONLY
# Rhino 6 / IronPython 2.7
# Tests candidate float32 arrays and the 16-bit block found by V5.
# No bytes are modified and no stream encoding is assumed.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def b(data, offset):
    return int(data[offset])

def u16(data, offset):
    return struct.unpack('<H', ''.join(chr(b(data, offset+i)) for i in range(2)))[0]

def u32(data, offset):
    return struct.unpack('<I', ''.join(chr(b(data, offset+i)) for i in range(4)))[0]

def f32(data, offset):
    return struct.unpack('<f', ''.join(chr(b(data, offset+i)) for i in range(4)))[0]

def inspect_float_region(data, start, end, label, sample_count):
    end = min(end, len(data))
    usable = ((end - start) // 4) * 4
    count = usable // 4
    values = []
    finite = 0
    zeros = 0
    minv = None
    maxv = None
    for i in range(count):
        value = f32(data, start + i * 4)
        values.append(value)
        if value == value and abs(value) != float('inf'):
            finite += 1
            if value == 0.0:
                zeros += 1
            if minv is None or value < minv:
                minv = value
            if maxv is None or value > maxv:
                maxv = value
    print('')
    print('-- FLOAT32 CANDIDATE: %s --' % label)
    print('RANGE 0x%X..0x%X BYTES=%d FLOATS=%d REMAINDER=%d' % (start, end, end-start, count, (end-start) % 4))
    print('FINITE=%d EXACT_ZERO=%d MIN=%s MAX=%s' % (finite, zeros, str(minv), str(maxv)))
    print('FIRST %d FLOATS:' % sample_count)
    for i in range(min(sample_count, count)):
        print('  [%4d] @0x%X = %.9g' % (i, start+i*4, values[i]))
    if count >= 12:
        print('FIRST 4 TRIPLES (3 floats each):')
        for i in range(4):
            k = i * 3
            print('  T%d: %.8g, %.8g, %.8g' % (i, values[k], values[k+1], values[k+2]))
    if count >= 16:
        print('FIRST 4 QUADS (4 floats each):')
        for i in range(4):
            k = i * 4
            print('  Q%d: %.8g, %.8g, %.8g, %.8g' % (i, values[k], values[k+1], values[k+2], values[k+3]))
    print('LAST 8 FLOATS:')
    for i in range(max(0, count-8), count):
        print('  [%4d] @0x%X = %.9g' % (i, start+i*4, values[i]))

def inspect_u16_block(data, start, end):
    end = min(end, len(data))
    print('')
    print('-- UINT16 BLOCK --')
    print('START=0x%X END=0x%X BYTES=%d' % (start, end, end-start))
    if end-start >= 4:
        print('DWORD AT 0x%X = %d (0x%X)' % (start, u32(data, start), u32(data, start)))
    payload = start + 4
    count = (end-payload)//2
    print('PAYLOAD START=0x%X UINT16 COUNT=%d' % (payload, count))
    vals = []
    for i in range(count):
        vals.append(u16(data, payload+i*2))
    if vals:
        print('MIN=%d MAX=%d UNIQUE=%d' % (min(vals), max(vals), len(set(vals))))
        print('FIRST 80 VALUES:')
        for i in range(0, min(80, len(vals)), 10):
            print('  %04d: %s' % (i, ' '.join('%04X' % x for x in vals[i:i+10])))
        print('LAST 20 VALUES:')
        begin = max(0, len(vals)-20)
        for i in range(begin, len(vals), 10):
            print('  %04d: %s' % (i, ' '.join('%04X' % x for x in vals[i:i+10])))
    tail = end - (payload + count*2)
    print('UNUSED TAIL BYTES=%d' % tail)

def inspect(path):
    data = File.ReadAllBytes(path)
    size = len(data)
    print('')
    print('='*72)
    print('NBA LIVE 06 MORPH STREAM PROBE V6 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE: %d (0x%X)' % (size, size))
    if size < 0x44C0 or b(data,0) != 69 or b(data,1) != 66 or b(data,2) != 79 or b(data,3) != 0:
        print('ERROR: not the expected EBO sample or file is too small')
        return

    print('')
    print('-- COORD ARRAY ARITHMETIC --')
    coord_len = u32(data, 0x11C)
    coord_start = u32(data, 0x120)
    print('start=0x%X length=%d vertices_if_float3=%d end=0x%X' %
          (coord_start, coord_len, coord_len//12, coord_start+coord_len))

    # Candidate regions are bounded by values observed in V5.
    inspect_float_region(data, 0x1CA4, 0x1FC4, '1CA4 to 1FC4 (200 floats)', 24)
    inspect_float_region(data, 0x1FC4, 0x3C6C, '1FC4 to 3C6C (1834 floats)', 24)
    inspect_u16_block(data, 0x3C6C, 0x3D70)
    inspect_float_region(data, 0x3D70, 0x43C0, '3D70 to 43C0 (404 floats)', 32)

    print('')
    print('-- LINKED METADATA VALUES --')
    for field in (0x144, 0x148, 0x14C, 0x16C, 0x170, 0x174, 0x194, 0x198, 0x19C, 0x1B0):
        value = u32(data, field)
        print('field 0x%04X = 0x%08X (%d)' % (field, value, value))

    print('')
    print('-- 43C0 STREAM PREFIX --')
    print('DWORD 0x43C0 = %d (0x%X)' % (u32(data,0x43C0), u32(data,0x43C0)))
    for pos in range(0x43C4, min(0x4474,size), 16):
        end = min(pos+16, 0x4474, size)
        print('0x%04X: %s' % (pos, ' '.join('%02X' % b(data,i) for i in range(pos,end))))

    print('')
    print('-- 4474 TO 449C BYTE POSITIONS --')
    for pos in range(0x4474, 0x449C):
        print('0x%04X = %02X' % (pos, b(data,pos)))

    print('')
    print('V6 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
    print('='*72)

def main():
    dialog = OpenFileDialog()
    dialog.Title = 'Select NBA Live 06 character Morph EBO'
    dialog.Filter = 'EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dialog.Multiselect = False
    if dialog.ShowDialog() != DialogResult.OK:
        print('Cancelled.')
        return
    inspect(dialog.FileName)

if __name__ == '__main__':
    main()
