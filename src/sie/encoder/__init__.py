import sie.encoder.v1
import sie.encoder.v2
import sie.encoder.v4
import sie.encoder.v5
import sie.encoder.v6
import sie.classconfigs
from sie.sie_util import ScummImageEncoderException

_version_map = [
    None,
    (v1.EncoderV1, sie.classconfigs.ConfigV1),
    (v2.EncoderV2, sie.classconfigs.ConfigV2),
    None,
    (v4.EncoderV4, sie.classconfigs.ConfigV4),
    (v5.EncoderV5, sie.classconfigs.ConfigV5),
    (v6.EncoderV6, sie.classconfigs.ConfigV6)
]

def encodeImage(lflf_path, image_path, version, quantization, palette_num, freeze_palette, compression_method=None):
    if version < 0 or version >= len(_version_map) or _version_map[version] is None:
        raise ScummImageEncoderException("Unsupported SCUMM version: %d" % version)
    encoder_class, config = _version_map[version]
    encoder = encoder_class(config)
    encoder.encodeImage(lflf_path, image_path, quantization, palette_num, freeze_palette, compression_method=None)
