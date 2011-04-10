import array

decryptvalue = 0x69

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