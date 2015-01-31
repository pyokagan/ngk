import math


def create(x=0, y=0, z=0, w=1):
    import array
    return array.array('f', (x, y, z, w))


def identity(out):
    out[0] = 0
    out[1] = 0
    out[2] = 0
    out[3] = 1


def add(out, a, b):
    out[0] = a[0] + b[0]
    out[1] = a[1] + b[1]
    out[2] = a[2] + b[2]
    out[3] = a[3] + b[3]


def multiply(out, a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    out[0] = ax * bw + aw * bx + ay * bz - az * by
    out[1] = ay * bw + aw * by + az * bx - ax * bz
    out[2] = az * bw + aw * bz + ax * by - ay * bx
    out[3] = aw * bw - ax * bx - ay * by - az * bz


def scale(out, a, b):
    out[0] = a[0] * b
    out[1] = a[1] * b
    out[2] = a[2] * b
    out[3] = a[3] * b


def rotate_x(out, a, rad):
    rad = rad * 0.5
    ax, ay, ax, aw = a
    bx = math.sin(rad)
    bw = math.cos(rad)
    out[0] = ax * bw + aw * bx
    out[1] = ay * bw + az * bx
    out[2] = az * bw - ay * bx
    out[3] = aw * bw - ax * bx


def rotate_y(out, a, rad):
    rad = rad * 0.5
    ax, ay, az, aw = a
    by = math.sin(rad)
    bw = math.cos(rad)
    out[0] = ax * bw - az * by
    out[1] = ay * bw + aw * by
    out[2] = az * bw + ax * by
    out[3] = aw * bw - ay * by


def rotate_z(out, a, rad):
    rad = rad * 0.5
    ax, ay, az, aw = a
    bz = math.sin(rad)
    bw = math.cos(rad)
    out[0] = ax * bw + ay * bz
    out[1] = ay * bw - ax * bz
    out[2] = az * bw + aw * bz
    out[3] = aw * bw - az * bz


def calculate_w(out, a):
    x, y, z, w = a
    out[0] = x
    out[1] = y
    out[2] = z
    out[3] = math.sqrt(abs(1.0 - x*x - y*y - z*z))


def invert(out, a):
    a0, a1, a2, a3 = a
    dot = a0*a0 + a1*a1 + a2*a2 + a3*a3
    inv_dot = 1.0 / dot if dot else 0
    out[0] = -a0*inv_dot
    out[1] = -a1*inv_dot
    out[2] = -a2*inv_dot
    out[3] = a3*inv_dot


def normalize(out, a):
    x, y, z, w = a
    length = x*x + y*y + z*z + w*w
    if length > 0:
        length = 1 / math.sqrt(length)
        out[0] = a[0] * length
        out[1] = a[1] * length
        out[2] = a[2] * length
        out[3] = a[3] * length


def set_axis_angle(out, axis, rad):
    rad = rad * 0.5
    s = math.sin(rad)
    out[0] = s * axis[0]
    out[1] = s * axis[1]
    out[2] = s * axis[2]
    out[3] = math.cos(rad)


def set_rotation_to(out, a, b):
    """Sets `out` to shortest rotation from `a` to `b`."""
    pass


def set_axes(out, view, right, up):
    pass
