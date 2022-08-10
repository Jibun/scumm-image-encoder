import array
import os
import logging
import struct
from sie.sie_util import ScummImageEncoderException

DEBUG_DUMP = False

def readCommonColours(lflf_path):
    coloursPath = os.path.join(lflf_path, 'ROv1', 'BCv1')
    if not os.path.isfile(coloursPath):
        raise ScummImageEncoderException("Could not find v1 colours file at location %s.\n"
                                    "Remember to run 'v1col_extract' once on any V1 game resources." %
                                    coloursPath)
    coloursFile = file(coloursPath, 'rb')
    colours = list(struct.unpack('4B', coloursFile.read(4)))
    coloursFile.close()
    return colours

def readCharMap(lflf_path):
    charFile = file(os.path.join(lflf_path, 'ROv1', 'B1v1'), 'rb')
    charMap = decodeC64Gfx(charFile, 2048)
    logging.debug("Background and objects CharMap after decompression (B1v1):")
    for idx in xrange(0, len(charMap), 8):
        logging.debug(' '.join(format(x, '02x') for x in charMap[idx:idx+8]))
    charFile.close()
    return charMap

def readPicMap(lflf_path, width, height):
    picFile = file(os.path.join(lflf_path, 'ROv1', 'B2v1'), 'rb')
    picMap = decodeC64Gfx(picFile, (width / 8) * (height / 8))
    logging.debug("Background and objects PicMap after decompression (B2v1):")
    for idx in xrange(0, len(picMap), height/8):
        logging.debug(' '.join(format(x, '02x') for x in picMap[idx:idx+height/8]))
    picFile.close()
    return picMap

def readColourMap(lflf_path, width, height):
    colourFile = file(os.path.join(lflf_path, 'ROv1', 'B3v1'), 'rb')
    colourMap = decodeC64Gfx(colourFile, (width / 8) * (height / 8))
    logging.debug("Background and objects ColourMap after decompression (B3v1):")
    for idx in xrange(0, len(colourMap), height/8):
        logging.debug(' '.join(format(x & 7, '02x') for x in colourMap[idx:idx+height/8]))
    colourFile.close()
    return colourMap

def readMaskPicMap(lflf_path, width, height):
    maskPicFile = file(os.path.join(lflf_path, 'ROv1', 'B4v1'), 'rb')
    maskPicMap = decodeC64Gfx(maskPicFile, (width / 8) * (height / 8))
    logging.debug("Background mask PicMap after decompression (B4v1):")
    for idx in xrange(0, len(maskPicMap), height/8):
        logging.debug(' '.join(format(x, '02d') for x in maskPicMap[idx:idx+height/8]))
    maskPicFile.close()
    return maskPicMap

def readMaskCharMap(lflf_path):
    """ The mask char map is variable length, since it also contains object mask data."""
    maskCharFile = file(os.path.join(lflf_path, 'ROv1', 'B5v1'), 'rb')
    # From ScummVM comments: "The 16bit length value seems to always be 8 too big. See bug #1837375 for details"
    size = struct.unpack('<H', maskCharFile.read(2))[0] - 8
    maskCharMap = decodeC64Gfx(maskCharFile, size)
    logging.debug("Background and objects MASK CharMap after decompression (B5v1):")
    for idx in xrange(0, size, 8):
        logging.debug(' '.join(format(x, '02x') for x in maskCharMap[idx:idx+8]))
    maskCharFile.close()
    return maskCharMap

def readObjectDimensions(lflf_path, objectNumAsStr):
    objCodeFile = file(os.path.join(lflf_path, 'ROv1', 'OCv1_%s' % objectNumAsStr), 'rb')
    objCodeFile.seek(9, os.SEEK_SET)
    width = ord(objCodeFile.read(1)) * 8
    objCodeFile.seek(13, os.SEEK_SET)
    height = ord(objCodeFile.read(1)) & 0xF8
    objCodeFile.close()
    return width, height

def readObjectMap(lflf_path, width, height, objectNumAsStr):
    objectFile = file(os.path.join(lflf_path, 'ROv1', 'OIv1_%s' % objectNumAsStr), 'rb')
    #logging.debug("object map width, height: %s, %s. strips, blocks: %s, %s" % (width, height, width / 8, height / 8))
    objectMap = decodeC64Gfx(objectFile, (width / 8) * (height / 8) * 3)
    objectFile.close()
    return objectMap

def unpackBlock(charMap, colours, img_data, col_start, y, charIdx, dstPitch):
    # For each of the 8 rows
    for i in xrange(8):
        row_start = col_start + ((y * 8 + i) * dstPitch)
        c = charMap[charIdx + i]
        # For 8 columns
        for j in xrange(0, 8, 2):
            # Each value is output twice - effectively means
            #  you've got a half-width image.
            val = colours[(c >> (6 - j)) & 3]
            img_data[row_start + j] = val
            img_data[row_start + j + 1] = val

def unpackV1Object(objectMap, charMap, colours, width, height):
    charIdx = None
    img_data = array.array('B', [0] * (width * height))
    dstPitch = width
    num_strips = width / 8
    num_blocks = height / 8
    #logging.debug("obj width: %d. height: %d. num_strips: %d. num_blocks: %d" % (width, height, num_strips, num_blocks))
    # For each column strip number
    for hstrip_i in xrange(num_blocks):
        for vstrip_i in xrange(num_strips): # x is equivalent to stripnr
            # Objects store custom colour at the end of all strip data, but before the mask data.
            #logging.debug("obj colour index: %d" % ((y + num_blocks) * num_strips + x))
            col_start = vstrip_i * 8 # For every 8th row
            colour_index = (hstrip_i + num_blocks) * num_strips + vstrip_i
            block_index = hstrip_i * num_strips + vstrip_i
            colours[3] = objectMap[colour_index] & 7
            charIdx = objectMap[block_index] * 8
            logging.debug("object - colour index: %d. custom colour: %d. bmp index: %d" % (colour_index, colours[3], block_index))
            unpackBlock(charMap, colours, img_data, col_start, hstrip_i, charIdx, dstPitch)
    return img_data

def unpackMaskBlock(charMap, img_data, col_start, y, charIdx, dstPitch):
    # For each of the 8 rows
    for i in xrange(8):
        row_start = col_start + ((y * 8 + i) * dstPitch)
        c = charMap[charIdx + i]
        # For 8 columns
        for j in xrange(8):
            # Masks only store 1 or 0. 1 byte holds mask values for 8 columns.
            img_data[row_start + j] = (c & (2 ** j)) >> j

def unpackV1ObjectMaskData(objectMap, maskCharMap, width, height):
    maskIdx = None
    img_data = array.array('B', [0] * (width * height))
    dstPitch = width
    num_strips = width / 8
    num_blocks = height / 8
    #logging.debug("obj width: %d. height: %d. num_strips: %d. num_blocks: %d" % (width, height, num_strips, num_blocks))
    # For each column strip number
    for hstrip_i in xrange(num_blocks):
        for vstrip_i in xrange(num_strips): # equivalent to stripnr
            # Objects store mask data (actually, indexes into the mask character map)
            #  after all bitmap data and colour data.
            col_start = vstrip_i * 8
            maskPic_index = (hstrip_i + 2 * num_blocks) * num_strips + vstrip_i
            maskIdx = objectMap[maskPic_index] * 8
            logging.debug("object mask - mask pic index: %d. mask char index: %d" % (maskPic_index, maskIdx))
            unpackMaskBlock(maskCharMap, img_data, col_start, hstrip_i, maskIdx, dstPitch)
    return img_data

def decodeV1Object(lflf_path, width, height, objectNumAsStr):
    global DEBUG_DUMP
    # The colours file requires running v1col_extract. Other files are generated by scummrp.
    colours = readCommonColours(lflf_path)
    charMap = readCharMap(lflf_path)
    objectMap = readObjectMap(lflf_path, width, height, objectNumAsStr)
    maskCharMap = readMaskCharMap(lflf_path)
    #logging.debug("obj objectMap size: %d" % len(objectMap))
    # Dump un-RLEed files
    if DEBUG_DUMP:
        charFile = file(os.path.join(lflf_path, 'charMap_%s' % objectNumAsStr), 'wb')
        charMap.tofile(charFile)
        charFile.close()
        objectFile = file(os.path.join(lflf_path, 'objectMap_%s' % objectNumAsStr), 'wb')
        objectMap.tofile(objectMap)
        objectFile.close()

    gfx_data = unpackV1Object(objectMap, charMap, colours, width, height)
    mask_data = unpackV1ObjectMaskData(objectMap, maskCharMap, width, height)

    return gfx_data, mask_data

def unpackV1Background(charMap, picMap, colourMap, colours, width, height):
    charIdx = None
    img_data = array.array('B', [0] * (width * height))
    num_strips = width / 8
    num_blocks = height / 8
    dstPitch = width
    # For each column strip number
    for x in xrange(num_strips): # x is equivalent to stripnr
        # For every 8th row
        col_start = x * 8
        for y in xrange(num_blocks):
            colour_index = y + x * num_blocks
            block_index = y + x * num_blocks
            colours[3] = (colourMap[colour_index] & 7)
            charIdx = picMap[block_index] * 8
            logging.debug("background - colour index: %d. bmp index: %d" % (colour_index, block_index))
            unpackBlock(charMap, colours, img_data, col_start, y, charIdx, dstPitch)
    return img_data

def unpackV1BackgroundMask(maskPicMap, maskCharMap, width, height):
    charIdx = None
    img_data = array.array('B', [0] * (width * height))
    num_strips = width / 8
    num_blocks = height / 8
    dstPitch = width
    # For each column strip number
    for x in xrange(num_strips): # x is equivalent to stripnr
        # For every 8th row
        col_start = x * 8
        for y in xrange(num_blocks):
            maskPic_index = y + x * num_blocks
            maskIdx = maskPicMap[maskPic_index] * 8
            logging.debug("background - mask pic index: %d. mask char index: %d" % (maskPic_index, maskIdx))
            unpackMaskBlock(maskCharMap, img_data, col_start, y, maskIdx, dstPitch)
    return img_data

def decodeV1Bitmap(lflf_path, width, height):
    """
    Room format (offsets):
    probably starts with the size of the chunk.
    0x04 : 1 byte =  width?
    0x05 : 1 byte = height?
    0x06 - 0x09: 1 byte each = palette

    0x0A : 2 bytes = offset of charMap -> B1v1
    0x0C : 2 bytes = offset of picMap -> B2v1
    0x0E : 2 bytes = offset of colourMap
    0x10 : 2 bytes = offset of maskMap
    0x12 : 2 bytes = offset of maskChar
    
    0x15 : 1 byte = offset of box data

    charMap has output size of 2048.
    picMap, colourMap, and maskMap have an output size of width * height (I think) -
    that's width in num_strips and height in num_blocks.
    """
    global DEBUG_DUMP
    # The colours file requires running v1col_extract. Other files are generated by scummrp.
    colours = readCommonColours(lflf_path)
    charMap = readCharMap(lflf_path)
    picMap = readPicMap(lflf_path, width, height)
    colourMap = readColourMap(lflf_path, width, height)
    maskCharMap = readMaskCharMap(lflf_path)
    maskPicMap = readMaskPicMap(lflf_path, width, height)

    # Dump un-RLEed files
    if DEBUG_DUMP:
        charFile = file(os.path.join(lflf_path, 'charMap'), 'wb')
        charMap.tofile(charFile)
        charFile.close()
        picFile = file(os.path.join(lflf_path, 'picMap'), 'wb')
        picMap.tofile(picFile)
        picFile.close()
        colourFile = file(os.path.join(lflf_path, 'colourMap'), 'wb')
        colourMap.tofile(colourFile)
        colourFile.close()

    img_data = unpackV1Background(charMap, picMap, colourMap, colours, width, height)
    mask_data = unpackV1BackgroundMask(maskPicMap, maskCharMap, width, height)

    return img_data, mask_data
    

def decodeC64Gfx(src, size):
    """This is an RLE variant."""
    colour = None # actually could be any value, not just colours.
    run = None
    # Read the most common values
    common = struct.unpack('<4B', src.read(4))
    #logging.debug("RLE-> common: 0x%X, 0x%X, 0x%X, 0x%X" % common)
    data = array.array('B')
    try:
        while len(data) < size:
            run, = struct.unpack('<B', src.read(1))
            #logging.debug("RLE-> item: %d.  run: 0x%X" % (len(data), run))
            # 0x80 indicates use of one of the common values.
            # common value index is stored in 0x60.
            # max run value is 31. (value is output 32 times)
            if run & 0x80:
                colour = common[(run >> 5) & 3]
                run &= 0x1F
                for _ in xrange(run + 1):
                    data.append(colour)
            # 0x40 indicates a run of one (uncommon) value.
            # The value to repeat is stored in the next byte.
            # max run value is 63. (value is output 64 times)
            elif run & 0x40:
                run &= 0x3F
                colour, = struct.unpack('<B', src.read(1))
                for _ in xrange(run + 1):
                    data.append(colour)
            # If bits in 0xC0 are not set, indicates a run of discrete (non-repeated) values.
            # max run value is 63. (64 values are read and output)
            else:
                for _ in xrange(run + 1):
                    colour, = struct.unpack('<B', src.read(1))
                    data.append(colour)
    except Exception, e:
        logging.error("ERROR unpacking C64 RLE data. Decoded %d bytes, expected %d. Dump follows.\n%s" % (len(data), size, data))
        raise e
    return data
