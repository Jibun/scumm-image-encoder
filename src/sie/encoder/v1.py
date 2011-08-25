import array
from collections import defaultdict
import logging
import os
from sie.sie_util import ScummImageEncoderException
import common

class EncoderV1(common.ImageEncoderBase):

    def compressRLEV1(self, data):
        pass

    def getCommonColoursV1(self, source):
        """
        Rather than get the 3 most common colours across the whole image, we want
        to get the most common colours across each 8x8 block.
        """
        width, height = source.size
        source_data = source.getdata()
        num_strips = width / 8
        num_blocks = height / 8

        dstPitch = width
        colour_freqs = defaultdict(lambda: 0)
        for strip_i in xrange(num_strips):
            col_start = strip_i * 8
            for block_i in xrange(num_blocks):
                block_colours = set()
                for row in xrange(8):
                    row_start = col_start + ((block_i * 8 + row) * dstPitch)
                    for col in xrange(0, 8, 2):
                        val = source_data[row_start + col]
                        block_colours.add(val)
                for bc in block_colours:
                    colour_freqs[bc] += 1
        logging.debug(colour_freqs)
        colour_freqs_sorted = sorted(colour_freqs.items(), cmp=lambda x,y: cmp(x[1], y[1]))
        return [c for c, f in colour_freqs_sorted[-3:]]

    def writeV1Bitmap(self, lflf_path, source):
        """
        Encoding:
        - Store 8 pixels in 1 byte (2 bits per colour, 4 colours per row, each colour output twice).
        - Store that value in charMap
        - Add the charMap index to picMap
        - Add the block's custom colour to colourMap
        When done, run RLE over each map.
        """
        commonColours = array.array('B') # BCv1 - always 4 bytes
        charMap = array.array('B') # B1v1 - always 2048 bytes
        picMap = array.array('B') # B2v1
        colourMap = array.array('B') # B3v1
        width, height = source.size
        source_data = source.getdata()

        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimentsions: %dx%d)" % (width, height))
        num_strips = width / 8
        num_blocks = height / 8

        # Get the three most used colours. The fourth colour is determined per block.
        #logging.debug(source.getcolors())
        #logging.debug(sorted(source.getcolors()))
        #common_colours = [clr for freq, clr in sorted(source.getcolors())[-3:]]
        common_colours = self.getCommonColoursV1(source)
        logging.debug("Common colours: %s" % common_colours)
        colours_used = []
        block_map = {} # map block CRCs to indices into the picMap

        dstPitch = width
        for strip_i in xrange(num_strips):
            col_start = strip_i * 8
            for block_i in xrange(num_blocks):
                block_data = []
                custom_colour = None
                for row in xrange(8):
                    row_start = col_start + ((block_i * 8 + row) * dstPitch)
                    row_data = 0
                    for col in xrange(0, 8, 2):
                        val1 = source_data[row_start + col]
                        val2 = source_data[row_start + col + 1] # only used for validation
                        if val1 != val2:
                            raise ScummImageEncoderException("V1 images can only have one colour per every two pixels on the x axis. " +
                            "Offending pixel at (%d, %d)" % ((row_start + col + 1) % width, (row_start + col + 1) / width))

                        # Convert from the source colour table index, to an index in our 4-value colour array.
                        if val1 in common_colours:
                            colour = common_colours.index(val1)
                        else:
                            if custom_colour is None:
                                custom_colour = val1
                            if custom_colour == val1:
                                colour = 3
                            else:
                                logging.error("Too many colours. Common: %s, custom: %s, offending: %s" % (common_colours, custom_colour, val1))
                                raise ScummImageEncoderException("Image has too many colours in a block - max of 4 colours allowed " +
                                                                 "(3 common colours and 1 custom colour for the block).  " +
                                "Offending pixel at (%d, %d)" % ((row_start + col) % width, (row_start + col) / width))

                        # Compress 4 pixels to 1 byte
                        colour &= 3
                        row_data |= colour << 6 - col
                        # end col
                    block_data.append(row_data)
                    # end row
                # If this 8x8 block has been used before in the image, re-use that block's index.
                # Otherwise, output the new data to the charMap, and store the hash of the block
                #  in a lookup table, so we can test if future blocks can re-use the same character data.
                block_key = tuple(block_data) # block data is going to be, at most, 8 bytes, so not too inefficient.
                if block_key in block_map:
                    picMap.append(block_map[block_key])
                else:
                    row_char_idx = len(charMap) / 8 # Need to store the index of the charMap entry that starts the row.
                    print row_char_idx
                    for r in block_data:
                        charMap.append(r)
                    picMap.append(row_char_idx)
                    block_map[block_key] = row_char_idx
                if custom_colour is None:
                    custom_colour = 0
                colourMap.append(custom_colour)
                # end block
            # end strip

        # If the charMap is too small, pad it out. Not sure why my encoded images use less chars.
        while len(charMap) < 2048:
            charMap.append(0)

        # If picMap or colourMap is not the size of the image (divided into 8x8 blocks),
        #  there's something wrong with my code.
        if len(picMap) != num_strips * num_blocks or \
            len(colourMap) != num_strips * num_blocks:
            raise ScummImageEncoderException("I don't seem to have generated enough entries in either the picMap or colourMap. " +
                "Expected entries: %d. picMap entries: %d. colourMap entries: %d." % (num_strips * num_blocks, len(picMap), len(colourMap)))

        # Output all files.
        # TODO: run RLE on them.
        charFile = file(os.path.join(lflf_path, 'charMap'), 'wb')
        charMap.tofile(charFile)
        charFile.close()
        picFile = file(os.path.join(lflf_path, 'picMap'), 'wb')
        picMap.tofile(picFile)
        charFile.close()
        colourFile = file(os.path.join(lflf_path, 'colourMap'), 'wb')
        colourMap.tofile(colourFile)
        colourFile.close()
