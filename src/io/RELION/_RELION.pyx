import cython
cimport cython

from libc.math cimport sin, cos, atan2, sqrt, fabs, M_PI
from libc.float cimport FLT_MIN, DBL_MIN
#from libc.stdlib cimport fabs

import numpy as np
cimport numpy as np

#from cython.cimports.libc.math import sin, cos, atan2, sqrt, abs

cdef float EPSILON = FLT_MIN
cdef float EPSILON16 = 16 * EPSILON

#cdef float M_PI = 	3.14159265358979323846

#DTYPE = np.float64

cdef cython.double sign(const cython.double x):
    cdef cython.double zero = 0
    return (zero < x) - (x < zero)

#src/jaz/math/Euler_angles_relion.h
@cython.boundscheck(False)  # Deactivate bounds checking
@cython.wraparound(False)   # Deactivate negative indexing.
cpdef void rot_from_matrix(const cython.double[:, ::1] matrix, cython.double[:] out1, cython.double[:] out2, cython.double[:] out3) nogil:

    cdef cython.double st2 = matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2];
    out2[0] = atan2(sqrt(st2), matrix[2, 2])

    #cdef double rot1 = 0.0
    #cdef double rot3 = 0.0

    if st2 > DBL_MIN:
        out1[0] = atan2(matrix[2, 0], -matrix[2, 1])
        out3[0] = atan2(matrix[2, 1], matrix[2,0])
    else:
        if matrix[2, 2] > 0:
            out1[0] = 0
            out3[0] = atan2(-matrix[1, 0], matrix[0, 0])
        else:
            out1[0] = 0
            out3[0] = atan2(matrix[1, 0], -matrix[0, 0])

# #src/jaz/math/Euler_angles_relion.h
# @cython.boundscheck(False)  # Deactivate bounds checking
# @cython.wraparound(False)   # Deactivate negative indexing.
# cpdef rot_from_matrix(const double[:, :] matrix, double[:] out):
#
#     cdef double st2 = matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2];
#     out[1] = atan2(sqrt(st2), matrix[2, 2])
#
#     #cdef double rot1 = 0.0
#     #cdef double rot3 = 0.0
#
#     if st2 > DBL_MIN:
#         out[0] = atan2(matrix[2, 0], -matrix[2, 1])
#         out[2] = atan2(matrix[2, 1], matrix[2,0])
#     else:
#         if matrix[2, 2] > 0:
#             out[0] = 0
#             out[2] = atan2(-matrix[1, 0], matrix[0, 0])
#         else:
#             out[0] = 0
#             out[2] = atan2(matrix[1, 0], -matrix[0, 0])

    #return rot1 * 180.0 / M_PI, rot2 * 180.0 / M_PI, rot3 * 180.0 / M_PI


cdef float rot1_from_matrix(float[:, :] matrix):
    """rlnAngleRot -- Phi"""

    cdef float abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        #angle = np.arctan2(matrix[2, 1], matrix[2, 0])
        angle = atan2(matrix[2, 1], matrix[2, 0])
    else:
        angle = 0

    return angle * 180.0 / M_PI

def rot1_from_matrix(float[:, :] matrix):
    """rlnAngleRot -- Phi"""

    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        #angle = np.arctan2(matrix[2, 1], matrix[2, 0])
        angle = atan2(matrix[2, 1], matrix[2, 0])
    else:
        angle = 0

    return angle * 180.0 / M_PI

def rot2_from_matrix(float[:, :] matrix):
    """rlnAngleTilt -- Theta"""

    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        sign_sb = _sign_rot2(matrix)
        #angle = np.arctan2(sign_sb * abs_sb, matrix[2, 2])
        angle = atan2(sign_sb * abs_sb, matrix[2, 2])
    else:
        #if np.sign(matrix[2, 2]) > 0:
        if sign(matrix[2, 2]) > 0:
            angle = 0
        else:
            angle = M_PI#np.pi

    return angle * 180.0 / M_PI

def rot3_from_matrix(float[:, :] matrix):
    """Psi"""
    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        #angle = np.arctan2(matrix[1, 2], -matrix[0, 2])
        angle = atan2(matrix[1, 2], -matrix[0, 2])
    else:
        #if np.sign(matrix[2, 2]) > 0:
        if sign(matrix[2, 2]) > 0:
            #angle = np.arctan2(-matrix[1, 0], matrix[0, 0])
            angle = atan2(-matrix[1, 0], matrix[0, 0])
        else:
            #angle = np.arctan2(matrix[1, 0], -matrix[0, 0])
            angle = atan2(matrix[1, 0], -matrix[0, 0])

    return angle * 180.0 / M_PI

def _abs_sb(float[:, :] matrix):
    #abs_sb = np.sqrt(matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2])
    abs_sb = sqrt(matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2])

    if abs_sb > EPSILON16:
        return abs_sb
    else:
        return None

def _sign_rot2(float[:,:] matrix):
    #rot3 = np.arctan2(matrix[1, 2], -matrix[0, 2])
    rot3 = atan2(matrix[1, 2], -matrix[0, 2])

    #if np.abs(np.sin(rot3)) < EPSILON:
    if fabs(sin(rot3)) < EPSILON:
        #sign_sb = np.sign(-matrix[0, 2] / np.cos(rot3))
        sign_sb = sign(-matrix[0, 2] / cos(rot3))
    else:
        #sign_sb = np.sign(matrix[1, 2]) if (np.sin(rot3) > 0) else -np.sign(matrix[1, 2])
        sign_sb = sign(matrix[1, 2]) if (sin(rot3) > 0) else -sign(matrix[1, 2])

    return sign_sb