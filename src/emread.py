'''
Reads .em file and returns just the 3D-data-matrix.
'''

import numpy as np
import struct


def emread(em_name):
    with open(em_name,"rb") as fin:
        machine=struct.unpack("b",fin.read(1))
        header=struct.unpack("bb",fin.read(2))
        data_type=struct.unpack("b",fin.read(1))

        fin.close()

    if machine[0]==6:
        endian="<"
    elif machine[0]==3 or machine[0]==5 or machine[0]==0:
        endian=">"
    else:
        print("Wrong File Format:")
        print(machine[0])

    with open(em_name,"rb") as fin:
        header_list=[]
        header_list.append(struct.unpack("i",fin.read(4)))
        header_list.append(struct.unpack("i",fin.read(4)))
        header_list.append(struct.unpack("i",fin.read(4)))
        header_list.append(struct.unpack("i",fin.read(4)))
        fin.read(496)
        xdim=header_list[1][0]
        ydim=header_list[2][0]
        zdim=header_list[3][0]
        # print(str(fin.read(496)))


        if data_type[0]==5:
            dat=np.reshape(struct.unpack(endian+(xdim*ydim*zdim)*"f",fin.read(4*xdim*ydim*zdim)),(zdim,ydim,xdim))
        elif data_type[0]==1:
            dat=np.reshape(struct.unpack(endian+(xdim*ydim*zdim)*"b",fin.read(xdim*ydim*zdim)),(zdim,ydim,xdim))
        elif data_type[0]==2:
            dat=np.reshape(struct.unpack(endian+(xdim*ydim*zdim)*"h",fin.read(2*xdim*ydim*zdim)),(zdim,ydim,xdim))
        else:
            print("Wrong Data Type:")
            print(data_type[0])
            return
        fin.close()

    return dat
