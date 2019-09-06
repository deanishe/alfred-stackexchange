# encoding: utf-8
#
# Copyright (c) 2019 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2019-09-06
#

"""Overlay check mark on icons."""

from __future__ import print_function, absolute_import


from Cocoa import (
    NSBitmapImageRep,
    NSPNGFileType,
    NSImage,
    NSMakeSize,
    NSCompositeCopy,
    NSSizeToCGSize,
    NSZeroPoint,
)
from CoreGraphics import CGRectZero


def overlay(src, overlay, dest):
    """Create image ``dest`` by putting ``overlay`` on top of ``src``.

    Args:
        src (str): Path to source image.
        overlay (str): Path to overlay image.
        dest (str): Path to save combined image to.
    """
    src = NSImage.alloc().initWithContentsOfFile_(src)
    overlay = NSImage.alloc().initWithContentsOfFile_(overlay)
    img = NSImage.alloc().initWithSize_(src.size())
    img.lockFocus()
    rect = (0, 0), src.size()
    src.drawInRect_(rect)
    overlay.drawInRect_(rect)
    img.unlockFocus()
    rep = NSBitmapImageRep.imageRepWithData_(img.TIFFRepresentation())
    data = rep.representationUsingType_properties_(NSPNGFileType,{})
    data.writeToFile_atomically_(dest, False)
