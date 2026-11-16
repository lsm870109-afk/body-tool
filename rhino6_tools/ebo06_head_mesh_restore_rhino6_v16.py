# -*- coding: utf-8 -*-
# NBA Live 06 HEAD MESH RESTORE V16.2
# Rhino 6 / IronPython 2.7
# Uses the V15-verified 573 -> 733 map and the unique index/UV buffer
# detection rules from EBOTools player_morph_core.py.
# READ ONLY: source EBO bytes are never modified.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import Rhino
import scriptcontext as sc
import math
import System

def bval(d,o): return int(d[o])
def u16(d,o): return bval(d,o) | (bval(d,o+1)<<8)
def u32(d,o):
    return (bval(d,o) | (bval(d,o+1)<<8) |
            (bval(d,o+2)<<16) | (bval(d,o+3)<<24))
def f32(d,o): return float(BitConverter.ToSingle(d,o))

def chunk_ranges(d):
    p=u32(d,0x10); count=u16(d,0x24); out=[]
    for i in range(count):
        if p+0x14>len(d): break
        size=u32(d,p+0x10)
        if size<0x14 or p+size>len(d): break
        out.append((p,p+size)); p+=size
    return out

def owner_start(ranges,off):
    for s,e in ranges:
        if s<=off<e: return s
    return -1

def validate_mapping_record(d,off,ranges):
    if off<0 or off+24>len(d): return None
    logical=u32(d,off); one=u32(d,off+4); rendered=u32(d,off+8)
    pos=u32(d,off+12); mp=u32(d,off+16); vb=u32(d,off+20)
    if logical!=573 or one!=1 or rendered<3 or rendered>5000: return None
    if mp>len(d)-rendered*2 or pos>len(d)-rendered*12 or vb+12>len(d): return None
    if u32(d,vb+4)!=12 or u32(d,vb)!=rendered*12 or u32(d,vb+8)!=pos: return None
    vals=[u16(d,mp+i*2) for i in range(rendered)]
    if min(vals)!=0 or max(vals)!=572 or len(set(vals))!=573: return None
    return (off,logical,rendered,pos,mp,owner_start(ranges,off),vals)

def find_head_mapping(d):
    ranges=chunk_ranges(d)
    item=validate_mapping_record(d,0x102B8,ranges)
    if item is not None: return item
    found=[]
    for off in range(0,len(d)-24,4):
        item=validate_mapping_record(d,off,ranges)
        if item is not None: found.append(item)
    if len(found)!=1:
        raise ValueError('Expected one V15-verified head map; matches=%d size=%d' % (len(found),len(d)))
    return found[0]

# Port of EBOTools _find_unique_index_buffer criteria.
def find_index_buffer(d,rendered):
    found=[]
    for off in range(0,len(d)-24,4):
        size=u32(d,off); stride=u32(d,off+4); ptr=u32(d,off+8)
        if stride!=2 or size<6 or size%2 or ptr>len(d)-size: continue
        count=size//2
        if count==0: continue
        vals=[u16(d,ptr+i*2) for i in range(count)]
        if max(vals)!=rendered-1 or len(set(vals))!=rendered: continue
        found.append((off,ptr,size,vals))
    if len(found)!=1:
        raise ValueError('Expected one unique %d-vertex index buffer; found %d' % (rendered,len(found)))
    return found[0]

# Port of EBOTools _find_unique_uv_buffer criteria.
def find_uv_buffer(d,rendered):
    wanted=rendered*8; found=[]
    for off in range(0,len(d)-28,4):
        size=u32(d,off); stride=u32(d,off+4); ptr=u32(d,off+8)
        if size!=wanted or stride!=8 or ptr>len(d)-wanted: continue
        vals=[f32(d,ptr+i*4) for i in range(rendered*2)]
        if any(math.isnan(v) or math.isinf(v) for v in vals): continue
        if min(vals)<-16.0 or max(vals)>16.0: continue
        found.append((off,ptr,size,vals))
    if len(found)!=1:
        raise ValueError('Expected one unique %d-vertex UV buffer; found %d' % (rendered,len(found)))
    return found[0]

def strip_faces(indices):
    faces=[]
    for i in range(len(indices)-2):
        a=indices[i]; b=indices[i+1]; c=indices[i+2]
        if a==b or b==c or a==c: continue
        if i&1: a,b=b,a
        faces.append((a,b,c))
    return faces

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select base_lodB.ebo (204,248 bytes; not a player Morph EBO)'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=False
    if dlg.ShowDialog()!=DialogResult.OK:
        print('Cancelled.'); return
    path=dlg.FileName; d=File.ReadAllBytes(path)
    if len(d)<0x60 or bval(d,0)!=69 or bval(d,1)!=66 or bval(d,2)!=79 or bval(d,3)!=0:
        raise ValueError('Selected file is not an EBO.')
    if len(d)==17724 or len(d)==10800:
        raise ValueError('Selected file appears to be a player Morph EBO. Select base_lodB.ebo.')

    record,logical,rendered,posptr,mapptr,owner,mapping=find_head_mapping(d)
    positions=[]
    for i in range(rendered):
        p=(f32(d,posptr+i*12),f32(d,posptr+i*12+4),f32(d,posptr+i*12+8))
        if any(math.isnan(v) or math.isinf(v) for v in p):
            raise ValueError('Non-finite position at rendered vertex %d' % i)
        positions.append(p)

    idx_header,idx_ptr,idx_size,indices=find_index_buffer(d,rendered)
    uv_header,uv_ptr,uv_size,uvvals=find_uv_buffer(d,rendered)
    faces=strip_faces(indices)
    if not faces: raise ValueError('Decoded triangle strip contains no faces.')
    for tri in faces:
        if min(tri)<0 or max(tri)>=rendered:
            raise ValueError('Decoded face index is outside rendered vertex range.')

    mesh=Rhino.Geometry.Mesh()
    for p in positions: mesh.Vertices.Add(p[0],p[1],p[2])
    for a,b,c in faces: mesh.Faces.AddFace(a,b,c)
    for i in range(rendered):
        mesh.TextureCoordinates.Add(uvvals[i*2],uvvals[i*2+1])
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    if mesh.Vertices.Count!=rendered or mesh.Faces.Count!=len(faces):
        raise ValueError('Rhino mesh vertex/face count validation failed.')

    attr=Rhino.DocObjects.ObjectAttributes()
    attr.Name='NBA06_headAShape_restored_from_EBO_V16_2'
    attr.SetUserString('SourceFile',path)
    attr.SetUserString('LogicalVertices',str(logical))
    attr.SetUserString('RenderedVertices',str(rendered))
    attr.SetUserString('PositionBuffer','0x%X' % posptr)
    attr.SetUserString('MapBuffer','0x%X' % mapptr)
    attr.SetUserString('IndexHeader','0x%X' % idx_header)
    attr.SetUserString('IndexBuffer','0x%X' % idx_ptr)
    attr.SetUserString('IndexCount',str(len(indices)))
    attr.SetUserString('UVBuffer','0x%X' % uv_ptr)
    attr.SetUserString('Topology','Triangle strip; alternating winding')
    gid=sc.doc.Objects.AddMesh(mesh,attr)
    if gid==System.Guid.Empty: raise ValueError('Rhino failed to add restored mesh.')
    sc.doc.Views.Redraw()

    print('')
    print('='*76)
    print('V16.2 HEAD MESH RESTORE COMPLETE')
    print('SOURCE=%s' % path)
    print('HEAD_CHUNK=0x%X MAP_RECORD=0x%X' % (owner,record))
    print('LOGICAL_VERTICES=%d RENDERED_VERTICES=%d' % (logical,rendered))
    print('POSITION_BUFFER=0x%X MAP_BUFFER=0x%X' % (posptr,mapptr))
    print('INDEX_HEADER=0x%X INDEX_BUFFER=0x%X INDEX_BYTES=%d INDEX_COUNT=%d' %
          (idx_header,idx_ptr,idx_size,len(indices)))
    print('UV_HEADER=0x%X UV_BUFFER=0x%X UV_BYTES=%d' % (uv_header,uv_ptr,uv_size))
    print('RHINO_MESH_VERTICES=%d RHINO_MESH_FACES=%d' % (mesh.Vertices.Count,mesh.Faces.Count))
    print('EBO_SOURCE_MODIFIED=NO')
    print('NOTE: index and strip decoding follow EBOTools player_morph_core.py rules.')
    print('='*76)

if __name__=='__main__':
    main()
