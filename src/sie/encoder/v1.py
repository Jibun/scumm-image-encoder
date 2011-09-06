import array
from collections import defaultdict
import logging
import os
import struct
import Image
from sie.sie_util import ScummImageEncoderException, makeDirs, xy2i
import common

DEBUG_DUMP = False

# TODO: maybe split this out into separate classes for backgrounds, background masks,
#  objects, and object masks.

class EncoderV1(common.ImageEncoderBase):

    def findCommonValuesForRLE(self, data):
        value_freqs = defaultdict(lambda: 0)
        for b in data:
            value_freqs[b] += 1
        # Sort first by values, then by frequencies. Most frequent should be first.
        value_freqs_sorted = sorted(value_freqs.items(), key=lambda x: x[0])
        value_freqs_sorted.sort(key=lambda x: x[1], reverse=True)
        common = [c for c, f in value_freqs_sorted[:4]]
        if len(common) < 4: # pad it out to 4 values.
            common.extend([0] * (4 - len(common)))
        return common

    def packRunInfo(self, value, run_length, common, discrete_buffer):
        # Original encoder seems to favour outputting single discrete values
        #  (i.e. only 1 value in the run) as a run - this gives better compression
        #  if the value is a common value, as it only uses 1 byte.
        if discrete_buffer is not None and len(discrete_buffer) == 1:
            value = discrete_buffer[0] # this is a bit hackish...
        
        # Output non-repeated values.
        if discrete_buffer is not None and len(discrete_buffer) > 1:
            # Maximum run length value is 0x3F (63) - actual run length of 64.
            data = ''
            while len(discrete_buffer) > 0:
                buf_size_to_output = min(len(discrete_buffer), 64)
                db = discrete_buffer[:buf_size_to_output]
                format = '<%dB' % (buf_size_to_output + 1)
                data += struct.pack(format,
                               buf_size_to_output - 1, # value counts start from 0, not 1.
                               *db)
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
                rl = min(run_length, 0x1F)
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
                rl = min(run_length, 0x3F)
                #print "run_length: %d. rl: %d" % (run_length, rl)
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
        last_value = None
        run_length = 0
        discrete_buffer = [] # holds non-run values
        output_data = ""

        # First, determine the most common values.
        common = self.findCommonValuesForRLE(data)
        output_data += struct.pack('<4B', *common)

        for value in data:
            if last_value is None: # special case for first item
                last_value = value
                continue
            if value == last_value:
                if len(discrete_buffer):
                    output_data += self.packRunInfo(None, run_length, common, discrete_buffer)
                    run_length = 1 # because we look a value behind, we already know this run's length is 2.
                    discrete_buffer = []
                else:
                    run_length += 1
            else:
                # Output previous run
                if run_length:
                    output_data += self.packRunInfo(last_value, run_length, common, None)
                    run_length = 0
                    discrete_buffer = []
                else:
                    discrete_buffer.append(last_value)
            last_value = value

        # Output last bit of data.
        if not run_length: # hackish
            discrete_buffer.append(last_value)
        output_data += self.packRunInfo(last_value, run_length, common, discrete_buffer)
        return output_data

    def getCommonColoursV1(self, source_data, width, height):
        """
        Rather than get the 3 most common colours across the whole image, we want
        to get the most common colours across each 8x8 block.
        """
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
        colour_freqs_sorted = sorted(colour_freqs.items(), key=lambda x: x[1], reverse=True)
        return [c for c, f in colour_freqs_sorted[:3]]

    def packRowData(self, source_data, common_colours, custom_colour, row_start, width):
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
                if custom_colour > 7:
                    raise ScummImageEncoderException("The fourth 'custom colour' per block cannot have a value higher than 7. " +
                    "Offending pixel at (%d, %d)" % ((row_start + col) % width, (row_start + col) / width))
                if custom_colour == val1:
                    colour = 3
                else:
                    logging.error("Too many colours. Common: %s, custom: %s, offending: %s" % (common_colours, custom_colour, val1))
                    raise ScummImageEncoderException("Image has too many colours in a block - max of 4 colours allowed " +
                                                     "(3 common colours and 1 custom colour for the block).  " +
                    "Offending pixel at (%d, %d).\n" % ((row_start + col) % width, (row_start + col) / width) +
                    "Colours: %s. Custom colour: %s. Offending colour: %s" % (common_colours, custom_colour, val1))

            # Compress 4 pixels to 1 byte
            colour &= 3
            row_data |= colour << 6 - col
            # end col
        return row_data, custom_colour
        # end row

    def packBlock(self, source_data, vstrip_i, hstrip_i, width, common_colours, block_map, picMap, charMap, colourMap):
        """
         Modifies:
          - block_map
          - picMap
          - charMap
          - colourMap
        """
        block_data = []
        custom_colour = None
        for row_i in xrange(8):
            row_start = xy2i(vstrip_i * 8, hstrip_i * 8 + row_i, width)
            #logging.debug("vstrip_i: %d. hstrip_i: %d. row start: %d" % (vstrip_i, hstrip_i, row_start,))
            row_data, custom_colour = self.packRowData(source_data, common_colours, custom_colour, row_start, width)
            block_data.append(row_data)
        self.storeBlockData(block_map, charMap, picMap, block_data)
        if custom_colour is None:
            custom_colour = 0
        colourMap.append(custom_colour)
        #logging.debug("last picMap: %d" % picMap[-1])

    def packBackgroundData(self, source_data, width, height):
        """
        Encoding:
        - Store 8 pixels in 1 byte (2 bits per colour, 4 colours per row, each colour output twice).
        - Store that value in charMap
        - Add the charMap index to picMap
        - Add the block's custom colour to colourMap
        When done, run RLE over each map, EXCEPT charMap (since it will be modified again later).
        Returns charMap, for further modification (to add object data).
        """
        charMap = array.array('B') # B1v1 - always 2048 bytes
        picMap = array.array('B') # B2v1
        colourMap = array.array('B') # B3v1

        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimensions: %dx%d)" % (width, height))
        num_strips = width / 8
        num_blocks = height / 8

        # Get the three most used colours. The fourth colour is determined per block.
        common_colours = self.getCommonColoursV1(source_data, width, height)
        logging.debug("Common colours: %s" % common_colours)
        block_map = {} # map block signatures to indices into the picMap

        for vstrip_i in xrange(num_strips):
            for hstrip_i in xrange(num_blocks):
                self.packBlock(source_data, vstrip_i, hstrip_i, width, common_colours, block_map, picMap, charMap, colourMap)

        # If picMap or colourMap is not the size of the image (divided into 8x8 blocks),
        #  there's something wrong with my code.
        if len(picMap) != num_strips * num_blocks or \
            len(colourMap) != num_strips * num_blocks:
            raise ScummImageEncoderException("I don't seem to have generated enough entries in either the picMap or colourMap. " +
                "Expected entries: %d. picMap entries: %d. colourMap entries: %d." % (num_strips * num_blocks, len(picMap), len(colourMap)))

        return charMap, picMap, colourMap, block_map, common_colours

    def writeBackgroundBitmap(self, lflf_path, source_image, width, height):
        charMap, picMap, colourMap, block_map, common_colours = self.packBackgroundData(source_image, width, height)

        # don't output charMap yet, since objects will modify it.

        if DEBUG_DUMP:
            out_path = os.path.join(lflf_path, 'picMap')
            self.genericWrite(out_path, picMap)
            out_path = os.path.join(lflf_path, 'colourMap')
            self.genericWrite(out_path, colourMap)

        picMap = self.compressRLEV1(picMap)
        out_path = os.path.join(lflf_path, 'ROv1', 'B2v1')
        self.genericWrite(out_path, picMap)
        colourMap = self.compressRLEV1(colourMap)
        out_path = os.path.join(lflf_path, 'ROv1', 'B3v1')
        self.genericWrite(out_path, colourMap)

        return charMap, block_map, common_colours

    def packBackgroundMaskData(self, source_data, width, height):
        maskCharMap = array.array('B')
        picMap = array.array('B')
        mask_block_map = {}
        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimensions: %dx%d)" % (width, height))
        num_vstrips = width / 8
        num_hstrips = height / 8
        for vstrip_i in xrange(num_vstrips):
            for hstrip_i in xrange(num_hstrips):
                self.packMaskBlock(source_data, vstrip_i, hstrip_i, width, mask_block_map, picMap, maskCharMap)
        return maskCharMap, picMap, mask_block_map

    def writeBackgroundMaskBitmap(self, lflf_path, source_image, width, height):
        maskCharMap, maskPicMap, mask_block_map = self.packBackgroundMaskData(source_image, width, height)

        if DEBUG_DUMP:
            out_path = os.path.join(lflf_path, 'maskPicMap')
            self.genericWrite(out_path, maskPicMap)

        maskPicMap = self.compressRLEV1(maskPicMap)
        out_path = os.path.join(lflf_path, 'ROv1', 'B4v1')
        self.genericWrite(out_path, maskPicMap)
        
        return maskCharMap, mask_block_map

    def packMaskRowData(self, source_data, row_start, width):
        """Compressess 8 values of 0 or 1 into one byte.   """
        row_data = 0
        for col in xrange(8):
            val = source_data[row_start + col]
            if val > 1:
                raise ScummImageEncoderException("V1 mask images can only have values of 0 or 1. " +
                "Offending pixel at (%d, %d). Value: %d." % ((row_start + col + 1) % width, (row_start + col + 1) / width, val))

            row_data |= (val << col)
        return row_data
        # end row

    def packMaskBlock(self, source_data, vstrip_i, hstrip_i, width, block_map, objectMap, maskCharMap):
        """
         Modifies:
          - block_map
          - objectMap
          - maskCharMap
        """
        block_data = []
        for row_i in xrange(8):
            row_start = xy2i(vstrip_i * 8, hstrip_i * 8 + row_i, width)
            #logging.debug("vstrip_i: %d. hstrip_i: %d. row start: %d" % (vstrip_i, hstrip_i, row_start,))
            row_data = self.packMaskRowData(source_data, row_start, width)
            block_data.append(row_data)
        self.storeBlockData(block_map, maskCharMap, objectMap, block_data)
        #logging.debug("last picMap: %d" % objectMap[-1])


    def packObjectMaskData(self, source_data, width, height, maskCharMap, mask_block_map):
        objectMap = array.array('B')
        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimensions: %dx%d)" % (width, height))
        num_vstrips = width / 8
        num_hstrips = height / 8
        for hstrip_i in xrange(num_hstrips):
            for vstrip_i in xrange(num_vstrips):
                self.packMaskBlock(source_data, vstrip_i, hstrip_i, width, mask_block_map, objectMap, maskCharMap)
        return objectMap, maskCharMap


    def packObjectData(self, source_data, width, height, charMap, block_map, common_colours, mask_data):
        """
        Objects seem to be compressed in blocks horizontally, rather than vertically.
        Custom colours are stored after all block data, in the same order as the
        blocks.

        Here's a real world example of indexes, from decoding an object.
        object - colour index: 6. bmp index: 0
        object - colour index: 8. bmp index: 2
        object - colour index: 10. bmp index: 4
        object - colour index: 7. bmp index: 1
        object - colour index: 9. bmp index: 3
        object - colour index: 11. bmp index: 5
        """
        objectMap = array.array('B') # B2v1
        colourMap = array.array('B')

        if width % 8 or height % 8:
            raise ScummImageEncoderException("Input image must have dimensions divisible by 8. (Input dimensions: %dx%d)" % (width, height))
        num_vstrips = width / 8
        num_hstrips = height / 8

        logging.debug("num_vstrips * num_hstrips: %d" % (num_vstrips * num_hstrips))

        for hstrip_i in xrange(num_hstrips):
            for vstrip_i in xrange(num_vstrips):
                self.packBlock(source_data, vstrip_i, hstrip_i, width, common_colours, block_map, objectMap, charMap, colourMap)

        # If objectMap or colourMap is not the size of the image (divided into 8x8 blocks),
        #  there's something wrong with my code.
        if len(objectMap) != num_vstrips * num_hstrips or \
            len(colourMap) != num_vstrips * num_hstrips:
            raise ScummImageEncoderException("I don't seem to have generated enough entries in either the picMap or colourMap. " +
                "Expected entries: %d. colourMap entries: %d." % (num_vstrips * num_hstrips, len(colourMap)))

        # Add colour map to the end of the bitmap data.
        objectMap.extend(colourMap)
        # Also add the mask data.
        objectMap.extend(mask_data)

        return objectMap, charMap

    def genericWrite(self, out_path, data):
        makeDirs(out_path)
        outFile = file(out_path, 'wb')
        if isinstance(data, array.array):
            data.tofile(outFile)
        elif isinstance(data, str):
            outFile.write(data)
        else:
            for b in data:
                outFile.write(b)
        outFile.close()

    def storeBlockData(self, block_map, charMap, picMap, block_data):
        """ Modifies the input block_map, the picMap, and the charMap.
        """
        # If this 8x8 block has been used before in the image, re-use that block's index.
        # Otherwise, output the new data to the charMap, and store the hash of the block
        #  in a lookup table, so we can test if future blocks can re-use the same character data.
        block_key = tuple(block_data) # block data is going to be, at most, 8 bytes, so not too inefficient.
        if block_key in block_map:
            picMap.append(block_map[block_key])
        else:
            row_char_idx = len(charMap) / 8 # Need to store the index of the charMap entry that starts the row.
            if row_char_idx > 255:
                logging.debug("block_map: %s" % block_map)
                raise ScummImageEncoderException("Too many entries in the character map - " +
                    "maximum distinct 8x8 blocks is 255 (incl. background and objects).\n")
            charMap.extend(block_data)
            picMap.append(row_char_idx)
            block_map[block_key] = row_char_idx

    def writeCharMap(self, lflf_path, charMap):
        if len(charMap) < 2048:
            charMap.extend([0] * (2048 - len(charMap)))
        elif len(charMap) > 2048:
            raise ScummImageEncoderException("Too many entries in the charMap - " +
            "your background and objects might be too complex!\n" +
            "See if you can re-use an 8x8 block of pixels somewhere.")
        charMap = self.compressRLEV1(charMap)
        out_path = os.path.join(lflf_path, 'ROv1', 'B1v1')
        self.genericWrite(out_path, charMap)

    def writeMaskCharMap(self, lflf_path, maskCharMap):
        size = len(maskCharMap) + 8
        if size > 65535:
            raise ScummImageEncoderException("Too many entries in the mask char map - max 65527.")
        data = self.compressRLEV1(maskCharMap)
        out_path = os.path.join(lflf_path, 'ROv1', 'B5v1')
        makeDirs(out_path)
        outFile = file(out_path, 'wb')
        outFile.write(struct.pack('<H', size))
        outFile.write(data)
        outFile.close()

    def writeCommonColours(self, lflf_path, common_colours):
        if len(common_colours) < 4:
            common_colours.append(0) # the 4th common colour doesn't seem to be used, so just put a dummy value.
        elif len(common_colours > 4):
            raise ScummImageEncoderException("I seem to have recorded too many common colours - " +
                                            ("expected 3 or 4, found %d. This is a bug.\n" % len(common_colours)) +
                                            "Colours: %s" % common_colours)
        out_path = os.path.join(lflf_path, 'ROv1', 'BCv1')
        data = struct.pack('<4B', *common_colours)
        self.genericWrite(out_path, data)

    def writeMaskBitmap(self, lflf_path, image_path, width, height):
        bi, biext = os.path.splitext(image_path)
        mask_path = bi + ".mask" + biext
        mask_image = Image.open(mask_path)
        mask_width, mask_height = mask_image.size
        if mask_width != width or mask_height != height:
            raise ScummImageEncoderException("The dimensions of the background image and it's associated mask image do not match. "
                "Background dimensions: %dx%d. Mask dimensions: %dx%d." % (width, height, mask_width, mask_height))
        maskCharMap, mask_block_map = self.writeBackgroundMaskBitmap(lflf_path, mask_image.getdata(), mask_width, mask_height)
        return maskCharMap, mask_block_map

    def writeBitmap(self, lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization):
        # Read & pack the background data - just the pic map and colour map for now.
        #  Character map and common colour data is written later, since this info is used/modified by
        #  objects as well.
        charMap, block_map, common_colours = self.writeBackgroundBitmap(lflf_path, source_image.getdata(), width, height)
        # Read & pack the mask data (as much as we can for now, anyway)
        maskCharMap, mask_block_map = self.writeMaskBitmap(lflf_path, image_path, width, height)
        self.encodeObjectImages(lflf_path, image_path, charMap, maskCharMap, block_map, mask_block_map, common_colours)
        self.writeCharMap(lflf_path, charMap)
        self.writeMaskCharMap(lflf_path, maskCharMap)
        self.writeCommonColours(lflf_path, common_colours)

    def encodeObjectImages(self, lflf_path, image_path, charMap, maskCharMap, block_map, mask_block_map, common_colours):
        # Get the dir containing all the object images
        object_images_path = os.path.split(image_path)[0]
        # Search for images that match an expected format, representing objects
        #  associated with a root background image. For example:
        #  background = "v1_image1.png"
        #  objects = "v1_image1-OIv1_0018.png", "v1_image1-OIv1_0019.png"
        #  object masks = "v1_image1-OIv1_0018.png.mask"
        oip, oipext = os.path.splitext(os.path.basename(image_path))
        obj_file_names = [f
                          for f
                          in os.listdir(object_images_path)
                          if f.startswith("%s-OIv1_" % oip)
                             and not os.path.splitext(f)[0].endswith('.mask')] # need to ignore mask images.
        for obj_image_name in obj_file_names:
            oibase, oiext = os.path.splitext(os.path.basename(obj_image_name))
            objNum = obj_image_name[-4 - len(oiext):-len(oiext)]
            logging.debug("encoding v1 object #%s" % objNum)

            # Read in the mask data.
            mask_file_name = oibase + ".mask" + oiext
            mask_image = Image.open(os.path.join(object_images_path, mask_file_name))
            width, height = mask_image.size
            mask_data, maskCharMap = self.packObjectMaskData(mask_image.getdata(), width, height, maskCharMap, mask_block_map)
            # Read in the source image data
            source_image = Image.open(os.path.join(object_images_path, obj_image_name))
            width, height = source_image.size
            # Pack and RLE compress the data
            objectMap, charMap = self.packObjectData(source_image.getdata(), width, height, charMap, block_map, common_colours, mask_data)
            objectMap = self.compressRLEV1(objectMap)

            out_path = os.path.join(lflf_path, 'ROv1', 'OIv1_%s' % (objNum.zfill(4)))
            self.genericWrite(out_path, objectMap)

    def writeHeader(self, lflf_path, width, height):
        """ Dimensions are stored as 1/8th the original value. e.g. 320 width becomes 40."""
        if width > 2040 or height > 2040: # 255 * 8 = 2040.
            raise ScummImageEncoderException("The image's width or height is too large - max dimensions are 2040x2040.")
        super(EncoderV1, self).writeHeader(lflf_path, width / 8, height / 8)