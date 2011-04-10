# setup script for Scummpacker

from distutils.core import setup
import py2exe

# includes for py2exe
includes=[]
includes += ['Image']

opts = { 'py2exe': { 'includes':includes } }
#print 'opts',opts

setup(version = "1.2",
      description = "SCUMM Image Encoder",
      name = "SCUMM Image Encoder",
      author = "Laurence Dougal Myers",
      author_email = "jestarjokin@jestarjokin.net",
      console = [
        {
            "script": "mi2img.py",
        }
      ],
      options=opts
      )

