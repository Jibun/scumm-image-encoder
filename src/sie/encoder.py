import array
import xml.etree.ElementTree as et
import os
import Image
from sie_util import intToBytes, getChunk, ScummImageEncoderException

def testEncodeInput(source, quantization):
    if source.size[0] % 8 > 0 or source.size[1] % 8 > 0:
        raise ScummImageEncoderException("Error: Input height and/or width must be a mulitple of 8.")
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


def writeSmap(lflf_path, version, source):
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
    numStrips = width/8
    stripsStartOffset = blockStart + (numStrips * 4) # each offset is a DWord
    currStripOffsetValue = stripsStartOffset
    stripSize = height*8
    # Write strip offsets
    # Because we're just using uncompressed things, we can cheat and
    # predict how big a strip will be
    for _ in xrange(numStrips):
        intToBytes(currStripOffsetValue, LE=1).tofile(newsmapfile)
        currStripOffsetValue += stripSize+1 # add one for compression ID

    # Figure out why it doesn't add the last strip
    for stripNum in xrange(numStrips):
        newsmapfile.write(chr(01)) # tell it it's an uncompressed thingo
        stripData = array.array('B')
        for rowNum in range(height):
            for pixel in bitdata[stripNum * 8 + rowNum * width:
                                 stripNum * 8 + rowNum * width + 8]:
                stripData.append(pixel + 16)
        ##if numStrips - stripNum <= 1:
            ##print stripData
        stripData.tofile(newsmapfile)

    # Write the header
    newsmapfile.seek(0,2)
    blocksize = newsmapfile.tell()
    newsmapfile.seek(0,0)
    newsmapfile.write('SMAP')
    intToBytes(blocksize).tofile(newsmapfile)
    newsmapfile.close()

# TODO: allow for larger number of colours by allowing users to
# specify costumes and/or objects palette to include
# Allow choice between room or object encoding (affects header generation)
# Currently just replaces 160 colours
def encodeImage(lflf_path, image_path, version, quantization, palette_num):
    """ Convert a paletted image to a 160-colour image, generating
    appropriate header and palette files as well."""
    source_image = Image.open(image_path)
    source_image = testEncodeInput(source_image, quantization)
    width, height = source_image.size

    # Only fix the palette if there's more than 160 colours
    if len(source_image.palette.palette) > quantization * 3:
        source_image = source_image.quantize(quantization) # This doesn't work because palette is shifted <--- what?

    # Have to save and re-open due to stupidity of PIL (or me)
    source_image.save('temp.png','png')
    source_image = Image.open('temp.png')

    # Update an existing room header
    updateRMHD(lflf_path, version, width, height)

    # Write new palette (copying missing palette info from old palette)
    updatePalette(lflf_path, version, source_image, quantization, palette_num)

    # Write the bitmap data
    writeSmap(lflf_path, version, source_image)

    # Cleanup
    os.remove(os.path.join(os.getcwd(), "temp.png"))
