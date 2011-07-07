# setup script for Scumm Image Encoder

from distutils.core import setup
import py2exe

# includes for py2exe
includes=['pyexpat', 'xml.etree.ElementTree', 'xml.etree.cElementTree']

opts = { 'py2exe': { 'includes':includes } }

setup(version = "2.2 beta 1",
      description = "SCUMM Image Encoder",
      name = "SCUMM Image Encoder",
      author = "Laurence Dougal Myers",
      author_email = "jestarjokin@jestarjokin.net",
      console = [
        {
            "script": "scummimg.py",
        }
      ],
      options=opts
      )

