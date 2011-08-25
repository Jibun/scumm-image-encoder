import sie.decoder.v1.DecoderV1
import sie.decoder.v2.DecoderV2
import sie.decoder.v4.DecoderV4
import sie.decoder.v5.DecoderV5
import sie.decoder.v6.DecoderV6
import sie.classconfigs
from sie.sie_util import ScummImageEncoderException

_version_map = [
    None,
    (sie.decoder.v1.DecoderV1, sie.classconfigs.ConfigV1),
    (sie.decoder.v2.DecoderV2, sie.classconfigs.ConfigV2),
    None,
    (sie.decoder.v4.DecoderV4, sie.classconfigs.ConfigV4),
    (sie.decoder.v5.DecoderV5, sie.classconfigs.ConfigV5),
    (sie.decoder.v6.DecoderV6, sie.classconfigs.ConfigV6)
]

def decodeImage(lflf_path, image_path, version, palette_num):
    if version < 0 or version >= len(_version_map) or _version_map[version] is None:
        raise ScummImageEncoderException("Unsupported SCUMM version: %d" % version)
    decoder_class, config = _version_map[version]
    decoder = decoder_class(config)
    decoder.decodeImage(lflf_path, image_path, palette_num)
