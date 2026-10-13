import json,struct,numpy as np
from pathlib import Path
def arrays(path):
 blob=path.read_bytes();offset=12;doc=None;binary=None
 while offset<len(blob):
  size,kind=struct.unpack_from('<II',blob,offset);chunk=blob[offset+8:offset+8+size]
  if kind==0x4e4f534a:doc=json.loads(chunk)
  if kind==0x004e4942:binary=chunk
  offset+=8+size
 dims={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16};types={5121:np.uint8,5123:np.dtype('<u2'),5125:np.dtype('<u4'),5126:np.dtype('<f4')}
 result=[]
 for ac in doc['accessors']:
  width=dims[ac['type']];dtype=np.dtype(types[ac['componentType']])
  if 'bufferView' in ac:
   view=doc['bufferViews'][ac['bufferView']];start=view.get('byteOffset',0)+ac.get('byteOffset',0)
   points=np.ndarray((ac['count'],width),dtype=dtype,buffer=binary,offset=start,strides=(view.get('byteStride',width*dtype.itemsize),dtype.itemsize)).copy()
  else:points=np.zeros((ac['count'],width),dtype=dtype)
  if 'sparse' in ac:
   sp=ac['sparse'];inds=sp['indices'];vals=sp['values'];iv=doc['bufferViews'][inds['bufferView']];vv=doc['bufferViews'][vals['bufferView']]
   ids=np.frombuffer(binary,dtype=types[inds['componentType']],count=sp['count'],offset=iv.get('byteOffset',0)+inds.get('byteOffset',0))
   ps=np.frombuffer(binary,dtype=dtype,count=sp['count']*width,offset=vv.get('byteOffset',0)+vals.get('byteOffset',0)).reshape(-1,width);points[ids]=ps
  result.append(points)
 return doc,result

def xyz_to_blender(points):return points[:,[0,2,1]]*np.array([1,-1,1])
