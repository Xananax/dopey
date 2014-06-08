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

class SelectFrame(Action):
    display_name = _("Select frame")
    automatic_undo = True
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.prev_layer_idx = None

    def redo(self):
        cel = self.timeline.layer.cel_at(self.idx)
        if cel is not None:
            # Select the corresponding layer:
            layer_idx = self.doc.layers.index(cel)
            self.prev_layer_idx = self.doc.layer_idx
            self.doc.layer_idx = layer_idx
        
        self.prev_frame_idx = self.timeline.idx
        self.timeline.select(self.idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_layer_idx is not None:
            self.doc.layer_idx = self.prev_layer_idx
        self.timeline.select(self.prev_frame_idx)
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
    def __init__(self, doc, frame, l_idx, idx, new_description):
        self.doc = doc
        self.frame = frame
	self.idx = idx
        self.l_idx = l_idx
        self.new_description = new_description
        if self.frame.cel != None:
            self.old_layername = self.frame.cel.name

    def redo(self):
        self.prev_value = self.frame.description
        self.frame.description = self.new_description
        self._notify_document_observers()
        if self.frame.cel != None:
            layername = self.doc.ani.generate_layername(self.idx, self.l_idx, self.frame.description)
            self.frame.cel.name = layername

    def undo(self):
        self.frame.description = self.prev_value
        self._notify_document_observers()
        if self.frame.cel != None:
            self.frame.cel.name = self.old_layername


class AddCel(Action):
    display_name = _("Add cel")
    def __init__(self, doc, l_idx, idx):
        self.doc = doc
	self.idx = idx
        self.lidx = l_idx
        self.frame = self.doc.ani.timeline[l_idx][idx]

        # Create new layer:
        layername = self.doc.ani.generate_layername(self.idx, self.lidx, self.frame.description)
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
    def __init__(self, doc, length, l_idx, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.layer = l_idx
        self.length = length

    def redo(self):
        self.timeline[self.layer].insert_frames(self.idx, self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.timeline[self.layer].remove_frames(self.idx, self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class RemoveCel(Action):
    display_name = _("Remove Cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame
        self.layer = self.frame.cel
        self.prev_idx = None
    
    def redo(self):
        self.doc.layers.remove(self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = len(self.doc.layers) - 1
        self._notify_canvas_observers([self.layer])

        self.frame.remove_cel()

        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.append(self.layer)
        self.doc.layer_idx = self.prev_idx
        self._notify_canvas_observers([self.layer])

        self.frame.add_cel(self.layer)

        self.doc.ani.update_opacities()
        self._notify_document_observers()


class RemoveFrame(Action):
    display_name = _("Remove Frame")
    def __init__(self, doc, frame, l_idx=None):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.frame = frame
        self.prev_idx = None
        self.layer = l_idx
        
        
    def redo(self):
        if self.timeline[self.layer][self.frame].cel:
            layer = self.timeline[self.layer][self.frame].cel
            self.doc.layers.remove(layer)
            self.prev_idx = self.doc.layer_idx
            self.doc.layer_idx = len(self.doc.layers) - 1
            self._notify_canvas_observers([layer])

        self.timeline[self.layer].remove_frames(self.layer)
        
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        self.timeline[self.layer].insert_frames([self.frame])
        if self.frame.cel:
            self.doc.layers.append(self.frame.cel)
            self.doc.layer_idx = self.prev_idx
            self._notify_canvas_observers([self.frame.cel])
        self.doc.ani.update_opacities()
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
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx

    def redo(self):
        self.timeline.insert_layer(idx=self.idx)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.timeline.remove_layer(self.idx)
        if self.timeline.idx == len(self.timeline):
            self.timeline.idx -= 1
        self.doc.ani.cleared = True
        self._notify_document_observers()


class RemoveLayer(Action):
    display_name = _("Remove Layer")
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.prev_idx = None
        self.replaced = False
        
    def redo(self):
        self.removed_layer = self.timeline.remove_layer(self.idx)
        for c in self.removed_layer.get_all_cels():
            self.doc.layers.remove(c)
        self.prev_idx = self.doc.layer_idx
        new_idx = self.timeline.layer.cel_at(self.idx)
        if new_idx is not None:
            self.doc.layer_idx = new_idx
        else:
            self.doc.layer_idx = 0

        if len(self.timeline) == 0:
            self.layers.append_layer()
            self.timeline.layer_idx = 0
            self.replaced = True

        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        if self.replaced:
            self.timeline.remove_layer()
            self.timeline.layer_idx = 0
        for c in self.removed_layer.get_all_cels():
            self.doc.layers.insert(c)
        self.timeline.insert_layer(self.removed_layer, self.idx)
        self.doc.layer_idx = self.prev_idx

        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()

