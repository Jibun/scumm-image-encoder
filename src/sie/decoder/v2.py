import logging
import os
import common
import ega

tableEGAPalette = [
    0x00, 0x00, 0x00, 	0x00, 0x00, 0xAA, 	0x00, 0xAA, 0x00, 	0x00, 0xAA, 0xAA,
    0xAA, 0x00, 0x00, 	0xAA, 0x00, 0xAA, 	0xAA, 0x55, 0x00, 	0xAA, 0xAA, 0xAA,
    0x55, 0x55, 0x55, 	0x55, 0x55, 0xFF, 	0x55, 0xFF, 0x55, 	0x55, 0xFF, 0xFF,
    0xFF, 0x55, 0x55, 	0xFF, 0x55, 0xFF, 	0xFF, 0xFF, 0x55, 	0xFF, 0xFF, 0xFF
]

class DecoderV2(common.ImageDecoderBase):
    def fixPalette(self):
        initial_length = len(tableEGAPalette) / 3
        num_elements = 3 * (256 - initial_length)
        extraEGAPallete = [0x00] * num_elements
        count = 0
        for i in xrange(0,num_elements,3):
            val = count + initial_length
            extraEGAPallete[i] = val
            extraEGAPallete[i+1] = val
            extraEGAPallete[i+2] = val
            count += 1
        tableEGAPalette.extend(extraEGAPallete)

    def decodeImage(self, lflf_path, image_path, palette_num):
        """ V2 background images share "character map" data with the objects, so decode all objects as well."""
        width, height = self.readDimensions(lflf_path)
        self.fixPalette()
        pal_data = self.readPalette(lflf_path, palette_num)
        bitmap_path = self.getExistingBitmapPath(lflf_path)
        bmp_data = self.readBitmap(lflf_path, bitmap_path, width, height, pal_data)
        self.saveImage(image_path, width, height, bmp_data, pal_data)
        # Decode all object images
        self.decodeObjectImages(lflf_path, bitmap_path, image_path, pal_data)

    def decodeObjectImages(self, lflf_path, bitmap_path, image_path, pal_data):
        objNumStrs = [f[-4:] for f in os.listdir(os.path.join(lflf_path, 'ROv2')) if f.startswith("OIv2_")]
        ip, ipext = os.path.splitext(image_path)
        for objNum in objNumStrs:
            logging.info("Decoding v2 object #%s" % objNum)
            width, height = ega.readObjectDimensions(lflf_path, objNum)
            logging.debug("object - width, height: %d, %d" % (width, height))
            object_path = self.getExistingObjectPath(lflf_path, objNum)
            bmp_data, mask_data = self.readObjectBitmap(lflf_path, object_path, width, height, pal_data)
            obj_image_path = "%s-OIv2_%s%s" % (ip, objNum, ipext)
            self.saveImage(obj_image_path, width, height, bmp_data, pal_data)
            obj_mask_path = "%s-OIv2_%s.mask%s" % (ip, objNum, ipext)
            self.saveBWImage(obj_mask_path, width, height, mask_data)

    def readPalette(self, lflf_path, palette_num):
        return tableEGAPalette
        
    def readObjectBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        bitmapFile = file(bitmap_path, 'rb')
        try:
            img_data, mask_data = ega.decodeV2ObjectBitmap(bitmapFile, width, height)
            return img_data, mask_data
        finally:
            bitmapFile.close()

    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        bitmapFile = file(bitmap_path, 'rb')
        try:
            img_data = ega.decodeV2Bitmap(bitmapFile, width, height)
            return img_data
        finally:
            bitmapFile.close()
