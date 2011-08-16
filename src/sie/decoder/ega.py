import logging
import struct
from sie.sie_util import initBitmapData

# For v2. RLE, column-based.
def decodeV2Bitmap(smap, width, height):
    run = 1
    colour = 0
    data = 0
    bleed = False # keep a track of horizontal bleeding
    bleed_table = [0] * 128 # (same value as the height of backgrounds...)
    bleed_table_i = 0
    img = initBitmapData(width, height)
    for x in xrange(width):
        logging.debug("column: %d" % x)
        logging.debug("smap tell: %d" % smap.tell())
        logging.debug("Bleed table: %s" % bleed_table)
        bleed_table_i = 0
        for y in xrange(height):
            run -= 1
            if run == 0:
                data, = struct.unpack('B', smap.read(1))
                if data & 0x80:
                    run = data & 0x7F
                    bleed = True
                else:
                    run = data >> 4
                    bleed = False
                if run == 0:
                    run, = struct.unpack('B', smap.read(1))
                colour = data & 0x0F
                logging.debug("data1: %d. run: %d. bleed: %s. colour: %d" % (data, run, bleed, colour))
            if not bleed:
                bleed_table[bleed_table_i] = colour
            img[y * width + x] = bleed_table[bleed_table_i]
            bleed_table_i += 1
        logging.debug("---")
    return img
