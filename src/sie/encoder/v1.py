import array
from collections import defaultdict
import logging
import os
import struct
from sie.sie_util import ScummImageEncoderException, makeDirs
import common

class EncoderV1(common.ImageEncoderBase):

    def packRunInfoV1(self, value, run_length, common, discrete_buffer):
        # Output non-repeated values.
        if discrete_buffer is not None and len(discrete_buffer):
            # Maximum run length value is 0x3F (63) - actual run length of 64.
            data = ''
            while len(discrete_buffer) > 0:
                buf_size_to_output = min(len(discrete_buffer), 64)
                data += struct.pack(('<%dB' % buf_size_to_output + 1),
                               buf_size_to_output - 1, # value counts start from 0, not 1.
                               *discrete_buffer[:buf_size_to_output])
                discrete_buffer = discrete_buffer[buf_size_to_output:]
            return data
        # Output common repeated values.
        elif value in common:
            # Maximum run length is 0x1F (31 [actually 32]), so output as many of these
            #  things as we need to capture the whole run.
            # Assume input run_length starts counting run lengths from 0
            #  (e.g. "12 12 12" has a run length value of 2)
            data = ''
            while run_length >= 0:
                output = 0x80
                comval = common.index(value) & 3
                output |= (comval << 5)
                rl = run_length & 0x1F
                output |= rl
                data += struct.pack('<B', output)
                run_length -= 0x1F
            return data
        # Output uncommon repeated values.
        else:
            # Maximum run length is 0x3F (63 [actually 64]), so output as many of these
            #  things as we need to capture the whole run.
            data = ''
            while run_length >= 0:
                output = 0x40
                rl = run_length & 0x3F
                output |= rl
                data += struct.pack('<2B', output, value)
                run_length -= 0x3F
            return data

    def compressRLEV1(self, data):
        """
        Compression compares the current value with the previous value, and
        performs one of two actions:
        1. If values are different:
           A. If previous run was a repeated value, output that run, and reset the "discrete value" buffer.
           B. Else, if in a "discrete value" run, add the previous value to the "discrete value" buffer.
        2. If values are the same:
           A. If previous run was a "discrete value" run, output the "discrete value" buffer, and reset the run.
           B. Else, if in a repeated value run, increment the run counter.
        """
        #value = None
        last_value = None
        run_length = 0
        discrete_buffer = [] # holds non-run values

        # First, determine the most common value.
        value_freqs = defaultdict(lambda: 0)
        for b in data:
            value_freqs[b] += 1
        value_freqs_sorted = sorted(value_freqs.items(), cmp=lambda x,y: cmp(x[1], y[1]))
        common = [c for c, f in value_freqs_sorted[-3:]]

        for value in data:
            if last_value is None: # special case for first item
                last_value = value
                continue
            if value == last_value:
                if len(discrete_buffer):
                    self.packRunInfoV1(None, run_length, common, discrete_buffer)
                    run_length = 0
                    discrete_buffer = []
                else:
                    run_length += 1
            else:
                # Output previous run
                if run_length:
                    self.packRunInfoV1(last_value, run_length, common, None)
                    run_length = 0
                    discrete_buffer = []
                else:
                    discrete_buffer.append(last_value)
            last_value = value

        # Output last bit of data.
        self.packRunInfoV1(last_value, run_length, common, discrete_buffer)

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

    def writeBackgroundBitmap(self, lflf_path, source_image, width, height):
        """
        Encoding:
        - Store 8 pixels in 1 byte (2 bits per colour, 4 colours per row, each colour output twice).
        - Store that value in charMap
        - Add the charMap index to picMap
        - Add the block's custom colour to colourMap
        When done, run RLE over each map, EXCEPT charMap (since it will be modified again later).
        Returns charMap, for further modification (to add object data).
        """
        commonColours = array.array('B') # BCv1 - always 4 bytes
        charMap = array.array('B') # B1v1 - always 2048 bytes
        picMap = array.array('B') # B2v1
        colourMap = array.array('B') # B3v1
        source_data = source_image.getdata()

        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimensions: %dx%d)" % (width, height))
        num_strips = width / 8
        num_blocks = height / 8

        # Get the three most used colours. The fourth colour is determined per block.
        #logging.debug(source.getcolors())
        #logging.debug(sorted(source.getcolors()))
        #common_colours = [clr for freq, clr in sorted(source.getcolors())[-3:]]
        common_colours = self.getCommonColoursV1(source_image)
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

        # If the charMap is too small, pad it out.
        # (charMaps are used by backgrounds and objects)
        #while len(charMap) < 2048:
        #    charMap.append(0)

        # If picMap or colourMap is not the size of the image (divided into 8x8 blocks),
        #  there's something wrong with my code.
        if len(picMap) != num_strips * num_blocks or \
            len(colourMap) != num_strips * num_blocks:
            raise ScummImageEncoderException("I don't seem to have generated enough entries in either the picMap or colourMap. " +
                "Expected entries: %d. picMap entries: %d. colourMap entries: %d." % (num_strips * num_blocks, len(picMap), len(colourMap)))

        # Output all files.
        # TODO: run RLE on them.
        out_path = os.path.join(lflf_path, 'charMap')
        makeDirs(out_path)
        charFile = file(out_path, 'wb')
        charMap.tofile(charFile)
        charFile.close()

        out_path = os.path.join(lflf_path, 'picMap')
        makeDirs(out_path)
        picFile = file(out_path, 'wb')
        picMap.tofile(picFile)
        charFile.close()

        out_path = os.path.join(lflf_path, 'colourMap')
        makeDirs(out_path)
        colourFile = file(out_path, 'wb')
        colourMap.tofile(colourFile)
        colourFile.close()

        return charMap

    def writeBitmap(self, lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization):
        charMap = self.writeBackgroundBitmap(lflf_path, source_image, width, height)
        self.encodeObjectImages(lflf_path, image_path, charMap)

    def encodeObjectImages(self, lflf_path, image_path, charMap):
        # Get the dir containing all the object images
        object_images_path = os.path.split(image_path)[0]
        # Search for images that match an expected format, representing objects
        #  associated with a root background image.
        # e.g.
        #  background = "v1_image1.png"
        #  objects = "v1_image1-OIv1_0018.png", "v1_image1-OIv1_0019.png"
        oip, oipext = os.path.splitext(os.path.basename(image_path))
        objNumStrs = [f[-4 - len(oipext):-len(oipext)] for f in os.listdir(object_images_path) if f.startswith("%s-OIv1_" % oip)]
        for objNum in objNumStrs:
            logging.debug("encoding v1 object #%s" % objNum)
            try:
                logging.info("TODO")
                #width, height = c64.readObjectDimensions(lflf_path, objNum)
                #bmp_data = c64.decodeV1Object(lflf_path, width, height, objNum)
                #obj_image_path = "%s-OIv1_%s%s" % (ip, objNum, ipext)
                #self.saveImage(obj_image_path, width, height, bmp_data, pal_data)
            except Exception, e:
                logging.error("Unhandled exception attempting to decode v1 object %s." % objNum)
                #raise e