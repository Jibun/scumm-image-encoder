import array
import os
import Image
from sie.common import ImageCodecBase, HeaderReaderWriterBinary, HeaderReaderWriterXml
from sie.sie_util import ScummImageEncoderException, intToBytes

class ImageEncoderBase(ImageCodecBase):
    def encodeImage(self, lflf_path, image_path, quantization, palette_num, freeze_palette, compression_method=None):
        source_image = self.validateAndQuantizeSourceImage(Image.open(image_path), quantization, freeze_palette)
        width, height = source_image.size
        #source_image = self.saveTempFile(source_image)
        self.writeBitmap(lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization)
        self.writeHeader(lflf_path, width, height)
        self.writePalette(lflf_path, source_image.palette.palette, quantization, palette_num, freeze_palette)
        #self.clearTempFile()

    def validateAndQuantizeSourceImage(self, source_image, quantization, freeze_palette):
        width, height = source_image.size
        if width % 8 or height % 8:
            raise ScummImageEncoderException("Error: Input image's height and width must both be a mulitple of 8.")
        elif freeze_palette:
            if source_image is None or source_image.palette is None or len(source_image.palette.palette) != 256 * 3:
                raise ScummImageEncoderException("Error: Input image must have 256 colour palette, if 'freeze palette' option is chosen.")
        elif source_image.palette is None or \
            (not freeze_palette and
             quantization and
             len(source_image.palette.palette) > quantization * 3):
            return source_image.quantize(quantization)
        return source_image

    def saveTempFile(self, source_image):
        """ A mega hack. Apparently required because of either a deficiency in PIL or my code."""
        source_image.save('temp.png','png')
        return Image.open('temp.png')

    def clearTempFile(self):
        dir_name = os.path.join(os.getcwd(), "temp.png")
        if os.path.exists(dir_name):
            os.remove(dir_name)

    def writeHeader(self, lflf_path, width, height):
        header_path = self.getExistingHeaderPath(lflf_path)
        header_binary_format = self.config.header_binary_format
        if header_binary_format:
            header_rw = HeaderReaderWriterBinary(header_binary_format, self.config.header_binary_index_map)
        else:
            header_rw = HeaderReaderWriterXml()
        header_rw.updateHeader(header_path, width, height)

    def writePalette(self, lflf_path, palette_data, quantization, palette_num, freeze_palette):
        if freeze_palette:
            return
        palette_path = self.getExistingPalettePath(lflf_path, palette_num)
        if not palette_path:
            return # If no palette path has been defined, assume we shouldn't write a palette.
        newclutfile = file(palette_path, 'ab')
        newclutfile.seek(8 + 16 * 3, 0) # skip header and EGA palette
        quantization = quantization if quantization else 256
        newpal = array.array('B', palette_data[:quantization * 3]) # copy RGB data for the quant colours
        newpal.tofile(newclutfile)
        newclutfile.close()

    def writeBitmap(self, lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization): # use of freeze_palette is a hack...
        pass

class ImageEncoderVgaBase(ImageEncoderBase):
    def writeBitmap(self, lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization):
        width, height = source_image.size
        bitdata = list(source_image.getdata())
        # Write strips
        newsmapfile = file(self.getNewBitmapPath(lflf_path), 'wb')
        # Write dummy header
        newsmapfile.write('00000000')
        blockStart = newsmapfile.tell()
        numStrips = width / 8
        stripsStartOffset = blockStart + (numStrips * 4) # each offset is a DWord
        currStripOffsetValue = stripsStartOffset
        stripSize = height * 8
        # Write strip offsets
        # Because we're just using uncompressed things, we can cheat and
        # predict how big a strip will be
        for _ in xrange(numStrips):
            intToBytes(currStripOffsetValue, LE=1).tofile(newsmapfile)
            currStripOffsetValue += stripSize + 1 # add one for compression ID

        palette_offset = 0 if (freeze_palette or not quantization or quantization < 240) else 16

        for stripNum in xrange(numStrips):
            newsmapfile.write(chr(01)) # tell it it's an uncompressed thingo
            stripData = array.array('B')
            for rowNum in range(height):
                for pixel in bitdata[stripNum * 8 + rowNum * width:
                                     stripNum * 8 + rowNum * width + 8]:
                    stripData.append(pixel + palette_offset)
            stripData.tofile(newsmapfile)

        # Write the header
        newsmapfile.seek(0, 2)
        blocksize = newsmapfile.tell()
        newsmapfile.seek(0, 0)
        newsmapfile.write('SMAP')
        intToBytes(blocksize).tofile(newsmapfile)
        newsmapfile.close()
