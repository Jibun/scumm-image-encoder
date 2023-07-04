import common
import logging
import os
import struct
from PIL import Image

class EncoderV2(common.ImageEncoderBase):
    def encodeImage(self, lflf_path, image_path, quantization, palette_num, freeze_palette, compression_method=None):
        source_image = self.validateAndQuantizeSourceImage(Image.open(image_path), quantization, freeze_palette)
        width, height = source_image.size
        self.writeBitmap(lflf_path, image_path, source_image, width, height, compression_method, freeze_palette, quantization)
        self.writeHeader(lflf_path, width, height)
        self.writePalette(lflf_path, source_image.palette.palette, quantization, palette_num, freeze_palette)
    
        # Encoding mask
        ip, ipext = os.path.splitext(image_path)
        mask_image_path = "%s-mask%s" % (ip, ipext)
        source_mask = self.validateAndQuantizeSourceMask(Image.open(mask_image_path))
        mask_path = self.getNewMaskPath(lflf_path)
        self.writeMask(mask_path, source_mask, width, height)
    
        # Get the dir containing all the object images
        object_images_path = os.path.split(image_path)[0]
        # Search for images that match an expected format, representing objects
        #  associated with a root background image. For example:
        #  background = "v2_image1.png"
        #  objects = "v2_image1-OIv2_0018.png", "v2_image1-OIv2_0019.png"
        #  masks = "v2_image1-OIv2_0018.mask.png", "v2_image1-OIv2_0019.mask.png"
        oip, oipext = os.path.splitext(os.path.basename(image_path))
        obj_file_names = [f
                          for f
                          in os.listdir(object_images_path)
                          if f.startswith("%s-OIv2_" % oip) and not f.endswith("mask.png")]
        for obj_image_name in obj_file_names:
            oibase, oiext = os.path.splitext(os.path.basename(obj_image_name))
            objNum = obj_image_name[-4 - len(oiext):-len(oiext)]
            logging.debug("encoding v2 object #%s" % objNum)
            
            # Read in the source image data
            source_image = self.validateAndQuantizeSourceImage(Image.open(os.path.join(object_images_path, obj_image_name)), quantization, freeze_palette)
            width, height = source_image.size
            # Read in the source mask data
            source_mask = None
            if os.path.exists(os.path.join(object_images_path, oibase + ".mask" + oiext)):
                logging.debug("getting mask %s" % os.path.join(object_images_path, oibase + ".mask" + oiext))
                source_mask = self.validateAndQuantizeSourceMask(Image.open(os.path.join(object_images_path, oibase + ".mask" + oiext)))
            # We do not save object header for now, so the image size can not be modified
            # self.writeObjectHeader(lflf_path, width, height)
            object_path = self.getNewObjectPath(lflf_path, objNum)
            self.writeObject(object_path, image_path, source_image, source_mask, width, height, compression_method, freeze_palette, quantization)
    
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
    
    def packRunInfoMaskV2(self, run, colour, last_bytes = False):
        total_bytes = 0
        array_bytes = []
        data = None
        if run > 1:
            pending = run;
            while pending > 0:
                if pending >= 0x7F:
                    logging.debug("Writing out run info. run: %d, colour: %s" % (0x7F, colour))
                    total_bytes += 2
                    array_bytes.extend([0xFF, colour])
                    pending -= 0x7F
                elif last_bytes and pending == 2 and colour == 0x00:
                    logging.debug("Writing out run info. run: %d, colour: %s" % (pending, colour))
                    logging.debug("Ignoring colour byte for coherence with original code")
                    total_bytes += 1
                    array_bytes.append(0x80 | pending)
                    pending = 0
                else:
                    logging.debug("Writing out run info. run: %d, colour: %s" % (pending, colour))
                    total_bytes += 2
                    array_bytes.extend([0x80 | pending, colour])
                    pending = 0
        else:
            logging.debug("Writing out run info. run: %d, colour: %s" % (run, colour))
            total_bytes += 2
            array_bytes.extend([run, colour])
        data = struct.pack(str(total_bytes) + 'B', *array_bytes)
        logging.debug("  packed data = %r" % data)
        return data
    
    def packRunInfoMaskMultiSingleV2(self, colours):
        run = len(colours)
        total_bytes = 0
        array_bytes = []
        data = None
        pending = run;
        current = 0;
        while pending > 0:
            if pending >= 0x7F:
                logging.debug("Writing out singles info. singles: %d" % 0x7F)
                total_bytes += 1
                array_bytes.append(0x7F)
                for i in xrange(0x7F):
                    logging.debug("\tcolour: %s" % colours[current+i])
                    total_bytes += 1
                    array_bytes.append(colours[current+i])
                current += 0x7F
                pending -= 0x7F
            else:
                logging.debug("Writing out singles info. singles: %d" % run)
                total_bytes += 1
                array_bytes.append(run)
                for i in xrange(pending):
                    logging.debug("\tcolour: %s" % colours[current+i])
                    total_bytes += 1
                    array_bytes.append(colours[current+i])
                current += pending
                pending = 0
        data = struct.pack(str(total_bytes) + 'B', *array_bytes)
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
    
    def writeMask(self, mask_path, source_mask, width, height):
        img_file = file(mask_path, 'wb')
        source_data = source_mask.getdata()
        
        logging.debug("Encoding mask image")
        logging.debug("width: %d, height: %d" % (width, height))
        if source_mask is not None:
            # We encode the mask
            small_width = width >> 3
            mask_data = source_mask.getdata()
            compact_data = [0] * small_width * height 
            
            for x in xrange(small_width):
                for y in xrange(height):
                    byte = 0x00
                    for i in xrange(8):
                        bit = mask_data[y * width + x*8+i] / 255
                        byte = byte | (bit << 7-i)
                    compact_data[y * small_width + x] = byte
            
            previous_value = None
            run = 0
            b = None
            bleeding = False
            single_values = []
            for x in xrange(small_width):
                for y in xrange(height):
                    b = compact_data[y * small_width + x]
                    if previous_value is None:
                        run += 1
                    elif b is not previous_value:
                        if run == 1:
                            single_values.append(previous_value)
                        else:
                            data = self.packRunInfoMaskV2(run, previous_value)
                            img_file.write(data)
                        run = 1   
                    elif b is previous_value: 
                        if run == 1 and len(single_values) > 0:
                            data = self.packRunInfoMaskMultiSingleV2(single_values)
                            img_file.write(data)
                            single_values = []
                        run += 1
                    previous_value = b        
            if run == 1 and len(single_values) > 0:
                single_values.append(b)
                data = self.packRunInfoMaskMultiSingleV2(single_values)
            else:
                data = self.packRunInfoMaskV2(run, previous_value, True)
            img_file.write(data)
            
        else:
            # We encode a completely black mask
            total_to_run = width/8 * height
            data = self.packRunInfoMaskV2(total_to_run, 0x00)
            img_file.write(data)
            
        img_file.close()
        
    def writeObject(self, object_path, image_path, source_image, source_mask, width, height, compression_method, freeze_palette, quantization):
        img_file = file(object_path, 'wb')
        source_data = source_image.getdata()
        bleed_table = [None] * height
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
                bleed_table = [None] * height

            logging.debug("Dither table: %s" % bleed_table)

            for y in xrange(height):
                # Get the current pixel.
                b = source_data[y * width + x]
                # Check if we can bleed. (The original encoder seems to favour bleeding over efficient run compression.
                # It will revert to bleeding even if it interrupts a continuous run of colour.)
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
        
        logging.debug("Encoding object mask")
        logging.debug("width: %d, height: %d" % (width, height))
        if source_mask is not None:
            # We encode the mask
            small_width = width >> 3
            mask_data = source_mask.getdata()
            compact_data = [0] * small_width * height 
            
            for x in xrange(small_width):
                for y in xrange(height):
                    byte = 0x00
                    for i in xrange(8):
                        bit = mask_data[y * width + x*8+i] / 255
                        byte = byte | (bit << 7-i)
                    compact_data[y * small_width + x] = byte
            
            previous_value = None
            run = 0
            b = None
            bleeding = False
            single_values = []
            for x in xrange(small_width):
                for y in xrange(height):
                    b = compact_data[y * small_width + x]
                    if previous_value is None:
                        logging.debug("Initial pixel")
                        run += 1
                    elif b is not previous_value:
                        if run == 1:
                            single_values.append(previous_value)
                        else:
                            data = self.packRunInfoMaskV2(run, previous_value)
                            img_file.write(data)
                        run = 1   
                    elif b is previous_value: 
                        if run == 1 and len(single_values) > 0:
                            data = self.packRunInfoMaskMultiSingleV2(single_values)
                            img_file.write(data)
                            single_values = []
                        run += 1
                    previous_value = b
            if run == 1 and len(single_values) > 0:
                single_values.append(b)
                data = self.packRunInfoMaskMultiSingleV2(single_values)
            else:
                data = self.packRunInfoMaskV2(run, previous_value, True)
            img_file.write(data)
            
        else:
            # We encode a completely black mask
            total_to_run = width/8 * height
            data = self.packRunInfoMaskV2(total_to_run, 0x00)
            img_file.write(data)
            
        img_file.close()

