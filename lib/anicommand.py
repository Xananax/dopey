# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from command import Action, SelectLayer
import layer
from gettext import gettext as _

def layername_from_description(idx, lidx, description):
    letter = ""
    for i in range(lidx // 26 + 1)[::-1]:
        n = lidx // (26 ** i)
        if i == 0: n += 1
        letter += chr(n+64)
        lidx -= 26 ** i
    layername = "<" + letter + "> CEL " + str(idx + 1)
    if description != '':
        layername += ": " + description
    return layername


class SelectFrame(Action):
    display_name = _("Select frame")
    automatic_undo = True
    def __init__(self, doc, idx):
        self.doc = doc
        self.frames = doc.ani.frames
        self.idx = idx
        self.prev_layer_idx = None

    def redo(self):
        cel = self.frames.cel_at(self.idx)
        if cel is not None:
            # Select the corresponding layer:
            layer_idx = self.doc.layers.index(cel)
            self.prev_layer_idx = self.doc.layer_idx
            self.doc.layer_idx = layer_idx
        
        self.prev_frame_idx = self.frames.idx
        self.frames.select(self.idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_layer_idx is not None:
            self.doc.layer_idx = self.prev_layer_idx
        self.frames.select(self.prev_frame_idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ToggleKey(Action):
    display_name = _("Toggle key")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame
    
    def redo(self):
        self.prev_value = self.frame.is_key
        self.frame.toggle_key()
        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.frame.is_key = self.prev_value
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ToggleSkipVisible(Action):
    display_name = _("Toggle skip visible")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame

    def redo(self):
        self.prev_value = self.frame.skip_visible
        self.frame.toggle_skip_visible()
        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.frame.skip_visible = self.prev_value
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ChangeDescription(Action):
    display_name = _("Change description")
    def __init__(self, doc, frame, idx, new_description):
        self.doc = doc
        self.frame = frame
	self.idx = idx
        self.lidx = self.doc.ani.layers.idx
        self.new_description = new_description
        if self.frame.cel != None:
            self.old_layername = self.frame.cel.name

    def redo(self):
        self.prev_value = self.frame.description
        self.frame.description = self.new_description
        self._notify_document_observers()
        if self.frame.cel != None:
            layername = layername_from_description(self.idx, self.lidx, self.frame.description)
            self.frame.cel.name = layername

    def undo(self):
        self.frame.description = self.prev_value
        self._notify_document_observers()
        if self.frame.cel != None:
            self.frame.cel.name = self.old_layername


class AddCel(Action):
    display_name = _("Add cel")
    def __init__(self, doc, frame, idx):
        self.doc = doc
        self.frame = frame
	self.idx = idx
        self.lidx = self.doc.ani.layers.idx

        # Create new layer:
        layername = layername_from_description(self.idx, self.lidx, self.frame.description)
        self.layer = layer.Layer(name=layername)
        self.layer._surface.observers.append(self.doc.layer_modified_cb)
    
    def redo(self):
        self.doc.layers.append(self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = len(self.doc.layers) - 1
        
        self.frame.add_cel(self.layer)
        self._notify_canvas_observers([self.layer])
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.remove(self.layer)
        self.doc.layer_idx = self.prev_idx
        self.frame.remove_cel()
        self._notify_canvas_observers([self.layer])
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class InsertFrames(Action):
    display_name = _("Insert Frame")
    def __init__(self, doc, length):
        self.doc = doc
        self.frames = doc.ani.frames
        self.idx = doc.ani.frames.idx
        self.length = length

    def redo(self):
        self.frames.insert_empty_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.remove_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class RemoveCel(Action):
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame
        self.layer = self.frame.cel
        self.prev_idx = None
    
    def redo(self):
        num = self.doc.ani.frames.count_cel(self.layer)
        if num == 1:
            self.doc.layers.remove(self.layer)
            self.prev_idx = self.doc.layer_idx
            self.doc.layer_idx = len(self.doc.layers) - 1
            self._notify_canvas_observers([self.layer])

        self.frame.remove_cel()

        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_idx is not None:
            self.doc.layers.append(self.layer)
            self.doc.layer_idx = self.prev_idx
            self._notify_canvas_observers([self.layer])

        self.frame.add_cel(self.layer)

        self.doc.ani.update_opacities()
        self._notify_document_observers()


class RemoveFrame(Action):
    display_name = _("Remove frame / cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frames = doc.ani.frames
        self.frame = frame
        self.prev_idx = None
        self.removed_frame = True
        self.layer = None
        
    def redo(self):
        if self.frame.cel:
            layer = self.frame.cel
            self.doc.layers.remove(layer)
            self.prev_idx = self.doc.layer_idx
            self.doc.layer_idx = len(self.doc.layers) - 1
            self._notify_canvas_observers([layer])
            
        if len(self.frames) == 1:
            self.removed_frame = False
            self.layer = self.frame.cel
            self.frame.remove_cel()
        else:
            self.frames.remove_frames(1)
        
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        if not self.removed_frame:
            self.frame.add_cel(self.layer)
        else:
            self.frames.insert_frames([self.frame])
        if self.frame.cel:
            self.doc.layers.append(self.frame.cel)
            self.doc.layer_idx = self.prev_idx
            self._notify_canvas_observers([self.frame.cel])
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()


class AppendFrames(Action):
    display_name = _("Append frame")
    def __init__(self, doc, length):
        self.doc = doc
        self.frames = doc.ani.frames
        self.length = length

    def redo(self):
        self.frames.append_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.remove_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class PasteCel(Action):
    display_name = _("Paste cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame

    def redo(self):
        self.prev_edit_operation = self.doc.ani.edit_operation
        self.prev_edit_frame = self.doc.ani.edit_frame
        self.prev_cel = self.frame.cel

        if self.doc.ani.edit_operation == 'copy':
            # TODO duplicate layer?
            self.frame.add_cel(self.doc.ani.edit_frame.cel)
        elif self.doc.ani.edit_operation == 'cut':
            self.frame.add_cel(self.doc.ani.edit_frame.cel)
            self.doc.ani.edit_frame.remove_cel()
        else:
            raise Exception 

        self.doc.ani.edit_operation = None
        self.doc.ani.edit_frame = None

        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.doc.ani.edit_operation = self.prev_edit_operation
        self.doc.ani.edit_frame = self.prev_edit_frame
        self.frame.add_cel(self.prev_cel)
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class InsertLayer(Action):
    display_name = _("Insert Layer")
    def __init__(self, doc):
        self.doc = doc
        self.layers = doc.ani.layers

    def redo(self):
        self.layers.insert_layer(self.doc)
        self.doc.ani.frames = self.layers.get_selected_layer()
        self._notify_document_observers()

    def undo(self):
        framelist = self.layers.get_selected_layer()
        for c in framelist.get_all_cels():
            self.doc.layers.remove(c)
        self.layers.remove_layer()
        if self.layers.idx == len(self.layers):
            self.layers.idx -= 1
        if self.doc.layer_idx == len(self.doc.layers):
            self.doc.layer_idx -= 1
        self.doc.ani.frames = self.layers.get_selected_layer()
        self._notify_document_observers()


class RemoveLayer(Action):
    display_name = _("Remove Layer")
    def __init__(self, doc):
        self.doc = doc
        self.layers = doc.ani.layers
        self.frames = self.layers.get_selected_layer()
        self.prev_idx = None
        
    def redo(self):
        self.removed_layer = self.layers.remove_layer()
        for c in self.frames.get_all_cels():
            self.doc.layers.remove(c)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = 0

        if len(self.layers) == 0:
            self.layers.append_layer(24, self.doc)
            self.doc.layer_idx = 0
        else:
            if self.layers.idx == len(self.layers):
                self.layers.idx -= 1

        self.doc.ani.frames = self.layers.get_selected_layer()
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        self.layers.insert_layer(self.doc, self.removed_layer)
        self.doc.ani.frames = self.layers.get_selected_layer()
        self.doc.layer_idx = self.prev_idx
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()


class SortLayers(Action):
    display_name = _("Reorder Layer Stack")
    automatic_undo = True
    def __init__(self, doc):
        self.doc = doc
        self.anilayers = self.doc.ani.layers
        self.new_order = self.anilayers.get_order(self.doc.layers)
        self.old_order = doc.layers[:]
        self.selection = self.old_order[doc.layer_idx]

    def redo(self):
        self.old_names = []
        for l in self.doc.layers:
            self.old_names.append(l.name)
        self.doc.layers[:] = self.new_order
        self.doc.layer_idx = self.doc.layers.index(self.selection)
        for l in range(len(self.anilayers)):
            for f in range(len(self.anilayers[l])):
                if self.anilayers[l][f].has_cel():
                    new_name = layername_from_description(f, l, self.anilayers[l][f].description)
                    self.anilayers[l][f].cel.name = new_name
        layer = self.anilayers.get_selected_layer()
        cel = layer.cel_at(layer.idx)
        if cel is not None:
            # Select the corresponding layer:
            layer_idx = self.doc.layers.index(cel)
            self.prev_layer_idx = self.doc.layer_idx
            self.doc.layer_idx = layer_idx
        self.doc.ani.update_opacities()




    def undo(self):
        self.doc.layers[:] = self.old_order
        self.doc.layer_idx = self.doc.layers.index(self.selection)
        for i in range(len(self.doc.layers)):
            self.doc.layers[i].name = self.old_names[i]
