import os.path
import struct
import Image
from vga import decodeVgaBitmap
from sie.common import ImageCodecBase, HeaderReaderWriterBinary, HeaderReaderWriterXml

class ImageDecoderBase(ImageCodecBase):
    def decodeImage(self, lflf_path, image_path, palette_num):
        width, height = self.readDimensions(lflf_path)
        pal_data = self.readPalette(lflf_path, palette_num)
        bitmap_path = self.getExistingBitmapPath(lflf_path)
        bmp_data = self.readBitmap(lflf_path, bitmap_path, width, height, pal_data)
        self.saveImage(image_path, width, height, bmp_data, pal_data)

    def readDimensions(self, lflf_path):
        header_path = self.getExistingHeaderPath(lflf_path)
        header_binary_format = self.config.header_binary_format
        if header_binary_format:
            header_reader = HeaderReaderWriterBinary(header_binary_format, self.config.header_binary_index_map)
        else:
            header_reader = HeaderReaderWriterXml()
        return header_reader.getDimensions(header_path)

    def readPalette(self, lflf_path, palette_num):
        palette_path = self.getExistingPalettePath(lflf_path, palette_num)
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

class ImageDecoderVgaBase(ImageDecoderBase):
    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        # Load pixelmap data
        smap = file(bitmap_path, 'rb')
        try:
            return decodeVgaBitmap(smap, width, height)
        finally:
            smap.close()
