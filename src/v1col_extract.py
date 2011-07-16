#! /usr/bin/python

import logging
from optparse import OptionParser
import os
import sys

def extract_colours(game_path, base_out_path):
    # Get all LFL files and ignore the index file.
    lfl_files = [f for f in os.listdir(game_path) if f.lower().endswith('.lfl') and not f.startswith('00.')]

    for lfl_name in lfl_files:
        lfl = file(os.path.join(game_path, lfl_name), 'rb')
        lfl.seek(6)
        # Read 4 seperate bytes, and decrypt them.
        colours = ""
        for _ in xrange(4):
            colours += chr(ord(lfl.read(1)) ^ 0xFF)
        lfl.close()

        # Output to out_path\LFv1_0001\ROv1\BCv1
        lfl_num = os.path.splitext(lfl_name)[0].zfill(4)
        full_out_path = os.path.join(base_out_path, "LFv1_" + lfl_num, "ROv1")
        if not os.path.isdir(full_out_path):
            os.makedirs(full_out_path)
        out_file = file(os.path.join(full_out_path, 'BCv1'), 'wb')
        out_file.write(colours)
        out_file.close()

def configure_logging():
    logging.basicConfig(format="", level=logging.INFO)


def validate_args(args, options):
    if len(args) < 2:
        print "Insufficient arguments. I need the game path and the output path."
        return False
    if not os.path.isdir(args[0]):
        print "Invalid game path."
        return False
    if not os.path.isdir(args[1]):
        print "Invalid output path (or it does not exist)."
        return False
    return True


def main(args):
    configure_logging()
    oparser = OptionParser(usage="%prog game_path output_path",
                           version="1.0")

    options, args = oparser.parse_args()

    if not validate_args(args, options):
        oparser.print_help()
        return 1

    game_path, out_path = args

    try:
        extract_colours(game_path, out_path)
    except Exception, e:
        logging.exception("Unhandled exception: \n")
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
