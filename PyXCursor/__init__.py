from time import time

import os
import ctypes
import ctypes.util
import numpy as np

# Define ctypes version of XFixesCursorImage structure.
PIXEL_DATA_PTR = ctypes.POINTER(ctypes.c_ulong)
Atom = ctypes.c_ulong

class XFixesCursorImage (ctypes.Structure):
    """ 
    See /usr/include/X11/extensions/Xfixes.h

    typedef struct {
        short	    x, y;
        unsigned short  width, height;
        unsigned short  xhot, yhot;
        unsigned long   cursor_serial;
        unsigned long   *pixels;
    if XFIXES_MAJOR >= 2
        Atom	    atom;	/* Version >= 2 only */
        const char	*name;	/* Version >= 2 only */
    endif
    } XFixesCursorImage;
    """
    _fields_ = [('x', ctypes.c_short),
                ('y', ctypes.c_short),
                ('width', ctypes.c_ushort),
                ('height', ctypes.c_ushort),
                ('xhot', ctypes.c_ushort),
                ('yhot', ctypes.c_ushort),
                ('cursor_serial', ctypes.c_ulong),
                ('pixels', PIXEL_DATA_PTR),
                ('atom', Atom),
                ('name', ctypes.c_char_p)]

class Display(ctypes.Structure):
    pass

# A helper function to convert data from Xlib to byte array.
import struct, array

class Xcursor:
    display = None
    def __init__(self, display=None):
        if not display:
            try:
                display = os.environ["DISPLAY"].encode("utf-8")
            except KeyError:
                raise Exception("$DISPLAY not set.")
        
        #XFixeslib = ctypes.CDLL('libXfixes.so')
        XFixes = ctypes.util.find_library("Xfixes")
        if not XFixes:
            raise Exception("No XFixes library found.")
        self.XFixeslib = ctypes.cdll.LoadLibrary(XFixes)

        #xlib = ctypes.CDLL('libX11.so.6')
        x11 = ctypes.util.find_library("X11")
        if not x11:
            raise Exception("No X11 library found.")
        self.xlib = ctypes.cdll.LoadLibrary(x11)

        # Define ctypes' version of XFixesGetCursorImage function
        XFixesGetCursorImage = self.XFixeslib.XFixesGetCursorImage
        XFixesGetCursorImage.restype = ctypes.POINTER(XFixesCursorImage)
        XFixesGetCursorImage.argtypes = [ctypes.POINTER(Display)]
        self.XFixesGetCursorImage = XFixesGetCursorImage

        XOpenDisplay = self.xlib.XOpenDisplay
        XOpenDisplay.restype = ctypes.POINTER(Display)
        XOpenDisplay.argtypes = [ctypes.c_char_p]

        if not self.display:
            self.display = self.xlib.XOpenDisplay(display) # (display) or (None)

    def argbdata_to_pixdata(self, data,  len):
        if data == None or len < 1: return None

        # Create byte array
        b = array.array('b', b'\x00'*4*len)	

        offset,i = 0,0
        while i < len:
            argb = data[i] & 0xffffffff
            rgba = (argb << 8) | (argb >> 24)
            b1 = (rgba >> 24)  & 0xff
            b2 = (rgba >> 16) & 0xff
            b3 = (rgba >> 8) & 0xff
            b4 = rgba & 0xff

            struct.pack_into("=BBBB", b, offset, b1, b2, b3, b4)
            offset = offset + 4
            i = i + 1

        return b 

    def GetCursorImageArray(self):
        # Call the function. Read data of cursor/mouse-pointer.
        cursor_data = self.XFixesGetCursorImage(self.display)

        if not (cursor_data and cursor_data[0]):
            raise Exception("Cannot read XFixesGetCursorImage()")

        # Note: cursor_data is a pointer, take cursor_data[0]
        cursor_data = cursor_data[0]

        # Check fields
        print("cursor x=", cursor_data.x)
        print("cursor y=", cursor_data.y)
        print("cursor width=", cursor_data.width)
        print("cursor height=", cursor_data.height)
        
        bytearr = self.argbdata_to_pixdata(cursor_data.pixels, cursor_data.width * cursor_data.height)
        
        imgarray = np.array(bytearr, dtype=np.uint8)
        imgarray = imgarray.reshape(cursor_data.height,cursor_data.width,4)
        del bytearr
        return imgarray

    def SaveImg(self,imgarray,text='testrgba.png'):
        from PIL import Image
        img = Image.fromarray(imgarray)
        img.save(text)