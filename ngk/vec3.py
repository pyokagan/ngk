import math


def create(x=0, y=0, z=0):
    import array
    return array.array('f', (x, y, z))


def add(out, a, b):
    out[0] = a[0] + b[0]
    out[1] = a[1] + b[1]
    out[2] = a[2] + b[2]


def subtract(out, a, b):
    out[0] = a[0] - b[0]
    out[1] = a[1] - b[1]
    out[2] = a[2] - b[2]


def multiply(out, a, b):
    out[0] = a[0] * b[0]
    out[1] = a[1] * b[1]
    out[2] = a[2] * b[2]


def divide(out, a, b):
    out[0] = a[0] / b[0]
    out[1] = a[1] / b[1]
    out[2] = a[2] / b[2]


def scale(out, a, b):
    out[0] = a[0] * b
    out[1] = a[1] * b
    out[2] = a[2] * b


def distance(a, b):
    x = b[0] - a[0]
    y = b[1] - a[1]
    z = b[2] - a[2]
    return math.sqrt(x*x + y*y + z*z)


def sqr_distance(a, b):
    x = b[0] - a[0]
    y = b[1] - a[1]
    z = b[2] - a[2]
    return x*x + y*y + z*z


def length(a):
    x, y, z = a
    return math.sqrt(x*x + y*y + z*z)


def sqr_length(a):
    x, y, z = a
    return x*x + y*y + z*z


def negate(out, a):
    out[0] = -a[0]
    out[1] = -a[1]
    out[2] = -a[2]


def invert(out, a):
    out[0] = 1.0 / a[0]
    out[1] = 1.0 / a[1]
    out[2] = 1.0 / a[2]


def normalize(out, a):
    x, y, z = a
    length = x*x + y*y + z*z
    if length > 0:
        length = 1.0 / math.sqrt(length)
        out[0] = a[0] * length
        out[1] = a[1] * length
        out[2] = a[2] * length


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(out, a, b):
    ax, ay, az = a
    bx, by, bz = b
    out[0] = ay * bz - az * by
    out[1] = az * bx - ax * bz
    out[2] = ax * by - ay * bx


def transform_mat4(out, a, m):
    x, y, z = a
    w = m[3] * x + m[7] * y + m[11] * z + m[15]
    w = w or 1.0
    out[0] = (m[0] * x + m[4] * y + m[8] * z + m[12]) / w
    out[1] = (m[1] * x + m[5] * y + m[9] * z + m[13]) / w
    out[2] = (m[2] * x + m[6] * y + m[10] * z + m[14]) / w


def transform_mat3(out, a, m):
    x, y, z = a
    out[0] = x * m[0] + y * m[3] + z * m[6]
    out[1] = x * m[1] + y * m[4] + z * m[7]
    out[2] = x * m[2] + y * m[5] + z * m[8]


def transform_quat(out, a, q):
    x, y, z = a
    qx, qy, qz, qw = q

    # Calculate quat * vec
    ix = qw * x + qy * z - qz * y
    iy = qw * y + qz * x - qx * z
    iz = qw * z + qx * y - qy * x
    iw = -qx * x - qy * y - qz * z

    # Calculate result * inverse quat
    out[0] = ix * qw + iw * -qx + iy * -qz - iz * -qy
    out[1] = iy * qw + iw * -qy + iz * -qx - ix * -qz
    out[2] = iz * qw + iw * -qz + ix * -qy - iy * -qx
