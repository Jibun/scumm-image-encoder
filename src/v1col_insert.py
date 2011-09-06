#! /usr/bin/python

import logging
from optparse import OptionParser
import os
import sys

def insert_colours_all(game_path, resource_path):
    lfv1_paths = [f for f in os.listdir(resource_path) if f.lower().startswith('LFv1_') and os.path.isdir(os.path.join(resource_path, f))]
    for lfv1_path in lfv1_paths:
        insert_colours_single(game_path, os.path.join(resource_path, lfv1_path))

def insert_colours_single(game_path, resource_path):
    lf_num = int(resource_path[-4:])
    bc_path = os.path.join(resource_path, 'ROv1', 'BCv1')
    lfl_path = os.path.join(game_path, str(lf_num).zfill(2) + '.LFL')
    if not os.path.isfile(bc_path):
        logging.warning("No colours file found at %s - skipping." % bc_path)
        return
    elif not os.path.isfile(lfl_path):
        logging.warning("No LFL file found at %s - skipping." % lfl_path)
        return
    # Read the colours
    bc_file = file(bc_path, 'rb')
    enc_colours = "" # encrypted colours
    for _ in xrange(4):
        enc_colours += chr(ord(bc_file.read(1)) ^ 0xFF)
    bc_file.close()
    # Inject the colours into the game resource files.
    lfl_file = file(lfl_path, 'ab')
    lfl_file.seek(6, os.SEEK_SET)
    lfl_file.write(enc_colours)
    lfl_file.close()

def configure_logging():
    logging.basicConfig(format="", level=logging.INFO)

def validate_args(args, options):
    if len(args) < 2:
        print "Insufficient arguments. I need the game path and the unpacked resources path."
        return False
    if not os.path.isdir(args[0]):
        print "Invalid game path."
        return False
    if not os.path.isdir(args[1]):
        print "Invalid unpacked resources path (or it does not exist)."
        return False
    return True

def main(args):
    configure_logging()
    oparser = OptionParser(usage="%prog game_path resource_path [-a]",
                           version="1.0")
    oparser.add_option("-a", "--all", action="store_true", dest="all",
                       help="Process all LFv1 directores in the given resource path. \n"
                            "If this option is omitted, the given resource path must be a LFv1 dir.")

    options, args = oparser.parse_args()

    if not validate_args(args, options):
        oparser.print_help()
        return 1

    game_path, resource_path = args

    try:
        if options.all:
            insert_colours_all(game_path, resource_path)
        else:
            insert_colours_single(game_path, resource_path)
    except Exception, e:
        logging.exception("Unhandled exception: \n")
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
