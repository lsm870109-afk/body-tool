# -*- coding: utf-8 -*-
# NBA Live 06 Morph EBO -> Rhino Mesh using verified clean OBJ topology
# Rhino 6 / IronPython 2.7
#
# V18 purpose:
#   Import a player Morph EBO directly as a Rhino mesh.
#   The neutral OBJ is used ONLY as the trusted vertex-order + face-topology
#   template. Its positions are displaced by the EBO coordinate deltas.
#
# Verified against:
#   06_head_neutral_mesh.obj (573 vertices / 1128 triangles)
#   damilicB.ebo (573 XYZ deltas; payload offset 0x1BC; 6876 bytes)
#   damilicB (2).obj (all 1719 output coordinates match within float rounding)
#
# READ ONLY: source EBO and OBJ are never modified.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
import System
import math


def open_file(title, filter_text):
    dlg = OpenFileDialog()
    dlg.Title = title
    dlg.Filter = filter_text
    dlg.Multiselect = False
    if dlg.ShowDialog() != DialogResult.OK:
        return None
    return dlg.FileName


def read_obj_template(path):
    lines = File.ReadAllLines(path)
    vertices = []
    faces = []

    for line_no, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        if line.startswith('v '):
            parts = line.split()
            if len(parts) < 4:
                raise ValueError('Invalid OBJ vertex at line %d' % (line_no + 1))
            p = (float(parts[1]), float(parts[2]), float(parts[3]))
            if not all_finite(p):
                raise ValueError('Non-finite OBJ vertex at line %d' % (line_no + 1))
            vertices.append(p)

        elif line.startswith('f '):
            tokens = line.split()[1:]
            indices = []
            for token in tokens:
                vtext = token.split('/')[0]
                if not vtext:
                    raise ValueError('Missing position index in OBJ face at line %d' % (line_no + 1))
                idx = int(vtext)
                if idx < 0:
                    idx = len(vertices) + idx
                else:
                    idx -= 1
                if idx < 0 or idx >= len(vertices):
                    raise ValueError('OBJ face index out of range at line %d' % (line_no + 1))
                indices.append(idx)

            if len(indices) < 3:
                raise ValueError('OBJ face has fewer than 3 vertices at line %d' % (line_no + 1))

            # Same fan triangulation as the verified HTML converter.
            for k in range(1, len(indices) - 1):
                a, b, c = indices[0], indices[k], indices[k + 1]
                if a != b and b != c and a != c:
                    faces.append((a, b, c))

    if len(vertices) != 573:
        raise ValueError('Expected 573 logical OBJ vertices; found %d' % len(vertices))
    if len(faces) != 1128:
        raise ValueError('Expected 1128 clean OBJ triangles; found %d' % len(faces))

    return vertices, faces


def all_finite(values):
    for value in values:
        if math.isnan(value) or math.isinf(value):
            return False
    return True


def read_morph_deltas(path, vertex_count):
    data = File.ReadAllBytes(path)

    if len(data) < 0x124:
        raise ValueError('EBO file is too small.')
    if int(data[0]) != 0x45 or int(data[1]) != 0x42 or int(data[2]) != 0x4F or int(data[3]) != 0:
        raise ValueError('Selected file does not have EBO magic.')

    # Layout verified with the actual damilicB.ebo file.
    size = int(BitConverter.ToUInt32(data, 0x11C))
    offset = int(BitConverter.ToUInt32(data, 0x120))
    expected = vertex_count * 12

    if size != expected:
        raise ValueError('Morph stream vertex count mismatch: EBO=%d, OBJ=%d' %
                         (size // 12, vertex_count))
    if offset < 0 or offset + size > len(data):
        raise ValueError('Morph coordinate stream is outside the EBO file.')

    deltas = []
    for i in range(vertex_count):
        x = float(BitConverter.ToSingle(data, offset + i * 12))
        y = float(BitConverter.ToSingle(data, offset + i * 12 + 4))
        z = float(BitConverter.ToSingle(data, offset + i * 12 + 8))
        if not all_finite((x, y, z)):
            raise ValueError('Non-finite EBO delta at vertex %d' % (i + 1))
        deltas.append((x, y, z))

    return deltas, offset, size, len(data)


def main():
    ebo_path = open_file('1/2 - Select player Morph EBO (e.g. damilicB.ebo)',
                         'EBO files (*.ebo)|*.ebo|All files (*.*)|*.*')
    if not ebo_path:
        print('Cancelled.')
        return

    obj_path = open_file('2/2 - Select neutral topology OBJ (06_head_neutral_mesh.obj)',
                         'OBJ files (*.obj)|*.obj|All files (*.*)|*.*')
    if not obj_path:
        print('Cancelled.')
        return

    try:
        base_vertices, faces = read_obj_template(obj_path)
        deltas, stream_offset, stream_size, ebo_size = read_morph_deltas(
            ebo_path, len(base_vertices))

        strength = rs.GetReal('Morph strength (1.0 = 100%)', 1.0, -5.0, 5.0)
        if strength is None:
            print('Cancelled.')
            return

        mesh = Rhino.Geometry.Mesh()
        for i in range(len(base_vertices)):
            b = base_vertices[i]
            d = deltas[i]
            mesh.Vertices.Add(
                b[0] + d[0] * strength,
                b[1] + d[1] * strength,
                b[2] + d[2] * strength)

        # Use the exact position-index topology from the clean OBJ.
        for face in faces:
            mesh.Faces.AddFace(face[0], face[1], face[2])

        mesh.FaceNormals.ComputeFaceNormals()
        mesh.Normals.ComputeNormals()

        if not mesh.IsValid:
            raise ValueError('Rhino reports the generated mesh as invalid.')
        if mesh.Vertices.Count != 573 or mesh.Faces.Count != 1128:
            raise ValueError('Generated mesh count validation failed.')

        attr = Rhino.DocObjects.ObjectAttributes()
        attr.Name = 'NBA06_MorphEBO_Imported_CleanTopology'
        attr.SetUserString('SourceMorphEBO', ebo_path)
        attr.SetUserString('TopologyTemplateOBJ', obj_path)
        attr.SetUserString('MorphStrength', str(strength))
        attr.SetUserString('LogicalVertices', '573')
        attr.SetUserString('TriangleFaces', '1128')
        attr.SetUserString('MorphStreamOffset', '0x%X' % stream_offset)
        attr.SetUserString('MorphStreamBytes', str(stream_size))
        attr.SetUserString('TopologySource', 'OBJ position indices; fan triangulation')

        object_id = sc.doc.Objects.AddMesh(mesh, attr)
        if object_id == System.Guid.Empty:
            raise ValueError('Rhino failed to add the mesh to the document.')

        sc.doc.Views.Redraw()

        print('')
        print('=' * 72)
        print('V18 MORPH EBO CLEAN-TOPOLOGY IMPORT: PASS')
        print('Morph EBO: %s' % ebo_path)
        print('Base topology OBJ: %s' % obj_path)
        print('EBO size: %d bytes' % ebo_size)
        print('Morph stream: offset=0x%X bytes=%d' % (stream_offset, stream_size))
        print('Morph strength: %.4f' % strength)
        print('Rhino mesh vertices: %d' % mesh.Vertices.Count)
        print('Rhino triangle faces: %d' % mesh.Faces.Count)
        print('Mesh valid: %s' % str(mesh.IsValid))
        print('Source files modified: NO')
        print('=' * 72)

    except Exception as e:
        print('V18 IMPORT ERROR: ' + str(e))
        Rhino.UI.Dialogs.ShowMessageBox(str(e), 'EBO Clean Topology Import')


if __name__ == '__main__':
    main()
