#! /usr/bin/python

import logging
from optparse import OptionParser
import os
import sys
import sie.decoder

def decodeV1():
    lflf_path = os.path.join("v1", "res", "LFv1_001")
    image_path = os.path.join("results", "v1_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 1, 1)

def decodeV2():
    lflf_path = os.path.join("v2", "res", "LFv2_001")
    image_path = os.path.join("results", "v2_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 2, 1)

def decodeV5():
    lflf_path = os.path.join("v5", "res", "LFLF_001")
    image_path = os.path.join("results", "v5_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 5, 1)

def decodeV6():
    lflf_path = os.path.join("v6", "res", "LFLF_001")
    image_path = os.path.join("results", "v6_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 6, 1)

    lflf_path = os.path.join("v6", "res", "LFLF_002")
    image_path = os.path.join("results", "v6_image2.png")
    sie.decoder.decodeImage(lflf_path, image_path, 6, 1)


    lflf_path = os.path.join("v6", "res", "LFLF_046")
    image_path = os.path.join("results", "v6_image3.png")
    sie.decoder.decodeImage(lflf_path, image_path, 6, 1)

def configure_logging():
    logging.basicConfig(format="", level=logging.DEBUG)

def validate_args(args, options):
    # TODO: replace this with your own validation
    if len(args) < 0:
        return False
    return True

def main(args):
    configure_logging()
    oparser = OptionParser(usage="%prog",
                           version="1.0")

    options, args = oparser.parse_args()

    if not validate_args(args, options):
        oparser.print_help()
        return 1

    try:
        decodeV1()
        decodeV2()
        decodeV5()
        decodeV6()
    except Exception, e:
        logging.exception("Unhandled exception: \n")
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
