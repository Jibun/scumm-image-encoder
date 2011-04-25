Unpack a LucasArts game with ScummPacker v3 or higher.
Decode a room background to a PNG file. Pass the LFLF directory as one argument, and the name of the output image as another argument. You may also wish to pass the version number.
Encode a PNG to a room background (will modify existing assets, so you might want to make a backup).
Pack the game again with ScummPacker.

If the room uses the background's palette to animate objects, you may get some funny colours when you encode the image. Use the option "-f" to freeze the palette, i.e. no changes will be made to the palette. This requires the input image to have the exact same palette/colour table as the original background.

This program and its source code is available at <http://www.jestarjokin.net>.

Any enquiries can be sent directly to Laurence at <jestarjokin@jestarjokin.net>.