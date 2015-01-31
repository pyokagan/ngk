"""Fancy OpenGL + SDL wrapper"""
import argparse
import array
import collections
import itertools
import os.path
import random
import sys
import time
import weakref
from cgles2 import *
from csdl2 import *
from . import mat4, vec3


class _Buffer:
    """Internal OpenGL Buffer handle"""

    __bufs = None

    def __init__(self, win, type, num_bufs=1):
        #: Window
        self.__win = win
        gl = win.gl
        #: Buffer type (GL_ARRAY_BUFFER or GL_ELEMENT_ARRAY_BUFFER)
        self.__type = type
        # Generate bufs
        self.__bufs = [gl.createBuffer() for i in range(num_bufs)]
        # Current buffer i
        self.__currentbuf = -1
        #: Update flag
        self.update = True

    def __del__(self):
        if self.__bufs:
            self.__win._del_buffers.extend(self.__bufs)

    type = property(lambda x: x.__type)

    def bind(self):
        """Bind buffer"""
        gl = self.__win.gl
        gl.bindBuffer(self.__type, self.__bufs[self.__currentbuf])

    def set_data(self, data, usage):
        gl = self.__win.gl
        nextbuf_i = (self.__currentbuf + 1) % len(self.__bufs)
        nextbuf = self.__bufs[nextbuf_i]
        gl.bindBuffer(self.__type, nextbuf)
        gl.bufferData(self.__type, data, usage)
        self.__currentbuf = nextbuf_i


class _Texture:
    """Internal OpenGL texture handle"""

    __tex = None

    def __init__(self, win, target):
        #: Window
        self.__win = win
        #: Texture target
        self.__target = target
        #: Texture handle
        self.__tex = gl.createTexture()
        #: Update flag
        self.update = True

    def __del__(self):
        if self.__tex:
            self.__win._del_textures.append(self.__tex)

    def bind(self):
        gl = self.__win.gl
        gl.bindTexture(self.__target, self.__tex)

    def texImage2D(self, target, w, h, fmt, data):
        gl = self.__win.gl
        self.bind()
        gl.texImage2D(target, 0, fmt, w, h, 0, fmt, GL_UNSIGNED_BYTE, data)


VertexAttribInfo = collections.namedtuple('VertexAttribInfo',
                                          'name size type index')


UniformInfo = collections.namedtuple('UniformInfo',
                                     'name size type loc texunit')


class _Program:
    __vertobj = None

    __fragobj = None

    __progobj = None

    def __init__(self, win):
        #: Window
        self.__win = win
        gl = self.__win.gl
        self.__vertobj = gl.createShader(GL_VERTEX_SHADER)
        self.__fragobj = gl.createShader(GL_FRAGMENT_SHADER)
        self.__progobj = gl.createProgram()
        gl.attachShader(self.__progobj, self.__vertobj)
        gl.attachShader(self.__progobj, self.__fragobj)
        #: Vertex attr info
        self.vert_attrs = {}
        #: Uniform info
        self.uniforms = {}
        #: Textures (mapping from texunit -> texture)
        self.__textures = {}
        #: Update flags
        self.update_uniforms = True
        self.update_compile = True

    def __del__(self):
        if self.__progobj:
            self.__win._del_programs.append(self.__progobj)
        if self.__fragobj:
            self.__win._del_shaders.append(self.__fragobj)
        if self.__vertobj:
            self.__win._del_shaders.append(self.__vertobj)

    def bind(self):
        gl = self.__win.gl
        oldprog = self.__win._prog
        if oldprog:
            oldprog = oldprog()
        if oldprog is self:
            return
        self.__win._prog = None
        gl.useProgram(self.__progobj)
        # Enable vertex arrays
        for v in self.vert_attrs.values():
            gl.enableVertexAttribArray(v.index)
        # Enable textures
        for texunit, tex in self.__textures.items():
            gl.activeTexture(GL_TEXTURE0 + texunit)
            tex.bind(self.__win)
        self.__win._prog = weakref.ref(self)

    def unbind(self):
        prog = self.__win._prog
        if prog:
            prog = prog()
        if prog is not self:
            return
        # Disable vertex arrays
        for v in self.vert_attrs.values():
            if v.index == 0:
                continue
            gl.disableVertexAttribArray(v.index)
        self.__win._prog = None

    def compile(self, vert, frag):
        """Compile and link program"""
        gl = self.__win.gl
        # vert
        gl.shaderSource(self.__vertobj, vert)
        gl.compileShader(self.__vertobj)
        compiled = gl.getShaderiv(self.__vertobj, GL_COMPILE_STATUS)
        if compiled == GL_FALSE:
            raise ValueError(gl.getShaderInfoLog(self.__vertobj))
        # frag
        gl.shaderSource(self.__fragobj, frag)
        gl.compileShader(self.__fragobj)
        compiled = gl.getShaderiv(self.__fragobj, GL_COMPILE_STATUS)
        if compiled == GL_FALSE:
            raise ValueError(gl.getShaderInfoLog(self.__fragobj))
        # prog
        gl.linkProgram(self.__progobj)
        linked = gl.getProgramiv(self.__progobj, GL_LINK_STATUS)
        if linked == GL_FALSE:
            raise ValueError(gl.getProgramInfoLog(self.__progobj))
        # Clear vertex attributes and uniforms
        self.vert_attrs.clear()
        self.uniforms.clear()
        self.__textures.clear()
        # Load vertex attributes
        num_attrs = gl.getProgramiv(self.__progobj, GL_ACTIVE_ATTRIBUTES)
        for i in range(num_attrs):
            size, type, name = gl.getActiveAttrib(self.__progobj, i)
            index = gl.getAttribLocation(self.__progobj, name)
            self.vert_attrs[name] = VertexAttribInfo(name, size, type, index)
        # Load uniforms
        texunit_ctr = 0
        num_uniforms = gl.getProgramiv(self.__progobj, GL_ACTIVE_UNIFORMS)
        for i in range(num_uniforms):
            size, type, name = gl.getActiveUniform(self.__progobj, i)
            loc = gl.getUniformLocation(self.__progobj, name)
            if type in (GL_SAMPLER_2D, GL_SAMPLER_CUBE):
                if texunit_ctr > 31:
                    raise ValueError('Too many texture units')
                texunit = texunit_ctr
                texunit_ctr += 1
            else:
                texunit = 0
            self.uniforms[name] = UniformInfo(name, size, type, loc, texunit)

    def set_uniform(self, name, value):
        """Sets uniform `name` to `value`"""
        gl = self.__win.gl
        self.bind()
        name, count, type, loc, texunit = self.uniforms[name]
        if type == GL_FLOAT:
            gl.uniform1fv(loc, count, value)
        elif type == GL_FLOAT_VEC2:
            gl.uniform2fv(loc, count, value)
        elif type == GL_FLOAT_VEC3:
            gl.uniform3fv(loc, count, value)
        elif type == GL_FLOAT_VEC4:
            gl.uniform4fv(loc, count, value)
        elif type == GL_INT or type == GL_BOOL:
            gl.uniform1iv(loc, count, value)
        elif type == GL_INT_VEC2 or type == GL_BOOL_VEC2:
            gl.uniform2iv(loc, count, value)
        elif type == GL_INT_VEC3 or type == GL_BOOL_VEC3:
            gl.uniform3iv(loc, count, value)
        elif type == GL_INT_VEC4 or type == GL_BOOL_VEC4:
            gl.uniform4iv(loc, count, value)
        elif type == GL_FLOAT_MAT2:
            gl.uniformMatrix2fv(loc, count, GL_FALSE, value)
        elif type == GL_FLOAT_MAT3:
            gl.uniformMatrix3fv(loc, count, GL_FALSE, value)
        elif type == GL_FLOAT_MAT4:
            gl.uniformMatrix4fv(loc, count, GL_FALSE, value)
        elif type == GL_SAMPLER_2D or type == GL_SAMPLER_CUBE:
            gl.activeTexture(GL_TEXTURE0 + texunit)
            value.bind(self.__win)  # Bind texture
            self.__textures[texunit] = value
            gl.uniform1i(loc, texunit)


KeyEvent = collections.namedtuple('KeyEvent', 'type key')


ButtonEvent = collections.namedtuple('ButtonEvent', 'type mouse button x y')


MotionEvent = collections.namedtuple('MotionEvent', 'type mouse state x y '
                                                    'relx rely')


class Window:
    _quad_elemid = None

    def __init__(self, title, w, h, near=None, far=None, max_quads=None,
                 resizable=True):
        #: Window title
        self.__title = str(title)
        #: Window width
        self.w = w
        #: Window height
        self.h = h
        #: Current viewport x
        self._viewportx = None
        #: Current viewport y
        self._viewporty = None
        #: Current viewport width
        self._viewportw = None
        #: Current viewport height
        self._viewporth = None
        #: Window width
        self._winw = None
        #: Window height
        self._winh = None
        #: Near depth
        self.near = near if near is not None else -self.h
        #: Far depth
        self.far = far if far is not None else self.h
        #: Is Window resizable
        self.__resizable = resizable
        #: Event queue
        self.events = []
        #: Back flag
        self.back = False
        #: Quit flag
        self.quit = False
        #: SDL Event Data
        self.__ev = SDL_Event()
        # Init SDL
        SDL_InitSubSystem(SDL_INIT_VIDEO)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,
                            SDL_GL_CONTEXT_PROFILE_ES)
        # Create SDL Window
        flags = SDL_WINDOW_OPENGL
        if self.__resizable:
            flags |= SDL_WINDOW_RESIZABLE
        self.__win = SDL_CreateWindow(self.title,
                                      SDL_WINDOWPOS_UNDEFINED,
                                      SDL_WINDOWPOS_UNDEFINED,
                                      self.w, self.h,
                                      flags)
        # Init SDL OpenGL Context
        self.__glctx = SDL_GL_CreateContext(self.__win)
        # Load OpenGL functions
        self.gl = GL(SDL_GL_GetProcAddress)
        #: Quad Element Buffer data
        self._quad_elemdata = array.array('H')
        if max_quads is None:
            max_quads = (2 ** (self._quad_elemdata.itemsize * 8)) // 6
        for i in range(max_quads):
            self._quad_elemdata.extend((4*i, 4*i+1, 4*i+2, 4*i+2, 4*i+3, 4*i))
        self._quad_elemid = self.gl.createBuffer()
        self.gl.bindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._quad_elemid)
        self.gl.bufferData(GL_ELEMENT_ARRAY_BUFFER, self._quad_elemdata,
                           GL_STATIC_DRAW)
        self.__frames = 0
        self.__last_fps_time = time.monotonic()
        self.__fps = 0
        # Slot variables for other objects
        #: Weak reference to current Program
        self._prog = None
        # Orthographic projection matrix
        self.ortho_mat = mat4.create()
        self.__resize_viewport(self.w, self.h)
        #: Garbage queues
        self._del_buffers = []
        self._del_textures = []
        self._del_shaders = []
        self._del_programs = []

    def __del__(self):
        if self._quad_elemid:
            self.gl.deleteBuffer(self._quad_elemid)
        SDL_QuitSubSystem(SDL_INIT_VIDEO)

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, v):
        SDL_SetWindowTitle(self.__win, '{0} (FPS:{1})'.format(v, self.__fps))
        self.__title = v

    def __resize_viewport(self, winw, winh):
        if winw > winh:
            h = min(winw / self.w * self.h, winh)
            w = h / self.h * self.w
        else:
            w = min(winh / self.h * self.w, winw)
            h = w / self.w * self.h
        x = (winw - w) / 2
        y = (winh - h) / 2
        self.gl.viewport(int(x), int(y), int(w), int(h))
        mat4.ortho(self.ortho_mat, -self.w/2, self.w/2, -self.h/2,
                   self.h/2, self.near, self.far)
        self._winw = winw
        self._winh = winh
        self._viewportx = int(x)
        self._viewporty = int(y)
        self._viewportw = int(w)
        self._viewporth = int(h)

    def __handle_window_event(self, ev):
        win = ev.window
        if win.event == SDL_WINDOWEVENT_SIZE_CHANGED:
            self.__resize_viewport(win.data1, win.data2)

    def before_step(self):
        self.events.clear()
        while SDL_PollEvent(self.__ev):
            if self.__ev.type == SDL_WINDOWEVENT:
                self.__handle_window_event(self.__ev)
            elif self.__ev.type == SDL_KEYDOWN:
                key = self.__ev.key.keysym.scancode
                if key == SDL_SCANCODE_AC_BACK:
                    self.back = True
                self.events.append(KeyEvent('KEYDOWN', key))
            elif self.__ev.type == SDL_KEYUP:
                key = self.__ev.key.keysym.scancode
                self.events.append(KeyEvent('KEYUP', key))
            elif self.__ev.type == SDL_MOUSEBUTTONDOWN:
                x = self.__ev.button
                y = ButtonEvent('MOUSEDOWN', x.which, x.button, x.x, x.y)
                self.events.append(y)
            elif self.__ev.type == SDL_MOUSEBUTTONUP:
                x = self.__ev.button
                y = ButtonEvent('MOUSEUP', x.which, x.button, x.x, x.y)
                self.events.append(y)
            elif self.__ev.type == SDL_MOUSEMOTION:
                x = self.__ev.motion
                y = MotionEvent('MOUSEMOVE', x.which, x.state,
                                x.x/self._winw*self.w,
                                x.y/self._winh*self.h,
                                x.xrel/self._viewportw*self.w,
                                -x.yrel/self._viewporth*self.h)
                self.events.append(y)
            elif self.__ev.type == SDL_QUIT:
                self.quit = True
        self.gl.clear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def after_step(self):
        # Cleanup garbage
        gl = self.gl
        for x in self._del_programs:
            gl.deleteProgram(x)
        self._del_programs.clear()
        for x in self._del_shaders:
            gl.deleteShader(x)
        self._del_shaders.clear()
        for x in self._del_textures:
            gl.deleteTexture(x)
        self._del_textures.clear()
        for x in self._del_buffers:
            gl.deleteBuffer(x)
        self._del_buffers.clear()
        SDL_GL_SwapWindow(self.__win)
        # FPS Count
        self.__frames += 1
        now = time.monotonic()
        if now >= self.__last_fps_time + 1.0:
            self.__fps = round(self.__frames / (now - self.__last_fps_time))
            self.__last_fps_time = now
            self.__frames = 0
            SDL_SetWindowTitle(self.__win,
                               '{0} (FPS:{1})'.format(self.title, self.__fps))
            SDL_Log('FPS: %d', self.__fps)

    def read_pixels(self):
        """Read current pixels. Returns bytearray"""
        out = bytearray(self._viewportw * self._viewporth * 3)
        self.gl.readPixels(self._viewportx, self._viewporty, self._viewportw,
                           self._viewporth, GL_RGB, GL_UNSIGNED_BYTE, out)
        # Flip image
        m = memoryview(out)
        tmp = bytearray(self._viewportw * 3)
        for y in range(self._viewporth // 2):
            src = m[y*self._viewportw*3:(y+1)*self._viewportw*3]
            tmp[:] = src
            y = self._viewporth - y
            dst = m[(y-1)*self._viewportw*3:y*self._viewportw*3]
            src[:] = dst
            dst[:] = tmp
        return self._viewportw, self._viewporth, out


class Texture2:
    num_frames = 1

    step = 1

    def __init__(self, w, h, data):
        #: Texture handles
        self.__tex = weakref.WeakKeyDictionary()
        # Upload
        self.set_data(w, h, data)

    w = property(lambda x: x.__w)

    h = property(lambda x: x.__h)

    data = property(lambda x: x.__data)

    def bind(self, win):
        gl = win.gl
        if win in self.__tex:
            tex = self.__tex[win]
        else:
            tex = self.__tex[win] = _Texture(win, GL_TEXTURE_2D)
        tex.bind()
        if tex.update:
            tex.texImage2D(GL_TEXTURE_2D, self.__w, self.__h, self.__fmt,
                           self.__data)
            tex.update = False
        gl.texParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        gl.texParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        gl.texParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        gl.texParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def set_data(self, w, h, data):
        # Validate data
        view = memoryview(data).cast('B')
        rgb_nbytes = w * h * 3
        rgba_nbytes = w * h * 4
        if view.nbytes == rgb_nbytes:
            fmt = GL_RGB
        elif view.nbytes == rgba_nbytes:
            fmt = GL_RGBA
        else:
            raise ValueError('Invalid data size')
        for tex in self.__tex.values():
            tex.update = True
        self.__w = w
        self.__h = h
        self.__data = data
        self.__fmt = fmt


class Tileset(Texture2):
    def __init__(self, w, h, data, tilew=0, tileh=0,
                 num_frames=1, step=1):
        super().__init__(w, h, data)
        #: Number of frames in tileset
        self.num_frames = num_frames
        #: Steps for each frame
        self.step = step
        #: Tile width
        self.tilew = tilew if tilew != 0 else self.w
        #: Tile height
        self.tileh = tileh if tileh != 0 else self.h

    @property
    def num_tilew(self):
        "Total number of tiles on x axis"
        return self.w // (self.tilew * self.num_frames)

    @property
    def num_tileh(self):
        "Total number of tiles on y axis"
        return self.h // self.tileh

    @property
    def num_tiles(self):
        "Total number of tiles"
        return self.num_tilew * self.num_tileh


class Program:
    #: Only write pixel on depth pass
    depth_check = False

    #: Depth write
    depth_write = False

    blend_src = GL_ONE

    blend_dst = GL_ZERO

    def __init__(self, vert, frag):
        #: Vertex shader source
        self.__vert = vert
        #: Fragment shader source
        self.__frag = frag
        #: Program object
        self.__prog = weakref.WeakKeyDictionary()
        #: Uniforms
        self.__uniforms = {}

    vert = property(lambda x: x.__vert)

    frag = property(lambda x: x.__frag)

    uniforms = property(lambda x: x.__uniforms)

    def __get_prog(self, win):
        if win in self.__prog:
            prog = self.__prog[win]
        else:
            prog = self.__prog[win] = _Program(win)
        if prog.update_compile:
            prog.compile(self.__vert, self.__frag)
            prog.update_compile = False
        if prog.update_uniforms:
            for k, v in self.__uniforms.items():
                prog.set_uniform(k, v)
            prog.update_uniforms = False
        return prog

    def bind(self, win):
        gl = win.gl
        prog = self.__get_prog(win)
        prog.bind()
        # Depth check
        if self.depth_check:
            gl.enable(GL_DEPTH_TEST)
        else:
            gl.disable(GL_DEPTH_TEST)
        # Depth write
        gl.depthMask(GL_TRUE if self.depth_write else GL_FALSE)
        # Blending
        if self.blend_src == GL_ONE and self.blend_dst == GL_ZERO:
            gl.disable(GL_BLEND)
        else:
            gl.enable(GL_BLEND)
            gl.blendFunc(self.blend_src, self.blend_dst)

    def compile(self, vert, frag):
        """Compile and links program"""
        self.__vert = vert
        self.__frag = frag
        self.__uniforms.clear()
        for prog in self.__prog.values():
            prog.update_compile = True

    def set_uniform(self, name, value):
        """Sets uniform `name` to `value`"""
        self.__uniforms[name] = value
        for prog in self.__prog.values():
            prog.update_uniforms = True

    def _get_uniform_info(self, win):
        prog = self.__get_prog(win)
        return prog.uniforms

    def _get_vertex_attrib_info(self, win):
        prog = self.__get_prog(win)
        return prog.vert_attrs


VertAttrPtr = collections.namedtuple('VertAttrPtr',
                                     'size type normalized stride offset')


class Geom:
    """Bring your own buffer Geom implementation"""

    def __init__(self, prim, vertdata, vertptrs, elemdata=None):
        #: Rendering primitive (e.g. GL_TRIANGLES)
        self.prim = prim
        #: Vertex data
        self.__vertdata = vertdata
        #: Vertex buffer
        self.__vertbuf = weakref.WeakKeyDictionary()
        #: Number of vertices
        self.__count = 0
        #: Vertex Attr Pointers (mapping name->VertAttrPtr)
        self.vertptrs = vertptrs
        #: Element Data
        self.__elemdata = elemdata
        #: Optional Element Buffer (or None)
        self.__elembuf = weakref.WeakKeyDictionary()
        self.__elemtype = None
        self.__update = True
        self.update()

    @property
    def vertdata(self):
        return self.__vertdata

    @vertdata.setter
    def vertdata(self, v):
        self.__vertdata = v
        self.__update = True

    @property
    def elemdata(self):
        return self.__elemdata

    @elemdata.setter
    def elemdata(self, v):
        self.__elemdata = v
        self.__update = True

    def __get_vertbuf(self, win):
        if win in self.__vertbuf:
            vertbuf = self.__vertbuf[win]
        else:
            vertbuf = self.__vertbuf[win] = _Buffer(win, GL_ARRAY_BUFFER)
        if vertbuf.update:
            vertbuf.set_data(self.vertdata, GL_STATIC_DRAW)
            vertbuf.update = False
        return vertbuf

    def __get_elembuf(self, win):
        if win in self.__elembuf:
            elembuf = self.__elembuf[win]
        else:
            elembuf = self.__elembuf[win] = _Buffer(win,
                                                    GL_ELEMENT_ARRAY_BUFFER)
        if elembuf.update:
            elembuf.set_data(self.elemdata, GL_STATIC_DRAW)
            elembuf.update = False
        return elembuf

    def update(self):
        """Updates Geom"""
        # Get stride from vertptrs
        stride = None
        for x in self.vertptrs.values():
            if stride is None:
                stride = x.stride
            elif x.stride != stride:
                raise ValueError('strides do not match')
        # Calculate number of vertices
        vertdata_v = memoryview(self.vertdata)
        if vertdata_v.len % stride != 0:
            raise ValueError('vertdata len is not a multiple of stride')
        if self.elemdata is not None:
            elemdata_v = memoryview(self.elemdata)
            if elemdata_v.itemsize == 1:
                self.__elemtype = GL_UNSIGNED_BYTE
            elif elemdata_v.itemsize == 2:
                self.__elemtype = GL_UNSIGNED_SHORT
            else:
                raise ValueError('Invalid itemsize')
            self.__count = elemdata_v.len // elemdata_v.itemsize
            for x in self.__elembuf.values():
                x.update = True
        else:
            self.__elembuf.clear()
            self.__count = vertdata_v.len // stride
        # Update self.__vertbuf
        for x in self.__vertbuf.values():
            x.update = True
        self.__update = False

    def draw(self, win, prog):
        """Draws geometry"""
        if self.__update:
            self.update()
        gl = win.gl
        prog.bind(win)  # Bind program
        # Bind vertex attribs
        vertbuf = self.__get_vertbuf(win)
        vertbuf.bind()
        vert_attrs = prog._get_vertex_attrib_info(win)
        for k, info in vert_attrs.items():
            size, type, normalized, stride, offset = self.vertptrs[k]
            gl.vertexAttribPointer(info.index, size, type, normalized, stride,
                                   offset)
        # Bind element
        if self.__elemdata:
            elembuf = self.__get_elembuf(win)
            elembuf.bind()
            gl.drawElements(self.prim, self.__count, self.__elemtype, 0)
        else:
            gl.drawArrays(self.prim, 0, self.__count)


class Tri3Geom(Geom):
    def __init__(self, num_floats=8, aPos='aPos', aUV='aUV',
                 aNorm='aNorm'):
        #: Number of floats per vertex (at least 8)
        self.num_floats = int(num_floats)
        assert self.num_floats >= 8
        #: Free indices
        self.__free = []
        #: Vertex data (8 verts per quad)
        self.__vertdata = array.array('f')
        #: Vertex buffer
        self.__vertbuf = weakref.WeakKeyDictionary()
        #: Vertex attr pointers
        self.vertptrs = {}
        # aPos -- Position vector
        sizeof_float = self.__vertdata.itemsize
        stride = self.num_floats * sizeof_float
        self.vertptrs[aPos] = VertAttrPtr(3, GL_FLOAT, GL_FALSE, stride, 0)
        # aNorm -- Normal vector
        self.vertptrs[aNorm] = VertAttrPtr(3, GL_FLOAT, GL_FALSE, stride,
                                           3 * sizeof_float)
        # aUV -- UV coordinates
        self.vertptrs[aUV] = VertAttrPtr(2, GL_FLOAT, GL_FALSE, stride,
                                         6 * sizeof_float)

    prim = property(lambda x: GL_TRIANGLES)

    vertdata = property(lambda x: x.__vertdata)

    elemdata = property(lambda x: None)

    def _get_tri3(self, index):
        """Returns (A, B, C) memoryviews of the 3 verts of tri `index`"""
        v = memoryview(self.__vertdata)
        I = int(index) * 3 * self.num_floats
        A = v[I:I + self.num_floats]
        B = v[I + self.num_floats:I + 2 * self.num_floats]
        C = v[I + 2 * self.num_floats:I + 3 * self.num_floats]
        return A, B, C

    def _alloc_tri3(self):
        """Allocates memory for tri. Returns new index."""
        if self.__free:
            index = self.__free.pop()
        else:
            # Alloc memory at end
            index = len(self.__vertdata) // (3 * self.num_floats)
            self.__vertdata.extend(itertools.repeat(0, 3 * self.num_floats))
        self.__update = True
        return index

    def set_tri3(self, index, aX, aY, aZ, aNX, aNY, aNZ, aU, aV,
                 bX, bY, bZ, bNX, bNY, bNZ, bU, bV,
                 cX, cY, cZ, cNX, cNY, cNZ, cU, cV):
        A, B, C = self._get_tri3(index)
        A[0], A[1], A[2], A[3], A[4], A[5] = aX, aY, aZ, aNX, aNY, aNZ
        A[6], A[7] = aU, aV
        B[0], B[1], B[2], B[3], B[4], B[5] = bX, bY, bZ, bNX, bNY, bNZ
        B[6], B[7] = bU, bV
        C[0], C[1], C[2], C[3], C[4], C[5] = cX, cY, cZ, cNX, cNY, cNZ
        C[6], C[7] = cU, cV
        self.__update = True

    def add_tri3(self, *args, **kwargs):
        index = self._alloc_tri3()
        try:
            self.set_tri3(index, *args, **kwargs)
            return index
        except:
            self.del_tri3(index)
            raise

    def del_tri3(self, index):
        I = index * 3 * self.num_floats
        x = array.array('f', itertools.repeat(0, 3*self.num_floats))
        self.__vertdata[I:I+3*self.num_floats] = x
        self.__free.append(index)  # Add to free list
        self.__update = True

    def clear(self):
        self.__free.clear()
        del self.__vertdata[:]
        self.__update = True

    def update(self):
        for x in self.__vertbuf.values():
            x.update = True
        self.__update = False

    def __get_vertbuf(self, win):
        if win in self.__vertbuf:
            vertbuf = self.__vertbuf[win]
        else:
            vertbuf = self.__vertbuf[win] = _Buffer(win, GL_ARRAY_BUFFER, 2)
        if vertbuf.update:
            vertbuf.set_data(self.__vertdata, GL_DYNAMIC_DRAW)
            vertbuf.update = False
        return vertbuf

    def draw(self, win, prog):
        if self.__update:
            self.update()
        gl = win.gl
        prog.bind(win)  # Bind program
        # Bind vertex attrib pointers
        vertbuf = self.__get_vertbuf(win)
        vertbuf.bind()
        vert_attrs = prog._get_vertex_attrib_info(win)
        for k, info in vert_attrs.items():
            size, type, normalized, stride, offset = self.vertptrs[k]
            gl.vertexAttribPointer(info.index, size, type, normalized, stride,
                                   offset)
        gl.drawArrays(GL_TRIANGLES, 0,
                      len(self.__vertdata) // self.num_floats)

    # tri2 interface

    def _alloc_tri2(self):
        return self._alloc_tri3()

    def set_tri2(self, index, aX, aY, aU, aV, bX, bY, bU, bV, cX, cY, cU, cV):
        A, B, C = self._get_tri3(index)
        A[:8] = aX, aY, 0, 0, 0, 1, aU, aV
        B[:8] = bX, bY, 0, 0, 0, 1, bU, bV
        C[:8] = cX, cY, 0, 0, 0, 1, cU, cV
        self.__update = True

    def add_tri2(self, *args, **kwargs):
        index = self._alloc_tri3()
        try:
            self.set_tri2(index, *args, **kwargs)
            return index
        except:
            self.remove(index)
            raise

    def del_tri2(self, index):
        return self.del_tri3(index)

    # quad3 interface

    def _alloc_quad3(self):
        for i, x in self.__free:
            if i >= len(self.__free) - 1:
                break
            if self.__free[i+1] == x-1:
                del self.__free[i:i+2]
                self.__update = True
                return x
        # Alloc memory at end
        index = len(self.__vertdata) // (3 * self.num_floats)
        self.__vertdata.extend(itertools.repeat(0, 6 * self.num_floats))
        self.__update = True
        return index

    def set_quad3(self, index, aX, aY, aZ, aNX, aNY, aNZ, aU, aV,
                  bX, bY, bZ, bNX, bNY, bNZ, bU, bV,
                  cX, cY, cZ, cNX, cNY, cNZ, cU, cV,
                  dX, dY, dZ, dNX, dNY, dNZ, dU, dV):
        A1, B, C1 = self._get_tri3(index)
        C2, D, A2 = self._get_tri3(index + 1)
        A1[:8] = A2[:8] = aX, aY, aZ, aNX, aNY, aNZ, aU, aV
        B[:8] = bX, bY, bZ, bNX, bNY, bNZ, bU, bV
        C1[:8] = C2[:8] = cX, cY, cZ, cNX, cNY, cNZ, cU, cV
        D[:8] = dX, dY, dZ, dNX, dNY, dNZ, dU, dV

    def add_quad3(self, *args, **kwargs):
        index = self._alloc_quad3()
        try:
            self.set_quad3(index, *args, **kwargs)
            return index
        except:
            self.del_quad3(index)
            raise

    def del_quad3(self, index):
        self.del_tri3(index+1)
        self.del_tri3(index)

    # quad2 interface

    def _alloc_quad2(self):
        return self._alloc_quad3()

    def set_quad2(self, index, aX, aY, aU, aV, bX, bY, bU, bV, cX, cY, cU, cV,
                  dX, dY, dU, dV):
        A1, B, C1 = self._get_tri3(index)
        C2, D, A2 = self._get_tri3(index + 1)
        A1[:8] = A2[:8] = aX, aY, 0, 0, 0, 1, aU, aV
        B[:8] = bX, bY, 0, 0, 0, 1, bU, bV
        C1[:8] = C2[:8] = cX, cY, 0, 0, 0, 1, cU, cV
        D[:8] = dX, dY, 0, 0, 0, 1, dU, dV

    def del_quad2(self, index):
        return self.del_quad3(index)


# TODO: Tri2Geom

# TODO: Quad3Geom

class Quad2Geom(Geom):
    def __init__(self, num_floats=4, aPos='aPos', aUV='aUV'):
        #: Number of floats per vertex (at least 4)
        self.__num_floats = int(num_floats)
        assert self.__num_floats >= 4
        #: Free indices
        self.__free = []
        #: Vertex data
        self.__vertdata = array.array('f')
        #: Vertex buffer
        self.__vertbuf = weakref.WeakKeyDictionary()
        self.__update = False
        #: Vertex Attr Pointers
        self.vertptrs = {}
        # aPos
        sizeof_float = self.__vertdata.itemsize
        stride = self.__num_floats * sizeof_float
        self.vertptrs[aPos] = VertAttrPtr(2, GL_FLOAT, GL_FALSE, stride, 0)
        # aUV
        self.vertptrs[aUV] = VertAttrPtr(2, GL_FLOAT, GL_FALSE, stride,
                                         2 * sizeof_float)

    prim = property(lambda x: GL_TRIANGLES)

    num_floats = property(lambda x: x.__num_floats)

    def _get_quad2(self, index):
        """Returns views of the 4 vertices of quad `index` (A, B, C, D)"""
        v = memoryview(self.__vertdata)
        I = int(index) * 4 * self.__num_floats
        A = v[I:I + self.__num_floats]
        B = v[I + self.__num_floats:I + 2 * self.__num_floats]
        C = v[I + 2 * self.__num_floats:I + 3 * self.__num_floats]
        D = v[I + 3 * self.__num_floats:I + 4 * self.__num_floats]
        return A, B, C, D

    def _alloc_quad2(self):
        """Allocates memory for a new rect. Returns new index."""
        if self.__free:
            index = self.__free.pop()
        else:
            # Alloc memory at end
            index = len(self.__vertdata) // (4 * self.__num_floats)
            self.__vertdata.extend(itertools.repeat(0, 4 * self.__num_floats))
        self.__update = True
        return index

    def set_quad2(self, index, aX, aY, aU, aV, bX, bY, bU, bV, cX, cY, cU, cV,
                  dX, dY, dU, dV):
        A, B, C, D = self._get_quad2(index)
        A[0], A[1], A[2], A[3] = aX, aY, aU, aV
        B[0], B[1], B[2], B[3] = bX, bY, bU, bV
        C[0], C[1], C[2], C[3] = cX, cY, cU, cV
        D[0], D[1], D[2], D[3] = dX, dY, dU, dV
        self.__update = True

    def add_quad2(self, *args, **kwargs):
        index = self._alloc_quad2()
        try:
            self.set_quad2(index, *args, **kwargs)
            return index
        except:
            self.del_quad2(index)
            raise

    def del_quad2(self, index):
        # Get array index
        I = index * 4 * self.__num_floats
        # Zero the quad data
        x = array.array('f', itertools.repeat(0, 4 * self.__num_floats))
        self.__vertdata[I:I+4*self.__num_floats] = x
        # Add to free list
        self.__free.append(index)
        self.__update = True

    def clear(self):
        self.__free.clear()
        del self.__vertdata[:]
        self.__update = True

    def update(self):
        for x in self.__vertbuf.values():
            x.update = True
        self.__update = False

    def __get_vertbuf(self, win):
        if win in self.__vertbuf:
            vertbuf = self.__vertbuf[win]
        else:
            vertbuf = self.__vertbuf[win] = _Buffer(win, GL_ARRAY_BUFFER, 2)
        if vertbuf.update:
            vertbuf.set_data(self.__vertdata, GL_DYNAMIC_DRAW)
        return vertbuf

    def draw(self, win, prog):
        """Draw geometry"""
        if self.__update:
            self.update()
        gl = win.gl
        prog.bind(win)  # Bind program
        # Bind vert attrs
        vertbuf = self.__get_vertbuf(win)
        vertbuf.bind()
        vert_attrs = prog._get_vertex_attrib_info(win)
        for k, info in vert_attrs.items():
            size, type, normalized, stride, offset = self.vertptrs[k]
            gl.vertexAttribPointer(info.index, size, type, normalized, stride,
                                   offset)
        # Bind element buffer
        gl.bindBuffer(GL_ELEMENT_ARRAY_BUFFER, win._quad_elemid)
        # Draw elements
        gl.drawElements(GL_TRIANGLES,
                        len(self.__vertdata) // self.__num_floats // 4 * 6,
                        GL_UNSIGNED_SHORT, 0)
