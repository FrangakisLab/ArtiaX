'''
This file contains a bunch of functions that are used
to rotate an object using the euler angles
'''

import math as ma
import numpy as np

def detRotMat(phi, psi, theta):
    # Initialize the matrix
    rot_mat = [[0 for i in range(3)] for j in range(3)]

    # Transform angles to radiants
    phi = phi*np.pi/180
    psi = psi*np.pi/180
    theta = theta*np.pi/180

    # Define every entry
    rot_mat[0][0] = np.cos(psi)*np.cos(phi) - np.cos(theta)*np.sin(psi)*np.sin(phi)
    rot_mat[1][0] = np.sin(psi)*np.cos(phi) + np.cos(theta)*np.cos(psi)*np.sin(phi)
    rot_mat[2][0] = np.sin(theta)*np.sin(phi)
    rot_mat[0][1] = -np.cos(psi)*np.sin(phi) - np.cos(theta)*np.sin(psi)*np.cos(phi)
    rot_mat[1][1] = -np.sin(psi)*np.sin(phi) + np.cos(theta)*np.cos(psi)*np.cos(phi)
    rot_mat[2][1] = np.sin(theta)*np.cos(phi)
    rot_mat[0][2] = np.sin(theta)*np.sin(psi)
    rot_mat[1][2] = -np.sin(theta)*np.cos(psi)
    rot_mat[2][2] = np.cos(theta)

    return rot_mat


def detInvRotMat(phi, psi, theta):
    # Initialize the matrix
    rot_mat = [[0 for i in range(3)] for j in range(3)]

    # Transform angles to radiants
    phi = phi*np.pi/180
    psi = psi*np.pi/180
    theta = theta*np.pi/180

    # Define every entry
    rot_mat[0][0] = np.cos(phi)*np.cos(psi) - np.sin(phi)*np.cos(theta)*np.sin(psi)
    rot_mat[1][0] = -np.sin(phi)*np.cos(psi) - np.cos(phi)*np.cos(theta)*np.sin(psi)
    rot_mat[2][0] = np.sin(theta)*np.sin(psi)
    rot_mat[0][1] = np.cos(phi)*np.sin(psi) + np.sin(phi)*np.cos(theta)*np.cos(psi)
    rot_mat[1][1] = -np.sin(phi)*np.sin(psi) + np.cos(phi)*np.cos(theta)*np.cos(psi)
    rot_mat[2][1] = -np.sin(theta)*np.cos(psi)
    rot_mat[0][2] = np.sin(phi)*np.sin(theta)
    rot_mat[1][2] = np.cos(phi)*np.sin(theta)
    rot_mat[2][2] = np.cos(theta)

    return rot_mat


def mulMatMat(mat_1, mat_2):
    out = [[0 for i in range(3)] for j in range(3)]

    out[0][0] = mat_1[0][0]*mat_2[0][0] + mat_1[0][1]*mat_2[1][0] + mat_1[0][2]*mat_2[2][0]
    out[0][1] = mat_1[0][0]*mat_2[0][1] + mat_1[0][1]*mat_2[1][1] + mat_1[0][2]*mat_2[2][1]
    out[0][2] = mat_1[0][0]*mat_2[0][2] + mat_1[0][1]*mat_2[1][2] + mat_1[0][2]*mat_2[2][2]
    out[1][0] = mat_1[1][0]*mat_2[0][0] + mat_1[1][1]*mat_2[1][0] + mat_1[1][2]*mat_2[2][0]
    out[1][1] = mat_1[1][0]*mat_2[0][1] + mat_1[1][1]*mat_2[1][1] + mat_1[1][2]*mat_2[2][1]
    out[1][2] = mat_1[1][0]*mat_2[0][2] + mat_1[1][1]*mat_2[1][2] + mat_1[1][2]*mat_2[2][2]
    out[2][0] = mat_1[2][0]*mat_2[0][0] + mat_1[2][1]*mat_2[1][0] + mat_1[2][2]*mat_2[2][0]
    out[2][1] = mat_1[2][0]*mat_2[0][1] + mat_1[2][1]*mat_2[1][1] + mat_1[2][2]*mat_2[2][1]
    out[2][2] = mat_1[2][0]*mat_2[0][2] + mat_1[2][1]*mat_2[1][2] + mat_1[2][2]*mat_2[2][2]

    return out


def mulVecMat(base_1, rot_mat):
    out = [0, 0, 0]
    rot_matrix = [[0 for i in range(3)] for j in range(3)]

    base1 = base_1
    rot_matrix = rot_mat

    out[0] = rot_matrix[0][0]*base1[0] + rot_matrix[0][1]*base1[1] + rot_matrix[0][2]*base1[2]
    out[1] = rot_matrix[1][0]*base1[0] + rot_matrix[1][1]*base1[1] + rot_matrix[1][2]*base1[2]
    out[2] = rot_matrix[2][0]*base1[0] + rot_matrix[2][1]*base1[1] + rot_matrix[2][2]*base1[2]

    return out


def getEulerAngles(mat):
    theta = np.arccos(mat[2][2])*180.0/np.pi

    if mat[2][2] > 0.999:
        sign = 1
        if mat[1][0] > 0:
            sign = 1.0
        else:
            sign = -1.0
        phi = sign*np.arccos(mat[0][0])*180.0/np.pi
        psi = 0.0
    else:
        phi = ma.atan2(mat[2][0], mat[2][1]) * 180.0/np.pi
        psi = ma.atan2(mat[0][2], -mat[1][2]) * 180.0/np.pi

    return psi, theta, phi


def updateCoordinateSystem(base_1, base_2, base_3, phi, psi, theta):
    # Calculate rotation matrix
    rotation_matrix = detRotMat(phi, psi, theta)

    # Rotate coordinate system
    base_1 = mulVecMat(base_1,rotation_matrix)
    base_2 = mulVecMat(base_2,rotation_matrix)
    base_3 = mulVecMat(base_3,rotation_matrix)

    # return coordinate system
    return base_1, base_2, base_3

# Get list numbers of models with the same name
# def same_name(listnum):

# Finally we have a function that rotates a 3D image using euler angles
# This function is taken from
# https://stackoverflow.com/questions/59738230/apply-rotation-defined-by-euler-angles-to-3d-image-in-python
# Called 31 August 2021
def rotateArray(array, orient):
    phi = orient[0]
    the = orient[1]
    psi = orient[2]

    # create meshgrid
    dim = array.shape
    ax = np.arange(dim[0])
    ay = np.arange(dim[1])
    az = np.arange(dim[2])
    coords = np.meshgrid(ax, ay, az)

    # stack the meshgrid to position vectors, center them around 0 by substracting dim/2
    xyz = np.vstack([coords[0].reshape(-1) - float(dim[0]) / 2,  # x coordinate, centered
                     coords[1].reshape(-1) - float(dim[1]) / 2,  # y coordinate, centered
                     coords[2].reshape(-1) - float(dim[2]) / 2])  # z coordinate, centered

    # create transformation matrix
    r = R.from_euler('zxz', [phi, the, psi], degrees=True)
    mat = r.as_matrix()

    # apply transformation
    transformed_xyz = np.dot(mat, xyz)

    # extract coordinates
    x = transformed_xyz[0, :] + float(dim[0]) / 2
    y = transformed_xyz[1, :] + float(dim[1]) / 2
    z = transformed_xyz[2, :] + float(dim[2]) / 2

    x = x.reshape((dim[1],dim[0],dim[2]))
    y = y.reshape((dim[1],dim[0],dim[2]))
    z = z.reshape((dim[1],dim[0],dim[2])) # reason for strange ordering: see next line

    # the coordinate system seems to be strange, it has to be ordered like this
    new_xyz = [y, x, z]

    # sample
    arrayR = ndimage.map_coordinates(array, new_xyz, order=1)

    return arrayR
