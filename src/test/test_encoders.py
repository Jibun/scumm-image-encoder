#! /usr/bin/python

import logging
from optparse import OptionParser
import os
import sys
import sie.encoder
import sie.decoder

def encodeV1():
    lflf_path = os.path.join("results", "v1", "LFv1_001")
    image_path = os.path.join("v1", "res", "v1_image1.png")
    sie.encoder.encodeImage(lflf_path, image_path, 1, None, 1, False)
    image_path = os.path.join("results", "encoded_v1_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 1, 1)

def encodeV2():
    lflf_path = os.path.join("results", "v2", "LFv2_001")
    image_path = os.path.join("v2", "res", "v2_image1.png")
    sie.encoder.encodeImage(lflf_path, image_path, 2, None, 1, False)
    image_path = os.path.join("results", "encoded_v2_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 2, 1)

def encodeV5():
    lflf_path = os.path.join("results", "v5", "LFLF_001")
    image_path = os.path.join("v5", "res", "v5_image1.png")
    sie.encoder.encodeImage(lflf_path, image_path, 5, None, 1, False)
    image_path = os.path.join("results", "encoded_v5_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 5, 1)

def encodeV6():
    lflf_path = os.path.join("results", "v6", "LFLF_001")
    image_path = os.path.join("v6", "res", "v6_image1.png")
    sie.encoder.encodeImage(lflf_path, image_path, 6, None, 1, False)
    image_path = os.path.join("results", "encoded_v6_image1.png")
    sie.decoder.decodeImage(lflf_path, image_path, 6, 1)

    lflf_path = os.path.join("results", "v6", "LFLF_002")
    image_path = os.path.join("v6", "res", "v6_image2.png")
    sie.encoder.encodeImage(lflf_path, image_path, 6, None, 1, False)
    image_path = os.path.join("results", "encoded_v6_image2.png")
    sie.decoder.decodeImage(lflf_path, image_path, 6, 1)

    lflf_path = os.path.join("results", "v6", "LFLF_046")
    image_path = os.path.join("v6", "res", "v6_image3.png")
    sie.encoder.encodeImage(lflf_path, image_path, 6, None, 1, False)
    image_path = os.path.join("results", "encoded_v6_image3.png")
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
        encodeV1()
        #encodeV2()
        #encodeV5()
        #encodeV6()
    except Exception, e:
        logging.exception("Unhandled exception: \n")
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
