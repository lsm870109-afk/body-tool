# -*- coding: utf-8 -*-
# NBA Live 06 HEAD MESH RESTORE V16
# Rhino 6 / IronPython 2.7
# READ ONLY: reads base_lodB.ebo and creates a Rhino Mesh only when
# one structurally valid 733-vertex triangle-strip index buffer is found.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import Rhino
import scriptcontext as sc
import math

def bval(d,o):
    return int(d[o])

def u16(d,o):
    return bval(d,o) | (bval(d,o+1)<<8)

def u32(d,o):
    return (bval(d,o) | (bval(d,o+1)<<8) |
            (bval(d,o+2)<<16) | (bval(d,o+3)<<24))

def f32(d,o):
    return float(BitConverter.ToSingle(d,o))

def chunk_ranges(d):
    p=u32(d,0x10)
    count=u16(d,0x24)
    out=[]
    for i in range(count):
        if p+0x14>len(d): break
        size=u32(d,p+0x10)
        if size<0x14 or p+size>len(d): break
        out.append((p,p+size))
        p+=size
    return out

def owner_start(ranges,off):
    for s,e in ranges:
        if s<=off<e: return s
    return -1

def find_head_mapping(d):
    ranges=chunk_ranges(d)
    found=[]
    # V14/V15 verified mapping record at 0x102B8 for this base file.
    for off in range(0,len(d)-24,4):
        logical=u32(d,off)
        if logical!=573 or u32(d,off+4)!=1:
            continue
        rendered=u32(d,off+8)
        pos=u32(d,off+12)
        mp=u32(d,off+16)
        vb=u32(d,off+20)
        if rendered!=733: continue
        if mp>len(d)-rendered*2 or pos>len(d)-rendered*12 or vb+12>len(d): continue
        if u32(d,vb)!=rendered*12 or u32(d,vb+4)!=12 or u32(d,vb+8)!=pos: continue
        vals=[u16(d,mp+i*2) for i in range(rendered)]
        if min(vals)!=0 or max(vals)!=572 or len(set(vals))!=573: continue
        found.append((off,logical,rendered,pos,mp,owner_start(ranges,off),vals))
    if not found:
        off=0x102B8
        if off+24<=len(d):
            logical=u32(d,off); rendered=u32(d,off+8)
            pos=u32(d,off+12); mp=u32(d,off+16); vb=u32(d,off+20)
            if (logical==573 and u32(d,off+4)==1 and rendered==733 and
                mp<=len(d)-rendered*2 and pos<=len(d)-rendered*12 and vb+12<=len(d) and
                u32(d,vb)==rendered*12 and u32(d,vb+4)==12 and u32(d,vb+8)==pos):
                vals=[u16(d,mp+i*2) for i in range(rendered)]
                if min(vals)==0 and max(vals)==572 and len(set(vals))==573:
                    found.append((off,logical,rendered,pos,mp,owner_start(ranges,off),vals))
    if len(found)!=1:
        raise ValueError('Expected one verified head map; found %d' % len(found))
    return found[0]

def find_index_buffers(d,rendered):
    found=[]
    for off in range(0,len(d)-12,4):
        size=u32(d,off)
        stride=u32(d,off+4)
        ptr=u32(d,off+8)
        if stride!=2 or size<6 or size%2:
            continue
        if ptr>len(d)-size:
            continue
        count=size//2
        # Avoid pathological scans and require an index stream with the
        # complete rendered-vertex domain, matching the known EBO parser.
        if count<rendered or count>200000:
            continue
        vals=[u16(d,ptr+i*2) for i in range(count)]
        if max(vals)!=rendered-1 or min(vals)<0 or len(set(vals))!=rendered:
            continue
        found.append((off,ptr,size,vals))
    return found

def strip_faces(indices):
    faces=[]
    for i in range(len(indices)-2):
        a=indices[i-2] if False else indices[i]
        b=indices[i+1]
        c=indices[i+2]
        if a==b or b==c or a==c:
            continue
        if i & 1:
            a,b=b,a
        faces.append((a,b,c))
    return faces

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select the same base_lodB.ebo used in V15'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=False
    if dlg.ShowDialog()!=DialogResult.OK:
        print('Cancelled.')
        return
    path=dlg.FileName
    d=File.ReadAllBytes(path)
    if len(d)<0x60 or bval(d,0)!=69 or bval(d,1)!=66 or bval(d,2)!=79 or bval(d,3)!=0:
        print('ERROR: invalid EBO file')
        return

    record,logical,rendered,posptr,mapptr,owner,mapping=find_head_mapping(d)
    positions=[]
    for i in range(rendered):
        x=f32(d,posptr+i*12)
        y=f32(d,posptr+i*12+4)
        z=f32(d,posptr+i*12+8)
        if (math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y) or
            math.isnan(z) or math.isinf(z)):
            raise ValueError('Non-finite vertex position at %d' % i)
        positions.append((x,y,z))

    candidates=find_index_buffers(d,rendered)
    print('')
    print('='*76)
    print('V16 HEAD INDEX / MESH RESTORE DIAGNOSTIC')
    print('SOURCE=%s' % path)
    print('HEAD_CHUNK=0x%X MAP_RECORD=0x%X' % (owner,record))
    print('POSITIONS=%d POSITION_BUFFER=0x%X' % (len(positions),posptr))
    print('INDEX_BUFFER_CANDIDATES=%d' % len(candidates))
    for i,item in enumerate(candidates):
        off,ptr,size,vals=item
        print('CANDIDATE[%d] HEADER=0x%X DATA=0x%X BYTES=%d INDICES=%d MIN=%d MAX=%d UNIQUE=%d' %
              (i,off,ptr,size,len(vals),min(vals),max(vals),len(set(vals))))

    if len(candidates)!=1:
        print('MESH_NOT_CREATED: index stream is not uniquely identified.')
        print('No guessed topology was used. Send this complete output.')
        print('='*76)
        return

    idx_header,idx_ptr,idx_size,indices=candidates[0]
    faces=strip_faces(indices)
    if len(faces)==0:
        print('MESH_NOT_CREATED: triangle-strip decoding produced zero faces.')
        return

    mesh=Rhino.Geometry.Mesh()
    for p in positions:
        mesh.Vertices.Add(p[0],p[1],p[2])
    for a,b,c in faces:
        mesh.Faces.AddFace(a,b,c)
    mesh.Normals.ComputeNormals()
    mesh.Compact()

    if mesh.Vertices.Count!=rendered or mesh.Faces.Count!=len(faces):
        raise ValueError('Rhino mesh count mismatch after creation.')

    attr=Rhino.DocObjects.ObjectAttributes()
    attr.Name='NBA06_headAShape_restored_from_EBO_V16'
    attr.SetUserString('SourceFile',path)
    attr.SetUserString('PositionBuffer','0x%X' % posptr)
    attr.SetUserString('IndexHeader','0x%X' % idx_header)
    attr.SetUserString('IndexBuffer','0x%X' % idx_ptr)
    attr.SetUserString('IndexCount',str(len(indices)))
    attr.SetUserString('Topology','Triangle strip')
    gid=sc.doc.Objects.AddMesh(mesh,attr)
    if gid==System.Guid.Empty:
        raise ValueError('Rhino failed to add restored mesh.')
    sc.doc.Views.Redraw()

    print('')
    print('MESH_RESTORE=SUCCESS')
    print('RHINO_VERTICES=%d RHINO_FACES=%d' % (mesh.Vertices.Count,mesh.Faces.Count))
    print('INDEX_HEADER=0x%X INDEX_DATA=0x%X INDEX_COUNT=%d' %
          (idx_header,idx_ptr,len(indices)))
    print('EBO_SOURCE_MODIFIED=NO')
    print('NOTE: Mesh topology decoded as an alternating-winding triangle strip.')
    print('='*76)

if __name__=='__main__':
    main()
