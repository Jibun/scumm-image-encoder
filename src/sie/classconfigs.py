class CodecClassConfig(object):
    def __init__(self,
                bitmap_path,
                object_path,
                palette_path,
                header_path,
                header_binary_format,
                header_binary_index_map):
        """
        bitmap_path: the path of the bitmap file (within the LFLF directory).
                     Should be a list of strings (for cross-platform sub-dir support).
        object_path: the path of the object bitmap file (within the LFLF directory).
                     Should be a list of strings (for cross-platform sub-dir support).
        palette_path: the path of the palette file (within the LFLF directory). Should be a list of strings.
                     Should be a list of strings (for cross-platform sub-dir support).
        header_path: the path of the header file (within the LFLF directory). Should be a list of strings.
                     Should be a list of strings (for cross-platform sub-dir support).
        header_binary_format: "None" if the header is expected in XML format.
                     Otherwise, a format string usable by Python's "struct" module, to pack/unpack the header data.
        header_binary_index_map: "None" if the header is expected in XML format.
                     Otherwise, a dictionary, mapping lookup keys to indexes in the unpacked struct data.
                     e.g. if "width" and "height" are respectively in the first and second positions of a binary
                     header, then the header_binary_index_map should look like this:
                      {"width" : 0, "height" : 1}
                     Required entries:
                      - width
                      - height
        """
        self.bitmap_path = bitmap_path
        self.object_path = object_path
        self.palette_path = palette_path
        self.header_path = header_path
        self.header_binary_format = header_binary_format
        self.header_binary_index_map = header_binary_index_map

ConfigV1 = CodecClassConfig(
    bitmap_path = ["ROv1"],
    object_path = None,
    palette_path = None,
    header_path = ["ROv1", "HDv1"],
    header_binary_format = "<4B", # include 2 unknown byte values
    header_binary_index_map = {"width" : 0, "height" : 1}
)

ConfigV2 = CodecClassConfig(
    bitmap_path = ["ROv2", "IMv2"],
    object_path = ["ROv2", "OIv2_"],
    palette_path = None,
    header_path = ["ROv2", "HDv2"],
    header_binary_format = "<2H",
    header_binary_index_map = {"width" : 0, "height" : 1}
)

ConfigV4 = CodecClassConfig(
    bitmap_path = ["RO", "BM.dmp"],
    object_path = None,
    palette_path = ["RO", "PA.dmp"],
    header_path = ["RO", "HD.xml"],
    header_binary_format = None,
    header_binary_index_map = None
)

ConfigV5 = CodecClassConfig(
    bitmap_path = ["ROOM", "RMIM", "IM00", "SMAP.dmp"],
    object_path = None,
    palette_path = ["ROOM", "CLUT.dmp"],
    header_path = ["ROOM", "RMHD.xml"],
    header_binary_format = None,
    header_binary_index_map = None
)

ConfigV6 = CodecClassConfig(
    bitmap_path = ["ROOM", "RMIM", "IM00", "SMAP.dmp"],
    object_path = None,
    palette_path = ["ROOM", "PALS", "WRAP", "APAL_%p.dmp"],
    header_path = ["ROOM", "RMHD.xml"],
    header_binary_format = None,
    header_binary_index_map = None
)
