# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live 06 EBO Geometry object raw inspector.
# Read-only. Does not modify the selected EBO.
#
# Purpose:
#   Follow the actual Geometry export (e.g. headAShape), rather than
#   interpreting a Geometry object as a Morph object.
#
# This is a diagnostic dumper, not yet a Geometry decoder.

import os
import struct
import rhinoscriptsyntax as rs

HEADER_SIZE = 0x60
MAX_DUMP = 0x400

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

def f32(data, off):
    return struct.unpack_from('<f', data, off)[0]

def safe_range(off, size, total):
    return off >= 0 and size >= 0 and off + size <= total

def cstr(data, off):
    if off < 0 or off >= len(data):
        return ''
    end = data.find('\x00', off)
    if end < 0:
        return ''
    try:
        return data[off:end].decode('ascii')
    except:
        return ''

def hex_dump(data, off, size, max_size=MAX_DUMP):
    end = min(off + size, off + max_size, len(data))
    p = off
    while p < end:
        row_end = min(p + 16, end)
        vals = []
        for i in range(p, row_end):
            vals.append('%02X' % ord(data[i]))
        print('  %08X  %s' % (p, ' '.join(vals)))
        p = row_end
    if size > max_size:
        print('  ... (%d bytes omitted)' % (size - max_size))

def parse_strings(data, strings_off, string_count):
    result = {}
    pos = strings_off + 4
    for i in range(string_count):
        if pos >= len(data):
            break
        value = cstr(data, pos)
        if value == '' and data[pos:pos+1] != '\x00':
            break
        result[pos - strings_off] = value
        n = len(value) + 1
        pos += n
        if n & 1:
            pos += 1
    return result

def inspect(data, path):
    print('')
    print('===== EBO GEOMETRY OBJECT RAW INSPECTION =====')
    print('FILE: %s (%d bytes / 0x%X)' %
          (os.path.basename(path), len(data), len(data)))

    if len(data) < HEADER_SIZE or data[:4] != 'EBO\x00':
        print('ERROR: unsupported EBO header.')
        return

    # EBO v17 header layout used by the container inspector.
    fields = struct.unpack_from('<IIIHHIIIIIHHHHH', data, 0)
    (magic, version, declared_size, endian0, endian1,
     chunks_off, usd_off, imports_off, exports_off, strings_off,
     chunk_count, usd_count, import_count, export_count, string_count) = fields

    print('Version=%d declared=0x%X exports=0x%X strings=0x%X exports_count=%d strings_count=%d' %
          (version, declared_size, exports_off, strings_off, export_count, string_count))

    if not safe_range(exports_off, export_count * 12, len(data)):
        print('ERROR: export table outside file.')
        return
    if not safe_range(strings_off, 4, len(data)):
        print('ERROR: string table outside file.')
        return

    strings = parse_strings(data, strings_off, string_count)

    def sref(rel):
        return strings.get(rel, '<string rel 0x%X>' % rel)

    exports = []
    print('')
    print('[EXPORTS]')
    for i in range(export_count):
        off = exports_off + i * 12
        type_rel, name_rel, data_rel = struct.unpack_from('<IIi', data, off)
        target = off + data_rel
        typ = sref(type_rel)
        name = sref(name_rel)
        exports.append((i, typ, name, target))
        print('%02d type=%s name=%s export_record=0x%X target=0x%X %s' %
              (i, typ, name, off, target,
               'OK' if safe_range(target, 4, len(data)) else 'OUT_OF_RANGE'))

    print('')
    print('[SELECTED GEOMETRY EXPORTS]')
    selected = []
    for item in exports:
        idx, typ, name, target = item
        if typ.lower() == 'geometry' and (
                name.lower() == 'headashape' or
                name.lower() == 'baseplyr' or
                'head' in name.lower()):
            selected.append(item)

    if not selected:
        print('No matching Geometry exports found. Dumping all Geometry exports is available by editing the name filter.')
        return

    for item in selected:
        idx, typ, name, target = item
        print('')
        print('--- Export %d: %s / %s ---' % (idx, typ, name))
        print('Object target: 0x%X' % target)

        # Dump the raw object bytes without assuming a Morph layout.
        dump_size = min(MAX_DUMP, len(data) - target)
        print('[RAW BYTES: first 0x%X bytes]' % dump_size)
        hex_dump(data, target, dump_size, MAX_DUMP)

        print('')
        print('[32-BIT WORD / FLOAT VIEW]')
        words = min(64, dump_size // 4)
        for j in range(words):
            off = target + j * 4
            iv = u32(data, off)
            fv = f32(data, off)
            rel = off - target
            annotations = []
            if iv < len(data):
                annotations.append('abs-file-offset?')
            if target + iv < len(data):
                annotations.append('object-relative-offset?')
            if iv in strings:
                annotations.append('string=%s' % strings[iv])
            print('+0x%03X  u32=0x%08X (%u)  f32=% .7g  %s' %
                  (rel, iv, iv, fv, ', '.join(annotations)))

        print('')
        print('[POTENTIAL STRING REFERENCES]')
        found = 0
        for j in range(words):
            off = target + j * 4
            iv = u32(data, off)
            if iv in strings and strings[iv] != '':
                print('+0x%03X -> string rel 0x%X: %s' %
                      (off - target, iv, strings[iv]))
                found += 1
        if found == 0:
            print('(none in first %d words)' % words)

        print('')
        print('[POTENTIAL IN-FILE POINTERS]')
        found = 0
        for j in range(words):
            off = target + j * 4
            iv = u32(data, off)
            if target <= iv < len(data):
                print('+0x%03X -> absolute 0x%X' % (off - target, iv))
                found += 1
            elif 0 < iv < len(data) - target:
                print('+0x%03X -> object-relative candidate 0x%X (absolute 0x%X)' %
                      (off - target, iv, target + iv))
                found += 1
        if found == 0:
            print('(none in first %d words)' % words)

    print('')
    print('Read-only diagnostic complete. No EBO bytes were changed.')
    print('IMPORTANT: raw values are not yet decoded as vertex counts or arrays.')

def main():
    path = rs.OpenFileName('Select NBA Live 06 EBO file',
        'NBA Live EBO (*.ebo)|*.ebo||')
    if not path:
        print('Cancelled.')
        return
    try:
        inspect(read_file(path), path)
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
