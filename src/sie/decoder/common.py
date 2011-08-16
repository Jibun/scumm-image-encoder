import xml.etree.ElementTree as et
import os.path
import struct
import Image
from vga import decodeVgaBitmap
from sie.sie_util import ScummImageEncoderException


class ImageDecoderBase(object):
    def __init__(self, config):
        self.config = config # a dictionary containing class-specific configuration, e.g. SMAP paths.

    def decodeImage(self, lflf_path, image_path, palette_num):
        width, height = self.readDimensions(lflf_path)
        pal_data = self.readPalette(lflf_path, palette_num)
        bitmap_path = self.getBitmapPath(lflf_path)
        bmp_data = self.readBitmap(lflf_path, bitmap_path, width, height, pal_data)
        self.saveImage(image_path, width, height, bmp_data, pal_data)

    def readDimensions(self, lflf_path):
        header_path = self.getHeaderPath(lflf_path)
        header_binary_format = self.config["header_binary_format"]
        if header_binary_format:
            header_reader = HeaderReaderBinary(header_binary_format)
        else:
            header_reader = HeaderReaderXml()
        return header_reader.getDimensions(header_path)

    def readPalette(self, lflf_path, palette_num):
        palette_path = self.getPalettePath(lflf_path, palette_num)
        palf = file(palette_path, 'rb')
        pal = None
        try:
            palf.seek(8) # skip the header
            # Don't try interpreting it as RGB tuples, PIL will understand.
            pal = struct.unpack('768B', palf.read(768))
        finally:
            palf.close()
        return pal

    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        return None

    def saveImage(self, image_path, width, height, bmp_data, pal_data):
        print "Creating output image file..."
        # Create our new image!
        im = Image.new('P', (width, height) )
        im.putpalette(pal_data)
        im.putdata(bmp_data)
        if os.path.splitext(image_path)[1].lower() != '.png':
            image_path += '.png'
        im.save(image_path, 'png') # always saves to PNG files.

    def getHeaderPath(self, lflf_path):
        header_path = self.config["header_path"]
        if header_path is None:
            return None
        header_path = os.path.join(lflf_path, *header_path)
        return header_path

    def getPalettePath(self, lflf_path, palette_num):
        palette_path = self.config["palette_path"]
        if palette_path is None:
            return None
        palette_path = os.path.join(lflf_path, *palette_path)
        palette_path = palette_path.replace("%p", str(palette_num).zfill(3)) # bit of a hack for V6 palettes
        if not os.path.exists(palette_path):
            raise ScummImageEncoderException("Can't find palette file or path: %s" % palette_path)
        return palette_path

    def getBitmapPath(self, lflf_path):
        bitmap_path = self.config["bitmap_path"]
        if bitmap_path is None:
            return None
        bitmap_path = os.path.join(lflf_path, *bitmap_path)
        if not os.path.exists(bitmap_path):
            raise ScummImageEncoderException("Can't find bitmap file or path: %s" % bitmap_path)
        return bitmap_path

class ImageDecoderVgaBase(ImageDecoderBase):
    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        # Load pixelmap data
        smap = file(bitmap_path, 'rb')
        try:
            return decodeVgaBitmap(smap, width, height)
        finally:
            smap.close()

class HeaderReaderBase(object):
    def getDimensions(self, header_path):
        return None, None

class HeaderReaderXml(HeaderReaderBase):
    def getDimensions(self, header_path):
        tree = et.parse(header_path)
        root = tree.getroot()
        width = int(root.find("width").text)
        height = int(root.find("height").text)
        return width, height

class HeaderReaderBinary(HeaderReaderBase):
    def __init__(self, struct_format):
        self.struct_format = struct_format

    def getDimensions(self, header_path):
        header_file = file(header_path, 'rb')
        data = header_file.read(struct.calcsize(self.struct_format))
        width, height = struct.unpack(self.struct_format, data)
        return width, height