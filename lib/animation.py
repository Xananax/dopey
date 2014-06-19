# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import glob
from gettext import gettext as _
import layer
import json
import tempfile
from subprocess import call

import pixbufsurface
import tiledsurface

import anicommand
from timeline import TimeLine
from xdna import XDNA
from mypaintlib import combine_mode_get_info


class Animation(object):
    
    opacities = {
    'cel':   0.5,
    'key':        0.4,
    'inbetweens': 0.2,
    'other keys': 0.3,
    'other':      0,
    }
    
    def __init__(self, doc):
        self.doc = doc
        self.timeline = None
        self.cleared = False
        self.using_legacy = False
        self.xdna = XDNA()

        # For reproduction, "play", "pause", "stop":
        self.player_state = None

        # For cut/copy/paste operations:
        self.edit_operation = None
        self.edit_frame = None

    def clear_xsheet(self, init=False):
        self.timeline = TimeLine(self.opacities)
        self.timeline.append_layer()
        self.cleared = True
    
    def legacy_xsheet_as_str(self):
        """
        Return animation X-Sheet as data in json format.
        (only saves first layer! (if it works? i dont even know. it should))

        """
        data = []
        for nf in self.timeline.layer:
            f = self.timeline.layer[nf]
            if f.cel is not None:
                layer_idx = self.doc.layers.index(f.cel)
            else:
                layer_idx = None
            data.append((f.is_key, f.description, layer_idx))
        str_data = json.dumps(data, sort_keys=True, indent=4)
        return str_data

    def rev1_xsheet_as_str(self):
        """
        Return animation X-Sheet as data in XDNA format.

        """
        x = self.xdna

        data = {
            'metadata': x.application_signature,
            'XDNA': x.xdna_signature,
            'xsheet': {
                'framerate': self.timeline.fps,
                'raster_frame_lists': []
            }
        }

        for l, lyr in enumerate(self.timeline):
            data['xsheet']['raster_frame_lists'].append([])
            for nf in range(len(lyr)):
                if nf in lyr:
                    f = lyr[nf]
                    if f.cel is not None:
                        layer_idx = self.doc.layers.index(f.cel)
                    else:
                        layer_idx = None
                    data['xsheet']['raster_frame_lists'][l].append({
                        'idx': layer_idx,
                        'is_key': f.is_key,
                        'description': f.description
                    })
                else:
                    data['xsheet']['raster_frame_lists'][l].append({
                        'idx': None,
                        'is_key': False,
                        'description': ''
                    })

        str_data = json.dumps(data, sort_keys=True, indent=4)
        return str_data

    def xsheet_as_str(self):
        """
        Return animation X-Sheet as data in newer XDNA format.

        """
        x = self.xdna

        data = {
            'metadata': x.application_signature,
            'XDNA': x.xdna_signature,
            'xsheet': {
                'framerate': self.timeline.fps,
                'raster_frame_lists': []
            }
        }

        self.timeline.cleanup()
        for l, lyr in enumerate(self.timeline):
            compop = combine_mode_get_info(lyr.composite).get("name", '')
            data['xsheet']['raster_frame_lists'].append({
                'name': lyr.name,
                'visible': lyr.visible,
                'opacity': lyr.opacity,
                'locked': lyr.locked,
                'composite': compop,
                'frames': {}
            })
            for nf in lyr:
                f = lyr[nf]
                if f.cel is not None:
                    layer_path = self.doc.layer_stack.deepindex(f.cel)
                else:
                    layer_path = None
                data['xsheet']['raster_frame_lists'][l]['frames'][nf] = {
                    'path': layer_path,
                    'is_key': f.is_key,
                    'description': f.description
                }

        str_data = json.dumps(data, sort_keys=True, indent=4)
        return str_data

    def _write_xsheet(self, xsheetfile):
        """
        Save FrameList to file.
        
        """
        str_data = self.xsheet_as_str()
        xsheetfile.write(str_data)

    def str_to_xsheet(self, ani_data):
        """
        Update TimeLine from animation data.
    
        """
        data = json.loads(ani_data)
        # first check if it's in the legacy non-descriptive JSON or new XDNA format
        if type(data) is dict and data['XDNA']:
            x = self.xdna

            raster_frames = data['xsheet']['raster_frame_lists']

            self.timeline = TimeLine(self.opacities)
            self.timeline.fps = int(data['xsheet']['framerate'])
            self.cleared = True


            #check which version of the XDNA format is being used
            if type(raster_frames[0]) is dict:
                print 'Loading using current file format'
                # load with current format (dictionaries)
                for j in range(len(raster_frames)):
                    self.timeline.append_layer()
                    self.timeline[j].name = str(raster_frames[j]['name'])
                    self.timeline[j].visible = raster_frames[j]['visible']
                    self.timeline[j].opacity = raster_frames[j]['opacity']
                    self.timeline[j].locked = raster_frames[j]['locked']
                    self.timeline[j].composite = tiledsurface.OPENRASTER_COMBINE_MODES.get(
                        str(raster_frames[j]['composite']), tiledsurface.DEFAULT_COMBINE_MODE)
                    for i in raster_frames[j]['frames']:
                        d = raster_frames[j]['frames'][i]
                        f = self.timeline[j][int(i)]
                        if d['path'] is not None:
                            cel = self.doc.layer_stack.deepget(d['path'])
                            if cel is None:
                                cel = layer.PaintingLayer()
                                self.doc.layer_stack.append(cel)
                        else:
                            cel = None
                        f.is_key = d['is_key']
                        f.description = d['description']
                        f.cel = cel
                
            else:
                # load with revision 1 format (lists)
                print 'Loading using revision 1 file format'
                for j in range(len(raster_frames)):
                    self.timeline.append_layer()
                    for i, d in enumerate(raster_frames[j]):
                        if d['idx'] is not None:
                            if d['idx'] < len(self.doc.layer_stack):
                                cel = self.doc.layer_stack.deepget(
                                       (len(self.doc.layer_stack)-int(d['idx'])-1,))
                            else:
                                cel = layer.PaintingLayer()
                                self.doc.layer_stack.append(cel)
                        else:
                            cel = None
                        self.timeline[j][i].is_key = d['is_key']
                        self.timeline[j][i].description = d['description']
                        self.timeline[j][i].cel = cel
                self.timeline.cleanup()

        else:
            # load in legacy non-descriptive JSON style
            print 'Loading using legacy file format'
            self.using_legacy = True
            self.timeline = TimeLine(self.opacities)
            self.timeline.append_layer()
            self.cleared = True
            for i, d in enumerate(data):
                is_key, description, layer_idx = d
                if layer_idx is not None:
                    if layer_idx < len(self.doc.layer_stack):
                        cel = self.doc.layer_stack.deepget(
                                 (len(self.doc.layer_stack)-int(d['idx'])-1,))
                    else:
                        cel = layer.PaintingLayer()
                        self.doc.layer_stack.append(cel)
                else:
                    cel = None
                self.timeline[0][i].is_key = is_key
                self.timeline[0][i].description = description
                self.timeline[0][i].cel = cel
            self.timeline.cleanup()

    def _read_xsheet(self, xsheetfile):
        """
        Update FrameList from file.
    
        """
        ani_data = xsheetfile.read()
        self.str_to_xsheet(ani_data)
    
    def save_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        xsheetfile = open(xsheet_fn, 'w')
        self._write_xsheet(xsheetfile)
    
    def load_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        try:
            xsheetfile = open(xsheet_fn, 'r')
        except IOError:
            self.clear_xsheet()
        else:
            self._read_xsheet(xsheetfile)
    
    def save_png(self, filename, **kwargs):
        prefix, ext = os.path.splitext(filename)
        # if we have a number already, strip it
        l = prefix.rsplit('-', 1)
        if l[-1].isdigit():
            prefix = l[0]
        doc_bbox = self.doc.get_effective_bbox()

        for i in range(self.timeline.get_first(), self.timeline.get_last()+1):
            frame = self.merge(self.timeline.cels_at(i))
            filename = '%s-%03d%s' % (prefix, i+1, ext)
            frame._surface.save_as_png(filename, *doc_bbox, **kwargs)

    def save_gif(self, filename, gif_fps=24, gif_loop=0, **kwargs):
        # Requires command tool imagemagick.
        tempdir = tempfile.mkdtemp()
        gifs_tempdir = os.path.join(tempdir, 'gifs')
        os.mkdir(gifs_tempdir)
        base_filename = os.path.basename(filename)
        prefix, ext = os.path.splitext(base_filename)
        out_filename = os.path.join(os.path.dirname(filename), prefix + '.gif')

        pngs_filename = os.path.join(tempdir, 'tempani.png')
        self.save_png(pngs_filename)

        # convert pngs to jpegs with imagemagick command:
        pngs_list = glob.glob(tempdir + os.path.sep + '*png')
        pngs_list.sort()
        for png_file in pngs_list:
            f_basename = os.path.basename(png_file)
            name, ext = os.path.splitext(f_basename)
            gif_file = os.path.join(gifs_tempdir, name + '.gif')
            print "converting %s to %s..." % (png_file, gif_file)
            call(["convert",
                  "-background", "white",
                  "-flatten",
                  png_file, gif_file])

        # convert the previous gifs to animated gif with imagemagick command:
        gifs = gifs_tempdir + os.path.sep + 'tempani-*.gif'
	gif_filename = os.path.join(tempdir, 'temp.gif')
        call(["convert",
              "-delay", "1x" + str(gif_fps),
              "-loop", str(gif_loop),
              gifs, gif_filename])

        # optimize gif size:
        call(["convert",
              "-layers", "Optimize",
              gif_filename, out_filename])

    def save_avi(self, filename, vid_width=800, vid_fps=24, **kwargs):
        """
        Save video file with codec mpeg4.

        Requires command tools imagemagick and ffmpeg .

        """
        tempdir = tempfile.mkdtemp()
        jpgs_tempdir = os.path.join(tempdir, 'jpgs')
        os.mkdir(jpgs_tempdir)
        base_filename = os.path.basename(filename)
        prefix, ext = os.path.splitext(base_filename)
        out_filename = os.path.join(os.path.dirname(filename), prefix + '.avi')

        pngs_filename = os.path.join(tempdir, 'tempani.png')
        self.save_png(pngs_filename)

        # convert pngs to jpegs with imagemagick command:
        pngs_list = glob.glob(tempdir + os.path.sep + '*png')
        pngs_list.sort()
        for png_file in pngs_list:
            f_basename = os.path.basename(png_file)
            name, ext = os.path.splitext(f_basename)
            jpg_file = os.path.join(jpgs_tempdir, name + '.jpg')
            print "converting %s to %s..." % (png_file, jpg_file)
            call(["convert",
                  "-resize", str(vid_width),
                  "-quality", "100",
                  "-background", "white",
                  "-flatten",
                  png_file, jpg_file])

        # convert the previous jpgs to video with ffmpeg command:
        jpgs = jpgs_tempdir + os.path.sep + 'tempani-%03d.jpg'
        call(["ffmpeg",
              "-r", str(vid_fps),
              "-b", "1800",
              "-y", "-i",
              jpgs, out_filename])

    def hide_all_frames(self):
        for cel in self.timeline.get_all_cels():
            cel.visible = False

    def change_visible_frame(self, prev_idx, cur_idx):
        prev_cels = self.timeline.cels_at(prev_idx)
        cur_cels = self.timeline.cels_at(cur_idx)
        if prev_cels == cur_cels: return
        for cel in prev_cels:
            if cel in cur_cels:
                continue
            if cel != None:
                cel.visible = False
        for cel in cur_cels:
            if cel in prev_cels:
                continue
            if cel != None:
                cel.opacity = 1
                cel.visible = True

    def update_opacities(self):
        opacities, visible = self.timeline.get_opacities()

        for cel, opa in opacities.items():
            if cel is None:
                continue
            cel.opacity = opa

        for cel, vis in visible.items():
            if cel is None:
                continue
            cel.visible = vis

    def number_to_letter(self, idx):
        letter = ""
        try:
            digits = int(math.log(idx, 26) + 1)
        except:
            digits = 1
        for i in range(digits)[::-1]:
            n = idx // (26 ** i)
            if i == 0: n += 1
            letter += chr(n+64)
            idx -= (26 ** i) * n
        return letter

    def generate_layername(self, idx, description):
        layername = "CEL " + str(idx + 1)
        if description != '':
            layername += ": " + description
        return layername

    def select_without_undo(self, idx):
        """Like the command but without undo/redo."""
        self.timeline.select(idx)
        self.update_opacities()

    def play_animation(self):
        self.player_state = "play"
        self.doc.call_doc_observers()

    def pause_animation(self):
        self.player_state = "pause"

    def playpause_animation(self):
        if self.player_state != "play":
            self.player_state = "play"
        else:
            self.player_state = "pause"
        self.doc.call_doc_observers()

    def stop_animation(self):
        self.player_state = "stop"

    def player_next(self, use_lightbox=False):
        prev_idx = self.timeline.idx
        if self.timeline.has_next():
            self.timeline.goto_next()
        else:
            self.timeline.select(self.timeline.get_first())
        if use_lightbox:
            self.update_opacities()
        else:
            self.change_visible_frame(prev_idx, self.timeline.idx)

    def toggle_key(self, lidx=None, idx=None):
        if lidx is None:
            lidx = self.timeline.layer_idx
        if idx is None:
            idx = self.timeline.idx
        if idx not in self.timeline[lidx]:
            self.doc.do(anicommand.AddFrame(self.doc, lidx, idx, True))
        frame = self.timeline[lidx][idx]
        self.doc.do(anicommand.ToggleKey(self.doc, frame))

    def toggle_skip_visible(self):
        if lidx is None:
            lidx = self.timeline.layer_idx
        if idx is None:
            idx = self.timeline.idx
        if idx not in self.timeline[lidx]:
            self.doc.do(anicommand.AddFrame(self.doc, lidx, idx, True))
        frame = self.timeline[lidx][idx]
        self.doc.do(anicommand.ToggleSkipVisible(self.doc, frame))

    def previous_frame(self, with_cel=False):
        if self.timeline.idx == 0: return
        self.select(self.timeline.idx - 1)

    def next_frame(self, with_cel=False):
        self.select(self.timeline.idx + 1)

    def previous_keyframe(self):
        new = self.timeline.goto_previous_key()
        cel = self.timeline.layer.cel_at(self.timeline.idx)
        if cel is not None:
            layer_idx = self.doc.layers.index(cel)
            self.doc.layer_idx = layer_idx
        self.update_opacities()
        if new: self.cleared = True
        self.doc.call_doc_observers()

    def next_keyframe(self):
        new = self.timeline.goto_next_key()
        cel = self.timeline.layer.cel_at(self.timeline.idx)
        if cel is not None:
            layer_idx = self.doc.layers.index(cel)
            self.doc.layer_idx = layer_idx
        self.update_opacities()
        if new: self.cleared = True
        self.doc.call_doc_observers()
    
    def change_description(self, new_description, frame=None):
        if frame is None: frame = self.timeline.get_selected()
        self.doc.do(anicommand.ChangeDescription(self.doc, frame, self.timeline.layer_idx, self.timeline.idx, new_description))
    
    def add_cel(self, lyr=None, frame=None):
        if lyr is None: lyr = self.timeline.layer_idx
        if frame is None: frame = self.timeline.idx
        if self.timeline[lyr][frame].cel is not None:
            return
        self.doc.do(anicommand.AddFrame(self.doc, lyr, frame))

    def remove_frame(self, lyr=None, frame=None):
        if lyr is None: lyr = self.timeline.layer_idx
        if frame is None: frame = self.timeline.idx
        self.doc.do(anicommand.RemoveFrame(self.doc, frame, lyr))

    def move_frame(self, frame, amount):	#@TODO: add to undo stack
        self.timeline.layer.insert(frame+amount,self.timeline.layer.pop(frame))
        self.sort_layers()
        self.doc.call_doc_observers()

    def move_layer(self, layer, amount):	#@TODO: add to undo stack
        self.timeline.insert_layer(layer+amount,self.timeline.pop(layer))
        self.sort_layers()
        self.doc.call_doc_observers()

    def select(self, idx):
        if self.timeline.idx != idx:
            self.doc.do(anicommand.SelectFrame(self.doc, idx))
            self.sort_layers()

    def select_layer(self, idx):
        if self.timeline.layer_idx != idx:
            self.doc.do(anicommand.SelectAnimationLayer(self.doc, idx))

    def previous_layer(self):
        self.select_layer(self.timeline.layer_idx - 1)

    def next_layer(self):
        self.select_layer(self.timeline.layer_idx + 1)

    def add_layer(self, idx=None):
        self.doc.do(anicommand.InsertLayer(self.doc, idx))

    def remove_layer(self, idx=None):
        self.doc.do(anicommand.RemoveLayer(self.doc, idx))

    def can_merge(self):
        return self.timeline.layer_idx < len(self.timeline) - 1

    def merge_layer_down(self):
        assert self.timeline.layer_idx < len(self.timeline) - 1
        top = self.timeline.layer
        bottom = self.timeline[self.timeline.layer_idx + 1]
        self.doc.do(anicommand.MergeAnimatedLayers(self.doc, (top, bottom)))

    def duplicate_layer(self):
        self.doc.do(anicommand.DuplicateAnimatedLayer(self.doc))

    def set_layer_opacity(self, opac):		#@TODO: add to command stack
        self.timeline.layer.opacity = opac
        self.update_opacities()

    def set_layer_composite(self, comp):	#@TODO: add to command stack
        self.timeline.layer.composite = comp
        for frame in self.timeline.layer:
            f = self.timeline.layer[frame]
            if f.cel:
                f.cel.compositeop = comp
        self.doc.call_doc_observers()

    def sort_layers(self):
        #@TODO: remove unneeded stacks
        #@TODO: make another method to pull the active cels to separate group
        layers = self.doc.layer_stack
        #new_order = self.timeline.get_order(layers)
        new_order = self.timeline.get_effective_paths()
        
        def get_layer_list():
            items = list(layers)
            frames = [y[2] for y in new_order]
            while len(items) > 0:
                item = items.pop(0)
                try:
                    items.extend(list(item))
                except TypeError:
                    if item not in frames:
                        yield item

        extra = [x for x in get_layer_list()]
        extra_order = []
        if len(extra) > 0:
            #if there are unanimated layers, put them on top and shuffle everything else down
            for ne, e in enumerate(extra):
                extra_order.append(((0,ne), None, e))
            new_order, tmp_order = [], new_order
            for pl, nl, l in tmp_order:
                path = (pl[0] + 1,) + pl[1:]
                new_order.append((path, nl, l))

        selection = self.doc.layer_stack.current
        changed = True
        while changed:
            changed = False
            for pl, nl, src in new_order + extra_order:
                src_path = layers.deepindex(src)
                tar_path = pl
                if src_path != tar_path:
                    changed = True
                    affected = []
                    tar_parent = layers.deepget(tar_path[:-1])
                    parent_exists = isinstance(tar_parent, layer.LayerStack)
                    #make placeholder
                    if src_path != None:
                        placeholder = layer.PlaceholderLayer(name="moving")
                        src_parent = layers.deepget(src_path[:-1])
                        src_index = src_path[-1]
                        src_parent[src_index] = placeholder
                        affected.append(src)
                    else:
                        placeholder = None

                    tar_parent = layers.deepget(tar_path[:-1])
                    #do the move
                    if parent_exists:
                        tar_index = tar_path[-1]
                        tar_parent.insert(tar_index, src)
                    elif tar_parent is None:
                        #make parent if it doesnt exist
                        parent = layer.LayerStack()
                        tar_gparent = layers.deepget(tar_path[:-2])
                        tar_gparent.append(parent)
                        parent.append(src)
                    else:
                        #another layer is where the parent should be, move it
                        tar_parent_index = tar_path[-2]
                        tar_gparent = layers.deepget(tar_path[:-2])
                        parent = layer.LayerStack()
                        tar_gparent[tar_parent_index] = parent
                        parent.append(src)
                        parent.append(tar_parent)
                        affected.append(tar_parent)
                    
                    # Remove placeholder
                    if placeholder:
                        layers.deepremove(placeholder)

        # Rename layers as necessary
        par_name = lambda i, n: n and str(n) or _("Layer ") + str(i+1)
        for pl, [a, f], l in new_order:
            #rename this layer if need be
            placeholder = layer.PlaceholderLayer(name="moving")
            parent = layers.deepget(pl[:-1])
            index = pl[-1]
            cel = parent.pop(index)
            new_name = self.generate_layername(f, self.timeline[a][f].description)
            cel.name = new_name		#@TODO: redo paintinglayer naming
            parent.insert(index, cel)

            #rename parent if need be
            if self.timeline[a].stack != pl[:-1]:
                parent.name = par_name(a, self.timeline[a].name)
                self.timeline[a].stack = pl[:-1]
        if len(extra) > 0:
            layers.deepget((0,)).name = _("Sketches")

        # Issue redraws
        layers.set_current_path(layers.canonpath(path=layers.deepindex(selection)))
        #redraw_bboxes = [a.get_full_redraw_bbox() for a in affected]
        #self._notify_canvas_observers(redraw_bboxes)


    def change_opacityfactor(self, opacityfactor):
        self.timeline.set_opacityfactor(opacityfactor)
        self.update_opacities()

    def toggle_opacity(self, attr, is_active):
        self.timeline.setup_active_cels({attr: is_active})
        self.update_opacities()
    
    def toggle_nextprev(self, nextprev, is_active):
        self.timeline.setup_nextprev({nextprev: is_active})
        self.update_opacities()
    
    def can_cutcopy(self):
        if self.timeline.idx not in self.timeline.layer: return False
        frame = self.timeline.get_selected()
        return frame.cel is not None

    def cutcopy_cel(self, edit_operation):
        frame = self.timeline.get_selected()
        self.doc.ani.edit_operation = edit_operation
        self.doc.ani.edit_frame = frame
        self.doc.call_doc_observers()

    def can_paste(self):
        if self.edit_frame is None: return False
        if self.timeline.idx not in self.timeline.layer: return True
        frame = self.timeline.get_selected()
        return self.edit_frame != frame and \
               frame.cel == None

    def paste_cel(self):
        frame = self.timeline.get_selected()
        self.doc.do(anicommand.PasteCel(self.doc, frame))

    def merge(self, layers):
        merge_layers = []
        for l in layers[::-1]:
            if l is None: continue
            vis, opa = l.visible, l.opacity
            idx = self.timeline.cel_index(l)
            l.visible, l.opacity = self.timeline[idx[0]].visible, self.timeline[idx[0]].opacity
            p = self.doc.layer_stack.deepindex(l)
            if p is None: continue
            lyr = self.doc.layer_stack.layer_new_normalized(p)
            merge_layers.append(lyr)
            l.visible, l.opacity = vis, opa
        # Build output strokemap, determine set of data tiles to merge
        dstlayer = layer.PaintingLayer()
        tiles = set()
        strokes = []
        for lyr in merge_layers:
            tiles.update(lyr.get_tile_coords())
            assert isinstance(lyr, layer.PaintingLayer) and not lyr.locked
            dstlayer.strokes[:0] = lyr.strokes
        # Build a (hopefully sensible) combined name too
        names = [l.name for l in reversed(merge_layers)
                 if l.has_interesting_name()]
        #TRANSLATORS: name combining punctuation for Merge Down
        name = _(u", ").join(names)
        if name != '':
            dstlayer.name = name
        # Rendering loop
        N = tiledsurface.N
        dstsurf = dstlayer._surface
        for tx, ty in tiles:
            with dstsurf.tile_request(tx, ty, readonly=False) as dst:
                for lyr in merge_layers:
                    lyr.composite_tile(dst, True, tx, ty, mipmap_level=0)
        return dstlayer

