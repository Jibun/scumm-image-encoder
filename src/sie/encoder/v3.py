import common
import logging
import os
import struct
from PIL import Image

UNDEFCOLOR = 125
MODE_NONE = 0
MODE_COLOR_RUN = 1
MODE_ALTERNATE = 2
MODE_BLEED = 3

class EncForm:
    def __init__(self):
        self.color1 = UNDEFCOLOR
        self.color2 = UNDEFCOLOR
        self.mode = MODE_NONE
        self.length = 0
        self.data = None
        self.used_chars = 255
        self.fin_width = 0
        self.fin_height = 0

class EncoderV3(common.ImageEncoderBase):
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
        #  background = "v3_image1.png"
        #  objects = "v3_image1-OIv3_0018.png", "v3_image1-OIv3_0019.png"
        #  masks = "v3_image1-OIv3_0018.mask.png", "v3_image1-OIv3_0019.mask.png"
        oip, oipext = os.path.splitext(os.path.basename(image_path))
        obj_file_names = [f
                          for f
                          in os.listdir(object_images_path)
                          if f.startswith("%s-OIv3_" % oip) and not f.endswith("mask.png")]
        for obj_image_name in obj_file_names:
            oibase, oiext = os.path.splitext(os.path.basename(obj_image_name))
            objNum = obj_image_name[-4 - len(oiext):-len(oiext)]
            logging.debug("encoding v3 object #%s" % objNum)
            
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
    
    def packRunInfoV3(self, run, colour, colour_alt, mode):
        logging.debug("Writing out run info. run: %d, colour1: %s, colour2: %s, mode: %s" % (run, colour, colour_alt, mode))
        data = None
        bytes = 0
        if mode == MODE_BLEED:
            if run > 0x3F:
                data = struct.pack('2B', 0x80, run)
                bytes = 2
            else:
                data = struct.pack('B', 0x80 | run)
                bytes = 1
        elif mode == MODE_ALTERNATE:
            if run > 0x3F:
                data = struct.pack('3B', 0xC0, (colour << 4) | colour_alt, run)
                bytes = 3
            else:
                data = struct.pack('2B', 0xC0 | run, (colour << 4) | colour_alt)
                bytes = 2
        else:
            if run > 0x07:
                data = struct.pack('2B', colour, run)
                bytes = 2
            else:
                data = struct.pack('B', (run << 4) | colour)
                bytes = 1
        logging.debug("  packed data = %r" % data)
        return data, bytes
    
    def packRunInfoMaskV3(self, run, colour, last_bytes = False):
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
                elif last_bytes and pending == 2: # and colour == 0x00:
                    logging.debug("Writing out run info. run: %d, colour: %s" % (pending, colour))
                    logging.debug("Ignoring colour byte for coherence with original code")
                    total_bytes += 1
                    array_bytes.append(0x80 | pending)
                    pending = 0
                elif pending == 1:
                    logging.debug("Writing out singles info. singles: %d" % run)
                    logging.debug("\tcolour: %s" % colour)
                    total_bytes += 2
                    array_bytes.extend([pending, colour])
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
        return data, total_bytes
    
    def packRunInfoMaskMultiSingleV3(self, colours):
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
        return data, total_bytes

    def checkLengthOfSamePixelsWithinChunk(self, cur_width, cur_height, f1, imHeight, imWidth, source_data):
        k = 0
        j = 0

        colorTmp = 0
        nextColumnChunkBorder = 0
        nextColumnChunkBorder = cur_width + 8 - (cur_width % 8)

        colorTmp = source_data[cur_height * imWidth + cur_width]

        f1.mode = MODE_COLOR_RUN
        f1.color1 = colorTmp
        f1.length = 1
        f1.fin_width = cur_width
        f1.fin_height = cur_height

        k = cur_width
        j = cur_height
        while True:
            j += 1
            if j >= imHeight:
                j = 0
                k += 1
                if k >= nextColumnChunkBorder or k >= imWidth:
                    break

            colorTmp = source_data[j * imWidth + k]

            if colorTmp == f1.color1 and f1.length < 255:
                f1.length += 1
                f1.fin_width = k
                f1.fin_height = j
            else:
                break

        f1.data, f1.used_chars = self.packRunInfoV3(f1.length, f1.color1, None, f1.mode)
            
        return f1
    
    def checkLengthOfSwitchingPixelsWithinChunk(self, cur_width, cur_height, f2, imHeight, imWidth, source_data):
        alterIdx = 0

        colorTmp = 0
        nextColumnChunkBorder = cur_width + 8 - (cur_width % 8)

        colorTmp = source_data[cur_height * imWidth + cur_width]
        
        f2.mode = MODE_ALTERNATE
        f2.color1 = colorTmp
        f2.length = 1
        f2.fin_width = cur_width
        f2.fin_height = cur_height

        k = cur_width
        j = cur_height
        alterIdx = 1;
        
        while True:
            j += 1
            if j >= imHeight:
                j = 0
                k += 1
                if k >= nextColumnChunkBorder or k >= imWidth:
                    break

            colorTmp = source_data[j * imWidth + k]
            
            if f2.color2 == UNDEFCOLOR:
                f2.color2 = colorTmp
                if f2.color2 == f2.color1:
                    return f2

            if ((alterIdx % 2 == 1) and (colorTmp == f2.color2)) or ((alterIdx % 2 == 0) and (colorTmp == f2.color1) and f2.length < 255):
                f2.length += 1
                f2.fin_width = k
                f2.fin_height = j
            else:
                break

            alterIdx += 1

        if f2.length == 2:
            f2.length = 0
            f2.fin_width = cur_width
            f2.fin_height = cur_height
            return f2

        f2.data, f2.used_chars = self.packRunInfoV3(f2.length, f2.color1, f2.color2, f2.mode)

        return f2
        
    def checkLengthOfCopyColumnPixelsWithinChunk(self, cur_width, cur_height, f3, imHeight, imWidth, source_data):
        k = 0
        j = 0
        colorTmp1 = 0
        colorTmp2 = 0

        colorInPalIdx1 = 0
        colorInPalIdx2 = 0

        nextColumnChunkBorder = 0
        if cur_width % 8 == 0:
            return f3

        nextColumnChunkBorder = cur_width + 8 - (cur_width % 8)

        colorTmp1 = source_data[cur_height * imWidth + cur_width]
        colorTmp2 = source_data[cur_height * imWidth + cur_width -1]
        if colorTmp1 != colorTmp2:
            return f3

        f3.mode = MODE_BLEED
        f3.length = 1
        f3.fin_width = cur_width
        f3.fin_height = cur_height

        k = cur_width
        j = cur_height
        while True: #k < nextColumnChunkBorder:
            j += 1
            if j >= imHeight:
                j = 0
                #break
                k += 1
                if k >= nextColumnChunkBorder or k >= imWidth:
                    break

            colorTmp1 = source_data[j * imWidth + k]
            colorTmp2 = source_data[j * imWidth + k - 1]
            if colorTmp1 == colorTmp2 and f3.length < 255:
                f3.length += 1
                f3.fin_width = k
                f3.fin_height = j
            else:
                break

        f3.data, f3.used_chars = self.packRunInfoV3(f3.length, None, None, f3.mode)

        return f3

    def findMode(self, resultForm, eFofSamePix, eFofAlternativePix, eFofCopyColPix):
        #If two are equal and greater than the third (3)
        if (eFofSamePix.length == eFofAlternativePix.length) and (eFofSamePix.length > eFofCopyColPix.length):
            # subcases for char_used (min is better):  
            # - If both are equal (1)
            # - If one of the two is less than the other (2)
            if eFofSamePix.used_chars <= eFofAlternativePix.used_chars:
                resultForm = eFofSamePix
            elif eFofAlternativePix.used_chars < eFofSamePix.used_chars:
                resultForm = eFofAlternativePix
        elif (eFofSamePix.length == eFofCopyColPix.length) and (eFofSamePix.length > eFofAlternativePix.length):
            # subcases for char_used (min is better):  
            # - If both are equal (1)
            # - If one of the two is less than the other (2)
            if eFofSamePix.used_chars < eFofCopyColPix.used_chars:
                resultForm = eFofSamePix
            elif eFofCopyColPix.used_chars <= eFofSamePix.used_chars:
                resultForm = eFofCopyColPix
        elif (eFofCopyColPix.length == eFofAlternativePix.length) and (eFofCopyColPix.length > eFofSamePix.length):
            # subcases for char_used (min is better):  
            # - If both are equal (1)
            # - If one of the two is less than the other (2)
            if eFofCopyColPix.used_chars <= eFofAlternativePix.used_chars:
                resultForm = eFofCopyColPix
            elif eFofAlternativePix.used_chars < eFofCopyColPix.used_chars:
                resultForm = eFofAlternativePix
        # If one out of three is greater than all others (3)
        elif (eFofSamePix.length > eFofAlternativePix.length) and (eFofSamePix.length > eFofCopyColPix.length):
            resultForm = eFofSamePix
        elif (eFofCopyColPix.length > eFofSamePix.length) and (eFofCopyColPix.length > eFofAlternativePix.length):
            resultForm = eFofCopyColPix
        elif (eFofAlternativePix.length > eFofCopyColPix.length) and (eFofAlternativePix.length > eFofSamePix.length):
            resultForm = eFofAlternativePix
        # If all three are equal (1) 
        elif (eFofSamePix.length == eFofAlternativePix.length) and (eFofSamePix.length == eFofCopyColPix.length):
            # subcases for char_used (min is better):
            # If two are equals and less than the third one (3)
            if (eFofSamePix.used_chars == eFofAlternativePix.used_chars) and (eFofSamePix.used_chars < eFofCopyColPix.used_chars):
                resultForm = eFofSamePix
            elif (eFofSamePix.used_chars == eFofCopyColPix.used_chars) and (eFofSamePix.used_chars < eFofAlternativePix.used_chars):
                resultForm = eFofCopyColPix
            elif (eFofCopyColPix.used_chars == eFofAlternativePix.used_chars) and (eFofCopyColPix.used_chars < eFofSamePix.used_chars):
                resultForm = eFofCopyColPix
            # If one out of the three is less than all the others (3)
            elif (eFofSamePix.used_chars < eFofAlternativePix.used_chars) and (eFofSamePix.used_chars < eFofCopyColPix.used_chars):
                resultForm = eFofSamePix
            elif (eFofCopyColPix.used_chars < eFofSamePix.used_chars) and (eFofCopyColPix.used_chars < eFofAlternativePix.used_chars):
                resultForm = eFofCopyColPix
            elif (eFofAlternativePix.used_chars < eFofSamePix.used_chars) and (eFofAlternativePix.used_chars < eFofCopyColPix.used_chars):
                resultForm = eFofAlternativePix
            # If all three are equal (copy color selection) (1)
            elif (eFofSamePix.used_chars == eFofAlternativePix.used_chars) and (eFofSamePix.used_chars == eFofCopyColPix.used_chars):
                resultForm = eFofCopyColPix
        return resultForm
        
    def writeBitmap(self, lflf_path, image_path, source_image, imWidth, imHeight, compression_method, freeze_palette, quantization):
        img_file = file(self.getNewBitmapPath(lflf_path), 'wb')
        source_data = source_image.getdata()
        
        logging.debug("Encoding background image")
        for i in range(1 + imWidth/8):
            img_file.write(struct.pack('2B', 0x00, 0x00))
        
        writtenImageBytes = 0;
        i = 0
        j = 0
        chnkIdx = 0

        arrayOfChunkColIndexes = [0] * (imWidth/8)
        arrayOfChunkColIndexes[chnkIdx] = 2 + (imWidth/8) * 2 + writtenImageBytes
        chnkIdx += 1
        while i < imWidth:
            eFofCopyColPix = EncForm()
            eFofSwitchingPix = EncForm()
            eFofSamePix = EncForm()

            eFofSamePix = self.checkLengthOfSamePixelsWithinChunk(i, j, eFofSamePix, imHeight, imWidth, source_data)
            eFofSwitchingPix = self.checkLengthOfSwitchingPixelsWithinChunk(i, j, eFofSwitchingPix, imHeight, imWidth, source_data)
            eFofCopyColPix = self.checkLengthOfCopyColumnPixelsWithinChunk(i, j, eFofCopyColPix, imHeight, imWidth, source_data)

            resultForm = EncForm()
            resultForm = self.findMode(resultForm, eFofSamePix, eFofSwitchingPix, eFofCopyColPix)
            img_file.write(resultForm.data)
            logging.debug("Chosen: %d" % resultForm.mode)

            i = resultForm.fin_width
            j = resultForm.fin_height + 1
            writtenImageBytes += resultForm.used_chars
            if j >= imHeight:
                j = 0
                i += 1
                if i >= imWidth:
                    break

                if i % 8 == 0:
                    arrayOfChunkColIndexes[chnkIdx] = 2 + (imWidth/8) * 2 + writtenImageBytes
                    chnkIdx += 1

        finalSize = 2 + (imWidth/8) * 2 + writtenImageBytes
        img_file.seek(0, os.SEEK_SET)
        img_file.write(struct.pack('H', finalSize))

        for i in range(chnkIdx):
            img_file.write(struct.pack('H', arrayOfChunkColIndexes[i]))
            
        img_file.close()
        
    def writeMask(self, mask_path, source_mask, imWidth, imHeight):
        img_file = file(mask_path, 'wb')
        source_data = source_mask.getdata()
        
        logging.debug("Encoding mask image")
        
        for i in range(imWidth/8):
            img_file.write(struct.pack('2B', 0x00, 0x00))
            
        writtenImageBytes = 0
        chnkIdx = 0
        arrayOfChunkColIndexes = [0] * (imWidth/8)
        arrayOfChunkColIndexes[chnkIdx] = (imWidth/8) * 2 + writtenImageBytes
        chnkIdx += 1
        
        if source_mask is not None:
            # We encode the mask
            small_width = imWidth >> 3
            mask_data = source_mask.getdata()
            compact_data = [0] * small_width * imHeight 
            
            for x in xrange(small_width):
                for y in xrange(imHeight):
                    byte = 0x00
                    for i in xrange(8):
                        bit = mask_data[y * imWidth + x*8+i] / 255
                        byte = byte | (bit << 7-i)
                    compact_data[y * small_width + x] = byte
            
            previous_value = None
            run = 0
            b = None
            bleeding = False
            single_values = []
            for x in xrange(small_width):
                for y in xrange(imHeight):
                    b = compact_data[y * small_width + x]
                    if previous_value is None:
                        run += 1
                    elif b is not previous_value:
                        if run == 1:
                            single_values.append(previous_value)
                        else:
                            data, bytes = self.packRunInfoMaskV3(run, previous_value)
                            img_file.write(data)
                            writtenImageBytes += bytes
                        run = 1   
                    elif b is previous_value: 
                        if run == 1 and len(single_values) > 0:
                            data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
                            img_file.write(data)
                            writtenImageBytes += bytes
                            single_values = []
                        run += 1
                    previous_value = b
                if x < small_width - 1:
                    #end run if any at chunk end
                    if run == 1 and len(single_values) > 0:
                        single_values.append(previous_value)
                        data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
                        single_values = []
                    else:
                        data, bytes = self.packRunInfoMaskV3(run, previous_value, True)
                    run = 0
                    previous_value = None
                    img_file.write(data)
                    writtenImageBytes += bytes
                    arrayOfChunkColIndexes[chnkIdx] = (imWidth/8) * 2 + writtenImageBytes
                    chnkIdx += 1
                            
            if run == 1 and len(single_values) > 0:
                single_values.append(b)
                data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
            else:
                data, bytes = self.packRunInfoMaskV3(run, previous_value, True)
            img_file.write(data)
            writtenImageBytes += bytes
            
        else:
            # We encode a completely black mask
            total_to_run = imWidth/8 * imHeight
            data, total_chars = self.packRunInfoMaskV3(total_to_run, 0x00)
            img_file.write(data)
        
        img_file.seek(0, os.SEEK_SET)

        for i in range(chnkIdx):
            img_file.write(struct.pack('H', arrayOfChunkColIndexes[i]))
            
        img_file.close()
        
    def writeObject(self, object_path, image_path, source_image, source_mask, imWidth, imHeight, compression_method, freeze_palette, quantization):
        img_file = file(object_path, 'wb')
        source_data = source_image.getdata()
        
        logging.debug("Encoding object image")
        for i in range(1 + imWidth/8):
            img_file.write(struct.pack('2B', 0x00, 0x00))
        
        writtenImageBytes = 0;
        i = 0
        j = 0
        chnkIdx = 0

        arrayOfChunkColIndexes = [0] * (imWidth/8)
        arrayOfChunkColIndexes[chnkIdx] = 2 + (imWidth/8) * 2 + writtenImageBytes
        chnkIdx += 1
        while i < imWidth:
            eFofCopyColPix = EncForm()
            eFofSwitchingPix = EncForm()
            eFofSamePix = EncForm()

            eFofSamePix = self.checkLengthOfSamePixelsWithinChunk(i, j, eFofSamePix, imHeight, imWidth, source_data)
            eFofSwitchingPix = self.checkLengthOfSwitchingPixelsWithinChunk(i, j, eFofSwitchingPix, imHeight, imWidth, source_data)
            eFofCopyColPix = self.checkLengthOfCopyColumnPixelsWithinChunk(i, j, eFofCopyColPix, imHeight, imWidth, source_data)

            resultForm = EncForm()
            resultForm = self.findMode(resultForm, eFofSamePix, eFofSwitchingPix, eFofCopyColPix)
            img_file.write(resultForm.data)
            logging.debug("Chosen: %d" % resultForm.mode)

            i = resultForm.fin_width
            j = resultForm.fin_height + 1
            writtenImageBytes += resultForm.used_chars
            if j >= imHeight:
                j = 0
                i += 1
                if i >= imWidth:
                    break

                if i % 8 == 0:
                    arrayOfChunkColIndexes[chnkIdx] = 2 + (imWidth/8) * 2 + writtenImageBytes
                    chnkIdx += 1

        finalSize = 2 + (imWidth/8) * 2 + writtenImageBytes
        img_file.seek(0, os.SEEK_SET)
        img_file.write(struct.pack('H', finalSize))

        for i in range(chnkIdx):
            img_file.write(struct.pack('H', arrayOfChunkColIndexes[i]))
            
        logging.debug("Encoding object mask")
        logging.debug("width: %d, height: %d" % (imWidth, imHeight))
        
        img_file.seek(0, os.SEEK_END)
        for i in range(imWidth/8):
                img_file.write(struct.pack('2B', 0x00, 0x00))
           
        writtenImageBytes = 0
        chnkIdx = 0
        arrayOfChunkColIndexes = [0] * (imWidth/8)
        arrayOfChunkColIndexes[chnkIdx] = (imWidth/8) * 2 + writtenImageBytes
        chnkIdx += 1
        
        if source_mask is not None:
            # We encode the mask
            small_width = imWidth >> 3
            mask_data = source_mask.getdata()
            compact_data = [0] * small_width * imHeight 
            
            for x in xrange(small_width):
                for y in xrange(imHeight):
                    byte = 0x00
                    for i in xrange(8):
                        bit = mask_data[y * imWidth + x*8+i] / 255
                        byte = byte | (bit << 7-i)
                    compact_data[y * small_width + x] = byte
            
            previous_value = None
            run = 0
            b = None
            bleeding = False
            single_values = []
            for x in xrange(small_width):
                for y in xrange(imHeight):
                    b = compact_data[y * small_width + x]
                    if previous_value is None:
                        run += 1
                    elif b is not previous_value:
                        if run == 1:
                            single_values.append(previous_value)
                        else:
                            data, bytes = self.packRunInfoMaskV3(run, previous_value)
                            img_file.write(data)
                            writtenImageBytes += bytes
                        run = 1   
                    elif b is previous_value: 
                        if run == 1 and len(single_values) > 0:
                            data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
                            img_file.write(data)
                            writtenImageBytes += bytes
                            single_values = []
                        run += 1
                    previous_value = b
                if x < small_width - 1:
                    #end run if any at chunk end
                    if run == 1 and len(single_values) > 0:
                        single_values.append(previous_value)
                        data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
                        single_values = []
                    else:
                        data, bytes = self.packRunInfoMaskV3(run, previous_value, True)
                    run = 0
                    previous_value = None
                    img_file.write(data)
                    writtenImageBytes += bytes
                    arrayOfChunkColIndexes[chnkIdx] = (imWidth/8) * 2 + writtenImageBytes
                    chnkIdx += 1
                            
            if run == 1 and len(single_values) > 0:
                single_values.append(b)
                data, bytes = self.packRunInfoMaskMultiSingleV3(single_values)
            else:
                data, bytes = self.packRunInfoMaskV3(run, previous_value, True)
            img_file.write(data)
            writtenImageBytes += bytes
            
        else:
            # We encode a completely black mask
            total_to_run = imWidth/8 * imHeight
            data, total_chars = self.packRunInfoMaskV3(total_to_run, 0x00)
            img_file.write(data)
        
        img_file.seek(finalSize, os.SEEK_SET)

        for i in range(chnkIdx):
            img_file.write(struct.pack('H', arrayOfChunkColIndexes[i]))
            
        img_file.close()