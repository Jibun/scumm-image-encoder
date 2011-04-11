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
#### Support objects images (including multiple images for a
#### single object)
####
#### Rename "INCPAL4" etc constants to what they actually are
####
##################################################################
import sys
import traceback
from optparse import OptionParser

from sie.decoder import *
from sie.encoder import *

def main():
    oparser = OptionParser(usage="%prog [options] lflf_path imagefile.png",
                      version="scumm image encoder v2 r1")
    
    oparser.add_option("-e", "--encode", action="store_true",
                      dest="encode", default=False,
                      help="Encode the given PNG into a format useable by SCUMM V5/v6 games. "
                      "You must already have an existing unpacked LFLF block, with a RMHD.xml, SMAP, and CLUT or APAL file.")
    oparser.add_option("-d", "--decode", action="store_true",
                      dest="decode", default=False,
                      help="Decode a SCUMM V5/V6 image into a PNG file, "
                      "from an unpacked LFLF block.")
    oparser.add_option("-v", "--sversion", action="store",
                      dest="version", default=6, type="int",
                      help="The version of SCUMM to target (5 or 6).")
    
    options, args = oparser.parse_args()
    
    if len(args) != 2 or options.version < 5 or options.version > 6:
        returnval = 1
        oparser.print_help()
        return returnval

    lflf_path = args[0]
    image_path = args[1]
    try:
        if options.encode:
            encodeImage(lflf_path, image_path, options.version)
            print "Done!"
            returnval = 0
        elif options.decode:
            decodeImage(lflf_path, image_path, options.version)
            print "Done!"
            returnval = 0
        else:
            returnval = 1
            oparser.print_help()
    except Exception, e:
        returnval = 1
        traceback.print_exc()

    return returnval

if __name__ == "__main__": sys.exit(main())
