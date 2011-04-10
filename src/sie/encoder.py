import os
import sys
import array
import Image
from sie_util import getWord, strToArray, intToBytes, getChunk

inputfilename = "input.png"
inputfiletype = "png"

def testEncodeInput(source):
    if source.size[0] % 8 > 0 or source.size[1] % 8 > 0:
        print "Error: Input height and/or width must be a mulitple of 8."
        sys.exit(1)
    elif source.palette == None:
        return source.quantize(160)
    return source

# TODO: allow for larger number of colours by allowing users to
# specify costumes and/or objects palette to include
# Allow choice between room or object encoding (affects header generation)
# Currently just replaces 160 colours
def encodeImage(rmhdfile, palfile):
    """ Convert a paletted image to a 160-colour image, generating
    appropriate header and palette files as well."""

    source = Image.open(inputfilename)
    source = testEncodeInput(source)
    width, height = source.size

    # Only fix the palette if there's more than 160 colours
    if len(source.palette.palette) > 160 * 3:
        source = source.quantize(160) # This doesn't work because palette is shifted
        ##newpal,

    # Have to save and re-open due to stupidity of PIL (or me)
    source.save('temp.png','png')
    source = Image.open('temp.png')
    bitdata = list(source.getdata())

    ##stripData = []
    # Write some files
    # RMHD file
    # get num objects from old RMHD file
    oldrmhdfile = file(rmhdfile, 'rb')
    oldrmhdfile.seek(-2, 2)
    oldnumobjects = getWord(oldrmhdfile, 0)
    oldrmhdfile.close()
    newrmhdfile = file(rmhdfile, 'wb')
    rmhdcontents = array.array('B')
    rmhdcontents += strToArray("RMHD")
    rmhdcontents += intToBytes(14)
    rmhdcontents += intToBytes(width, 2, 1)
    rmhdcontents += intToBytes(height, 2, 1)
    rmhdcontents += oldnumobjects
    rmhdcontents.tofile(newrmhdfile)
    newrmhdfile.close()

    # Write new palette (copying missing palette info from old palette)
    oldclutfile = file(palfile, 'rb')
    oldclutcontents = getChunk(oldclutfile, 776, 0)
    oldclutfile.close()
    newclutfile = file(palfile, 'wb')
    oldclutcontents.tofile(newclutfile)
    newclutfile.seek(8 + 16 * 3, 0)
    newpal = array.array('B', source.palette.palette[:160 * 3])
    newpal.tofile(newclutfile)
    newclutfile.close()

    # Write strips
    newsmapfile = file('000_SMAP.dmp', 'wb')
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
    for i in range(numStrips):
        intToBytes(currStripOffsetValue, LE=1).tofile(newsmapfile)
        currStripOffsetValue += stripSize+1 # add one for compression ID

    # Figure out why it doesn't add the last strip
    for stripNum in range(numStrips):
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
    os.remove(os.path.join(os.getcwd(), "temp.png"))
