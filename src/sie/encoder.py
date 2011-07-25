import array
from collections import defaultdict
import xml.etree.ElementTree as et
import logging
import os
import struct
import Image
from decoder import getPalette
from sie_util import intToBytes, getChunk, ScummImageEncoderException

def testEncodeInput(source, quantization, freeze_palette):
    if source.size[0] % 8 > 0 or source.size[1] % 8 > 0:
        raise ScummImageEncoderException("Error: Input height and/or width must be a mulitple of 8.")
    elif freeze_palette:
        if source.palette == None or len(source.palette.palette) != 256 * 3:
            raise ScummImageEncoderException("Error: Input image must have 256 colour palette, if 'freeze palette' option is chosen.")
    elif source.palette == None:
        return source.quantize(quantization)
    return source

def updateRMHD(lflf_path, version, width, height):
    if version <= 4:
        rmhd_path = os.path.join(lflf_path, "RO", "HD.xml")
    elif version >= 5:
        rmhd_path = os.path.join(lflf_path, "ROOM", "RMHD.xml")
    if not os.path.isfile(rmhd_path):
        raise ScummImageEncoderException("Can't find room header file: %s" % rmhd_path)
    tree = et.parse(rmhd_path)
    root = tree.getroot()

    root.find("width").text = str(width)
    root.find("height").text = str(height)

    et.ElementTree(root).write(rmhd_path)

def updatePalette(lflf_path, version, source_image, quantization, palette_num):
    if version <= 4:
        pal_path = os.path.join(lflf_path, "RO", "PA.dmp")
    elif version == 5:
        pal_path = os.path.join(lflf_path, "ROOM", "CLUT.dmp")
    elif version >= 6:
        pal_path = os.path.join(lflf_path, "ROOM", "PALS", "WRAP", "APAL_" + str(palette_num).zfill(3) + ".dmp")
    if not os.path.isfile(pal_path):
        raise ScummImageEncoderException("Can't find palette file: %s" % pal_path)
    oldclutfile = file(pal_path, 'rb')
    oldclutcontents = getChunk(oldclutfile, 776, 0)
    oldclutfile.close()
    newclutfile = file(pal_path, 'wb')
    oldclutcontents.tofile(newclutfile)
    newclutfile.seek(8 + 16 * 3, 0) # skip header and EGA palette
    newpal = array.array('B', source_image.palette.palette[:quantization * 3]) # copy RGB data for first 160 colours
    newpal.tofile(newclutfile)
    newclutfile.close()


def writeSmap(lflf_path, version, source, freeze_palette):
    if version <= 4:
        smap_path = os.path.join(lflf_path, "RO", "BM.dmp")
    elif version >= 5:
        smap_path = os.path.join(lflf_path, "ROOM", "RMIM", "IM00", "SMAP.dmp")
    if not os.path.isfile(smap_path):
        raise ScummImageEncoderException("Can't find existing SMAP file: %s" % smap_path)
    width, height = source.size
    bitdata = list(source.getdata())
    # Write strips
    newsmapfile = file(smap_path, 'wb')
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

    if freeze_palette:
        palette_offset = 0
    else:
        palette_offset = 16

    # Figure out why it doesn't add the last strip
    for stripNum in xrange(numStrips):
        newsmapfile.write(chr(01)) # tell it it's an uncompressed thingo
        stripData = array.array('B')
        for rowNum in range(height):
            for pixel in bitdata[stripNum * 8 + rowNum * width:
                                 stripNum * 8 + rowNum * width + 8]:
                stripData.append(pixel + palette_offset)
        ##if numStrips - stripNum <= 1:
            ##print stripData
        stripData.tofile(newsmapfile)

    # Write the header
    newsmapfile.seek(0, 2)
    blocksize = newsmapfile.tell()
    newsmapfile.seek(0, 0)
    newsmapfile.write('SMAP')
    intToBytes(blocksize).tofile(newsmapfile)
    newsmapfile.close()

def updateV2HD(lflf_path, version, width, height):
    hd_file = file(os.path.join(lflf_path, "ROv2", "HDv2"), 'wb')
    data = struct.pack('<2H', width, height)
    hd_file.write(data)
    hd_file.close()

def packRunInfoV2(run, colour, dithering):
    logging.debug("Writing out run info. run: %d, colour: %s, dithering: %s" % (run, colour, dithering))
    data = None
    if dithering:
        if run > 0x7F:
            data = struct.pack('2B', 0x80, run)
        else:
            data = struct.pack('B', 0x80 | run)
    else:
        if run > 0x07:
            data = struct.pack('2B', colour, run)
        else:
            data = struct.pack('B', (run << 4) | colour)
    logging.debug("  packed data = %r" % data)
    return data

def writeV2Bitmap(lflf_path, source):
    img_file = file(os.path.join(lflf_path, "ROv2", "IMv2"), 'wb')
    width, height = source.size
    source_data = source.getdata()
    dither_table = [None] * 128
    run = 0
    colour = None
    b = None
    dithering = False
    for x in xrange(width):
        dither_i = 0
        logging.debug("Column: %d" % x)

        # Original encoded images seem to reset the dither table every 8th column.
        # Presumably to aid in drawing "strips", which are 8 pixels wide.
        if not x % 8:
            dither_table = [None] * 128

        logging.debug("Dither table: %s" % dither_table)

        for y in xrange(height):
            # Get the current pixel.
            b = source_data[y * width + x]
            # Check if we can dither. (The original encoder seems to favour dithering over efficient run compression.
            #  It will revert to dithering even if it interrupts a continuous run of colour.)
            if not dithering and b == dither_table[dither_i]:
                if run:
                    data = packRunInfoV2(run, colour, dithering)
                    img_file.write(data)
                dithering = True
                run = 1
                colour = None
            # If the current pixel is the same, or we're currently dithering and
            # the dither colour matches this pixel, increment run counter.
            # Also need to check bounds - maximum value of a run is
            # 0xFF.
            elif run < 0xFF and \
               (b == colour or (dithering and b == dither_table[dither_i])):
                run += 1
                if not dithering:
                    dither_table[dither_i] = colour
            # Current pixel is not the same as the last.
            else:
                logging.debug("Ending run. b: %d. dither_table value: %s" % (b, dither_table[dither_i]))
                # End the run, only if we have started one (e.g. the start of a column).
                if run:
                    data = packRunInfoV2(run, colour, dithering)
                    img_file.write(data)
                # Start a new run.
                run = 1
                # If the current pixel is the same as the dither colour, engage dithering mode.
                if b == dither_table[dither_i]:
                    dithering = True
                    colour = None
                else:
                    dithering = False
                    colour = b
                    dither_table[dither_i] = colour
                logging.debug("Start of new run. colour: %s, dithering: %s" % (colour, dithering))
            dither_i += 1

        logging.debug("---")

    # End the last run encountered, once we reach the end of the file.
    data = packRunInfoV2(run, colour, dithering)
    img_file.write(data)
    img_file.close()

def compressRLEV1(data):
    pass

def getCommonColoursV1(source):
    """
    Rather than get the 3 most common colours across the whole image, we want
    to get the most common colours across each 8x8 block.
    """
    width, height = source.size
    source_data = source.getdata()
    num_strips = width / 8
    num_blocks = height / 8

    dstPitch = width
    colour_freqs = defaultdict(lambda: 0)
    for strip_i in xrange(num_strips):
        col_start = strip_i * 8
        for block_i in xrange(num_blocks):
            block_colours = set()
            for row in xrange(8):
                row_start = col_start + ((block_i * 8 + row) * dstPitch)
                for col in xrange(0, 8, 2):
                    val = source_data[row_start + col]
                    block_colours.add(val)
            for bc in block_colours:
                colour_freqs[bc] += 1
    logging.debug(colour_freqs)
    colour_freqs_sorted = sorted(colour_freqs.items(), cmp=lambda x,y: cmp(x[1], y[1]))
    return [c for c, f in colour_freqs_sorted[-3:]]

def writeV1Bitmap(lflf_path, source):
    """
    Encoding:
    - Store 8 pixels in 1 byte (2 bits per colour, 4 colours per row, each colour output twice).
    - Store that value in charMap
    - Add the charMap index to picMap
    - Add the block's custom colour to colourMap
    When done, run RLE over each map.
    """
    commonColours = array.array('B') # BCv1 - always 4 bytes
    charMap = array.array('B') # B1v1 - always 2048 bytes
    picMap = array.array('B') # B2v1
    colourMap = array.array('B') # B3v1
    width, height = source.size
    source_data = source.getdata()

    if width % 8 or height % 8:
        raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimentsions: %dx%d)" % (width, height))
    num_strips = width / 8
    num_blocks = height / 8

    # Get the three most used colours. The fourth colour is determined per block.
    #logging.debug(source.getcolors())
    #logging.debug(sorted(source.getcolors()))
    #common_colours = [clr for freq, clr in sorted(source.getcolors())[-3:]]
    common_colours = getCommonColoursV1(source)
    logging.debug("Common colours: %s" % common_colours)
    colours_used = []
    block_map = {} # map block CRCs to indices into the picMap

    dstPitch = width
    for strip_i in xrange(num_strips):
        col_start = strip_i * 8
        for block_i in xrange(num_blocks):
            block_data = []
            custom_colour = None
            for row in xrange(8):
                row_start = col_start + ((block_i * 8 + row) * dstPitch)
                row_data = 0
                for col in xrange(0, 8, 2):
                    val1 = source_data[row_start + col]
                    val2 = source_data[row_start + col + 1] # only used for validation
                    if val1 != val2:
                        raise ScummImageEncoderException("V1 images can only have one colour per every two pixels on the x axis. " +
                        "Offending pixel at (%d, %d)" % ((row_start + col + 1) % width, (row_start + col + 1) / width))

                    # Convert from the source colour table index, to an index in our 4-value colour array.
                    if val1 in common_colours:
                        colour = common_colours.index(val1)
                    else:
                        if custom_colour is None:
                            custom_colour = val1
                        if custom_colour == val1:
                            colour = 3
                        else:
                            logging.error("Too many colours. Common: %s, custom: %s, offending: %s" % (common_colours, custom_colour, val1))
                            raise ScummImageEncoderException("Image has too many colours in a block - max of 4 colours allowed " +
                                                             "(3 common colours and 1 custom colour for the block).  " +
                            "Offending pixel at (%d, %d)" % ((row_start + col) % width, (row_start + col) / width))

                    # Compress 4 pixels to 1 byte
                    colour &= 3
                    row_data |= colour << 6 - col
                    # end col
                block_data.append(row_data)
                # end row
            # If this 8x8 block has been used before in the image, re-use that block's index.
            # Otherwise, output the new data to the charMap, and store the hash of the block
            #  in a lookup table, so we can test if future blocks can re-use the same character data.
            block_key = tuple(block_data) # block data is going to be, at most, 8 bytes, so not too inefficient.
            if block_key in block_map:
                picMap.append(block_map[block_key])
            else:
                row_char_idx = len(charMap) / 8 # Need to store the index of the charMap entry that starts the row.
                print row_char_idx
                for r in block_data:
                    charMap.append(r)
                picMap.append(row_char_idx)
                block_map[block_key] = row_char_idx
            if custom_colour is None:
                custom_colour = 0
            colourMap.append(custom_colour)
            # end block
        # end strip

    # If the charMap is too small, pad it out. Not sure why my encoded images use less chars.
    while len(charMap) < 2048:
        charMap.append(0)

    # If picMap or colourMap is not the size of the image (divided into 8x8 blocks),
    #  there's something wrong with my code.
    if len(picMap) != num_strips * num_blocks or \
        len(colourMap) != num_strips * num_blocks:
        raise ScummImageEncoderException("I don't seem to have generated enough entries in either the picMap or colourMap. " +
            "Expected entries: %d. picMap entries: %d. colourMap entries: %d." % (num_strips * num_blocks, len(picMap), len(colourMap)))

    # Output all files.
    # TODO: run RLE on them.
    charFile = file(os.path.join(lflf_path, 'charMap'), 'wb')
    charMap.tofile(charFile)
    charFile.close()
    picFile = file(os.path.join(lflf_path, 'picMap'), 'wb')
    picMap.tofile(picFile)
    charFile.close()
    colourFile = file(os.path.join(lflf_path, 'colourMap'), 'wb')
    colourMap.tofile(colourFile)
    colourFile.close()

                


# TODO: allow for larger number of colours by allowing users to
# specify costumes and/or objects palette to include
# Allow choice between room or object encoding (affects header generation)
# Currently just replaces 160 colours
def encodeImage(lflf_path, image_path, version, quantization, palette_num, freeze_palette):
    """ Convert a paletted image to a 160-colour image, generating
    appropriate header and palette files as well."""
    source_image = Image.open(image_path)
    source_image = testEncodeInput(source_image, quantization, freeze_palette)
    width, height = source_image.size

    # Only fix the palette if there's more than colours than the quantization limit.
    if version > 2 and \
        not freeze_palette and len(source_image.palette.palette) > quantization * 3:
        source_image = source_image.quantize(quantization) # This doesn't work because palette is shifted <--- what?

    # Have to save and re-open due to stupidity of PIL (or me)
    source_image.save('temp.png','png')
    source_image = Image.open('temp.png')

    if version == 1:
        # TODO: update V1HD
        writeV1Bitmap(lflf_path, source_image)
    elif version <= 2:
        # Removed because my decoder outputs images with 256 colour palettes.
#        if len(source_image.palette.palette) > 0xF * 3:
#            raise ScummImageEncoderException("Encoding a V2 image requires a palette of 16 colours (input image uses %d colours)." % len(source_image.palette.palette) / 3)
        updateV2HD(lflf_path, version, width, height)
        writeV2Bitmap(lflf_path, source_image)
    else:
        # Update an existing room header
        updateRMHD(lflf_path, version, width, height)

        if freeze_palette:
            # Reload the original palette. Just in case.
            pal = getPalette(lflf_path, version, palette_num)
            source_image.putpalette(pal)
        else:
            # Write new palette (copying missing palette info from old palette)
            updatePalette(lflf_path, version, source_image, quantization, palette_num)


        # Write the bitmap data
        writeSmap(lflf_path, version, source_image, freeze_palette)

    # Cleanup
    os.remove(os.path.join(os.getcwd(), "temp.png"))
