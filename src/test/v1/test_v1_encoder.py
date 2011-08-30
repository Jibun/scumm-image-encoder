import array
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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
        result = self.encoder.packRunInfoV1(value, run_length, common, discrete_buffer)
        print "expected: %s.\nactual:%s" % ([ord(c) for c in expected], [ord(c) for c in result])
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