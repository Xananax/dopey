# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from command import Command, SelectLayer
import layer, timeline
from copy import deepcopy
from gettext import gettext as _

class SelectFrame(Command):
    display_name = _("Select frame")
    automatic_undo = True
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.prev_layer_path = None

    def redo(self):
        cel = self.timeline.layer.cel_at(self.idx)
        if cel is not None:
            # Select the corresponding layer:
            layers = self.doc.layer_stack
            layer_path = layers.deepindex(cel)
            self.prev_layer_path = layers.get_current_path()
            layers.set_current_path(layer_path)
        
        self.prev_frame_idx = self.timeline.idx
        self.timeline.select(self.idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_layer_path is not None:
            layers = self.doc.layer_stack
            layers.set_current_path(self.prev_layer_path)
        self.timeline.select(self.prev_frame_idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()

class SelectAnimationLayer(Command):
    display_name = _("Select layer")
    automatic_undo = True
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.prev_layer_path = None

    def redo(self):
        self.prev_idx = self.timeline.idx
        self.timeline.select_layer(self.idx)

        cel = self.timeline.cel
        layers = self.doc.layer_stack
        if cel is not None:
            # Select the corresponding layer:
            layer_path = layers.deepindex(cel)
            self.prev_layer_path = layers.get_current_path()
            layers.set_current_path(layer_path)
        else:
            layers.set_current_path((0,))

        self.doc.ani.cleared = True
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_layer_path is not None:
            layers = self.doc.layer_stack
            layers.set_current_path(self.prev_layer_path)
        self.timeline.select_layer(self.prev_idx)

        self.doc.ani.cleared = True
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ToggleKey(Command):
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


class ToggleSkipVisible(Command):
    display_name = _("Toggle skip visible")
    automatic_undo = True
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


class ChangeDescription(Command):
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
            layername = self.doc.ani.generate_layername(self.idx, self.frame.description)
            self.frame.cel.name = layername

    def undo(self):
        self.frame.description = self.prev_value
        self._notify_document_observers()
        if self.frame.cel != None:
            self.frame.cel.name = self.old_layername


class AddFrame(Command):
    display_name = _("Add frame")
    def __init__(self, doc, l_idx, idx, auto=False):
        self.automatic_undo = auto
        self.doc = doc
	self.idx = idx
        self.lidx = l_idx
        self.timeline = doc.ani.timeline
        self.frame = timeline.Frame()

        # Create new layer:
        layername = self.doc.ani.generate_layername(self.idx, self.frame.description)
        self.layer = layer.PaintingLayer(name=layername)
        self.layer.set_symmetry_axis(self.doc.get_symmetry_axis())
    
    def redo(self):
        layers = self.doc.layer_stack
        self.prev_path = layers.get_current_path()
        layers.deepinsert(self.prev_path, self.layer)
        inserted_path = layers.deepindex(self.layer)
        layers.set_current_path(inserted_path)
        
        self.timeline[self.lidx][self.idx] = self.frame
        self.frame.add_cel(self.layer)
        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self._notify_document_observers()
    
    def undo(self):
        layers = self.doc.layer_stack
        layers.deepremove(self.layer)
        layers.set_current_path(self.prev_path)
        self.prev_path = None
        self.timeline[self.lidx].pop(self.idx)
        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self._notify_document_observers()


class RemoveFrame(Command):
    display_name = _("Remove Frame")
    def __init__(self, doc, idx, l_idx=None):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.layer = l_idx
        self.frame = self.timeline[self.layer][self.idx]
        self.prev_path = None
        if self.frame.cel:
            layers = self.doc.layer_stack
            self.removed_path = layers.deepindex(self.frame.cel)
            self.replacement_layer = None
        
    def redo(self):
        self.removed = self.timeline[self.layer].remove_frames(self.idx)

        if self.frame.cel:
            layers = self.doc.layer_stack
            self.prev_path = layers.get_current_path()
            layers.deeppop(self.removed_path)
            path = layers.get_current_path()
            path_above = layers.deepget(path[:-1])
            if len(layers) == 0:
                logger.debug("Removed last layer")
                if self.doc.CREATE_PAINTING_LAYER_IF_EMPTY:
                    logger.debug("Replacing removed layer")
                    repl = self.replacement_layer
                    if repl is None:
                        repl = lib.layer.PaintingLayer()
                        repl.set_symmetry_axis(self.doc.get_symmetry_axis())
                        self.replacement_layer = repl
                        repl.name = layers.get_unique_name(repl)
                    layers.append(repl)
                    layers.set_current_path((0,))

            cel = self.timeline.cel
            if cel is not None:
                # Select the corresponding layer:
                layer_path = layers.deepindex(cel)
                layers.set_current_path(layer_path)
            else:
                layers.set_current_path((0,))
        
        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        self.timeline[self.layer].insert_frames(self.idx, self.removed)
        if self.frame.cel:
            layers = self.doc.layer_stack
            if self.replacement_layer is not None:
                layers.deepremove(self.replacement_layer)
            layers.deepinsert(self.removed_path, self.frame.cel)
            layers.set_current_path(self.prev_path)
        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self.doc.ani.cleared = True
        self._notify_document_observers()


class PasteCel(Command):		#@TODO
    display_name = _("Paste cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame
        self.prev_edit_operation = self.doc.ani.edit_operation
        self.prev_edit_frame = self.doc.ani.edit_frame
        self.prev_cel = self.frame.cel
        self.operation = self.doc.ani.edit_operation
        if self.operation == 'copy':
            self.prev_path = None
            snapshot = self.doc.ani.edit_frame.cel.save_snapshot()
            self.new_layer = layer.PaintingLayer()
            self.new_layer.load_snapshot(snapshot)
            self.new_layer.set_symmetry_axis(doc.get_symmetry_axis())

    def redo(self):
        if self.operation == 'copy':
            layers = self.doc.layer_stack
            self.prev_path = layers.get_current_path()
            layers.deepinsert(self.prev_path, self.new_layer)
            inserted_path = layers.deepindex(self.new_layer)
            layers.set_current_path(inserted_path)
            self.frame.add_cel(self.new_layer)
        elif self.operation == 'cut':
            self.frame.add_cel(self.doc.ani.edit_frame.cel)
            self.doc.ani.edit_frame.remove_cel()
        else:
            raise Exception 

        self.doc.ani.edit_operation = None
        self.doc.ani.edit_frame = None

        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self._notify_document_observers()

    def undo(self):
        self.doc.ani.edit_operation = self.prev_edit_operation
        self.doc.ani.edit_frame = self.prev_edit_frame
        self.frame.add_cel(self.prev_cel)
        if self.operation == 'copy':
            layers = self.doc.layer_stack
            layers.deepremove(self.new_layer)
            layers.set_current_path(self.prev_path)
        self.doc.ani.update_opacities()
        self.doc.ani.sort_layers()
        self._notify_document_observers()


class InsertLayer(Command):
    display_name = _("Insert Layer")
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx

    def redo(self):
        self.timeline.insert_layer(idx=self.idx)
        self.doc.ani.cleared = True
        self.doc.ani.sort_layers()
        self._notify_document_observers()

    def undo(self):
        self.timeline.remove_layer(self.idx)
        if self.timeline.idx == len(self.timeline):
            self.timeline.idx -= 1
        self.doc.ani.cleared = True
        self.doc.ani.sort_layers()
        self._notify_document_observers()


class RemoveLayer(Command):
    display_name = _("Remove Layer")
    def __init__(self, doc, idx):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = idx
        self.prev_path = None
        self.replaced = False
        self.replacement_layer = None
        
    def redo(self):
        layers = self.doc.layer_stack
        self.prev_path = layers.get_current_path()
        layers.deeppop(self.removed_layer.stack)
        self.removed_layer = self.timeline.remove_layer(self.idx)

        path = layers.get_current_path()
        path_above = layers.deepget(path[:-1])
        if len(layers) == 0:
            logger.debug("Removed last layer")
            if self.doc.CREATE_PAINTING_LAYER_IF_EMPTY:
                logger.debug("Replacing removed layer")
                repl = self.replacement_layer
                if repl is None:
                    repl = lib.layer.PaintingLayer()
                    repl.set_symmetry_axis(self.doc.get_symmetry_axis())
                    self.replacement_layer = repl
                    repl.name = layers.get_unique_name(repl)
                layers.append(repl)
                layers.set_current_path((0,))

        if len(self.timeline) == 0:
            self.timeline.append_layer()
            self.timeline.layer_idx = 0
            self.replaced = True

        cel = self.timeline.cel
        if cel is not None:
            # Select the corresponding layer:
            layer_path = layers.deepindex(cel)
            layers.set_current_path(layer_path)
        else:
            layers.set_current_path((0,))

        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self.doc.ani.sort_layers()
        self._notify_document_observers()
            
    def undo(self):
        layers = self.doc.layer_stack
        if self.replaced:
            self.timeline.remove_layer()
            self.timeline.layer_idx = 0
        if self.replacement_layer is not None:
            layers.deepremove(self.replacement_layer)
        for c in self.removed_layer.get_all_cels():
            layers.deepinsert(self.prev_path, c)
        layers.set_current_path(self.prev_path)
        self.timeline.insert_layer(self.idx, self.removed_layer)

        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self.doc.ani.sort_layers()
        self._notify_document_observers()


class MergeAnimatedLayers(Command):
    display_name = _("Merge Down")
    def __init__(self, doc, layers):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.indices = [self.timeline.index(l) for l in layers]
        self.unmerged_layers = layers
        self.merged_layer = None

    def redo(self):
        rootstack = self.doc.layer_stack
        merged = self.merged_layer
        if merged is None:
            merged = timeline.FrameList()
            start = min(l.get_first() for l in self.unmerged_layers)
            stop = max(l.get_last() for l in self.unmerged_layers)
            for i in range(start, stop + 1):
                if all(i not in l for l in self.unmerged_layers):
                    continue
                is_key, skip_visible, cel, desc = False, False, None, ''
                is_key = any(l[i].is_key for l in self.unmerged_layers)
                skip_visible = all(l[i].skip_visible for l in self.unmerged_layers)
                desc = reduce(lambda a,b:a and b and a + _(', ') + b or b and b or a,
                              (l[i].description for l in self.unmerged_layers))
                if reduce(lambda a,b:a or b,
                          (l[i].cel for l in self.unmerged_layers)):
                    cel = self.doc.ani.merge([l.cel_at(i) for l in self.unmerged_layers])
                    cel.set_symmetry_axis(self.doc.get_symmetry_axis())
                merged[i] = timeline.Frame(is_key, skip_visible, cel, desc)
            self.merged_layer = merged

        idx = max(self.indices) + 1
        if idx < len(self.timeline):
            following = self.timeline[idx]
            last = False
        else:
            last = True
        for i in sorted(self.indices, reverse=True):
            self.timeline.pop(i)
        if last:
            self.idx = len(self.timeline)
        else:
            self.idx = self.timeline.index(following)
        self.timeline.insert(self.idx, merged)

        for layer in self.unmerged_layers:
            for i in layer:
                if layer[i].cel:
                    rootstack.deeppop(rootstack.deepindex(layer[i].cel))
        for i in merged:
            if merged[i].cel:
                rootstack.deepinsert((0,), merged[i].cel)

        self.prev_idx = self.timeline.layer_idx
        self.timeline.layer_idx = self.idx
        cel = self.timeline.cel
        if cel is not None:
            # Select the corresponding layer:
            layer_path = rootstack.deepindex(cel)
            rootstack.set_current_path(layer_path)
        else:
            rootstack.set_current_path((0,))

        self.doc.ani.sort_layers()
        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        rootstack = self.doc.layer_stack

        for nl, layer in enumerate(self.unmerged_layers):
            for i in layer:
                if layer[i].cel:
                    rootstack.deepinsert((self.indices[nl],), layer[i].cel)
        for i in self.merged_layer:
            if self.merged_layer[i].cel:
                rootstack.deeppop(rootstack.deepindex(self.merged_layer[i].cel))

        self.timeline.pop(self.timeline.index(self.merged_layer))
        for i, j in sorted(enumerate(self.indices), key=lambda x:x[1], reverse=True):
            self.timeline.insert(j, self.unmerged_layers[i])

        self.timeline.layer_idx = self.prev_idx
        cel = self.timeline.cel
        if cel is not None:
            # Select the corresponding layer:
            layer_path = rootstack.deepindex(cel)
            rootstack.set_current_path(layer_path)
        else:
            rootstack.set_current_path((0,))

        self.doc.ani.sort_layers()
        self.doc.ani.update_opacities()
        self._notify_document_observers()



        return

        rootstack = self.doc.layer_stack
        merged = self._merged_layer
        removed = rootstack.deeppop(self._upper_path)
        assert removed is merged
        rootstack.deepinsert(self._upper_path, self._lower_layer)
        rootstack.deepinsert(self._upper_path, self._upper_layer)
        assert rootstack.deepget(self._upper_path) is self._upper_layer
        assert rootstack.deepget(self._lower_path) is self._lower_layer
        self._upper_layer = None
        self._lower_layer = None
        rootstack.current_path = self._upper_path


class DuplicateAnimatedLayer(Command):
    display_name = _("Duplicate Layer")
    def __init__(self, doc, **kwds):
        self.doc = doc
        self.timeline = doc.ani.timeline
        self.idx = self.timeline.layer_idx
        self.new_layer = deepcopy(self.timeline.layer)

    def redo(self):
        layers = self.doc.layer_stack
        for i in self.new_layer:
            cel = self.new_layer[i].cel
            if cel:
                path = layers.deepindex(self.timeline.layer[i].cel)
                layers.deepinsert(path, cel)
        self.timeline.insert(self.idx, self.new_layer)
        self.doc.ani.sort_layers()
        self._notify_document_observers()

    def undo(self):
        layers = self.doc.layer_stack
        for i in self.new_layer:
            cel = self.new_layer[i].cel
            if cel:
                path = layers.deepindex(cel)
                layers.deeppop(path)
        self.timeline.pop(self.idx)
        self._notify_document_observers()

