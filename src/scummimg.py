##################################################################
####
#### SCUMM Image Encoder
#### Laurence Dougal Myers
#### Begun 25 September 2004
#### Slightly modified 12 May 2009
#### Revitalised April 2011
####
#### Encode/decode images from LucasArts adventure games.
####
####
##################################################################
#### TODO:
####
#### Allow choices for input and output (including output filetype)
####
#### Support objects images (including multiple images for a
#### single object)
####
#### Rename "INCPAL4" etc constants to what they actually are
####
##################################################################
import os
import sys
import array
import Image
import traceback
import copy
from optparse import OptionParser

rmhdfile = "000_RMHD.dmp"
smapfile = "000_SMAP.dmp"
palfile = "006_CLUT.dmp"

requireddecodefiles = [rmhdfile, smapfile, palfile]
requiredencodefiles = [rmhdfile, palfile]

outfilename = "output"
outfiletype = "png"
inputfilename = "input.png"
inputfiletype = "png"

egapal = [(0x00, 0x00, 0x00), (0x00, 0x00, 0xAB), (0x00, 0xAB, 0x00), (0x00, 0xAB, 0xAB),
          (0xAB, 0x00, 0x00), (0xAB, 0x00, 0xAB), (0xAB, 0x57, 0x00), (0xAB, 0xAB, 0xAB),
          (0x57, 0x57, 0x57), (0x57, 0x57, 0xFF), (0x57, 0xFF, 0x57), (0x57, 0xFF, 0xFF),
          (0xFF, 0x57, 0x57), (0xFF, 0x57, 0xFF), (0xFF, 0xFF, 0x57), (0xFF, 0xFF, 0xFF)]

##indexmap = {}
# Leave room for new index palette mappings, but leave EGA palette as-is
indexmap  = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15] + [0]*240

decryptvalue = 0x69

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


class ImageContainer:
    def __init__(self, width, height):
        """ Container for an image array, with dimensions metadata."""
        self.width = width
        self.height = height
        # Initialise the img array to the given dimensions
        # Should probably use a 2D array from numarray, but when I tried that
        # it was slower initialising and it didn't work properly.
        # Need to add an extra row for padding (should be ignored when writing
        # to a file anyway)
        self.img = array.array('B', [0] * (width * height))
        ##[self.img.append(0) for dummyvar in range(width*height+width)]

# Decrypt also doubles as encrypt, I'm just too lazy to name it properly
def decrypt(input):
    """ Perform an XOR with a decrypt value on an array."""
    if isinstance(input, array.array):
        # Should also check if it's an array of the same typecode
        for i, byte in enumerate(input):
            input[i] = byte ^ decryptvalue 
    return input

def getByte(file, encrypted=1):
    """ Retrieve a single byte from a given file and decrypt it."""
    temparray = array.array('B')
    temparray.fromfile(file, 1)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getWord(file, encrypted=1):
    """ Retrieve two bytes from a given file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, 2)
    if encrypted:
        return decrypt(temparray)
    return temparray

# Is LE right? I get confused between endians.
def getWordLE(file, encrypted=1):
    """ Retrieve two bytes from a given file, decrypt them, reverse them and return an 
    array.
    """
    
    temp = getWord(file, encrypted)
    temp.reverse()
    return temp

def getDWord(file, encrypted=1):
    """ Retrieve four bytes from a given file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, 4)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getDWordLE(file, encrypted=1):
    """ Retrieve four bytes from a given file and decrypt them, and return an 
    array in reverse order.
    """
    
    temp = getDWord(file, encrypted)
    temp.reverse()
    return temp

def getQWord(file, encrypted=1):
    """ Retrieve eight bytes from a given file and decrypt them.
    
    Not actually used in the program, but could be used to get the header
    (rather than calling getDWord twice).
    """
    
    temparray = array.array('B')
    temparray.fromfile(file, 8)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getChunk(file, size, encrypted=1):
    """ Retrieve any number of bytes from a gven file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, size)
    if encrypted:
        return decrypt(temparray)
    return temparray

def arrayToInt(input):
    """ Convert an array of bytes (assumed to be in BE format) into a
    single value.

    Can probably be abused quite badly as there's no check on the length,
    so it may end up returning a really rather large number.
    """
    ##if isinstance(input, array.array):
    output = 0
    input.reverse()
    for i, c in enumerate(input):
        output += c << 8*i
    return output

def byteToBits(input, LE=0):
    """ Converts a byte (in an array) into an array of 1s and/or 0s."""
    if len(input) > 1:
        print "byteToBits function given an array larger than one byte."
        return
    output = array.array('B')
    input = input[0]
    for i in range(8):
        output.append(input & 0x01)
        input = input >> 1
    if not LE:
        output.reverse()
    return output

# Haven't used or tested this
def bitsToByte(input, LE=0):
    """ Converts an array of bits into a array containing a single byte."""

    output = array.array('B')
    acc = 0
    if LE:
        input.reverse()
    for i in input:
        acc << 1
        acc += i
    output.append(acc)
    return output

def bitsToInt(input, LE=0):
    """ Converts an array of bits into an integer value."""

    acc = 0
    if LE:
        input.reverse()
    for i in input:
        acc << 1
        acc += i
    return acc

def intToBytes(input, length=4, LE=0):
    """ Convert an integer into its machine code equivalent."""

    output = array.array('B')
    # May be a long integer or a regular integer
    while hex(input) != '0x0' and hex(input) != '0x0L':
        output.append(input & 0xFF)
        input = input >> 8
    # Pad output as necessary (also accounts for "0" input)
    while len(output) < length:
        output.append(0)
    if not LE:
        output.reverse()
    return output

def strToArray(input):
    """ Convert a string into its machine code equivalent."""
    
    output = array.array('B')
    output.fromstring(input)
    return output

#---- End basic data manipulation

def getDimensions():

    rmhd = file(rmhdfile, 'rb')
    getQWord(rmhd, 0)
    width = getWordLE(rmhd, 0)
    height = getWordLE(rmhd, 0)
    rmhd.close()
    return arrayToInt(width), arrayToInt(height)

def getPalette():
    palf = file(palfile, 'rb')
    header = getQWord(palf)
    pal = []
    # Add tuples of RGB values for 256 colours
    ##[pal.append((arrayToInt(getByte(palf, 0)), arrayToInt(getByte(palf, 0)),
    ##             arrayToInt(getByte(palf, 0)))) for i in range(256)]
    [pal.append( arrayToInt(getByte(palf, 0)) ) for i in range(768)]
    # While testing, just add one byte
    ##[pal.append(arrayToInt(getByte(palf, 0))) for i in range(256)]
    palf.close()
    return pal

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

# Should work now
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
    
# Should work now
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
    ##print "put first pixel"


    while smap.tell() < limit and yCounter < img.height:
    ##while smap.tell() < limit:
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
                    print "x_index + y_index = %s, which is outside the image (max: %s)." % (final_index, len(img.img))
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

def decodeImage(lflf):
    print "Reading dimensions from RMHD..."
    # Get dimensions from RMHD file and initialise an image container
    width, height = getDimensions()
    print width, height
    img = ImageContainer(width, height)

    print "Reading palette from CLUT..."
    # Get the palette
    pal = getPalette()
    
    # Load pixelmap data
    #destpath = os.path.join("008_RMIM", "001_IM00")
    #os.chdir(os.path.join(os.getcwd(), destpath))
    smap = file(smapfile, 'rb')
    
    # Do these things so we know the size of the last strip
    limit = 0
    header = getDWord(smap, 0) # not used
    blocksize = arrayToInt(getDWord(smap, 0))
    
    print "Retrieving strip offsets from SMAP..."
    # Get strip offsets
    numStrips = width/8
    stripOffsets = []
    [stripOffsets.append(arrayToInt(getDWordLE(smap, 0)))
         for dummyvar in range(numStrips)]

    print "Reading strips from SMAP... "
    # For reach strip
    for stripnum, s in enumerate(stripOffsets):
        smap.seek(s, 0)
        compID = arrayToInt(getByte(smap,0))
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
                print "Processing uncompresed strip"
                doUncompressed(smap, img, limit, stripnum)
            elif compMethod == 1:
                print "Processing strip with method one"
                doMethodOne(smap, img, limit, stripnum, paramSub, rendDir)
            elif compMethod == 2:
                print "Processing strip with method two"
                doMethodTwo(smap, img, limit, stripnum, paramSub, pal)
        except Exception, e:
            traceback.print_exc()
            print "ERROR: %s" % e
            print "An error occured - attempting to show incomplete image."
            im = Image.new('P', (img.width, img.height) )
            im.putpalette(pal)
            im.putdata(img.img)
            ##im.fromstring(img.img.tostring())
            im.show()
            smap.close()
            sys.exit(1)

    smap.close()
    
    # Go back two directories
    ##os.chdir(os.path.dirname(os.path.dirname(os.getcwd())))

    print "Creating image file..."
    # Create our new image!
    im = Image.new('P', (img.width, img.height) )
    im.putpalette(pal)
    im.putdata(img.img)
    ##im.fromstring(img.img.tostring())
    ##im.show()
    im.save(outfilename + "." + outfiletype, outfiletype)


# Not used as PIL's optimize seems to do a better job
# This is basically a rip-off of the technique for palette-based quantization
# from the article "Optimizing Color Quantization for ASP.NET Images"
# by Morgan Skinner from MSDN.
# I added some crap predominant colour checking.
def getNearestColour(incolour, pal):
    newIndex = 0
    leastDistance = 2147483647 # max value for integer
    checkrange = 5
    in_r, in_g, in_b = incolour
    
    for i, (r,g,b) in enumerate(pal):
        redDistance = r - in_r
        greenDistance = g - in_g
        blueDistance = b - in_b

        # Check for a predominant colour.
        # Silly hack because there's heaps of greens and I can't tell
        # the difference between them.
        # This makes for poorer saturation matching but better
        # luminosity. Mostly, this means we can (ab)use the EGA palette
        # which is included in every palette.
        if greenDistance < 16 and redDistance >= 87 and blueDistance >= 87:
            redDistance -= 48
            blueDistance -= 48
        elif blueDistance < 16 and greenDistance >= 87 and redDistance >= 87:
            redDistance -= 48
            greenDistance -= 48
        elif redDistance < 16 and greenDistance >= 87 and blueDistance >= 87:
            greenDistance -= 48
            blueDistance -= 48
        
        distance = (redDistance * redDistance) + \
                   (greenDistance * greenDistance) + \
                   (blueDistance * blueDistance)
        
        if distance < leastDistance:
            newIndex = i
            leastDistance = distance
            # Exact match, don't bother searching any more
            if distance == 0:
                ##print "exact colour found"
                return newIndex

    return newIndex

# Not used as PIL's optimize seems to do a better job
def fixPalette(palsorted, paltuples, outputdata,):
    droppal = palsorted[:len(palsorted)-160]
    print str(len(droppal)) + " colours will be dropped."
    # Truncate old palette
    newpaltuples = copy.copy(egapal)
    
    for newindex, (count, oldindex) in enumerate(palsorted[-160:]):
        # In EGA pal
        ##if oldindex < 16:
            # Don't bother remapping, EGA pal stays the same
            # Don't bother adding it, EGA pal already added
        ##    continue
        ##else:
            # Add new colour
            newpaltuples.append( paltuples[oldindex] )
            # Remap to new index (and compensate for EGA pal)
            indexmap[oldindex] = newindex + 16
    # Remap all dropped colours
    for count, oldindex in droppal:
        ##if oldindex < 16:
        ##    continue
        newindex = getNearestColour(paltuples[oldindex], newpaltuples)
        indexmap[oldindex] = newindex
    
    # Re-assign the palette indexes of the entire image (booo)
    newdata = array.array('B', [0] * (width * height))
    for i, oldpixelindex in enumerate(outputdata):
        ##if oldpixelindex < 16:
        ##    continue
        newdata[i] = indexmap[oldpixelindex]

    return newdata, newpaltuples

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
def encodeImage():
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


def main():
    oparser = OptionParser(usage="%prog [options] lflf_path imagefile.png",
                      version="mi2img v1 r2")
    
    oparser.add_option("-e", "--encode", action="store_true",
                      dest="encode", default=False,
                      help="Encode the given PNG into a format useable by SCUMM V5/v6 games. "
                      "You must already have an existing 000_RMHD.dmp, 000_SMAP.dmp, and 006_CLUT.dmp.")
    oparser.add_option("-d", "--decode", action="store_true",
                      dest="decode", default=False,
                      help="Decode a SCUMM V5/V6 image into a PNG file, "
                      "from 000_RMHD.dmp, 000_SMAP.dmp, and 006_CLUT.dmp files.")
    
    options, args = oparser.parse_args()
    
    if len(args) != 2:
        returnval = 1
        oparser.print_help()
    elif options.encode:
        global inputfilename
        inputfilename = args[1]
        encodeImage()
        print "Done!"
        returnval = 0
    elif options.decode:
        global outfilename
        outfilename = args[1]
        decodeImage()
        print "Done!"
        returnval = 0
    else:
        returnval = 1
        oparser.print_help()
        

    return returnval

if __name__ == "__main__": main()
