import array
import xml.etree.ElementTree as et
import logging
import os
import struct
import sys
import Image # from Python Imaging Library
from sie_util import getQWord, getWordLE, arrayToInt, getByte, byteToBits, ImageContainer, getDWord, getDWordLE, ScummImageEncoderException

HORIZONTAL = 0
VERTICAL = 1

DRAWPIX = 0
READPAL = 2
READVAL = 3
SUBVAR = 6
NEGVAR = 7

INCPAL4 = 0
INCPAL3 = 1
INCPAL2 = 2
INCPAL1 = 3
READ8BITS = 4
DECPAL1 = 5
DECPAL2 = 6
DECPAL3 = 7



tableEGAPalette = [
    0x00, 0x00, 0x00, 	0x00, 0x00, 0xAA, 	0x00, 0xAA, 0x00, 	0x00, 0xAA, 0xAA,
    0xAA, 0x00, 0x00, 	0xAA, 0x00, 0xAA, 	0xAA, 0x55, 0x00, 	0xAA, 0xAA, 0xAA,
    0x55, 0x55, 0x55, 	0x55, 0x55, 0xFF, 	0x55, 0xFF, 0x55, 	0x55, 0xFF, 0xFF,
    0xFF, 0x55, 0x55, 	0xFF, 0x55, 0xFF, 	0xFF, 0xFF, 0x55, 	0xFF, 0xFF, 0xFF
]

tableV1Palette = [
    0x00, 0x00, 0x00, 	0xFF, 0xFF, 0xFF, 	0xAA, 0x00, 0x00, 	0x00, 0xAA, 0xAA,
    0xAA, 0x00, 0xAA, 	0x00, 0xAA, 0x00, 	0x00, 0x00, 0xAA, 	0xFF, 0xFF, 0x55,
    0xFF, 0x55, 0x55, 	0xAA, 0x55, 0x00, 	0xFF, 0x55, 0x55, 	0x55, 0x55, 0x55,
    0xAA, 0xAA, 0xAA, 	0x55, 0xFF, 0x55, 	0x55, 0x55, 0xFF, 	0x55, 0x55, 0x55,
    0xFF, 0x55, 0xFF
]


def getDimensions(lflf_path, version):
    rmhd_path = None
    is_binary = False
    if version == 1:
        rmhd_path = os.path.join(lflf_path, "ROv1", "HDv1")
        is_binary = True
    elif version == 2:
        rmhd_path = os.path.join(lflf_path, "ROv2", "HDv2")
        is_binary = True
    elif version <= 4:
        rmhd_path = os.path.join(lflf_path, "RO", "HD.xml")
        is_binary = False
    elif version >= 5:
        rmhd_path = os.path.join(lflf_path, "ROOM", "RMHD.xml")
        is_binary = False
    if not os.path.isfile(rmhd_path):
        raise ScummImageEncoderException("Can't find room header file: %s" % rmhd_path)

    if is_binary:
        if version == 1:
            struct_format = '<2B'
            length = 2
        elif version == 2:
            struct_format = '<2H'
            length = 4
        else:
            raise ScummImageEncoderException("Unsupported SCUMM version to read a binary room header: %d" % version)
        rmhd_file = file(rmhd_path, 'rb')
        width, height = struct.unpack(struct_format, rmhd_file.read(length))
    else:
        tree = et.parse(rmhd_path)
        root = tree.getroot()
        width = int(root.find("width").text)
        height = int(root.find("height").text)
    return width, height

def getPalette(lflf_path, version, palette_num):
    pal_path = None
    if version == 1:
        # Use hardcoded V1 (C64) palette.
        return tableV1Palette # maybe TODO: expand to 768 bytes?
    elif version == 2:
        # Use hardcoded EGA palette.
        return tableEGAPalette # maybe TODO: expand to 768 bytes?
    elif version <= 4:
        pal_path = os.path.join(lflf_path, "RO", "PA.dmp")
    elif version <= 5:
        pal_path = os.path.join(lflf_path, "ROOM", "CLUT.dmp")
    elif version >= 6:
        pal_path = os.path.join(lflf_path, "ROOM", "PALS", "WRAP", "APAL_" + str(palette_num).zfill(3) + ".dmp")
    if not os.path.isfile(pal_path):
        raise ScummImageEncoderException("Can't find palette file: %s" % pal_path)
    palf = file(pal_path, 'rb')
    header = getQWord(palf)
    pal = []
    # Don't try interpreting it as RGB tuples, PIL will understand.
    for _ in xrange(768):
        pal.append( arrayToInt(getByte(palf, 0)) )
    palf.close()
    return pal

def getSmapPath(lflf_path, version):
    # V1 has multiple files for the bitmap data.
    #if version == 1:
    #    smap_path = os.path.join(lflf_path, "ROv1", "B1v1") # TODO: hm... support for other "B" blocks? B2, B3, BX...
    if version == 2:
        smap_path = os.path.join(lflf_path, "ROv2", "IMv2")
    elif version <= 4:
        smap_path = os.path.join(lflf_path, "RO", "BM.dmp")
    elif version >= 5:
        smap_path = os.path.join(lflf_path, "ROOM", "RMIM", "IM00", "SMAP.dmp")
    if not os.path.isfile(smap_path):
        raise ScummImageEncoderException("Can't find SMAP file: %s" % smap_path)
    return smap_path


def decodeV1BitmapOld(smap, img, width, height):
    charIdx = None
    new_height /= 8
    new_width /= 8
    for x in xrange(new_width):
        for y in xrange(new_height):
            # TODO: colour map

            #charIdx = y + x * height * 8
            #src_i = y *
            for i in xrange(8):
                c, = struct.unpack('B', smap.read(1))
                #img.img[]

def decodeV1Bitmap(lflf_path, img, width, height):
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
    picMap, colourMap, and maskMap have an output size of width * height (I think).
    """
    # This file requires running v1col_extract. Other files are generated by scummrp.
    coloursFile = file(os.path.join(lflf_path, 'ROv1', 'BCv1'), 'rb')
    colours = list(struct.unpack('4B', coloursFile.read(4)))
    coloursFile.close()

    charFile = file(os.path.join(lflf_path, 'ROv1', 'B1v1'), 'rb')
    charMap = array.array('B')
    charMap.fromstring(charFile.read())
    #charMap = decodeC64Gfx(charFile, img, 2048)
    charFile.close()
    picFile = file(os.path.join(lflf_path, 'ROv1', 'B2v1'), 'rb')
    picMap = array.array('B')
    picMap.fromstring(picFile.read())
    #picMap = decodeC64Gfx(picFile, img, width * height)
    picFile.close()
    colourFile = file(os.path.join(lflf_path, 'ROv1', 'B3v1'), 'rb')
    colourMap = array.array('B')
    colourMap.fromstring(colourFile.read())
    #colourMap = decodeC64Gfx(colourFile, img, width * height)
    colourFile.close()

    # Dump un-RLEed files
    if True:
        charFile = file(os.path.join(lflf_path, 'charMap'), 'wb')
        charMap.tofile(charFile)
        charFile.close()
        picFile = file(os.path.join(lflf_path, 'picMap'), 'wb')
        picMap.tofile(picFile)
        picFile.close()
        colourFile = file(os.path.join(lflf_path, 'colourMap'), 'wb')
        colourMap.tofile(colourFile)
        colourFile.close()


    charIdx = None
    img_data = array.array('B', [0] * ((width * 8) * (height * 8)))
    dstPitch = width * 8
    # For each column strip number
    for x in xrange(width): # x is equivalent to stripnr
        # For every 8th row
        col_start = x * 8
        for y in xrange(height):
            colours[3] = (colourMap[y + x * height] & 7)

            charIdx = picMap[y + x * height] * 8
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

    img.img = img_data
    img.width = width * 8 #/ 2
    img.height = height * 8
    

def decodeC64Gfx(src, img, size):
    """void GdiV1::decodeC64Gfx(const byte *src, byte *dst, int size) const {
        int x, z;
        byte color, run, common[4];

        for (z = 0; z < 4; z++) {
            common[z] = *src++;
        }

        x = 0;
        while (x < size) {
            run = *src++;
            if (run & 0x80) {
                color = common[(run >> 5) & 3];
                run &= 0x1F;
                for (z = 0; z <= run; z++) {
                    dst[x++] = color;
                }
            } else if (run & 0x40) {
                run &= 0x3F;
                color = *src++;
                for (z = 0; z <= run; z++) {
                    dst[x++] = color;
                }
            } else {
                for (z = 0; z <= run; z++) {
                    dst[x++] = *src++;
                }
            }
        }"""

    x = None
    z = None
    colour = None
    run = None
    # Read the... common colours?
    common = struct.unpack('<4B', src.read(4))

    data = array.array('B')

    while len(data) < size:
        run, = struct.unpack('<B', src.read(1))
        if run & 0x80:
            colour = common[(run >> 5) & 3]
            run &= 0x1F
            for _ in xrange(run + 1):
                data.append(colour)
        elif run & 0x40:
            run &= 0x3F
            colour, = struct.unpack('<B', src.read(1))
            for _ in xrange(run + 1):
                data.append(colour)
        else:
            for _ in xrange(run + 1):
                colour, = struct.unpack('<B', src.read(1))
                data.append(colour)

    return data



# For v2. RLE, column-based.
def decodeV2Bitmap(smap, img, width, height):
    run = 1
    colour = 0
    data = 0
    dither = False
    dither_table = [0] * 128 # (same value as the height of backgrounds...)
    dither_table_i = 0
    for x in xrange(width):
        logging.debug("column: %d" % x)
        logging.debug("smap tell: %d" % smap.tell())
        logging.debug("Dither table: %s" % dither_table)
        dither_table_i = 0
        for y in xrange(height):
            run -= 1
            if run == 0:
                data, = struct.unpack('B', smap.read(1))
                if data & 0x80:
                    run = data & 0x7F
                    dither = True
                else:
                    run = data >> 4
                    dither = False
                if run == 0:
                    run, = struct.unpack('B', smap.read(1))
                colour = data & 0x0F
                logging.debug("data1: %d. run: %d. dither: %s. colour: %d" % (data, run, dither, colour))
            if not dither:
                dither_table[dither_table_i] = colour
            img.img[y * width + x] = dither_table[dither_table_i]
            dither_table_i += 1
        logging.debug("---")


# Works in custom-made image
def doUncompressed(smap, img, limit, stripNum):
    ##print "In uncompressed"
    xCounter = 0
    yCounter = 0

    while smap.tell() < limit:
        currPalIndex = arrayToInt(getByte(smap,0))
        img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
        xCounter += 1
        if xCounter >= 8:
            xCounter = 0
            yCounter += 1
            # This bit makes sure we don't go past the image's boundaries
            # (which can happen because a byte requires 8 bits but the
            # image may not need all those bits)
            if yCounter >= img.height:
                break

def doMethodOne(smap, img, limit, stripNum, paramSub, rendDir):
    ##print "In method one"
    xCounter = 0
    yCounter = 0
    bitAcc = 0 # Bit accumulator
    contReadingPal = False
    readCount = 0
    iSubVar = 1

    # Get first (top-left) colour/palette index
    currPalIndex = arrayToInt(getByte(smap, 0))
    ##print "initial pal index is " + str(currPalIndex)
    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
    # Move to next pixel
    if rendDir == HORIZONTAL:
        xCounter += 1
    else:
        ##print "In VERTICAL style"
        yCounter += 1
    ##print "put first pixel"


    while smap.tell() < limit and \
    ((rendDir == HORIZONTAL and yCounter < img.height) or
     (rendDir == VERTICAL and xCounter < 8)):
        thisByte = byteToBits(getByte(smap, 0), LE=1)

        # For each bit
        for b in thisByte:
            # Reading a palette index
            if contReadingPal:
                bitAcc += (b << readCount) # compensates for reading it in reverse
                readCount += 1
                # Finished reading palette index number
                if readCount == paramSub:
                    currPalIndex = bitAcc
                    ##print "Read new palette index, now " + str(currPalIndex)
                    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                    iSubVar = 1 # set subvar
                    # Move to next pixel
                    if rendDir == HORIZONTAL:
                        xCounter += 1
                        if xCounter >= 8:
                            xCounter = 0
                            yCounter += 1
                            if yCounter >= img.height:
                                break
                    else:
                        yCounter += 1
                        if yCounter >= img.height:
                            yCounter = 0
                            xCounter += 1
                            if xCounter >= 8:
                                break
                    ##print "put pixel"
                    contReadingPal = False
                    readCount = 0
                    bitAcc = 0

            elif b == 1:
                bitAcc = bitAcc << 1
                bitAcc += 1
                if bitAcc == NEGVAR:
                    iSubVar = ~iSubVar + 1 # convert -1 to 1 and vice versa
                    currPalIndex -= iSubVar
                    bitAcc = 0
                    # Place pixel
                    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                    # Move to next pixel
                    if rendDir == HORIZONTAL:
                        xCounter += 1
                        if xCounter >= 8:
                            xCounter = 0
                            yCounter += 1
                            if yCounter >= img.height:
                                break
                    else:
                        yCounter += 1
                        if yCounter >= img.height:
                            yCounter = 0
                            xCounter += 1
                            if xCounter >= 8:
                                break

            # Place pixel / end (and execute) a command
            elif b == 0:
                bitAcc = bitAcc << 1 # Do this so we get proper value for checking READPAL
                if bitAcc == READPAL:
                    contReadingPal = True
                    bitAcc = 0
                    # Don't place the pixel until we get the new palette index
                    continue
                elif bitAcc == SUBVAR:
                    currPalIndex -= iSubVar
                    bitAcc = 0
                # Place pixel
                img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                # Move to next pixel
                if rendDir == HORIZONTAL:
                    xCounter += 1
                    if xCounter >= 8:
                        xCounter = 0
                        yCounter += 1
                        if yCounter >= img.height:
                            break
                else:
                    yCounter += 1
                    if yCounter >= img.height:
                        yCounter = 0
                        xCounter += 1
                        if xCounter >= 8:
                            break
                ##print "put pixel"

def doMethodTwo(smap, img, limit, stripNum, paramSub, pal):
    ##print "In method two"
    xCounter = 0
    yCounter = 0
    bitAcc = 0 # Bit accumulator
    contReadingPal = False
    contReadingNumPix = False
    contReadingDecom = False
    readCount = 0

    # Get first (top-left) colour/palette index
    currPalIndex = arrayToInt(getByte(smap, 0))
    ##print "initial pal index is " + str(currPalIndex)
    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
    # Move to next pixel
    xCounter += 1


    while smap.tell() < limit and yCounter < img.height:
        thisByte = byteToBits(getByte(smap, 0), LE=1)

        # For each bit
        for b in thisByte:
            # Reading a palette index
            if contReadingPal:
                bitAcc += (b << readCount)
                readCount += 1
                # Finished reading palette index number
                if readCount == paramSub:
                    currPalIndex = bitAcc
                    ##print "Read new palette index, now " + str(currPalIndex)
                    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                    # Move to next pixel
                    xCounter += 1
                    if xCounter >= 8:
                        xCounter = 0
                        yCounter += 1
                        if yCounter >= img.height:
                                break
                    ##print "put pixel"
                    contReadingPal = False
                    readCount = 0
                    bitAcc = 0

            elif contReadingNumPix:
                bitAcc += (b << readCount)
                readCount += 1
                if readCount == 8:
                    for i in range(bitAcc):
                        img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                        xCounter += 1
                        if xCounter >= 8:
                            xCounter = 0
                            yCounter += 1
                            if yCounter >= img.height:
                                break
                        ##print "put pixel"
                    contReadingNumPix = False
                    readCount = 0
                    bitAcc = 0


            elif contReadingDecom:
                bitAcc += (b << readCount)
                ##print bitAcc
                readCount += 1 # how many bits it has read
                if readCount == 3:
                    # Serge's doc seems to have decrement and increments
                    # mixed up - hence contradictary names
                    if bitAcc == INCPAL4:
                        currPalIndex -= 4
                    elif bitAcc == INCPAL3:
                        currPalIndex -= 3
                    elif bitAcc == INCPAL2:
                        currPalIndex -= 2
                    elif bitAcc == INCPAL1:
                        currPalIndex -= 1
                    elif bitAcc == READ8BITS:
                        contReadingNumPix = True
                        bitAcc = 0
                        readCount = 0
                        contReadingDecom = False
                        continue
                    elif bitAcc == DECPAL1:
                        currPalIndex += 1
                    elif bitAcc == DECPAL2:
                        currPalIndex += 2
                    elif bitAcc == DECPAL3:
                        currPalIndex += 3
                    ##print "new currPalIndex is " + str(currPalIndex)
                    # Place pixel
                    img.img[(stripNum * 8 + xCounter) + (yCounter * img.width)] = currPalIndex
                    # Move to next pixel
                    xCounter += 1
                    if xCounter >= 8:
                        xCounter = 0
                        yCounter += 1
                        if yCounter >= img.height:
                            break
                    ##print "put pixel"
                    bitAcc = 0
                    readCount = 0
                    contReadingDecom = False

            elif b == 1:
                bitAcc = bitAcc << 1
                bitAcc += 1
                if bitAcc == READVAL:
                    contReadingDecom = True
                    bitAcc = 0

            # Place pixel / end (and execute) a command
            elif b == 0:
                bitAcc = bitAcc << 1 # Do this so we get proper value for checking READPAL
                if bitAcc == READPAL:
                    contReadingPal = True
                    bitAcc = 0
                    # Don't place the pixel until we get the new palette index
                    continue
                # Place pixel
                x_index = (stripNum * 8 + xCounter)
                y_index = (yCounter * img.width)
                final_index = x_index + y_index
                # This seems to occur in Sam 'n' Max room 2. The final image seems to be alright
                #  if we ignore these pixels.
                if final_index >= len(img.img):
                    pass
                    #print "x_index + y_index = %s, which is outside the image (max: %s)." % (final_index, len(img.img))
                else:
                    img.img[x_index + y_index] = currPalIndex
                # Move to next pixel
                xCounter += 1
                if xCounter >= 8:
                    xCounter = 0
                    yCounter += 1
                    if yCounter >= img.height:
                        break
                ##print "put pixel"

def decodeImage(lflf_path, image_path, version, palette_num):
    print "Reading dimensions..."
    # Get dimensions from RMHD file and initialise an image container
    width, height = getDimensions(lflf_path, version)
    print width, height
    img = ImageContainer(width, height)

    print "Reading palette..."
    # Get the palette
    pal = getPalette(lflf_path, version, palette_num)

    if version == 1:
        decodeV1Bitmap(lflf_path, img, width, height)
    elif version == 2:
        # Load pixelmap data
        smap_path = getSmapPath(lflf_path, version)
        smap = file(smap_path, 'rb')
        decodeV2Bitmap(smap, img, width, height)
        smap.close()
    else:
        # Load pixelmap data
        smap_path = getSmapPath(lflf_path, version)
        smap = file(smap_path, 'rb')
        # Do these things so we know the size of the last strip
        limit = 0
        header = getDWord(smap, 0) # not used
        blocksize = arrayToInt(getDWord(smap, 0))

        print "Retrieving strip offsets from SMAP..."
        # Get strip offsets
        numStrips = width/8
        stripOffsets = []
        [stripOffsets.append(arrayToInt(getDWordLE(smap, 0)))
             for _ in range(numStrips)]

        print "Reading strips from SMAP... "
        is_transparent = False
        # For reach strip
        for stripnum, s in enumerate(stripOffsets):
            smap.seek(s, 0)
            try:
                compID = arrayToInt(getByte(smap,0))
            except Exception, eofe:
                break # v4, loom CD, room 2
            # Default variables (based on uncompressed settings)
            compMethod = 0 # 0 will also stand for uncompressed
            paramSub = 0
            trans = False
            rendDir = HORIZONTAL

            ##print compID
            # Determine compression type
            if compID == 0x01:
                # Values are already initialised to uncompressed method settings
                pass
            # Method 1 variations
            elif compID >= 0x0E and compID <= 0x12:
                paramSub = compID - 0x0A
                rendDir = VERTICAL
                compMethod = 1
            elif compID >= 0x18 and compID <= 0x1C:
                paramSub = compID - 0x14
                compMethod = 1
            elif compID >= 0x22 and compID <= 0x26:
                paramSub = compID - 0x1E
                rendDir = VERTICAL
                trans = True
                compMethod = 1
            elif compID >= 0x2C and compID <= 0x30:
                paramSub = compID - 0x28
                trans = True
                compMethod = 1
            # Method 2 variations
            elif compID >= 0x40 and compID <= 0x44:
                paramSub = compID - 0x3C
                compMethod = 2
            elif compID >= 0x54 and compID <= 0x58:
                paramSub = compID - 0x50 # Serge's thing says 0x51
                trans = True
                compMethod = 2
            elif compID >= 0x68 and compID <= 0x6C:
                paramSub = compID - 0x64
                trans = True
                compMethod = 2
            elif compID >= 0x7C and compID <= 0x80:
                paramSub = compID - 0x78
                compMethod = 2
            else:
                print "Unknown compression method for strip " + str(compID)
                smap.close()
                sys.exit(1)

            if stripnum+1 == len(stripOffsets): # is it the last strip?
                limit = blocksize
            else:
                limit = stripOffsets[stripnum+1]
            # Try/except is for debugging - will show however much image we've decoded
            try:
                if compMethod == 0:
                    #print "Processing uncompresed strip"
                    doUncompressed(smap, img, limit, stripnum)
                elif compMethod == 1:
                    #print "Processing strip with method one"
                    doMethodOne(smap, img, limit, stripnum, paramSub, rendDir)
                elif compMethod == 2:
                    #print "Processing strip with method two"
                    doMethodTwo(smap, img, limit, stripnum, paramSub, pal)
                is_transparent = is_transparent or trans
            except Exception, e:
                print "ERROR: %s" % e
                print "An error occured - attempting to show incomplete image."
                im = Image.new('P', (img.width, img.height) )
                im.putpalette(pal)
                im.putdata(img.img)
                im.show()
                smap.close()
                raise e
        if is_transparent:
            print "WARNING! The original image contains transparency!\n " + \
                    "If you try to re-encode the output file, you will lose all transparency!"
        smap.close()

    print "Creating output image file..."
    # Create our new image!
    im = Image.new('P', (img.width, img.height) )
    im.putpalette(pal)
    im.putdata(img.img)
    if os.path.splitext(image_path)[1].lower() != '.png':
        image_path += '.png'
    im.save(image_path, 'png') # always saves to PNG files.
