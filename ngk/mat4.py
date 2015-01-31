import array


def create():
    """Return new identity mat4"""
    return array.array('f', [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1])


IDENTITY = create()


def identity(out):
    out[:] = IDENTITY


def invert(out, a):
    """Invert a mat4"""
    (a00, a01, a02, a03, a10, a11, a12, a13, a20, a21, a22, a23, a30, a31,
     a32, a33) = a
    b00 = a00 * a11 - a01 * a10
    b01 = a00 * a12 - a02 * a10
    b02 = a00 * a13 - a03 * a10
    b03 = a01 * a12 - a02 * a11
    b04 = a01 * a13 - a03 * a11
    b05 = a02 * a13 - a03 * a12
    b06 = a20 * a31 - a21 * a30
    b07 = a20 * a32 - a22 * a30
    b08 = a20 * a33 - a23 * a30
    b09 = a21 * a32 - a22 * a31
    b10 = a21 * a33 - a23 * a31
    b11 = a22 * a33 - a23 * a32
    det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06
    if not det:
        return None
    det = 1.0 / det
    out[0] = (a11 * b11 - a12 * b10 + a13 * b09) * det
    out[1] = (a02 * b10 - a01 * b11 - a03 * b09) * det
    out[2] = (a31 * b05 - a32 * b04 + a33 * b03) * det
    out[3] = (a22 * b04 - a21 * b05 - a23 * b03) * det
    out[4] = (a12 * b08 - a10 * b11 - a13 * b07) * det
    out[5] = (a00 * b11 - a02 * b08 + a03 * b07) * det
    out[6] = (a32 * b02 - a30 * b05 - a33 * b01) * det
    out[7] = (a20 * b05 - a22 * b02 + a23 * b01) * det
    out[8] = (a10 * b10 - a11 * b08 + a13 * b06) * det
    out[9] = (a01 * b08 - a00 * b10 - a03 * b06) * det
    out[10] = (a30 * b04 - a31 * b02 + a33 * b00) * det
    out[11] = (a21 * b02 - a20 * b04 - a23 * b00) * det
    out[12] = (a11 * b07 - a10 * b09 - a12 * b06) * det
    out[13] = (a00 * b09 - a01 * b07 + a02 * b06) * det
    out[14] = (a31 * b01 - a30 * b03 - a32 * b00) * det
    out[15] = (a20 * b03 - a21 * b01 + a22 * b00) * det


def multiply(out, a, b):
    (a00, a01, a02, a03, a10, a11, a12, a13, a20, a21, a22, a23, a30, a31,
     a32, a33) = a

    # Cache only the current line of the second matrix
    b0, b1, b2, b3 = b[0:4]
    out[0] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[1] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[2] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[3] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0, b1, b2, b3 = b[4:8]
    out[4] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[5] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[6] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[7] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0, b1, b2, b3 = b[8:12]
    out[8] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[9] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[10] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[11] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0, b1, b2, b3 = b[12:16]
    out[12] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[13] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[14] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[15] = b0*a03 + b1*a13 + b2*a23 + b3*a33


def translate(out, a, v):
    x, y, z = v
    if a is out:
        out[12] = a[0] * x + a[4] * y + a[8] * z + a[12]
        out[13] = a[1] * x + a[5] * y + a[9] * z + a[13]
        out[14] = a[2] * x + a[6] * y + a[10] * z + a[14]
        out[15] = a[3] * x + a[7] * y + a[11] * z + a[15]
    else:
        (a00, a01, a02, a03, a10, a11, a12, a13, a20, a21, a22, a23, a30, a31,
         a32, a33) = a
        out[:] = a
        out[12] = a00 * x + a10 * y + a20 * z + a[12]
        out[13] = a01 * x + a11 * y + a21 * z + a[13]
        out[14] = a02 * x + a12 * y + a22 * z + a[14]
        out[15] = a03 * x + a13 * y + a23 * z + a[15]


def scale(out, a, v):
    x, y, z = v
    out[0] = a[0] * x
    out[1] = a[1] * x
    out[2] = a[2] * x
    out[3] = a[3] * x
    out[4] = a[4] * y
    out[5] = a[5] * y
    out[6] = a[6] * y
    out[7] = a[7] * y
    out[8] = a[8] * z
    out[9] = a[9] * z
    out[10] = a[10] * z
    out[11] = a[11] * z
    out[12] = a[12]
    out[13] = a[13]
    out[14] = a[14]
    out[15] = a[15]


def ortho(out, left, right, bottom, top, near, far):
    """Returns orthogonal projection matrix"""
    lr = 1 / (left - right)
    bt = 1 / (bottom - top)
    nf = 1 / (near - far)
    out[0] = -2 * lr
    out[1] = 0
    out[2] = 0
    out[3] = 0
    out[4] = 0
    out[5] = -2 * bt
    out[6] = 0
    out[7] = 0
    out[8] = 0
    out[9] = 0
    out[10] = 2 * nf
    out[11] = 0
    out[12] = (left + right) * lr
    out[13] = (top + bottom) * bt
    out[14] = (far + near) * nf
    out[15] = 1
