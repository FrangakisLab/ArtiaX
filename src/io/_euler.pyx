from libc.math cimport sin, cos, M_PI

cpdef rot_x(double angle, double[:, :] arr):
    ca = cos(angle * M_PI/180)
    sa = sin(angle * M_PI/180)

    arr[0, 0] = 1
    arr[0, 1] = 0
    arr[0, 2] = 0
    arr[1, 0] = 0
    arr[1, 1] = ca
    arr[1, 2] = -sa
    arr[2, 0] = 0
    arr[2, 1] = sa
    arr[2, 2] = ca

cpdef rot_y(double angle, double[:, :] arr):
    ca = cos(angle * M_PI/180)
    sa = sin(angle * M_PI/180)

    arr[0, 0] = ca
    arr[0, 1] = 0
    arr[0, 2] = sa
    arr[1, 0] = 0
    arr[1, 1] = 1
    arr[1, 2] = 0
    arr[2, 0] = -sa
    arr[2, 1] = 0
    arr[2, 2] = ca

cpdef rot_z(double angle, double[:, :] arr):
    ca = cos(angle * M_PI/180)
    sa = sin(angle * M_PI/180)

    arr[0, 0] = ca
    arr[0, 1] = -sa
    arr[0, 2] = 0
    arr[1, 0] = sa
    arr[1, 1] = ca
    arr[1, 2] = 0
    arr[2, 0] = 0
    arr[2, 1] = 0
    arr[2, 2] = 1