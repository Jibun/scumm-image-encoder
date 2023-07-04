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
    
def decodeV2Mask(smap, width, height):
    smap.seek(0, os.SEEK_END)
    file_size = smap.tell()
    smap.seek(0, os.SEEK_SET)
    logging.debug("mask file total size in bytes: %d" % file_size)
    
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
    return mask
    
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
    
def readObjectDimensions(config, header_object_path):
    objCodeFile = file(header_object_path, 'rb')
    objCodeFile.seek(config.header_object_index_map["width"], os.SEEK_SET)
    width = ord(objCodeFile.read(1))  * 8
    objCodeFile.seek(config.header_object_index_map["height"], os.SEEK_SET)
    height = ord(objCodeFile.read(1)) & 0xF8
    objCodeFile.close()
    return width, height
    
def decodeV3Bitmap(smap, width, height):
    smap.seek(0, os.SEEK_END)
    file_size = smap.tell()
    smap.seek(0, os.SEEK_SET)
    logging.debug("object file total size in bytes: %d" % file_size)
    
    mask_start = 0
    image_start = 0
    mask_start, = struct.unpack('H', smap.read(2))
    image_start, = struct.unpack('H', smap.read(2))
    
    smap.seek(image_start, os.SEEK_SET)
    
    run = 1
    inv_run = 1
    colour = 0
    bleed = False # keep a track of horizontal bleeding
    bleed_table = [0] * height # (same value as the height of backgrounds...)
    bleed_table_i = 0
    alternative = False # keep a track of the vertical color pair aternation
    alternative_table = [0] * height # (same value as the height of backgrounds...)
    alternative_table_i = 0
    colour_alt= 0
    img = initBitmapData(width, height)
    for x in xrange(width):
        logging.debug("column: %d" % x)
        logging.debug("smap tell: %d" % smap.tell())
        logging.debug("Bleed table: %s" % bleed_table)
        bleed_table_i = 0
        for y in xrange(height):
            run -= 1
            inv_run += 1
            if run == 0:
                colour, = struct.unpack('B', smap.read(1))
                if colour & 0xC0 == 0xC0:
                    run = colour & 0x3F
                    bleed = False
                    alternative = True
                    colour, = struct.unpack('B', smap.read(1))
                    colour_alt = colour >> 4
                elif colour & 0x80:
                    run = colour & 0x3F
                    bleed = True
                    alternative = False
                else:
                    run = colour >> 4
                    bleed = False
                    alternative = False
                if run == 0:
                    run, = struct.unpack('B', smap.read(1))
                colour = colour & 0x0F
                inv_run = 1
                logging.debug("data1: %d. run: %d. bleed: %s. colour: %d" % (colour, run, bleed, colour))
            if not bleed:
                if not alternative:
                    bleed_table[bleed_table_i] = colour
                else:
                    bleed_table[bleed_table_i] = colour if inv_run % 2 == 0 else colour_alt
            img[y * width + x] = bleed_table[bleed_table_i]
            bleed_table_i += 1
        logging.debug("---")
    return img
    
def decodeV3Mask(smap, width, height):
    smap.seek(0, os.SEEK_END)
    file_size = smap.tell()
    smap.seek(0, os.SEEK_SET)
    logging.debug("mask file total size in bytes: %d" % file_size)
    
    mask_start = 0
    mask_start, = struct.unpack('H', smap.read(2))
    
    smap.seek(mask_start, os.SEEK_SET)
    
    bleed = False
    small_width = width >> 3
    mask = initBitmapData(width, height)
    x = y = 0
    run = 1
    end_chunk_count = 0
    end_chunk = False
    
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
                        end_chunk, end_chunk_count = manageChunkCount(end_chunk, end_chunk_count, height, run)
                        if end_chunk and colour == 0x82:
                            logging.warning("mask is missing a byte at chunk end")
                        else:
                            colour, = struct.unpack('B', smap.read(1))
                    
                if not bleed:
                    end_chunk, end_chunk_count = manageChunkCount(end_chunk, end_chunk_count, height, 1)
                    colour, = struct.unpack('B', smap.read(1))
                setMaskBitmapData(mask, y ,x, width, colour)   
    except:
        #FIXME OI masks finished by 0x82 are 1 byte too short. Why?
        logging.debug("mask ended before expected")
    return mask
    
def decodeV3ObjectBitmap(smap, width, height):
    smap.seek(0, os.SEEK_END)
    file_size = smap.tell()
    smap.seek(0, os.SEEK_SET)
    logging.debug("object file total size in bytes: %d" % file_size)
    
    mask_start = 0
    image_start = 0
    mask_start, = struct.unpack('H', smap.read(2))
    image_start, = struct.unpack('H', smap.read(2))
    
    smap.seek(image_start, os.SEEK_SET)
    
    run = 1
    inv_run = 1
    colour = 0
    bleed = False # keep a track of horizontal bleeding
    bleed_table = [0] * height # (same value as the height of backgrounds...)
    bleed_table_i = 0
    alternative = False # keep a track of the vertical color pair aternation
    alternative_table = [0] * height # (same value as the height of backgrounds...)
    alternative_table_i = 0
    colour_alt= 0
    img = initBitmapData(width, height)
    for x in xrange(width):
        logging.debug("column: %d" % x)
        logging.debug("smap tell: %d" % smap.tell())
        logging.debug("Bleed table: %s" % bleed_table)
        bleed_table_i = 0
        for y in xrange(height):
            run -= 1
            inv_run += 1
            if run == 0:
                colour, = struct.unpack('B', smap.read(1))
                if colour & 0xC0 == 0xC0:
                    run = colour & 0x3F
                    bleed = False
                    alternative = True
                    colour, = struct.unpack('B', smap.read(1))
                    colour_alt = colour >> 4
                elif colour & 0x80:
                    run = colour & 0x3F
                    bleed = True
                    alternative = False
                else:
                    run = colour >> 4
                    bleed = False
                    alternative = False
                if run == 0:
                    run, = struct.unpack('B', smap.read(1))
                colour = colour & 0x0F
                inv_run = 1
                logging.debug("data1: %d. run: %d. bleed: %s. colour: %d" % (colour, run, bleed, colour))
            if not bleed:
                if not alternative:
                    bleed_table[bleed_table_i] = colour
                else:
                    bleed_table[bleed_table_i] = colour if inv_run % 2 == 0 else colour_alt
            img[y * width + x] = bleed_table[bleed_table_i]
            bleed_table_i += 1
        logging.debug("---")
        
    #obtaining mask
    #remaining_size = file_size - smap.tell() 
    #logging.debug("object mask size in bytes: %d" % remaining_size)
    
    smap.seek(mask_start, os.SEEK_SET)
    mask_image_start, = struct.unpack('H', smap.read(2))
    smap.seek(mask_start + mask_image_start, os.SEEK_SET)
    
    bleed = False
    small_width = width >> 3
    mask = initBitmapData(width, height)
    x = y = 0
    run = 1
    end_chunk_count = 0
    end_chunk = False
    
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
                        end_chunk, end_chunk_count = manageChunkCount(end_chunk, end_chunk_count, height, run)
                        if end_chunk and colour == 0x82:
                            logging.warning("mask is missing a byte at chunk end")
                        else:
                            colour, = struct.unpack('B', smap.read(1))
                    
                if not bleed:
                    end_chunk, end_chunk_count = manageChunkCount(end_chunk, end_chunk_count, height, 1)
                    colour, = struct.unpack('B', smap.read(1))
                setMaskBitmapData(mask, y ,x, width, colour)   
    except:
        #FIXME OI masks finished by 0x82 are 1 byte too short. Why?
        logging.debug("mask ended before expected")
    return img, mask

def manageChunkCount(end_chunk, end_chunk_count, height, increase):
    if end_chunk:
        end_chunk = False
        end_chunk_count = 0
    end_chunk_count += increase
    if end_chunk_count >= height:
        end_chunk = True
    return end_chunk, end_chunk_count
