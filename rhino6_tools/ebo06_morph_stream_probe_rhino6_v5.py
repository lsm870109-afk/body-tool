# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V5 - READ ONLY
# Rhino 6 / IronPython 2.7
# Investigates candidate offsets found in the V4 metadata.
# All offsets are treated as candidates, not assumed to be proven pointers.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def read_bytes(path):
    return File.ReadAllBytes(path)

def raw_string(data, offset, count):
    chars = []
    for i in range(count):
        chars.append(chr(int(data[offset + i])))
    return ''.join(chars)

def u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        return None
    return struct.unpack('<H', raw_string(data, offset, 2))[0]

def u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('<I', raw_string(data, offset, 4))[0]

def i8(value):
    if value >= 128:
        return value - 256
    return value

def show_hex(data, start, end, title):
    print('')
    print('-- %s [0x%X..0x%X] --' % (title, start, min(end, len(data))))
    pos = max(0, start)
    limit = min(end, len(data))
    while pos < limit:
        count = min(16, limit - pos)
        hx = []
        tx = []
        for j in range(count):
            value = int(data[pos + j])
            hx.append('%02X' % value)
            if 32 <= value <= 126:
                tx.append(chr(value))
            else:
                tx.append('.')
        print('%08X  %-47s  %s' % (pos, ' '.join(hx), ''.join(tx)))
        pos += count

def byte_stats(data, start, end, title):
    start = max(0, start)
    end = min(len(data), end)
    counts = [0] * 256
    for pos in range(start, end):
        counts[int(data[pos])] += 1
    total = end - start
    high = 0
    zero = counts[0]
    for value in range(128, 256):
        high += counts[value]
    print('')
    print('-- BYTE STATISTICS: %s --' % title)
    print('RANGE: 0x%X..0x%X LENGTH=%d' % (start, end, total))
    if total:
        print('ZERO=%d (%.2f%%) HIGH_BIT_SET=%d (%.2f%%)' % (zero, 100.0 * zero / total, high, 100.0 * high / total))
    ranked = []
    for value in range(256):
        if counts[value]:
            ranked.append((counts[value], value))
    ranked.sort(reverse=True)
    print('MOST COMMON BYTE VALUES:')
    for count, value in ranked[:20]:
        print('  %02X : %d' % (value, count))

def run_stats(data, start, end, title):
    start = max(0, start)
    end = min(len(data), end)
    print('')
    print('-- REPEATED-BYTE RUNS: %s --' % title)
    pos = start
    runs = []
    while pos < end:
        value = int(data[pos])
        finish = pos + 1
        while finish < end and int(data[finish]) == value:
            finish += 1
        length = finish - pos
        if length >= 3:
            runs.append((pos, value, length))
        pos = finish
    if not runs:
        print('No same-byte run of length >= 3.')
    else:
        for item in runs[:100]:
            print('0x%X  byte=%02X  length=%d' % item)
        if len(runs) > 100:
            print('... %d more runs omitted' % (len(runs) - 100))

def inspect(path):
    data = read_bytes(path)
    size = len(data)
    print('')
    print('=' * 76)
    print('NBA LIVE 06 MORPH STREAM PROBE V5 - READ ONLY')
    print('FILE: %s' % str(path))
    print('SIZE: %d (0x%X)' % (size, size))
    if size < 0x40:
        print('ERROR: file too small')
        return
    if int(data[0]) != 69 or int(data[1]) != 66 or int(data[2]) != 79 or int(data[3]) != 0:
        print('ERROR: EBO magic not found')
        return

    print('')
    print('-- HEADER DWORDS --')
    for off in (0x10, 0x14, 0x18, 0x1C, 0x20):
        print('0x%02X = 0x%08X (%d)' % (off, u32(data, off), u32(data, off)))

    # Values observed in the V4 metadata. These are inspected as candidate offsets only.
    candidates = (0x1BC, 0x1C98, 0x1CA4, 0x1FC4, 0x3C6C, 0x3D70, 0x43C4, 0x4474, 0x4494, 0x449C, 0x44B4, 0x44C0)
    print('')
    print('-- CANDIDATE OFFSET CHECK --')
    for off in candidates:
        state = 'IN FILE' if off < size else 'OUTSIDE FILE'
        print('0x%08X  %10d  %s' % (off, off, state))

    # Metadata DWORD values that looked like offsets/lengths in earlier probe output.
    print('')
    print('-- SELECTED METADATA FIELDS --')
    for off in (0x11C, 0x120, 0x144, 0x148, 0x14C, 0x16C, 0x170, 0x174, 0x194, 0x198, 0x19C, 0x1B0):
        value = u32(data, off)
        state = ''
        if value is not None and value < size:
            state = ' [IN-FILE OFFSET CANDIDATE]'
        print('0x%04X -> 0x%08X (%d)%s' % (off, value, value, state))

    # Inspect likely boundaries separately to avoid assuming stream semantics.
    regions = (
        (0x1C98, 0x1FC4, 'AFTER COORD TO CANDIDATE 1FC4'),
        (0x1FC4, 0x3C6C, 'CANDIDATE REGION 1FC4 TO 3C6C'),
        (0x3C6C, 0x3D70, 'CANDIDATE REGION 3C6C TO 3D70'),
        (0x3D70, 0x43C4, 'CANDIDATE REGION 3D70 TO 43C4'),
        (0x43C4, 0x4474, 'TAIL BINARY REGION 43C4 TO 4474'),
        (0x4474, 0x449C, 'TAIL METADATA REGION 4474 TO 449C')
    )
    for start, end, title in regions:
        if start < size and end > start:
            byte_stats(data, start, min(end, size), title)
            run_stats(data, start, min(end, size), title)

    show_hex(data, 0x1C80, 0x1D20, 'COORD END / NEXT DATA')
    show_hex(data, 0x1F80, 0x2040, 'AROUND CANDIDATE 1FC4')
    show_hex(data, 0x3C20, 0x3D90, 'AROUND CANDIDATES 3C6C AND 3D70')
    show_hex(data, 0x43A0, 0x44C0, 'TAIL STREAM AND METADATA')

    # Show the final tail as signed and unsigned bytes; useful for testing candidate
    # variable-length or signed-delta encodings without claiming a decode.
    start = 0x43C4
    end = min(0x449C, size)
    print('')
    print('-- TAIL BYTE VALUES (UNSIGNED / SIGNED INT8) --')
    pos = start
    while pos < end:
        count = min(16, end - pos)
        parts = []
        for j in range(count):
            value = int(data[pos + j])
            parts.append('%02X/%4d' % (value, i8(value)))
        print('0x%04X  %s' % (pos, '  '.join(parts)))
        pos += count

    print('')
    print('V5 COMPLETE. READ ONLY; NO SOURCE BYTES MODIFIED.')
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
        print('V5 ERROR: %s' % repr(error))
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
