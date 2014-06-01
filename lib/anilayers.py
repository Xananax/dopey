# This file is part of MyPaint.

from framelist import FrameList

DEFAULT_NEXTPREV = {
    'next': True,
    'previous': True,
}

class AnimationLayerList(list):
    """
    list of animated layers, each layer is a FrameList

    """
    def __init__(self, nextprev=None):
        self.idx = 0
        if nextprev is None:
            nextprev = {}
        self.nextprev = dict(DEFAULT_NEXTPREV)
        self.nextprev.update(nextprev)


    def append_layer(self, length, doc, opacities=None, active_cels=None, nextprev=None, init=True):
        self.append(FrameList(length, doc, opacities, active_cels, nextprev, init))

    def remove_layer(self, at_end=False):
        if at_end:
            idx = len(self) - 1
        else:
            idx = self.idx
        removed = self.pop(idx)
        if self.idx > len(self) - 1:
            self.idx = len(self) - 1
        return removed

    def insert_layer(self, doc, frames=None, idx=None):
        if idx is None:
            idx = self.idx
        if frames is None:
            frames = FrameList(len(self[self.idx]), doc)
        else:
            for c in frames.get_all_cels():
                doc.layers.insert(0, c)
        self.insert(idx, frames)

    def get_selected_layer(self):
        return self[self.idx]

    def select_layer(self, n):
        if not 0 <= n <= len(self)-1:
            print "IndexError: Trying to select nonexistent layer."
            return
        self.idx = n

    def goto_next_layer(self):
        if not self.has_next():
            print "IndexError: Trying to go to next at the last layer."
        else:
            self.idx += 1

    def goto_previous_layer(self):
        if not self.has_previous():
            print "IndexError:Trying to go to previous at the first layer."
        else:
            self.idx -= 1

    def has_next(self):
        if self.idx == len(self)-1:
            return False
        return True

    def has_previous(self):
        if self.idx == 0:
            return False
        return True

    def get_opacities(self):
        opacities = {}
        visible = {}
        for s in self:
            opac, visi = s.get_opacities(self[self.idx].idx)
            opacities.update(opac)
            visible.update(visi)
        return opacities, visible

    def get_order(self, old_order):
        new_order = []
        for i in range(len(self)):
            new_order.extend(self[i].get_all_cels())
        if len(old_order) > len(self):
            extra = [elem for elem in old_order if elem not in new_order]
            new_order.extend(extra)
        return new_order[::-1]
