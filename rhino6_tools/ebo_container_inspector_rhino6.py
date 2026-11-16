# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live PC EBO v17 container inspector.
# Read-only. Does not modify the selected EBO.

import os
import struct
import rhinoscriptsyntax as rs

HEADER_FMT = '<IIIHHIIIIIHHHHH'
HEADER_SIZE = 0x60
CHUNK_HEADER_SIZE = 0x14
TOC_SIZE = 0x10

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def u16(data, off):
    return struct.unpack_from('<H', data, off)[0]

def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]

def i32(data, off):
    return struct.unpack_from('<i', data, off)[0]

def cstr(data, off):
    if off < 0 or off >= len(data):
        return '<BAD_STRING_OFFSET>'
    end = data.find('\x00', off)
    if end < 0:
        return '<UNTERMINATED_STRING>'
    try:
        return data[off:end].decode('ascii')
    except:
        return repr(data[off:end])

def safe_range(off, size, total):
    return off >= 0 and size >= 0 and off + size <= total

def dump_hex(data, off, size, max_size=96):
    end = min(off + size, off + max_size, len(data))
    p = off
    while p < end:
        row_end = min(p + 16, end)
        values = []
        for i in range(p, row_end):
            values.append('%02X' % ord(data[i]))
        print('    %08X  %s' % (p, ' '.join(values)))
        p = row_end
    if size > max_size:
        print('    ... (%d more bytes)' % (size - max_size))

def inspect_ebo(data, path):
    print('')
    print('===== EBO V17 CONTAINER INSPECTION =====')
    print('FILE: %s' % os.path.basename(path))
    print('Actual size: %d (0x%X)' % (len(data), len(data)))

    if len(data) < HEADER_SIZE or data[:4] != 'EBO\x00':
        print('ERROR: not a supported EBO file or header too short.')
        return

    fields = struct.unpack_from(HEADER_FMT, data, 0)
    (magic, version, declared_size, endian_original, endian_current,
     chunks_off, usd_off, imports_off, exports_off, strings_off,
     chunk_count, usd_count, import_count, export_count, string_count) = fields

    print('')
    print('[HEADER]')
    print('Magic: %s' % repr(data[:4]))
    print('Version: %d (0x%X)' % (version, version))
    print('Declared size: %d (0x%X)' % (declared_size, declared_size))
    print('Actual size:   %d (0x%X)' % (len(data), len(data)))
    print('Size difference (actual - declared): %d' % (len(data) - declared_size))
    print('Endian original/current: 0x%04X / 0x%04X' % (endian_original, endian_current))
    print('Chunks offset: 0x%X' % chunks_off)
    print('USD offset: 0x%X' % usd_off)
    print('Imports offset: 0x%X' % imports_off)
    print('Exports offset: 0x%X' % exports_off)
    print('Strings offset: 0x%X' % strings_off)
    print('Counts: chunks=%d USD=%d imports=%d exports=%d strings=%d' %
          (chunk_count, usd_count, import_count, export_count, string_count))

    print('')
    print('[HEADER VALIDATION]')
    checks = [
        ('header', 0, HEADER_SIZE),
        ('chunk start', chunks_off, CHUNK_HEADER_SIZE),
        ('USD table', usd_off, usd_count * 4),
        ('import table', imports_off, import_count * 24),
        ('export table', exports_off, export_count * 12),
        ('string prefix', strings_off, 4)
    ]
    for label, off, size in checks:
        print('%s: %s (offset=0x%X size=0x%X)' %
              (label, 'OK' if safe_range(off, size, len(data)) else 'OUT_OF_RANGE', off, size))

    if not safe_range(strings_off, 4, len(data)):
        print('Cannot parse string pool.')
        return

    print('')
    print('[STRING POOL]')
    print('Prefix bytes at 0x%X:' % strings_off)
    dump_hex(data, strings_off, 4, 4)
    pos = strings_off + 4
    string_values = []
    for idx in range(string_count):
        if pos >= len(data):
            print('String %d: OUT_OF_RANGE' % idx)
            break
        value = cstr(data, pos)
        print('[%d] rel=0x%X abs=0x%X value=%s' %
              (idx, pos - strings_off, pos, value))
        string_values.append((pos - strings_off, value))
        if value.startswith('<BAD_') or value.startswith('<UNTERMINATED_'):
            break
        raw_len = len(value.encode('ascii', 'replace')) + 1
        pos += raw_len
        if raw_len & 1:
            pos += 1
    print('String pool parsed end: 0x%X' % pos)

    string_map = {}
    for rel, value in string_values:
        string_map[rel] = value

    def string_ref(rel):
        if rel == 0:
            return ''
        return string_map.get(rel, '<UNKNOWN_REL_0x%X>' % rel)

    print('')
    print('[USD TYPE TABLE]')
    usd_types = []
    if safe_range(usd_off, usd_count * 4, len(data)):
        for i in range(usd_count):
            rel = u32(data, usd_off + i * 4)
            name = string_ref(rel)
            usd_types.append(name)
            print('[%d] rel=0x%X type=%s' % (i, rel, name))
    else:
        print('USD table outside file.')

    print('')
    print('[CHUNKS]')
    cursor = chunks_off
    for ci in range(chunk_count):
        if not safe_range(cursor, CHUNK_HEADER_SIZE, len(data)):
            print('Chunk %d header OUT_OF_RANGE at 0x%X' % (ci, cursor))
            break
        flags, toc_count, rel_toc, chunk_type, chunk_version, chunk_size = struct.unpack_from(
            '<HHIIII', data, cursor)
        chunk_end = cursor + chunk_size
        toc_base = cursor + rel_toc
        print('')
        print('Chunk %d @0x%X' % (ci, cursor))
        print('  flags=0x%X toc_count=%d rel_toc=0x%X toc_abs=0x%X' %
              (flags, toc_count, rel_toc, toc_base))
        print('  chunk_type=0x%X version=0x%X size=0x%X end=0x%X %s' %
              (chunk_type, chunk_version, chunk_size, chunk_end,
               'OK' if chunk_size >= CHUNK_HEADER_SIZE and chunk_end <= len(data) else 'INVALID'))
        if chunk_size < CHUNK_HEADER_SIZE or chunk_end > len(data):
            print('  Stop: invalid chunk size.')
            break
        if not safe_range(toc_base, toc_count * TOC_SIZE, len(data)):
            print('  TOC table OUT_OF_RANGE.')
            break
        for ti in range(toc_count):
            to = toc_base + ti * TOC_SIZE
            tflags, usd_index, struct_count, aligned_size, rel_data = struct.unpack_from(
                '<HHIIi', data, to)
            target = to + rel_data
            if usd_index < len(usd_types):
                type_name = usd_types[usd_index]
            else:
                type_name = '<USD_INDEX_OUT_OF_RANGE>'
            valid = safe_range(target, 0, len(data)) and target < len(data)
            print('  TOC %d @0x%X flags=0x%X usd=%d (%s)' %
                  (ti, to, tflags, usd_index, type_name))
            print('    struct_count=%d aligned_size=0x%X rel_data=%d (0x%X) target=0x%X %s' %
                  (struct_count, aligned_size, rel_data, rel_data & 0xFFFFFFFF,
                   target, 'OK' if valid else 'OUT_OF_RANGE'))
            if valid:
                preview_size = min(aligned_size, 96, max(0, chunk_end - target))
                if preview_size > 0:
                    print('    data preview:')
                    dump_hex(data, target, preview_size, 96)
        cursor = chunk_end

    print('')
    print('[IMPORTS]')
    if import_count == 0:
        print('(none)')
    elif safe_range(imports_off, import_count * 24, len(data)):
        for i in range(import_count):
            off = imports_off + i * 24
            nxt, prev, type_rel, name_rel, iat_rel, iat_count = struct.unpack_from(
                '<6I', data, off)
            print('[%d] @0x%X type=%s name=%s IAT_rel=0x%X IAT_count=%d' %
                  (i, off, string_ref(type_rel), string_ref(name_rel), iat_rel, iat_count))
            iat = off + iat_rel
            if safe_range(iat, iat_count * 4, len(data)):
                for j in range(iat_count):
                    print('    fixup[%d] file_offset=0x%X' %
                          (j, off + i32(data, iat + j * 4)))
            else:
                print('    IAT OUT_OF_RANGE')

    print('')
    print('[EXPORTS]')
    if export_count == 0:
        print('(none)')
    elif safe_range(exports_off, export_count * 12, len(data)):
        for i in range(export_count):
            off = exports_off + i * 12
            type_rel, name_rel, data_rel = struct.unpack_from('<IIi', data, off)
            target = off + data_rel
            print('[%d] @0x%X type=%s name=%s rel=%d target=0x%X %s' %
                  (i, off, string_ref(type_rel), string_ref(name_rel),
                   data_rel, target,
                   'OK' if safe_range(target, 0, len(data)) else 'OUT_OF_RANGE'))
    else:
        print('Export table OUT_OF_RANGE.')

    print('')
    print('[TAIL / UNREFERENCED BYTES]')
    if cursor <= len(data):
        print('Last parsed chunk end: 0x%X' % cursor)
    print('File end: 0x%X' % len(data))
    print('This inspector is read-only. No geometry or morph stream is modified.')

def main():
    path = rs.OpenFileName('Select NBA Live 06 EBO file',
        'NBA Live EBO (*.ebo)|*.ebo||')
    if not path:
        print('Cancelled.')
        return
    try:
        data = read_file(path)
        inspect_ebo(data, path)
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
