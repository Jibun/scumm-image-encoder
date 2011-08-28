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
        bmp_data = self.readBitmap(lflf_path, bitmap_path, width, height, pal_data)
        self.saveImage(image_path, width, height, bmp_data, pal_data)
        self.readAndSaveObjectImages(lflf_path, bitmap_path, image_path, pal_data)

    def readAndSaveObjectImages(self, lflf_path, bitmap_path, image_path, pal_data):
        pass

    def readPalette(self, lflf_path, palette_num):
        return tableV1Palette

    def readBitmap(self, lflf_path, bitmap_path, width, height, pal_data):
        img_data = c64.decodeV1Bitmap(lflf_path, width, height)
        return img_data

    def saveImage(self, image_path, width, height, bmp_data, pal_data):
        """V1 / C64 images store the height and width divided by 8 -
        need to multiply by 8 to get the real height/width."""
        super(DecoderV1, self).saveImage(image_path, width * 8, height * 8, bmp_data, pal_data)
