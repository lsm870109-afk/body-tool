# -*- coding: utf-8 -*-
"""
NBA Live 06 Morph EBO exporter - Rhino 6 / IronPython 2.7
Creates a new morph EBO by replacing only the 573-vertex XYZ delta payload.
Original EBO and OBJ files are never modified.
"""

import os
import struct
import math
import rhinoscriptsyntax as rs
import scriptcontext as sc

EXPECTED_VERTICES = 573
EXPECTED_TRIANGLES = 1128
EXPECTED_PAYLOAD_SIZE = EXPECTED_VERTICES * 3 * 4
HEADER_SIZE_FIELD = 0x11C
HEADER_OFFSET_FIELD = 0x120


def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()


def write_file(path, data):
    f = open(path, 'wb')
    try:
        f.write(data)
    finally:
        f.close()


def parse_obj(path):
    vertices = []
    triangles = []

    f = open(path, 'r')
    try:
        for line_number, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if not parts:
                continue

            if parts[0] == 'v':
                if len(parts) < 4:
                    raise Exception('OBJ vertex has fewer than 3 coordinates at line %d' % line_number)
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))

            elif parts[0] == 'f':
                if len(parts) < 4:
                    raise Exception('OBJ face has fewer than 3 vertices at line %d' % line_number)

                face_indices = []
                for token in parts[1:]:
                    # OBJ face tokens can be v, v/vt, or v/vt/vn.
                    raw_index = token.split('/')[0]
                    if not raw_index:
                        raise Exception('Missing OBJ position index at line %d' % line_number)

                    index = int(raw_index)
                    if index < 0:
                        index = len(vertices) + index
                    else:
                        index = index - 1

                    if index < 0 or index >= len(vertices):
                        raise Exception('OBJ position index out of range at line %d' % line_number)
                    face_indices.append(index)

                # Match the same fan triangulation used by the clean-topology importer.
                for i in range(1, len(face_indices) - 1):
                    triangles.append((face_indices[0], face_indices[i], face_indices[i + 1]))
    finally:
        f.close()

    return vertices, triangles


def read_u32(data, offset, label):
    if len(data) < offset + 4:
        raise Exception('EBO is too short to read %s at 0x%X' % (label, offset))
    return struct.unpack_from('<I', data, offset)[0]


def main():
    ebo_path = rs.OpenFileName(
        'Select ORIGINAL NBA Live 06 morph EBO (for example damilicB.ebo)',
        'EBO files (*.ebo)|*.ebo||')
    if not ebo_path:
        return

    base_obj_path = rs.OpenFileName(
        'Select neutral base OBJ (06_head_neutral_mesh.obj)',
        'OBJ files (*.obj)|*.obj||')
    if not base_obj_path:
        return

    edited_obj_path = rs.OpenFileName(
        'Select edited clean-topology OBJ (for example aliversB.obj)',
        'OBJ files (*.obj)|*.obj||')
    if not edited_obj_path:
        return

    try:
        base_vertices, base_faces = parse_obj(base_obj_path)
        edited_vertices, edited_faces = parse_obj(edited_obj_path)

        if len(base_vertices) != EXPECTED_VERTICES:
            raise Exception('Neutral OBJ must contain %d positions; found %d' %
                            (EXPECTED_VERTICES, len(base_vertices)))
        if len(edited_vertices) != EXPECTED_VERTICES:
            raise Exception('Edited OBJ must contain %d positions; found %d' %
                            (EXPECTED_VERTICES, len(edited_vertices)))

        if len(base_faces) != EXPECTED_TRIANGLES:
            raise Exception('Neutral OBJ must contain %d triangles; found %d' %
                            (EXPECTED_TRIANGLES, len(base_faces)))
        if len(edited_faces) != EXPECTED_TRIANGLES:
            raise Exception('Edited OBJ must contain %d triangles; found %d' %
                            (EXPECTED_TRIANGLES, len(edited_faces)))

        if base_faces != edited_faces:
            raise Exception('Topology mismatch: face indices/order/winding differ between the two OBJ files.')

        ebo_data = read_file(ebo_path)

        payload_size = read_u32(ebo_data, HEADER_SIZE_FIELD, 'payload size')
        payload_offset = read_u32(ebo_data, HEADER_OFFSET_FIELD, 'payload offset')

        if payload_size != EXPECTED_PAYLOAD_SIZE:
            raise Exception('Unexpected morph payload size: %d bytes (expected %d)' %
                            (payload_size, EXPECTED_PAYLOAD_SIZE))
        if payload_offset < 0 or payload_offset + payload_size > len(ebo_data):
            raise Exception('Morph payload range is outside the EBO file.')
        if len(ebo_data) < 0x124:
            raise Exception('EBO header is incomplete.')

        payload_parts = []
        moved_count = 0
        max_displacement = 0.0
        sum_displacement = 0.0

        for i in range(EXPECTED_VERTICES):
            bx, by, bz = base_vertices[i]
            ex, ey, ez = edited_vertices[i]

            dx = ex - bx
            dy = ey - by
            dz = ez - bz

            displacement = math.sqrt(dx * dx + dy * dy + dz * dz)
            if displacement > 0.000001:
                moved_count += 1
            if displacement > max_displacement:
                max_displacement = displacement
            sum_displacement += displacement

            payload_parts.append(struct.pack('<fff', dx, dy, dz))

        new_payload = ''.join(payload_parts)
        if len(new_payload) != EXPECTED_PAYLOAD_SIZE:
            raise Exception('Internal payload length error: %d' % len(new_payload))

        # Patch only the morph XYZ stream. Every other original byte is retained.
        output_data = (ebo_data[:payload_offset] +
                       new_payload +
                       ebo_data[payload_offset + payload_size:])

        if len(output_data) != len(ebo_data):
            raise Exception('Output size changed unexpectedly.')

        # Verify the new payload and byte-for-byte preservation outside that range.
        if output_data[payload_offset:payload_offset + payload_size] != new_payload:
            raise Exception('Payload verification failed.')

        if output_data[:payload_offset] != ebo_data[:payload_offset]:
            raise Exception('EBO prefix changed unexpectedly.')
        if output_data[payload_offset + payload_size:] != ebo_data[payload_offset + payload_size:]:
            raise Exception('EBO suffix changed unexpectedly.')

        default_name = os.path.splitext(os.path.basename(edited_obj_path))[0] + '_morph.ebo'
        output_path = rs.SaveFileName(
            'Save new morph EBO (original will not be overwritten)',
            'EBO files (*.ebo)|*.ebo||',
            os.path.dirname(edited_obj_path),
            default_name)
        if not output_path:
            return

        if os.path.abspath(output_path).lower() == os.path.abspath(ebo_path).lower():
            raise Exception('Output path must be different from the original EBO.')

        write_file(output_path, output_data)

        # Re-open and verify the saved file too.
        saved_data = read_file(output_path)
        if len(saved_data) != len(ebo_data):
            raise Exception('Saved EBO size verification failed.')
        if saved_data[payload_offset:payload_offset + payload_size] != new_payload:
            raise Exception('Saved EBO payload verification failed.')
        if saved_data[:payload_offset] != ebo_data[:payload_offset]:
            raise Exception('Saved EBO header/prefix differs from original.')
        if saved_data[payload_offset + payload_size:] != ebo_data[payload_offset + payload_size:]:
            raise Exception('Saved EBO trailing data differs from original.')

        average_displacement = sum_displacement / float(EXPECTED_VERTICES)

        message = (
            'EBO EXPORT SUCCESS\n\n'
            'Vertices: %d\n'
            'Triangles: %d\n'
            'Moved vertices: %d / %d\n'
            'Max displacement: %.9f\n'
            'Average displacement: %.9f\n'
            'Payload offset: 0x%X (%d)\n'
            'Payload size: %d bytes\n'
            'Original EBO size: %d bytes\n'
            'Saved EBO size: %d bytes\n\n'
            'Only the XYZ morph payload was replaced.\n'
            'All bytes outside the payload were verified unchanged.\n\n'
            'Output:\n%s'
        ) % (EXPECTED_VERTICES, EXPECTED_TRIANGLES,
             moved_count, EXPECTED_VERTICES,
             max_displacement, average_displacement,
             payload_offset, payload_offset, payload_size,
             len(ebo_data), len(saved_data), output_path)

        rs.MessageBox(message, 0, 'NBA Live 06 Morph EBO Exporter V19')

    except Exception as error:
        rs.MessageBox('V19 EXPORT ERROR\n\n%s' % str(error), 0,
                      'NBA Live 06 Morph EBO Exporter V19')


if __name__ == '__main__':
    main()
