import array
import xml.etree.ElementTree as et
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

def packRunInfo(run, colour, dithering, img_file):
    pass

def writeV2Bitmap(lflf_path, version, source):
    img_file = file(os.path.join(lflf_path, "ROv2", "IMv2"))
    width, height = source.size
    run = 0
    colour = None
    b = None
    left_b = None
    dithering = False
    source_data = source.getdata()
    for x in xrange(width):
        colour = None
        dithering = False
        for y in xrange(height):
            # Get the current pixel.
            b = source_data[y * width + x]
            # Get the pixel to the left of the current pixel. Used for "dithering" table.
            if x:
                left_b = source_data[y * width + x - 1]
            # If the current pixel is the same, or we're currently dithering and
            # the left pixel matches this pixel, increment run counter
            if b == colour or \
                (dithering and left_b == b):
                run += 1
            # Current pixel is not the same as the last.
            else:
                # End the run, only if this is not the start of a column.
                if y:
                    packRunInfo(run, colour, dithering, img_file)
                run = 1
                colour = b

        # TODO: End the last run encountered.
        pass


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


    if version <= 2:
        updateV2HD(lflf_path, version, width, height)
        writeV2Bitmap(lflf_path, version, source_image)
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
