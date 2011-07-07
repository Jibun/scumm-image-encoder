----
V5 or V6

Unpack a LucasArts game with ScummPacker v3 or higher.
Decode a room background to a PNG file. Pass the LFLF directory as one argument, and the name of the output image as another argument. Also pass the SCUMM version number to target. Pass the "-d" option to decode.
Encode a PNG to a room background (will modify existing assets, so you might want to make a backup). Pass the "-e" option to encode.
Pack the game again with ScummPacker.

If the room uses the background's palette to animate objects, you may get some funny colours when you encode the image. Use the option "-f" to freeze the palette, i.e. no changes will be made to the palette. This requires the input image to have the exact same palette/colour table as the original background.
----
V2

Unpack a LucasArts game with ScummRp.
Decode a room background to a PNG file. Similar to V5 or V6. Will look for a folder "ROv2", containing the files "HDv2" and "IMv2"
Encode a PNG to a room background. This requires a "ROv2" folder to exist in the output directory, and will write new "HDv2" and "IMv2" files (replacing any existing files).
Pack the game again with ScummRp.
----
This program and its source code is available at <http://www.jestarjokin.net>.

Any enquiries can be sent directly to Laurence at <jestarjokin@jestarjokin.net>.