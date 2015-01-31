import unittest
import os.path
import stbi
from ngk import vid


root = os.path.dirname(__file__)


def mse(i, k):
    if len(i) != len(k):
        raise ValueError('Len does not match')
    return 1 / len(i) * sum(a - b for a, b in zip(i, k))


class TestCase(unittest.TestCase):
    def compareImage(self, name, w, h, comp, img, tolerance=1.0):
        filename = '{0}-{1}.png'.format(self.id(), name)
        path = os.path.join(root, 'refimgs')
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, filename)
        conflictfilename = '{0}-{1}-CONFLICT.png'.format(self.id(), name)
        conflictpath = os.path.join(root, 'refimgs', conflictfilename)
        if os.path.exists(path):
            _w, _h, _comp, src = stbi.load(path, comp)
            if _w != w or _h != h or _comp != comp:
                stbi.write_png(conflictpath, w, h, comp, img)
                self.fail('Reference image dimensions do not match\n'
                          'Reference: {0}\n'
                          'Conflict: {1}'.format(path, conflictpath))
            x = mse(src, img)
            if x < tolerance:
                if os.path.exists(conflictpath):
                    os.remove(conflictpath)
            else:
                stbi.write_png(conflictpath, w, h, comp, img)
                self.fail('compareImage failed ({0} >= {1})\n'
                          'Reference: {2}\n'
                          'Conflict: {3}'.format(x, tolerance, path,
                                                 conflictpath))
        else:
            stbi.write_png(path, w, h, comp, img)
            if os.path.exists(conflictpath):
                os.remove(conflictpath)

    def compareWin(self, name, win, tolerance=1.0):
        w, h, out = win.read_pixels()
        return self.compareImage(name, w, h, 3, out, tolerance)


class TestWindow(TestCase):
    pass


class TestBuffer(TestCase):
    pass


class TestTexture2(TestCase):
    pass


class TestTileset(TestCase):
    pass


class TestProgram(TestCase):
    pass


class TestGeom(TestCase):
    pass


class TestTri3Geom(TestCase):
    vertsrc = r'''
    attribute vec3 aPos;
    attribute vec2 aUV;
    varying highp vec3 vColor;
    void main() {
        vColor = vec3(aUV, aPos.z);
        gl_Position = vec4(aPos.x, aPos.y, 0.0, 1.0);
    }
    '''

    fragsrc = r'''
    varying highp vec3 vColor;
    void main() {
        gl_FragColor = vec4(vColor, 1.0);
    }
    '''

    def setUp(self):
        self.win = vid.Window(self.id(), 160, 120, resizable=False)

    def test_add_set_del_clear_tri3(self):
        geom = vid.Tri3Geom()
        i1 = geom.add_tri3(-1.0, -1.0, 0.1, 0.0, 0.0, 1.0, 0.0, 1.0,
                           0.0, -1.0, 0.2, 0.0, 0.0, 1.0, 1.0, 1.0,
                           -0.5, 1.0, 0.4, 0.0, 0.0, 1.0, 0.5, 0.0)
        prog = vid.Program(self.vertsrc, self.fragsrc)
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(0, self.win)


class TestQuad2Geom(TestCase):
    vertsrc = r'''
    attribute vec2 aPos;
    attribute vec2 aUV;
    varying highp vec2 vUV;
    void main() {
        gl_Position = vec4(aPos, 0.0, 1.0);
        vUV = aUV;
    }
    '''

    fragsrc = r'''
    varying highp vec2 vUV;
    void main() {
        gl_FragColor = vec4(vUV, 0.0, 1.0);
    }
    '''

    def setUp(self):
        self.win = vid.Window(self.id(), 160, 120, resizable=False)

    def test_add_set_del_clear_quad2(self):
        geom = vid.Quad2Geom()
        # Add left quad
        i1 = geom.add_quad2(-1.0, -1.0, 0.0, 1.0,
                            0.0, -1.0, 1.0, 1.0,
                            0.0, 1.0, 1.0, 0.0,
                            -1.0, 1.0, 0.0, 0.0)
        prog = vid.Program(self.vertsrc, self.fragsrc)
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(0, self.win)
        # Add right quad
        i2 = geom.add_quad2(0.0, -1.0, 0.0, 1.0,
                            1.0, -1.0, 1.0, 1.0,
                            1.0, 1.0, 1.0, 0.0,
                            0.0, 1.0, 0.0, 0.0)
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(1, self.win)
        # Delete left quad
        geom.del_quad2(i1)
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(2, self.win)
        # Add left quad again
        i3 = geom.add_quad2(-1.0, -1.0, 0.0, 0.0,
                            0.0, -1.0, 1.0, 0.0,
                            0.0, 1.0, 1.0, 1.0,
                            -1.0, 1.0, 0.0, 1.0)
        self.assertEqual(i1, i3)
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(3, self.win)
        # Clear all quads
        geom.clear()
        self.win.before_step()
        geom.draw(self.win, prog)
        self.win.after_step()
        self.compareWin(4, self.win)


if __name__ == '__main__':
    unittest.main()
