import xml.etree.ElementTree as et
import logging
import os
import struct
from sie_util import ScummImageEncoderException, makeDirs

class ImageCodecBase(object):
    PATH_MUST_EXIST = True
    PATH_CAN_BE_NEW = False

    def __init__(self, config):
        self.config = config # a dictionary containing class-specific configuration, e.g. SMAP paths.

    def getHeaderPath(self, lflf_path):
        """ Can return None, if path defined in config is None."""
        header_path = self.config.header_path
        if header_path is None:
            return None
        return os.path.join(lflf_path, *header_path)

    def getExistingHeaderPath(self, lflf_path):
        """ Can return None, if path defined in config is None."""
        header_path = self.getHeaderPath(lflf_path)
        if header_path and not os.path.exists(header_path):
            raise ScummImageEncoderException("Can't find header file or path: %s" % header_path)
        return header_path

    def getPalettePath(self, lflf_path, palette_num):
        """ Can return None, if path defined in config is None."""
        palette_path = self.config.palette_path
        if palette_path is None:
            return None
        palette_path = os.path.join(lflf_path, *palette_path)
        return palette_path.replace("%p", str(palette_num).zfill(3)) # bit of a hack for V6 palettes

    def getExistingPalettePath(self, lflf_path, palette_num):
        """ Can return None, if path defined in config is None."""
        palette_path = self.getPalettePath(lflf_path, palette_num)
        if palette_path and not os.path.exists(palette_path):
            raise ScummImageEncoderException("Can't find palette file or path: %s" % palette_path)
        return palette_path

    def getBitmapPath(self, lflf_path):
        """ Can return None, if path defined in config is None."""
        bitmap_path = self.config.bitmap_path
        if bitmap_path is None:
            return None
        return os.path.join(lflf_path, *bitmap_path)

    def getNewBitmapPath(self, lflf_path):
        """ Can return None, if path defined in config is None."""
        bitmap_path = self.getBitmapPath(lflf_path)
        makeDirs(bitmap_path)
        return bitmap_path

    def getExistingBitmapPath(self, lflf_path):
        bitmap_path = self.getBitmapPath(lflf_path)
        if bitmap_path and not os.path.exists(bitmap_path):
            raise ScummImageEncoderException("Can't find bitmap file or path: %s" % bitmap_path)
        return bitmap_path


class HeaderReaderWriterBase(object):
    def getHeaderData(self, header_path):
        return None

    def getDimensions(self, header_path):
        return None, None

    def updateHeader(self, header_path, width, height):
        pass


class HeaderReaderWriterXml(HeaderReaderWriterBase):
    def getHeaderData(self, header_path):
        """Returns the root node of a parsed XML tree."""
        tree = et.parse(header_path)
        return tree.getroot()

    def getDimensions(self, header_path):
        root = self.getHeaderData(header_path)
        width = int(root.find("width").text)
        height = int(root.find("height").text)
        return width, height

    def updateHeader(self, header_path, width, height):
        root = self.getHeaderData(header_path)
        root.find("width").text = str(width)
        root.find("height").text = str(height)
        et.ElementTree(root).write(header_path)

        
class HeaderReaderWriterBinary(HeaderReaderWriterBase):
    def __init__(self, struct_format, header_binary_index_map):
        self.struct_format = struct_format
        self.header_binary_index_map = header_binary_index_map

    def getHeaderData(self, header_path):
        """Returns a tuple of values."""
        header_file = file(header_path, 'rb')
        data = header_file.read(struct.calcsize(self.struct_format))
        data = struct.unpack(self.struct_format, data)
        return data

    def getDimensions(self, header_path):
        data = self.getHeaderData(header_path)
        logging.debug("Input dimensions: %s" % (data,))
        return data[self.header_binary_index_map["width"]],\
               data[self.header_binary_index_map["height"]]

    def updateHeader(self, header_path, width, height):
        data = list(self.getHeaderData(header_path))
        data[self.header_binary_index_map["width"]] = width
        data[self.header_binary_index_map["height"]] = height
        logging.debug("Output dimensions: %s" % (data,))
        hd_file = file(header_path, 'wb')
        data = struct.pack(self.struct_format, *data)
        hd_file.write(data)
        hd_file.close()
