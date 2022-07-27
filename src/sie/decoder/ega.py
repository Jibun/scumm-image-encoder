import logging
import os
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
    
def decodeV2ObjectBitmap(smap, width, height):
    smap.seek(0, os.SEEK_END)
    file_size = smap.tell()
    smap.seek(0, os.SEEK_SET)
    logging.debug("object file total size in bytes: %d" % file_size)
    
    run = 1
    colour = 0
    bleed = False # keep a track of horizontal bleeding
    bleed_table = [0] * height # (same value as the height of backgrounds...)
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
                colour, = struct.unpack('B', smap.read(1))
                if colour & 0x80:
                    run = colour & 0x7F
                    bleed = True
                else:
                    run = colour >> 4
                    bleed = False
                if run == 0:
                    run, = struct.unpack('B', smap.read(1))
                colour = colour & 0x0F
                logging.debug("data1: %d. run: %d. bleed: %s. colour: %d" % (colour, run, bleed, colour))
            if not bleed:
                bleed_table[bleed_table_i] = colour
            img[y * width + x] = bleed_table[bleed_table_i]
            bleed_table_i += 1
        logging.debug("---")
        
    #obtaining mask
    remaining_size = file_size - smap.tell() 
    logging.debug("object mask size in bytes: %d" % remaining_size)
    bleed = False
    small_width = width >> 3
    mask = initBitmapData(width, height)
    x = y = 0
    run = 1
    try:
        for x in xrange(small_width):
            for y in xrange(height):
                run -= 1
                if run == 0:
                    colour, = struct.unpack('B', smap.read(1))
                    if colour & 0x80:
                        run = colour & 0x7F
                        bleed = True
                    else:
                        run = colour;
                        bleed = False
                    if run == 0:
                        run, = struct.unpack('B', smap.read(1))
                    if bleed:
                        colour, = struct.unpack('B', smap.read(1))
                if not bleed:
                    colour, = struct.unpack('B', smap.read(1))
                setMaskBitmapData(mask, y ,x, width, colour)   
    except:
        #FIXME OI masks finished by 0x82 are 1 byte too short. Why?
        logging.debug("mask ended before expected")
    return img, mask
    
def setMaskBitmapData(mask, y, x, width, colour):
    for i in xrange(8):
        bit = ((colour << i) & 0x80) >> 7
        mask[y * width + x*8+i] = bit
    
def readObjectDimensions(lflf_path, objectNumAsStr):
    objCodeFile = file(os.path.join(lflf_path, 'ROv2', 'OCv2_%s' % objectNumAsStr), 'rb')
    objCodeFile.seek(9, os.SEEK_SET)
    width = ord(objCodeFile.read(1))  * 8
    objCodeFile.seek(13, os.SEEK_SET)
    height = ord(objCodeFile.read(1)) & 0xF8
    objCodeFile.close()
    return width, height
