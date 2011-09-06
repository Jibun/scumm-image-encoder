import logging
import os
import common
import c64

tableV1Palette = [
    0x00, 0x00, 0x00, 	0xFF, 0xFF, 0xFF, 	0xAA, 0x00, 0x00, 	0x00, 0xAA, 0xAA,
    0xAA, 0x00, 0xAA, 	0x00, 0xAA, 0x00, 	0x00, 0x00, 0xAA, 	0xFF, 0xFF, 0x55,
    0xFF, 0x55, 0x55, 	0xAA, 0x55, 0x00, 	0xFF, 0x55, 0x55, 	0x55, 0x55, 0x55,
    0xAA, 0xAA, 0xAA, 	0x55, 0xFF, 0x55, 	0x55, 0x55, 0xFF, 	0x55, 0x55, 0x55,
    0xFF, 0x55, 0xFF
]


class DecoderV1(common.ImageDecoderBase):
    def decodeImage(self, lflf_path, image_path, palette_num):
        """ V1 background images share "character map" data with the objects, so decode all objects as well."""
        width, height = self.readDimensions(lflf_path)
        pal_data = self.readPalette(lflf_path, palette_num)
        bitmap_path = self.getExistingBitmapPath(lflf_path)
        bmp_data, mask_data = self.readBitmap(lflf_path, bitmap_path, width, height, pal_data)
        self.saveImage(image_path, width, height, bmp_data, pal_data)
        # Save the mask as well
        ip, ipext = os.path.splitext(image_path)
        self.saveImage(ip + ".mask" + ipext, width, height, mask_data, pal_data)
        # Decode all object images
        self.decodeObjectImages(lflf_path, bitmap_path, image_path, pal_data)

    def decodeObjectImages(self, lflf_path, bitmap_path, image_path, pal_data):
        objNumStrs = [f[-4:] for f in os.listdir(bitmap_path) if f.startswith("OIv1_")]
        ip, ipext = os.path.splitext(image_path)
        for objNum in objNumStrs:
            logging.info("Decoding v1 object #%s" % objNum)
            #try:
            width, height = c64.readObjectDimensions(lflf_path, objNum)
            logging.debug("object - width, height: %d, %d" % (width, height))
            bmp_data, mask_data = c64.decodeV1Object(lflf_path, width, height, objNum)
            obj_image_path = "%s-OIv1_%s%s" % (ip, objNum, ipext)
            self.saveImage(obj_image_path, width, height, bmp_data, pal_data)
            obj_mask_path = "%s-OIv1_%s.mask%s" % (ip, objNum, ipext)
            self.saveImage(obj_mask_path, width, height, mask_data, pal_data)
            #except Exception, e:
            #    logging.error("Unhandled exception attempting to decode v1 object %s." % objNum)
                #raise e

    def readPalette(self, lflf_path, palette_num):
        return tableV1Palette

    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        img_data = c64.decodeV1Bitmap(lflf_path, width, height)
        return img_data

    def readDimensions(self, lflf_path):
        """V1 / C64 images store the height and width divided by 8 -
        need to multiply by 8 to get the real height/width."""
        width, height = super(DecoderV1, self).readDimensions(lflf_path)
        return width * 8, height * 8
