def create(x=0, y=0, z=0, w=0):
    import array
    return array.array('f', (x, y, z, w))


def copy(out, a):
    out[0] = a[0]
    out[1] = a[1]
    out[2] = a[2]
    out[3] = a[3]


def set(out, x, y, z, w):
    out[0] = x
    out[1] = y
    out[2] = z
    out[3] = w


def add(out, a, b):
    out[0] = a[0] + b[0]
    out[1] = a[1] + b[1]
    out[2] = a[2] + b[2]
    out[3] = a[3] + b[3]


def subtract(out, a, b):
    out[0] = a[0] - b[0]
    out[1] = a[1] - b[1]
    out[2] = a[2] - b[2]
    out[3] = a[3] - b[3]


def multiply(out, a, b):
    out[0] = a[0] * b[0]
    out[1] = a[1] * b[1]
    out[2] = a[2] * b[2]
    out[3] = a[3] * b[3]


def divide(out, a, b):
    out[0] = a[0] / b[0]
    out[1] = a[1] / b[1]
    out[2] = a[2] / b[2]
    out[3] = a[3] / b[3]


def scale(out, a, b):
    out[0] = a[0] * b
    out[1] = a[1] * b
    out[2] = a[2] * b
    out[3] = a[3] * b


def distance(a, b):
    x = b[0] - a[0]
    y = b[1] - a[1]
    z = b[2] - a[2]
    w = b[3] - a[3]
    return math.sqrt(x*x + y*y + z*z + w*w)


def sqr_distance(a, b):
    x = b[0] - a[0]
    y = b[1] - a[1]
    z = b[2] - a[2]
    w = b[3] - a[3]
    return x*x + y*y + z*z + w*w


def length(a):
    x, y, z, w = a
    return math.sqrt(x*x + y*y + z*z + w*w)


def sqr_length(a):
    x, y, z, w = a
    return x*x + y*y + z*z + w*w


def negate(out, a):
    out[0] = -a[0]
    out[1] = -a[1]
    out[2] = -a[2]
    out[3] = -a[3]


def invert(out, a):
    out[0] = 1.0 / a[0]
    out[1] = 1.0 / a[1]
    out[2] = 1.0 / a[2]
    out[3] = 1.0 / a[3]


def normalize(out, a):
    x, y, z, w = a
    length = x*x + y*y + z*z + w*w
    if length > 0:
        length = 1 / math.sqrt(length)
        out[0] = a[0] * length
        out[1] = a[1] * length
        out[2] = a[2] * length
        out[3] = a[3] * length


def dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]


def transform_mat4(out, a, m):
    x, y, z, w = a
    out[0] = m[0] * x + m[4] * y + m[8] * z + m[12] * w
    out[1] = m[1] * x + m[5] * y + m[9] * z + m[13] * w
    out[2] = m[2] * x + m[6] * y + m[10] * z + m[14] * w
    out[3] = m[3] * x + m[7] * y + m[11] * z + m[15] * w


def transform_quat(out, a, q):
    x, y, z, w = a
    qx, qy, qz, qw = q
    # calculate quat * vec
    ix = qw * x + qy * z - qz * y
    iy = qw * y + qz * x - qx * z
    iz = qw * z + qx * y - qy * x
    iw = -qx * x - qy * y - qz * z
    # calculate result * inverse quat
    out[0] = ix * qw + iw * -qx + iy * -qz - iz * -qy
    out[1] = iy * qw + iw * -qy + iz * -qx - ix * -qz
    out[2] = iz * qw + iw * -qz + ix * -qy - iy * -qx
    out[3] = w
