import v1
import v2
import v4
import v5
import v6

from sie.sie_util import ScummImageEncoderException

_version_map = [
    None,
    (v1.DecoderV1, {
          "bitmap_path" : ["ROv1"],
          "palette_path" : None,
          "header_path" : ["ROv1", "HDv1"],
          "header_binary_format" : "<2B"}),
    (v2.DecoderV2, {
          "bitmap_path" : ["ROv2", "IMv2"],
          "palette_path" : None,
          "header_path" : ["ROv2", "HDv2"],
          "header_binary_format" : "<2H"}),
    None,
    (v4.DecoderV4, {
          "bitmap_path" : ["RO", "BM.dmp"],
          "palette_path" : ["RO", "PA.dmp"],
          "header_path" : ["RO", "HD.xml"],
          "header_binary_format" : None
    }),
    (v5.DecoderV5, {
          "bitmap_path" : ["ROOM", "RMIM", "IM00", "SMAP.dmp"],
          "palette_path" : ["ROOM", "CLUT.dmp"],
          "header_path" : ["ROOM", "RMHD.xml"],
          "header_binary_format" : None
     }),
    (v6.DecoderV6, {
          "bitmap_path" : ["ROOM", "RMIM", "IM00", "SMAP.dmp"],
          "palette_path" : ["ROOM", "PALS", "WRAP", "APAL_%p.dmp"],
          "header_path" : ["ROOM", "RMHD.xml"],
          "header_binary_format" : None
    })
]

def decodeImage(lflf_path, image_path, version, palette_num):
    if version >= len(_version_map) or _version_map[version] is None:
        raise ScummImageEncoderException("Unsupported SCUMM version: %d" % version)
    decoder_class, config = _version_map[version]
    decoder = decoder_class(config)
    decoder.decodeImage(lflf_path, image_path, palette_num)
