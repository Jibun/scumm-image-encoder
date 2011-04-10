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
from optparse import OptionParser

from sie.decoder import *
from sie.encoder import *

rmhdfile = "000_RMHD.dmp"
smapfile = "000_SMAP.dmp"
palfile = "006_CLUT.dmp"

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
