# This file is part of MyPaint.
# Based on code originally by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation

DEFAULT_OPACITIES = {
    'cel': 1./2, # The immediate next and previous cels
    'key': 1./2, # The cel keys that are after and before the current cel
    'inbetweens': 1./4, # The cels that are between the keys mentioned above
    'other keys': 1./4, # The other keys
    'other': 0,    # The rest of the cels
}

DEFAULT_ACTIVE_CELS = {
    'cel': True,
    'key': True,
    'inbetweens': True,
    'other keys': True,
    'other': False,
}

DEFAULT_NEXTPREV = {
    'next': True,
    'previous': True,
}

class Frame(object):
    def __init__(self, is_key=False, skip_visible=False, cel=None, description=''):
        self.is_key = is_key
        self.description = description
        self.cel = cel
        self.skip_visible = skip_visible

    def __repr__(self):
        return 'Frame(is_key=' + str(self.is_key) + ', skip_visible=' + str(self.skip_visible) + ', cel=' + str(self.cel) + ', description="' + self.description + '")'

    def __str__(self):
        string = '<Frame:'
        if self.is_key: string += ' KEY'
        if self.skip_visible: string += ' skip-visible'
        if self.cel is not None: string += ' ' + str(self.cel)
        string += ' "' + self.description + '">'
        return string

    def set_key(self):
        self.is_key = True

    def unset_key(self):
        self.is_key = False

    def toggle_key(self):
        self.is_key = not self.is_key

    def toggle_skip_visible(self):
        self.skip_visible = not self.skip_visible

    def add_cel(self, cel):
        self.cel = cel

    def remove_cel(self):
        self.cel = None

    def has_cel(self):
        return self.cel is not None

    def is_needed(self):
        if self.is_key or self.skip_visible:
            return True
        if self.cel is not None:
            return True
        if self.description != "":
            return True
        return False

class FrameList(dict):
    """
    list of the frames making up the animation.
    now in a dictionary, so only the necessary frames actually exist.

    """
    def __init__(self, description='Untitled layer', **kargs):
        self.description = description
        self.visible = True
        self.opacity = 1.0
        self.locked = False
        self.composite = 'svg:src-over'
        for k in kargs:
            self[k] = kargs[k]

    def __len__(self):
        try:
            return self.get_last() - self.get_first() + 1
        except:
            return 0

    def __getitem__(self, key):
        """
        gets the items at requested key(s).
        if specifically requested frames dont exist, creates them.

        """
        if type(key) is type(None): return None
        if type(key) is int:
            return self.setdefault(key, Frame())
        if type(key) is slice: key = [key]
        items = []
        for k in key:
            if type(k) is int:
                items.append(self.setdefault(k, Frame()))
            elif type(k) is slice:
                start, stop, step = k.start, k.stop, k.step
                if start is None:
                    start = self.get_first()
                if stop is None:
                    stop = self.get_last()
                if step is None:
                    step = 1
                if start is None or stop is None: continue
                for i in (item for item in range(start, stop + 1, step) if item in self):
                    items.append(self.setdefault(i, Frame()))
        return items

    def __iter__(self):
        return self.keys().__iter__()

    def enumerate(self):			#temporary
        enum = []
        start = self.get_first()
        for f in self:
            enum.append((f - start, self[f]))
        return sorted(enum)

    def cleanup(self):
        """
        checks which frames can be safely removed, and removes them.

        """
        for f in self:
            if self[f] is None or not self[f].is_needed():
                self.pop(f)

    def get_first(self):
        try:
            return min(self)
        except:
            return None

    def get_last(self):
        try:
            return max(self)
        except:
            return None

    def index(self, value):
        for i in self:
            if self[i] == value:
                return i
        return None

    def key_range(self, idx, step, end=None):
        if step == -1:
            if end is None:
                return sorted(filter(lambda item: item < idx, self))[::-1]
            return sorted(filter(lambda item: end <= item < idx, self))[::-1]
        elif step == 1:
            if end is None:
                return sorted(filter(lambda item: item > idx, self))
            return sorted(filter(lambda item: end >= item > idx, self))
        return []

    def change_keys(self, amount, start=None, end=None):
        """
        Modifies the keys between start and end by amount

        """
        tmp = {}
        for n in self:
            if n >= start and (n <= end or end is None):
                tmp[n + amount] = self.pop(n)
        self.update(tmp)

    def remove_frames(self, idx, length=1):
        """
        Remove the frame(s) at idx.

        """

        removed = []
        for n in range(idx, idx + length):
            removed.append(self.pop(n, None))
        self.change_keys(-length, idx)
        return removed

    def insert_frames(self, idx, frames):
        """
        Inserts frames at idx, moving everything after down.

        """
        if type(frames) is type(None): frames = 1
        if type(frames) is int:
            length = frames
            frames = []
            for f in range(length):
                frames.append(Frame())
        self.change_keys(len(frames), idx)
        for i in range(len(frames)):
            self[idx + i] = frames[i]

    def cel_at(self, n):
        """
        Return the cel at the nth frame.

        """
        for i in sorted(self)[::-1]:
            if i > n: continue
            if self[i].cel is not None:
                return self[i].cel
        return None

    def get_all_cels(self):
        cels = []
        for f in self.values():
            if f.cel is not None and f.cel not in cels:
                cels.append(f.cel)
        return cels

    def get_all_cel_keys(self):
        keys = []
        for f in self:
            if self[f].cel is not None and f not in keys:
                keys.append(f)
        return keys


class TimeLine(list):
    """
    the timeline containing all of the data for the animation.
    has no set start, end, or length.
    each animated layer is a framelist.

    """
    def __init__(self, opacities=None, active_cels=None, nextprev=None):
        self.idx = 0
        self.layer_idx = 0
        if opacities is None:
            opacities = {}
        self.opacities = dict(DEFAULT_OPACITIES)
        if active_cels is None:
            active_cels = {}
        self.active_cels = dict(DEFAULT_ACTIVE_CELS)
        if nextprev is None:
            nextprev = {}
        self.setup_opacities(opacities)
        self.setup_active_cels(active_cels)
        self.nextprev = dict(DEFAULT_NEXTPREV)
        self.nextprev.update(nextprev)

    def setup_opacities(self, opacities):
        self.opacities.update(opacities)
        self.convert_opacities()

    def set_opacityfactor(self, factor):
        self.convert_opacities(factor)

    def convert_opacities(self, factor=1):
        self.converted_opacities = {}
        for k, v in self.opacities.items():
            self.converted_opacities[k] = v * factor

    def setup_active_cels(self, active_cels):
        self.active_cels.update(active_cels)

    def cleanup(self):
        for layer in self:
            layer.cleanup()

    def check_key(self, key, layer=None):
        if layer is None: layer = self.layer
        if key < self.idx:
            return key >= layer.get_first()
        elif key > self.idx:
            return key <= layer.get_last()
        return True

    def get_first(self):
        first = self.layer.get_first()
        for layer in self:
            fi = layer.get_first()
            if fi < first and fi is not None: first = fi
        return first

    def get_last(self):
        last = None
        for layer in self:
            la = layer.get_last()
            if la > last: last = la
        return last

    def check(self):
        self.layer[self.idx]

    def get_selected(self):
        return self[self.layer_idx][self.idx]

    def select(self, n):
        self.idx = n
        self.check()

    def goto_next(self, with_cel=False):
        if with_cel:
            next_frame = self.get_next_cel()
            if next_frame is None:
                raise IndexError("There is no next frame with cel.")
                return
            else:
                new = not self.check_key(next_frame)
                self.idx = next_frame
                self.check()
                return new
        new = not self.check_key(self.idx + 1)
        self.idx += 1
        self.check()
        return new

    def goto_previous(self, with_cel=False):
        if with_cel:
            prev_frame = self.get_previous_cel()
            if prev_frame is None:
                raise IndexError("There is no previous frame with cel.")
                return
            else:
                new = not self.check_key(prev_frame)
                self.idx = prev_frame
                self.check()
                return new
        new = not self.check_key(self.idx - 1)
        self.idx -= 1
        self.check()
        return new

    def has_next(self, with_cel=False):
        if with_cel:
            return self.get_next_cel() is not None
        if self.idx >= self.get_last():
            return False
        return True

    def has_previous(self, with_cel=False):
        if with_cel:
            return self.get_previous_cel() is not None
        if self.idx <= self.get_first():
            return False
        return True

    def get_next_key(self, layer=None, recursive=True):
        if layer is None: layer = self.layer_idx
        for f in self[layer].key_range(self.idx, 1):
            if self[layer][f].is_key and not self[layer][f].skip_visible:
                return f
        if recursive:
            keys = []
            for l in filter(lambda item: item != layer, self):
                for f in l.key_range(self.idx, 1):
                    if l[f].is_key and not l[f].skip_visible:
                        keys.append(f)
            if len(keys) > 0: return min(keys)
        return None

    def get_previous_key(self, layer=None, recursive=True):
        if layer is None: layer = self.layer_idx
        for f in self[layer].key_range(self.idx, -1):
            if self[layer][f].is_key and not self[layer][f].skip_visible:
                return f
        if recursive:
            keys = []
            for l in filter(lambda item: item != layer, self):
                for f in l.key_range(self.idx, -1):
                    if l[f].is_key and not l[f].skip_visible:
                        keys.append(f)
            if len(keys) > 0: return max(keys)
        return None

    def goto_next_key(self):
        f = self.get_next_key()
        if f is None:
            raise IndexError("Trying to go to nonexistent next keyframe.")
        else:
            new = not self.check_key(f)
            self.idx = f
            self.check()
            return new

    def goto_previous_key(self):
        f = self.get_previous_key()
        if f is None:
            raise IndexError("Trying to go to nonexistent previous keyframe.")
        else:
            new = not self.check_key(f)
            self.idx = f
            self.check()
            return new

    def has_next_key(self): 
        if self.get_next_key() is None:
            return False
        return True

    def has_previous_key(self): 
        if self.get_previous_key() is None:
            return False
        return True

    def cels_at(self, n):
        """
        Return the cels at the nth frame.

        """
        cels = []
        for layer in self:
            cel = layer.cel_at(n)
            if cel is not None:
                cels.append(cel)
        return cels

    def get_previous_cel(self, layer=None):
        """
        Return the previous frame with a cel that is different than
        the cel of the current frame.

        """
        if layer is None: layer = self.layer_idx
        cur_cel = self[layer].cel_at(self.idx)
        if not cur_cel:
            return None
        for f in self[layer].key_range(self.idx, -1):
            frame = self[layer][f]
            if frame.cel is not None and frame.cel != cur_cel and not frame.skip_visible:
                return f
        return None

    def get_next_cel(self, layer=None):
        """
        Return the next frame with a cel that is different than the
        cel of the current frame.

        """
        if layer is None: layer = self.layer_idx
        cur_cel = self[layer].cel_at(self.idx)
        for f in self[layer].key_range(self.idx, 1):
            frame = self[layer][f]
            if frame.cel is not None and frame.cel != cur_cel and not frame.skip_visible:
                return f
        return None

    def get_all_cels(self):
        cels = []
        for f in self:
            for c in f.get_all_cels():
                if c not in cels:
                    cels.append(c)
        return cels


    @property
    def layer(self):
        return self[self.layer_idx]

    @layer.setter
    def layer(self, value):
        if type(value) == int:
            self.select_layer(value)
        elif value in self:
            self.layer_idx = self.index(value)
        else:
            self.append_layer(value)
            self.layer_idx = len(self) - 1

    @layer.deleter
    def layer(self):
        self.remove_layer()

    def append_layer(self, layer=None, description="Untitled layer", **kargs):
        if type(layer) is FrameList:
            self.append(layer)
        elif layer is None:
            self.append(FrameList(description, **kargs))
        else:
            raise TypeError('append_layer() FrameList expected, got ' + str(type(layer)) + '.')

    def remove_layer(self, at_end=False):
        if at_end:
            idx = len(self) - 1
        else:
            idx = self.layer_idx
        removed = self.pop(idx)
        if self.layer_idx > len(self) - 1:
            self.layer_idx = len(self) - 1
        return removed

    def insert_layer(self, frames=None, idx=None):
        if idx is None:
            idx = self.layer_idx
        if frames is None:
            frames = FrameList(len(self.layer))
        self.insert(idx, frames)

    def select_layer(self, n):
        if not 0 <= n <= len(self)-1:
            raise IndexError('Trying to select nonexistent layer.')
            return
        self.layer_idx = n

    def goto_next_layer(self):
        if not self.has_next_layer():
            print 'IndexError: Trying to go to next at the last layer.'
        else:
            self.layer_idx += 1
            self.check()

    def goto_previous_layer(self):
        if not self.has_previous_layer():
            print 'IndexError: Trying to go to previous at the first layer.'
        else:
            self.layer_idx -= 1
            self.check()

    def has_next_layer(self):
        if self.layer_idx == len(self)-1:
            return False
        return True

    def has_previous_layer(self):
        if self.layer_idx == 0:
            return False
        return True

    def get_list(self):
        matrix = []
        first, last = self.get_first(), self.get_last()
        if first is None or last is None: first, last = 0, 0
        for i in range(first, last + 1):
            matrix.append([i - first])
            for layer in self:
                if i in layer:
                    matrix[i - first].append(layer[i])
                else:
                    matrix[i - first].append(None)
        return matrix

    def get_opacities(self):
        """
        Return a map of cels and the opacity they should have.

        To draw the current cel, the artist has to see it 100%
        opaque, and they may want to see the neighbour cels
        semi-transparent.

        """
        opacities = {}

        def get_opa(nextprev, c, idx):
            can_nextprev = self.nextprev[nextprev]
            if can_nextprev and self.active_cels[c]:
                try:
                    return round(self.converted_opacities[c] * (abs(self.idx - idx) ** -.1), 4)
                except ZeroDivisionError:
                    return self.converted_opacities[c]
            return 0

        # current cel, always full opacity:
        for cel in self.cels_at(self.idx):
            if cel is not None: opacities[cel] = 1

        for l_idx, layer in enumerate(self):

            # explicit skip of cels:
            for f in layer.get_all_cel_keys():
                if layer[f].skip_visible and layer[f].cel:
                    opacities[layer[f].cel] = 0

            # next:
            next = self.get_next_cel(l_idx)
            if layer[next] and layer[next].cel not in opacities:
                opacities[layer[next].cel] = get_opa('next', 'cel', next)

            # previous:
            prev = self.get_previous_cel(l_idx)
            if layer[prev] and layer[prev].cel not in opacities:
                opacities[layer[prev].cel] = get_opa('previous', 'cel', prev)

            # previous key:
            prevkey = self.get_previous_key(l_idx, False)
            if prevkey:
                if layer[prevkey].cel and layer[prevkey].cel not in opacities:
                    opacities[layer[prevkey].cel] = get_opa('previous', 'key', prevkey)
            else:
                prevkey = layer.get_first()

            # next key:
            nextkey = self.get_next_key(l_idx, False)
            if nextkey:
                if layer[nextkey].cel and layer[nextkey].cel not in opacities:
                    opacities[layer[nextkey].cel] = get_opa('next', 'key', nextkey)
            else:
                nextkey = layer.get_last()

            def has_cel(f):
                return layer[f].cel is not None

            # inbetweens:
            next_inbetweens_range = layer.key_range(self.idx, 1, nextkey)
            for f in filter(has_cel, next_inbetweens_range):
                if layer[f].cel not in opacities.keys():
                    opacities[layer[f].cel] = get_opa('next', 'inbetweens', f)
            prev_inbetweens_range = layer.key_range(self.idx, -1, prevkey)
            for f in filter(has_cel, prev_inbetweens_range):
                if layer[f].cel not in opacities.keys():
                    opacities[layer[f].cel] = get_opa('previous', 'inbetweens', f)
            del next_inbetweens_range, prev_inbetweens_range

            # frames outside immediate keys:
            next_outside_range = layer.key_range(nextkey, 1)
            for f in filter(has_cel, next_outside_range):
                cel = layer[f].cel
                if cel not in opacities.keys():
                    if layer[f].is_key:
                        opacities[cel] = get_opa('next', 'other keys', f)
                    else:
                        opacities[cel] = get_opa('next', 'other', f)

            prev_outside_range = layer.key_range(prevkey, -1)
            for f in filter(has_cel, prev_outside_range):
                cel = layer[f].cel
                if cel not in opacities.keys():
                    if layer[f].is_key:
                        opacities[cel] = get_opa('previous', 'other keys', f)
                    else:
                        opacities[cel] = get_opa('previous', 'other', f)

            del next_outside_range, prev_outside_range

        visible = {}
        for cel, opa in opacities.items():
            visible[cel] = True
            if opa == 0:
                visible[cel] = False

        return opacities, visible

    def get_order(self, old_order):
        new_order = self.get_all_cels()
        if len(old_order) > len(new_order):
            extra = [elem for elem in old_order if elem not in new_order]
            new_order.extend(extra)
        return new_order[::-1]

