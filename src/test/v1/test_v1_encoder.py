import array
import logging
import unittest
import sie.encoder
import sie.classconfigs

class TestRLEPackRunInfoV1(unittest.TestCase):
    def setUp(self):
        self.encoder = sie.encoder.v1.EncoderV1(sie.classconfigs.ConfigV1)

    def test_packRunInfo_run(self):
        expected = "\x64\x0C"
        value = 12
        run_length = 36
        common = []
        discrete_buffer = None
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_run_long(self):
        expected = "\x7F\x0D\x4E\x0D"
        value = 13
        run_length = 77
        common = []
        discrete_buffer = None
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_common(self):
        expected = "\xC4"
        value = 6
        run_length = 4
        common = [4, 5, 6, 7]
        discrete_buffer = None
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_common_long(self):
        expected = "\xDF\xCD"
        value = 6
        run_length = 44
        common = [4, 5, 6, 7]
        discrete_buffer = None
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_discrete(self):
        value = None
        run_length = None
        common = []
        discrete_buffer = range(16)
        expected = "\x0F" + "".join([chr(c) for c in discrete_buffer])
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_discrete_long(self):
        value = None
        run_length = None
        common = []
        discrete_buffer = range(73)
        temp_buf = [chr(c) for c in discrete_buffer]
        expected = "\x3F" + "".join(temp_buf[:64]) + "\x08" + "".join(temp_buf[64:])
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_discrete_single_value(self):
        value = None
        run_length = 0 # run_length must be provided, and must be 0.
        common = []
        discrete_buffer = [135]
        expected = "\x40\x87"
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_packRunInfo_discrete_single_common_value(self):
        value = None
        run_length = 0 # run_length must be provided, and must be 0.
        common = [136]
        discrete_buffer = [136]
        expected = "\x80"
        result = self.encoder.packRunInfo(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

class TestRLEV1(unittest.TestCase):
    def setUp(self):
        self.encoder = sie.encoder.v1.EncoderV1(sie.classconfigs.ConfigV1)

    def test_rle_simple_1(self):
        data = array.array('B',
            [1]
        )
        expected = ("\x01\x00\x00\x00" + # common colours
                    "\x80" # 1 discrete value of 1 (output as a run of a common value)
        )
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_rle_simple_2(self):
        data = array.array('B',
            [1, 2, 2]
        )
        expected = ("\x02\x01\x00\x00" + # common colours
                    "\xA0" + # 1 discrete value of 1 (output as a run of a common value)
                    "\x81" # 1 discrete value of 1 (output as a run of a common value)
        )
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_rle_simple_3(self):
        data = array.array('B',
            [1, 2, 2, 3, 3, 3, 24, 24, 46, 46, 71, 71]
        )
        expected = ("\x03\x02\x18\x2E" + # common colours
                    "\x40\x01" + # 1 discrete value of 1
                    "\xA1" + # 2 common run of 2
                    "\x82" + # 3 common run of 3
                    "\xC1" + # 2 common run of 24
                    "\xE1" + # 2 common run of 46
                    "\x41\x47" # 2 uncommon run of 71
        )
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_rle_simple_4(self):
        data = array.array('B',
            [1, 2, 3, 4, 1, 1, 23, 2, 2]
        )
        expected = ("\x01\x02\x03\x04" + # common colours
                    "\x03\x01\x02\x03\x04" + # 4 discrete values
                    "\x81" + # 2 common colours
                    "\x40\x17" + # 1 discrete value, output as a run of an uncommon colour
                    "\xA1" # 2 common colours
        )
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_rle_real_1(self):
        data = array.array('B',
            [1, 1, 23, 2, 2, 1, 1, 23, 2, 2, 52, 53, 54, 55, 56, 15, 12, 15, 15, 15, 15, 12, 15, 15, 15, 15, 12, 15, 15, 15, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
        )
        expected = "\x03\x0F\x01\x02\xC1\x40\x17\xE1\xC1\x40\x17\xE1\x06\x34\x35\x36\x37\x38\x0F\x0C\xA3\x40\x0C\xA3\x40\x0C\xA2\x8E"
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

    def test_rle_real_2(self):
        data = array.array('B',
            [21, 22, 22, 15, 15, 15, 3, 3, 3]
        )
        expected = "\x03\x0F\x16\x15\xE0\xC1\xA2\x82"
        result = self.encoder.compressRLEV1(data)
        print "expected: %s.\nactual:   %s" % ([ord(c) for c in expected], [ord(c) for c in result])
        self.assertEqual(
            expected,
            result
        )

class TestRowPack(unittest.TestCase):
    def setUp(self):
        self.encoder = sie.encoder.v1.EncoderV1(sie.classconfigs.ConfigV1)

    def test_row_pack_1(self):
        source_data = array.array('B',
                    [10, 10, 190, 190, 10, 10, 190, 190,
                    10, 10, 105, 105, 10, 10, 105, 105,
                    10, 10, 5, 5, 10, 10, 5, 5,
                    190, 190, 10, 10, 190, 190, 10, 10,
                    190, 190, 190, 190, 190, 190, 190, 190,
                    190, 190, 105, 105, 190, 190, 105, 105,
                    190, 190, 5, 5, 190, 190, 5, 5,
                    105, 105, 10, 10, 105, 105, 10, 10])
        common_colours = [10, 190, 105]
        width = 8
        custom_colour = 5
        row_start = 0
        expected = 0x11
        
        result = self.encoder.packRowData(source_data, common_colours, custom_colour, row_start, width)

        self.assertTrue(expected, result)

class TestBlockPack(unittest.TestCase):
    def setUp(self):
        self.encoder = sie.encoder.v1.EncoderV1(sie.classconfigs.ConfigV1)

    def test_block_pack_1(self):
        source_data = array.array('B',
                    [10, 10, 190, 190, 10, 10, 190, 190,
                    10, 10, 105, 105, 10, 10, 105, 105,
                    10, 10, 5, 5, 10, 10, 5, 5,
                    190, 190, 10, 10, 190, 190, 10, 10,
                    190, 190, 190, 190, 190, 190, 190, 190,
                    190, 190, 105, 105, 190, 190, 105, 105,
                    190, 190, 5, 5, 190, 190, 5, 5,
                    105, 105, 10, 10, 105, 105, 10, 10])
        vstrip_i = 0
        hstrip_i = 0
        width = 8
        common_colours = [10, 190, 105]
        block_map = {}
        picMap = []
        charMap = []
        colourMap = []
        expectedBlockMap = {(0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88) : 0}
        expectedPicMap = [0]
        expectedCharMap = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
        expectedColourMap = [5]

        self.encoder.packBlock(source_data, vstrip_i, hstrip_i, width, common_colours, block_map, picMap, charMap, colourMap)
        print block_map
        print picMap
        print charMap
        print colourMap
        self.assertEqual(expectedBlockMap, block_map)
        self.assertEqual(expectedPicMap, picMap)
        self.assertEqual(expectedCharMap, charMap)
        self.assertEqual(expectedColourMap, colourMap)


class TestObjectPack(unittest.TestCase):
    def setUp(self):
        configure_logging()
        self.encoder = sie.encoder.v1.EncoderV1(sie.classconfigs.ConfigV1)

    def test_object_pack_1(self):
        source_data = array.array('B',
                    [10, 10, 190, 190, 10, 10, 190, 190,
                    10, 10, 105, 105, 10, 10, 105, 105,
                    10, 10, 5, 5, 10, 10, 5, 5,
                    190, 190, 10, 10, 190, 190, 10, 10,
                    190, 190, 190, 190, 190, 190, 190, 190,
                    190, 190, 105, 105, 190, 190, 105, 105,
                    190, 190, 5, 5, 190, 190, 5, 5,
                    105, 105, 10, 10, 105, 105, 10, 10])
        width = 8
        height = 8
        charMap = array.array('B')
        block_map = {}
        common_colours = [0x0A, 0xBE, 0x69, 0x13]
        mask_data = array.array('B', [0x01])

        expected_objectMap = array.array('B',
            [0x00, 0x05, 0x01]
        )
        expected_charMap = array.array('B',
            [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
        )


        objectMap, charMap = self.encoder.packObjectData(source_data, width, height, charMap, block_map, common_colours, mask_data)
        self.assertEqual(objectMap, expected_objectMap)
        self.assertEqual(charMap, expected_charMap)

    def test_object_pack_2(self):
        source_data = array.array('B',
                    [10, 10, 190, 190, 10, 10, 190, 190,
                    10, 10, 105, 105, 10, 10, 105, 105,
                    10, 10, 5, 5, 10, 10, 5, 5,
                    190, 190, 10, 10, 190, 190, 10, 10,
                    190, 190, 190, 190, 190, 190, 190, 190,
                    190, 190, 105, 105, 190, 190, 105, 105,
                    190, 190, 5, 5, 190, 190, 5, 5,
                    105, 105, 10, 10, 105, 105, 10, 10,

                     105, 105, 10, 10, 105, 105, 10, 10,
                     190, 190, 5, 5, 190, 190, 5, 5,
                     190, 190, 105, 105, 190, 190, 105, 105,
                     190, 190, 190, 190, 190, 190, 190, 190,
                     190, 190, 10, 10, 190, 190, 10, 10,
                     10, 10, 5, 5, 10, 10, 5, 5,
                     10, 10, 105, 105, 10, 10, 105, 105,
                     10, 10, 190, 190, 10, 10, 190, 190])
        width = 8
        height = 16
        charMap = array.array('B')
        block_map = {}
        common_colours = [0x0A, 0xBE, 0x69]
        mask_data = array.array('B', [0x11, 0x22])

        expected_objectMap = array.array('B',
            [0x00, 0x01, 0x05, 0x05, 0x11, 0x22]
        )
        expected_charMap = array.array('B',
            [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
             0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11]
        )

        objectMap, charMap = self.encoder.packObjectData(source_data, width, height, charMap, block_map, common_colours, mask_data)
        self.assertEqual(objectMap, expected_objectMap)
        self.assertEqual(charMap, expected_charMap)


    def test_object_pack_3(self):
        source_data = array.array('B',
                    [10, 10, 190, 190, 10, 10, 190, 190,     105, 105, 10, 10, 105, 105, 10, 10,
                    10, 10, 105, 105, 10, 10, 105, 105,      190, 190, 5, 5, 190, 190, 5, 5,
                    10, 10, 5, 5, 10, 10, 5, 5,              190, 190, 105, 105, 190, 190, 105, 105,
                    190, 190, 10, 10, 190, 190, 10, 10,      190, 190, 190, 190, 190, 190, 190, 190,
                    190, 190, 190, 190, 190, 190, 190, 190,  190, 190, 10, 10, 190, 190, 10, 10,
                    190, 190, 105, 105, 190, 190, 105, 105,  10, 10, 5, 5, 10, 10, 5, 5,
                    190, 190, 5, 5, 190, 190, 5, 5,          10, 10, 105, 105, 10, 10, 105, 105,
                    105, 105, 10, 10, 105, 105, 10, 10,      10, 10, 190, 190, 10, 10, 190, 190
        ])
        width = 16
        height = 8
        charMap = array.array('B')
        block_map = {}
        common_colours = [0x0A, 0xBE, 0x69]
        mask_data = array.array('B', [0x3A, 0x3B])

        expected_objectMap = array.array('B',
            [0x00, 0x01, 0x05, 0x05, 0x3A, 0x3B]
        )
        expected_charMap = array.array('B',
            #[0x11, 0x88, 0x22, 0x77, 0x33, 0x66, 0x44, 0x55,
            # 0x55, 0x44, 0x66, 0x33, 0x77, 0x22, 0x88, 0x11]
            [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
             0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11]
        )

        objectMap, charMap = self.encoder.packObjectData(source_data, width, height, charMap, block_map, common_colours, mask_data)
        self.assertEqual(objectMap, expected_objectMap)
        self.assertEqual(charMap, expected_charMap)

    def test_object_pack_real_1(self):
        source_data = array.array('B', [0, 0, 0, 0, 7, 7, 7, 7, 7, 7, 0, 0, 0, 0, 7, 7, 7, 7, 0, 0, 0, 0, 7, 7, 7, 7, 7, 7, 0, 0, 0, 0, 0, 0, 7, 7, 8, 8, 0, 0, 0, 0, 7, 7, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 7, 7, 8, 8, 0, 0, 0, 0, 7, 7, 8, 8, 0, 0, 0, 0, 7, 7, 0, 0, 7, 7, 0, 0, 0, 0, 0, 0, 7, 7, 9, 9, 0, 0, 0, 0, 7, 7, 9, 9, 0, 0, 0, 0, 0, 0, 0, 0, 7, 7, 9, 9, 0, 0, 8, 8, 8, 8, 9, 9, 0, 0, 8, 8, 8, 8, 0, 0, 7, 7, 9, 9, 0, 0, 8, 8, 8, 8, 7, 7, 0, 0, 8, 8, 8, 8, 7, 7, 0, 0, 9, 9, 0, 0, 0, 0, 9, 9, 7, 7, 0, 0, 0, 0, 7, 7, 7, 7, 0, 0, 0, 0, 7, 7, 0, 0, 9, 9, 7, 7, 0, 0, 0, 0, 7, 7, 9, 9, 9, 9, 0, 0, 7, 7, 9, 9, 9, 9])
        width = 3 * 8
        height = 8
        self.assertTrue(len(source_data) == width * height)
        charMap = array.array('B', # contains all blocks already
            [
                0xFF, 0xF5, 0x55, 0x5A, 0xAA, 0xA0, 0x00, 0x0E, 0xE7, 0x7A, 0xA7, 0x7C, 0xC7, 0x78, 0x87, 0x70, 0x01, 0x1A, 0xA9, 0x9F, 0xFE, 0xE8, 0x85, 0x50, 0x03, 0x35, 0x55, 0x59, 0x95, 0x5A, 0xA9, 0x9F, 0xFE, 0xE8, 0x83, 0x3A, 0xA2, 0x20, 0x01, 0x19, 0x95, 0x5E, 0xEA, 0xA8, 0x82, 0x2A, 0xA4, 0x40, 0x02, 0x2A, 0xA5, 0x5F, 0xFA, 0xAF, 0xFF, 0xFA, 0xA5, 0x50, 0x01, 0x10, 0x00, 0x0A, 0xAA, 0xAA, 0xA4, 0x40, 0x02, 0x25, 0x5A, 0xA0, 0x0F, 0xF8, 0x8F, 0xFA, 0xA2, 0x20, 0x02, 0x25, 0x56, 0x66, 0x6B, 0xBB, 0xBF, 0xF8, 0x81, 0x1A, 0xA1, 0x10, 0x01, 0x15, 0x5A, 0xAA, 0xAF, 0xF8, 0x83, 0x30, 0x01, 0x15, 0x5A, 0xAA, 0xAF, 0xF8, 0x85, 0x54, 0x47, 0x7A, 0xA9, 0x90, 0x02, 0x25, 0x55, 0x5D, 0xD4, 0x4D, 0xD4, 0x44, 0x44, 0x4C, 0xCC, 0xC8, 0x86, 0x64, 0x40, 0x0F, 0xFC, 0xC8, 0x81, 0x10, 0x05, 0x53, 0x33, 0x33, 0x33, 0x30, 0x03, 0x3C, 0xCF, 0xF1, 0x13, 0x35, 0x54, 0x44, 0x47, 0x7E, 0xE8, 0x80, 0x04, 0x4F, 0xFF, 0xFF, 0xF0, 0x0C, 0xC0, 0x00, 0x03, 0x30, 0x03, 0x38, 0x83, 0x3E, 0xE1, 0x18, 0x85, 0x50, 0x03, 0x33, 0x3F, 0xF0, 0x0F, 0xF0, 0x03, 0x30, 0x03, 0x38, 0x82, 0x2C, 0xC3, 0x34, 0x43, 0x38, 0x85, 0x5C, 0xC3, 0x3A, 0xA3, 0x34, 0x47, 0x75, 0x5A, 0xA4, 0x47, 0x7F, 0xF9, 0x90, 0x08, 0x80, 0x00, 0x0F, 0xF7, 0x7F, 0xF7, 0x7C, 0xC4, 0x4D, 0xD5, 0x5C, 0xC4, 0x4D, 0xD1, 0x17, 0x7D, 0xD0, 0x00, 0x08, 0x86, 0x60, 0x02, 0x20, 0x00, 0x0D, 0xDF, 0xFD, 0xDF, 0xF4, 0x43, 0x35, 0x57, 0x74, 0x40, 0x07, 0x7D, 0xD8, 0x81, 0x1C, 0xC0, 0x0A, 0xA4, 0x48, 0x82, 0x2C, 0xC0, 0x0A, 0xA3, 0x38, 0x83, 0x3C, 0xC0, 0x0A, 0xA2, 0x28, 0x84, 0x4C, 0xC0, 0x0A, 0xA1, 0x10
            ]
        )
        # Need to fake the block map too.
        block_map = {}
        for i in xrange(0, len(charMap), 8):
            block_key = tuple(charMap[i : i + 8])
            block_map[block_key] = i / 8
        common_colours = [0x00, 0x08, 0x09, 0x06]
        mask_data = array.array('B')

        expected_objectMap = array.array('B',
            # NOTE: the original colour values were "15, 15, 15",
            #  but the decoder ANDs it with 7 - this means the
            #  colours will be 7 when we encode.
            # Also, this does not include the mask data.
            #[21, 22, 22, 15, 15, 15]
            [21, 22, 22, 7, 7, 7]
        )
        expected_charMap = array.array('B', # same
            [
                0xFF, 0xF5, 0x55, 0x5A, 0xAA, 0xA0, 0x00, 0x0E,
                0xE7, 0x7A, 0xA7, 0x7C, 0xC7, 0x78, 0x87, 0x70,
                0x01, 0x1A, 0xA9, 0x9F, 0xFE, 0xE8, 0x85, 0x50,
                0x03, 0x35, 0x55, 0x59, 0x95, 0x5A, 0xA9, 0x9F,
                0xFE, 0xE8, 0x83, 0x3A, 0xA2, 0x20, 0x01, 0x19,
                0x95, 0x5E, 0xEA, 0xA8, 0x82, 0x2A, 0xA4, 0x40,
                0x02, 0x2A, 0xA5, 0x5F, 0xFA, 0xAF, 0xFF, 0xFA,
                0xA5, 0x50, 0x01, 0x10, 0x00, 0x0A, 0xAA, 0xAA,
                0xA4, 0x40, 0x02, 0x25, 0x5A, 0xA0, 0x0F, 0xF8,
                0x8F, 0xFA, 0xA2, 0x20, 0x02, 0x25, 0x56, 0x66,
                0x6B, 0xBB, 0xBF, 0xF8, 0x81, 0x1A, 0xA1, 0x10,
                0x01, 0x15, 0x5A, 0xAA, 0xAF, 0xF8, 0x83, 0x30,
                0x01, 0x15, 0x5A, 0xAA, 0xAF, 0xF8, 0x85, 0x54,
                0x47, 0x7A, 0xA9, 0x90, 0x02, 0x25, 0x55, 0x5D,
                0xD4, 0x4D, 0xD4, 0x44, 0x44, 0x4C, 0xCC, 0xC8,
                0x86, 0x64, 0x40, 0x0F, 0xFC, 0xC8, 0x81, 0x10,
                0x05, 0x53, 0x33, 0x33, 0x33, 0x30, 0x03, 0x3C,
                0xCF, 0xF1, 0x13, 0x35, 0x54, 0x44, 0x47, 0x7E,
                0xE8, 0x80, 0x04, 0x4F, 0xFF, 0xFF, 0xF0, 0x0C,
                0xC0, 0x00, 0x03, 0x30, 0x03, 0x38, 0x83, 0x3E,
                0xE1, 0x18, 0x85, 0x50, 0x03, 0x33, 0x3F, 0xF0,
                0x0F, 0xF0, 0x03, 0x30, 0x03, 0x38, 0x82, 0x2C,
                0xC3, 0x34, 0x43, 0x38, 0x85, 0x5C, 0xC3, 0x3A,
                0xA3, 0x34, 0x47, 0x75, 0x5A, 0xA4, 0x47, 0x7F,
                0xF9, 0x90, 0x08, 0x80, 0x00, 0x0F, 0xF7, 0x7F,
                0xF7, 0x7C, 0xC4, 0x4D, 0xD5, 0x5C, 0xC4, 0x4D,
                0xD1, 0x17, 0x7D, 0xD0, 0x00, 0x08, 0x86, 0x60,
                0x02, 0x20, 0x00, 0x0D, 0xDF, 0xFD, 0xDF, 0xF4,
                0x43, 0x35, 0x57, 0x74, 0x40, 0x07, 0x7D, 0xD8,
                0x81, 0x1C, 0xC0, 0x0A, 0xA4, 0x48, 0x82, 0x2C,
                0xC0, 0x0A, 0xA3, 0x38, 0x83, 0x3C, 0xC0, 0x0A,
                0xA2, 0x28, 0x84, 0x4C, 0xC0, 0x0A, 0xA1, 0x10
            ]
        )

        objectMap, charMap = self.encoder.packObjectData(source_data, width, height, charMap, block_map, common_colours, mask_data)
        print "objectMap: %s. charMap: %s." % (objectMap, charMap)
        self.assertEqual(expected_objectMap, objectMap)
        self.assertEqual(expected_charMap, charMap)

def configure_logging():
    logging.basicConfig(format="", level=logging.DEBUG)