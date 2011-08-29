import common
import logging
import struct

class EncoderV2(common.ImageEncoderBase):
    def packRunInfoV2(self, run, colour, bleeding):
        logging.debug("Writing out run info. run: %d, colour: %s, bleeding: %s" % (run, colour, bleeding))
        data = None
        if bleeding:
            if run > 0x7F:
                data = struct.pack('2B', 0x80, run)
            else:
                data = struct.pack('B', 0x80 | run)
        else:
            if run > 0x07:
                data = struct.pack('2B', colour, run)
            else:
                data = struct.pack('B', (run << 4) | colour)
        logging.debug("  packed data = %r" % data)
        return data

    def writeBitmap(self, lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization):
        img_file = file(self.getNewBitmapPath(lflf_path), 'wb')
        source_data = source_image.getdata()
        bleed_table = [None] * 128
        run = 0
        colour = None
        b = None
        bleeding = False
        for x in xrange(width):
            bleed_i = 0
            logging.debug("Column: %d" % x)

            # Original encoded images seem to reset the bleed table every 8th column.
            # Presumably to aid in drawing "strips", which are 8 pixels wide.
            if not x % 8:
                bleed_table = [None] * 128

            logging.debug("Dither table: %s" % bleed_table)

            for y in xrange(height):
                # Get the current pixel.
                b = source_data[y * width + x]
                # Check if we can bleed. (The original encoder seems to favour bleeding over efficient run compression.
                #  It will revert to bleeding even if it interrupts a continuous run of colour.)
                if not bleeding and b == bleed_table[bleed_i]:
                    if run:
                        data = self.packRunInfoV2(run, colour, bleeding)
                        img_file.write(data)
                    bleeding = True
                    run = 1
                    colour = None
                # If the current pixel is the same, or we're currently bleeding and
                # the bleed colour matches this pixel, increment run counter.
                # Also need to check bounds - maximum value of a run is
                # 0xFF.
                elif run < 0xFF and \
                   (b == colour or (bleeding and b == bleed_table[bleed_i])):
                    run += 1
                    if not bleeding:
                        bleed_table[bleed_i] = colour
                # Current pixel is not the same as the last.
                else:
                    logging.debug("Ending run. b: %d. bleed_table value: %s" % (b, bleed_table[bleed_i]))
                    # End the run, only if we have started one (e.g. the start of a column).
                    if run:
                        data = self.packRunInfoV2(run, colour, bleeding)
                        img_file.write(data)
                    # Start a new run.
                    run = 1
                    # If the current pixel is the same as the bleed colour, engage bleeding mode.
                    if b == bleed_table[bleed_i]:
                        bleeding = True
                        colour = None
                    else:
                        bleeding = False
                        colour = b
                        bleed_table[bleed_i] = colour
                    logging.debug("Start of new run. colour: %s, bleeding: %s" % (colour, bleeding))
                bleed_i += 1

            logging.debug("---")

        # End the last run encountered, once we reach the end of the file.
        data = self.packRunInfoV2(run, colour, bleeding)
        img_file.write(data)
        img_file.close()

