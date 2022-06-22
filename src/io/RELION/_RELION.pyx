import numpy as np

EPSILON = np.finfo(np.float32).eps
EPSILON16 = 16 * EPSILON

def rot1_from_matrix(matrix):
    """rlnAngleRot -- Phi"""

    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        angle = np.arctan2(matrix[2, 1], matrix[2, 0])
    else:
        angle = 0

    return angle * 180.0 / np.pi

def rot2_from_matrix(matrix):
    """rlnAngleTilt -- Theta"""

    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        sign_sb = _sign_rot2(matrix)
        angle = np.arctan2(sign_sb * abs_sb, matrix[2, 2])
    else:
        if np.sign(matrix[2, 2]) > 0:
            angle = 0
        else:
            angle = np.pi

    return angle * 180.0 / np.pi

def rot3_from_matrix(matrix):
    """Psi"""
    abs_sb = _abs_sb(matrix)

    if abs_sb is not None:
        angle = np.arctan2(matrix[1, 2], -matrix[0, 2])
    else:
        if np.sign(matrix[2, 2]) > 0:
            angle = np.arctan2(-matrix[1, 0], matrix[0, 0])
        else:
            angle = np.arctan2(matrix[1, 0], -matrix[0, 0])

    return angle * 180.0 / np.pi

def _abs_sb(matrix):
    abs_sb = np.sqrt(matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2])

    if abs_sb > EPSILON16:
        return abs_sb
    else:
        return None

def _sign_rot2(matrix):
    rot3 = np.arctan2(matrix[1, 2], -matrix[0, 2])

    if np.abs(np.sin(rot3)) < EPSILON:
        sign_sb = np.sign(-matrix[0, 2] / np.cos(rot3))
    else:
        sign_sb = np.sign(matrix[1, 2]) if (np.sin(rot3) > 0) else -np.sign(matrix[1, 2])

    return sign_sb