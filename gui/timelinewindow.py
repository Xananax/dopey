#@TODO  This is a huge mess, lots of things can be removed or simplified..
#             and a lot of other things should be renamed and tweaked

from lib.helpers import escape


from gi.repository import Gtk, GObject
from gi.repository import Gdk, GdkPixbuf

import cairo
import textwrap

import anidialogs
from layerswindow import stock_button
from gettext import gettext as _

from lib.timeline import DEFAULT_ACTIVE_CELS
        
        
class LayerWidget(Gtk.DrawingArea):
    __gtype_name__ = 'LayerWidget'

    def __init__(self, timeline, app):
        Gtk.Widget.__init__(self)
        self.ani = app.doc.ani.model
        self.timeline = timeline
        self.move_layer = False
        self.close_box_list = []

        self.set_size_request(100, 25)
        self.set_has_tooltip(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK )
        self.connect('button-press-event', self.clic)
        self.connect('motion-notify-event', self.move)
        self.connect('button-release-event', self.release)
        self.connect('query-tooltip', self.tooltip)
        self.timeline.connect('update', self.update)
        
        
    def update(self, *args):
        self.queue_draw()
    
    def tooltip(self, item, x, y, keyboard_mode, tooltip):
        idx = self.timeline.convert_layer(x)
        if not 0 <= idx < len(self.timeline.data): return False
        c = self.close_box_list[idx]
        if c[0] < x < c[0]+c[2] and c[1] < y < c[1]+c[3]:
            text = _("Remove Layer")
        else:
            text = self.timeline.data[idx].description
        tooltip.set_text(text)
        return True
        
    def resize(self, arg, w, h):
        ww, wh = self.get_allocation().width, self.get_allocation().height
        if ww < w:
            self.set_size_request(w, wh)
            self.queue_draw()
    
    def draw_button(self, cr, x, y, type='close', sz=12):
        cr.rectangle(x, y, sz, sz)
        cr.set_source_rgb(0, 0, 0)
        cr.fill()
        cr.rectangle(x+1, y+1, sz-2, sz-2)
        
        cr.set_source_rgb(1, .67, .67)
        self.close_box_list.append((x, y, sz, sz))

        cr.fill()
        
    def do_draw(self, cr):
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
        # frame size
        fw, fwa = self.timeline.frame_width, self.timeline.frame_width_active
        self.close_box_list = []
        
        cr.rectangle(0, 1, 1, wh-1)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
        cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        th, tw = 9, 6
        for nl, l in enumerate(self.timeline.data):
            if nl > self.timeline.data.layer_idx:
                x = nl * fw + fwa - fw
            else:
                x = nl * fw
            if nl == self.timeline.data.layer_idx:
                cr.rectangle(x+1, 1, fwa-1, wh)
            else:
                cr.rectangle(x+1, 1, fw-1, wh)
            if self.timeline.data.layer_idx == nl:
                cr.set_source_rgb(0.9, 0.9, 0.9)
            else:
                cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.fill();
            if nl == self.timeline.data.layer_idx:
                self.draw_button(cr, x+fwa-11, 0)
                cr.rectangle(x+fwa, 1, 1, wh-1)
                cr.rectangle(x+1, 0, fwa-1, 1)
                cr.set_font_size(10)
                text = textwrap.wrap(l.description, fwa//tw)
                lines = int(wh // th)
                cr.set_source_rgb(0, 0, 0)
                for nt, t in enumerate(text):
                    dimx = cr.text_extents(t)[2]
                    if nt > lines - 1: break
                    if len(text) == 1:
                        cr.move_to(x + (fwa - dimx)//2, (th + wh)//2)
                    else:
                        cr.move_to(x + (fwa - dimx)//2, th + nt*th)
                    if nt == lines - 1 and len(text) > lines:
                        cr.show_text(t[:-2]+'...')
                    else:
                        cr.show_text(t)
            else:
                self.draw_button(cr, x+fw-11, 0)
                cr.rectangle(x+fw, 1, 1, wh-1)
                cr.rectangle(x+1, 0, fw-1, 1)
            cr.set_source_rgb(0, 0, 0)
            cr.fill();
    
    def get_in_list(self, l, x, y):
        try:
            c = self.close_box_list[l]
            if c[0] < x < c[0]+c[2] and c[1] < y < c[1]+c[3]:
                self.ani.remove_layer(l)
                return True
        except:
            return False
    
    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            layer = self.timeline.convert_layer(event.x)
            if self.get_in_list(layer, event.x, event.y):
                return True
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                if 0 <= layer < len(self.timeline.data):
                    description = anidialogs.ask_for(self, _("Change description"),
                        _("Description"), self.timeline.data[layer].description)
                    if description:
                        self.timeline.data[layer].description = description
                        self.timeline.emit('update')
                else:
                    self.ani.add_layer(len(self.timeline.data))
                    self.timeline.data.layer_idx = len(self.timeline.data) - 1
                    self.timeline.emit('update')
                self.move_layer = False
            else:
                if 0 <= layer < len(self.timeline.data):
                    for l, i in enumerate(self.close_box_list):
                        if i[0] < event.x < i[0]+i[2] and i[1] < event.y < i[1]+i[3]:
                            return True
                self.move_layer = layer
                self.timeline.emit('change_selected_layer', layer)
        return True
        
    def move(self, widget, event):
        l = self.timeline.convert_layer(event.x)
        sl = self.move_layer
        if sl is not False and sl < len(self.timeline.data):
            if l == sl:
                return
            while l > sl and sl < len(self.timeline.data) - 1:
                self.ani.move_layer(sl, 1)
                sl += 1
            while l < sl and sl > 0:
                self.ani.move_layer(sl, -1)
                sl -= 1
            self.move_layer = sl
            self.timeline.emit('change_selected_layer', sl)

    def release(self, widget, event):
        self.move_layer = False
        
        
class FrameWidget(Gtk.DrawingArea):
    __gtype_name__ = 'FrameWidget'

    def __init__(self, timeline, app):
        Gtk.Widget.__init__(self)
        self.app = app
        self.timeline = timeline

        self.set_size_request(10, 600)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK )
        self.connect('button-press-event', self.clic)
        self.connect('motion-notify-event', self.move)
        self.connect('button-release-event', self.release)
        self.timeline.connect('update', self.update)
        
    def update(self, *args):
        self.queue_draw()
        
    def resize(self, arg, w, h):
        ww, wh = self.get_allocation().width, self.get_allocation().height
        if wh < h:
            self.set_size_request(ww, h)
            self.queue_draw()
        
    def do_draw(self, cr):
        # widget size			#@TODO: kinda hackish fix for wrong size
        ww, wh = self.timeline.scroll_frame.get_allocation().width-9, \
                 self.get_allocation().height
        # frame size
        fw, fh = self.timeline.frame_width, self.timeline.frame_height
        m = self.timeline.margin_top
        # background
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.rectangle(1, 1, ww-1, wh-2)
        cr.fill();
        # border
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(1, 0, ww, 1)
        cr.rectangle(0, 1, 1, wh)
        cr.rectangle(1, wh-1, ww, 1)
        cr.fill();
        # current frame
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.rectangle(1, self.timeline.data.idx*fh+m, ww, fh)
        cr.fill();
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, self.timeline.data.idx*fh+m, ww, 1)
        cr.rectangle(0, self.timeline.data.idx*fh+fh+m, ww, 1)
        cr.fill();
        
        fps = float(self.timeline.data.fps)
        div_li = self.timeline.get_divisions()
        div = (1, True)
        for li in reversed(div_li + [int(fps)]):
            if 9 * li < fps * fh:
                div = (li, True)
                break
        if div == (1, True):
            div = (int(9 / (fps * fh)) + 1, False)

        cr.set_font_size(10)
        cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        for f, i in enumerate(range(0, wh, fh), 1):
            cr.rectangle(ww-2, i+m, 6, 1)
            dimx = cr.text_extents(str(f))[2]
            if f % fps == 0:
                if div[1] == False and (f/fps) % div[0]: continue
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                dimx = cr.text_extents(str(f))[2]
                cr.move_to(ww-dimx-5, i+fh+m-(fh/4))
                cr.show_text(str(f))
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_NORMAL)
            elif div[1] == True and len(div_li) == 1:
                n = 2 ** ((8 - fh) / 4)
                o = 2 ** ((8 - fh) / 3)
                if f % (2**n) == 0 and o < f % fps < fps-o:
                    cr.move_to(ww-dimx-5, i+fh+m-(fh/4))
                    cr.show_text(str(f))
            elif div[1] == True:
                if f % (fps/div[0]) == 0:
                    cr.move_to(ww-dimx-5, i+fh+m-(fh/4))
                    cr.show_text(str(f))
        cr.fill();

    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self.timeline.emit('change_current_frame', 
                               int((event.y-1)/self.timeline.frame_height))
        return True
        
    def move(self, widget, event):
        self.timeline.emit('change_current_frame', 
                           int((event.y-1)/self.timeline.frame_height))

    def release(self, widget, event):
        pass
        
        
class TimelineWidget(Gtk.DrawingArea):
    __gtype_name__ = 'TimelineWidget'
    __gsignals__ = {
        'size_changed': (GObject.SIGNAL_RUN_FIRST, None,(int, int))
    }
    def __init__(self, timeline, app):
        Gtk.Widget.__init__(self)
        self.app = app
        self.ani = app.doc.ani.model

        self.timeline = timeline

        self.set_has_tooltip(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect('button-press-event', self.clic)
        self.connect('motion-notify-event', self.move)
        self.connect('button-release-event', self.release)
        self.connect('query-tooltip', self.tooltip)
        self.timeline.connect('update', self.update)
        
        self.key_box_list = []
        self.close_box_list = []
        self.move_frame = False
        self.drag_scroll = False
        self.h = [0, 0]
        self.connect('show', self.resize)

    def update(self, *args):
        self.queue_draw()
    
    def tooltip(self, item, x, y, keyboard_mode, tooltip):
        l_idx = self.timeline.convert_layer(x)
        if not 0 <= l_idx < len(self.timeline.data): return False
        idx = int((y - self.timeline.margin_top) / self.timeline.frame_height)
        if idx not in self.timeline.data[l_idx]: return False
        if idx in self.close_box_list:
            c = self.close_box_list[l_idx][idx]
        else:
            c = (0,0,0,0)
        if idx in self.key_box_list:
            k = self.key_box_list[l_idx][idx]
        else:
            k = (0,0,0,0)
        if c[0] < x < c[0]+c[2] and c[1] < y < c[1]+c[3]:
            text = _("Remove Frame")
        elif k[0] < x < k[0]+k[2] and k[1] < y < k[1]+k[3]:
            text = _("Toggle Keyframe")
        else:
            text = self.timeline.data[l_idx][idx].description
        if text != '':
            tooltip.set_text(text)
            return True
        
    def resize(self, *args, **delay):
        fh = self.timeline.frame_height
        w = self.timeline.frame_width * (len(self.timeline.data) - 1) + \
                   self.timeline.frame_width_active + 8
        h = self.timeline.get_last() + (self.timeline.margin_top * 2) + 24
        ww, wh = self.get_allocation().width, self.get_allocation().height
        if ww != w or wh != h:
            self.set_size_request(w, h)
            self.emit('size_changed', w, h)
    
    def draw_button(self, cr, x, y, l, f, type='close', sz=12):
        cr.rectangle(x, y, sz, sz)
        cr.set_source_rgb(0, 0, 0)
        cr.fill()
        cr.rectangle(x+1, y+1, sz-2, sz-2)
        if type == 'key':
            cr.set_source_rgb(.9, .9, .14)
            self.key_box_list[l][f] = (x, y, sz, sz)
        else:
            cr.set_source_rgb(1, .67, .67)
            self.close_box_list[l][f] = (x, y, sz, sz)
        cr.fill()
        
    def do_draw(self, cr):
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
        # frame size
        fw, fwa, fh = self.timeline.frame_width, self.timeline.frame_width_active, \
                      self.timeline.frame_height
        m = self.timeline.margin_top
        cr.set_source_rgba(0, 0, 0, 0.1)
        cr.paint()
        # current frame
        cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.rectangle(0, self.timeline.data.idx*fh+m, ww, fh+1)
        cr.fill()
        # draw layers
        self.key_box_list = []
        self.close_box_list = []

        #lines marking seconds
        fps = self.timeline.data.fps
        div_li = self.timeline.get_divisions()[1:]

        for i in range(0, max(self.ani.timeline.get_length(), 
                       self.ani.timeline.idx, wh//fh) + fps, fps):
            y = i*fh+m
            cr.set_source_rgb(.74, .74, .74)
            for j in range(1, fps):
                cr.rectangle(0, y + j*fh, ww, 1)
            cr.fill()
            for li in reversed(div_li):
                col=.75 - (0.5/li)
                cr.set_source_rgb(col, col, col)
                for j in range(1, li):
                    cr.rectangle(0, y + j*fps/li*fh, ww, 1)
                cr.fill()
            cr.set_source_rgb(.2, .2, .2)
            cr.rectangle(0, y, ww, 2)
            cr.fill()


        for nl, l in enumerate(self.timeline.data):
            self.close_box_list.append({})
            self.key_box_list.append({})
            if nl > self.timeline.data.layer_idx:
                x = (nl - 1) * fw + fwa + 1
            else:
                x = nl * fw + 1
            lenn = self.ani.timeline.get_length()-1

            # between layer
            if nl == self.timeline.data.layer_idx:
                cr.rectangle(x+fwa-1, 0, 1, wh)
            else:
                cr.rectangle(x+fw-1, 0, 1, wh)
            cr.set_source_rgb(.2, .2, .2)
            cr.fill();

            cr.set_font_size(10)
            cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            th, tw = 10, 7

            for nf in l:
                y = nf*fh+m
                if nl == self.timeline.data.layer_idx:
                    if nf == self.timeline.data.idx:
                        cr.set_source_rgb(0.94, 0.94, 0.94)
                    else:
                        cr.set_source_rgb(0.87, 0.87, 0.87)
                    cr.rectangle(x, y, fwa - 1, fh)
                    cr.fill()
                    if l[nf].is_key:
                        cr.set_source_rgb(.95, .95, 0)
                        cr.rectangle(x, y, fwa-1, 5)
                        cr.rectangle(x, y+fh-5, fwa-1, 5)
                        cr.rectangle(x, y, 5, fh)
                        cr.rectangle(x+fwa-6, y, 5, fh)
                        cr.fill()
                    cr.set_source_rgb(0, 0, 0)
                    cr.rectangle(x, y, fwa, 1)
                    cr.rectangle(x, y+fh, fwa, 1)
                    text = textwrap.wrap(l[nf].description, fwa//tw)
                    lines = int(fh // th)
                    cr.set_source_rgb(0, 0, 0)
                    for nt, t in enumerate(text):
                        if nt > lines - 1:
                            break
                        elif nt == lines - 1 and len(text) > lines:
                            cr.move_to(x + 1, y + th + nt*th)
                            cr.show_text(t[:-2]+'...')
                        else:
                            cr.move_to(x + 1, y + th + nt*th)
                            cr.show_text(t)
                    if fh > 8 or self.timeline.data.idx == nf:
                        self.draw_button(cr, x+fwa-26, y-1, nl, nf, 'key')
                        self.draw_button(cr, x+fwa-12, y-1, nl, nf)
                    cr.fill();
                else:
                    if nf == self.timeline.data.idx:
                        cr.set_source_rgb(0.91, 0.91, 0.91)
                    else:
                        cr.set_source_rgb(0.84, 0.84, 0.84)
                    cr.rectangle(x, y, fw - 1, fh)
                    cr.fill();
                    if l[nf].is_key:
                        cr.set_source_rgb(.95, .95, 0)
                        cr.rectangle(x, y, fw-1, 3)
                        cr.rectangle(x, y+fh-3, fw-1, 3)
                        cr.rectangle(x, y, 3, fh)
                        cr.rectangle(x+fw-4, y, 3, fh)
                        cr.fill()
                    cr.rectangle(x, y, fw, 1)
                    cr.rectangle(x, y+fh, fw, 1)
                    cr.set_source_rgb(0, 0, 0)
                    cr.fill()
                    if fh > 8:
                        self.draw_button(cr, x+fw-12, y-1, nl, nf)
        # before layer
        cr.rectangle(0, 0, 1, wh)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
        # border
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, ww, 1)
        cr.fill();
    
    def get_in_list(self, l, f, x, y):
        try:
            c = self.close_box_list[l][f]
            if c[0] < x < c[0]+c[2] and c[1] < y < c[1]+c[3]:
                self.ani.remove_frame(l, f)
                return True
        except:
            return False
        try:
            k = self.key_box_list[l][f]
            if k[0] < x < k[0]+k[2] and k[1] < y < k[1]+k[3]:
                self.ani.toggle_key(l, f)
                return True
        except:
            return False

    def clic(self, widget, event):
        self.move_frame = False
        if event.button == Gdk.BUTTON_PRIMARY:
            frame = (int(event.y)-1-self.timeline.margin_top)//self.timeline.frame_height
            layer = self.timeline.convert_layer(event.x)
            if self.get_in_list(layer, frame, event.x, event.y):
                return True
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                if not 0 <= layer < len(self.timeline.data):
                    self.ani.add_layer(len(self.timeline.data))
                    layer = self.timeline.data.layer_idx = len(self.timeline.data) - 1
                if frame in self.timeline.data[layer]:
                    description = anidialogs.ask_for(self, _("Change description"),
                             _("Description"), self.timeline.data[layer][frame].description)
                    if description:
                        self.ani.change_description(description, 
                                                    self.timeline.data[layer][frame])
                else:
                    self.ani.add_cel(layer, frame)
                self.resize()
            else:
                if layer < len(self.timeline.data) and frame in self.timeline.data[layer]:
                    self.move_frame = (layer, frame, False)
                self.timeline.emit('change_current_frame', frame)
                self.timeline.emit('change_selected_layer', layer)
        elif event.button == Gdk.BUTTON_MIDDLE:
            self.drag_scroll = [event.x, event.y]
        return True
                    
    def move(self, widget, event):
        if self.move_frame:
            f = int((event.y-1-self.timeline.margin_top)/self.timeline.frame_height)
            sl, sf = self.move_frame[0], self.move_frame[1]
            if f == sf:
                return
            #~ if not self.strechFrame[2]:
                #~ self.parent.project.saveToUndo('frames')
            while f > sf:
                if sf+1 not in self.timeline.data[sl]:
                    self.timeline.data[sl][sf+1] = self.timeline.data[sl].pop(sf)
                else:
                    self.timeline.data[sl][sf+1], self.timeline.data[sl][sf] = \
                          self.timeline.data[sl].pop(sf), self.timeline.data[sl].pop(sf+1)
                sf += 1
            while f < sf and 0 < sf:
                if sf-1 not in self.timeline.data[sl]:
                    self.timeline.data[sl][sf-1] = self.timeline.data[sl].pop(sf)
                else:
                    self.timeline.data[sl][sf-1], self.timeline.data[sl][sf] = \
                          self.timeline.data[sl].pop(sf), self.timeline.data[sl].pop(sf-1)
                sf -= 1
            self.move_frame = (sl, sf, True)
            
            #self.resize(delayed=True)
            self.resize()
            self.timeline.emit('change_current_frame', f)

        elif self.drag_scroll != False:
            x, y = self.drag_scroll
            dx, dy = x - event.x, y - event.y
            self.drag_scroll = [event.x, event.y]
            self.timeline.emit('scroll_amount', dx, dy)

    def release(self, widget, event):
        self.move_frame = False
        self.drag_scroll = False



class TimelineTool(Gtk.VBox):

    stock_id = 'mypaint-tool-animation'

    tool_widget_icon_name = "mypaint-tool-timeline"
    tool_widget_title = _("Timeline")
    tool_widget_description = _("Create cel-based animation")

    __gtype_name__ = 'MyPaintTimelineTool'
    __gsignals__ = {
        'change_current_frame': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'change_selected_layer': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'addrename_layer': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'scroll_amount': (GObject.SIGNAL_RUN_FIRST, None,(int,int,)),
        'update': (GObject.SIGNAL_RUN_FIRST, None,())
    }
    
    def __init__(self):
        from application import get_app
        Gtk.VBox.__init__(self)
        app = get_app()
        self.app = app
        self.doc = self.app.doc.model
        self.ani = app.doc.ani.model
        self.data = self.ani.timeline
        self.is_playing = False

        self.frame_width = 22
        self.frame_width_active = 70
        self.frame_height = 32
        self.margin_top = 6

        self.grid = Gtk.Grid()

        self.timeline_widget = TimelineWidget(self, app)
        self.scroll_timeline = Gtk.ScrolledWindow()
        self.scroll_timeline.add(self.timeline_widget)
        self.scroll_timeline.set_hexpand(True)
        self.scroll_timeline.set_vexpand(True)
        self.scroll_timeline.set_min_content_height(200)
        self.scroll_timeline.set_min_content_width(100)
        self.scroll_timeline.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        self.scroll_timeline.get_vscrollbar().connect('value-changed', self.on_scrolled)
        
        self.frame_widget = FrameWidget(self, app)
        self.scroll_frame = Gtk.ScrolledWindow()
        self.scroll_frame.set_vadjustment(self.scroll_timeline.get_vadjustment())
        self.scroll_frame.get_vscrollbar().hide()
        self.scroll_frame.get_hscrollbar().hide()
        self.scroll_frame.add(self.frame_widget)
        self.scroll_frame.set_min_content_width(23)
        self.scroll_frame.set_vexpand(True)
        self.timeline_widget.connect('size_changed', self.frame_widget.resize)
        
        self.layer_widget = LayerWidget(self, self.app)
        self.scroll_layer = Gtk.ScrolledWindow()
        self.scroll_layer.set_hadjustment(self.scroll_timeline.get_hadjustment())
        self.scroll_layer.get_vscrollbar().hide()
        self.scroll_layer.get_hscrollbar().hide()
        self.scroll_layer.add(self.layer_widget)
        self.scroll_layer.set_min_content_height(25)
        self.scroll_layer.set_hexpand(True)
        self.timeline_widget.connect('size_changed', self.layer_widget.resize)

        
        # try to use wheel value
        self.scroll_timeline.add_events(Gdk.EventMask.SCROLL_MASK)
        self.scroll_timeline.connect('scroll_event', self.on_scroll_zoom)


        self.size_adjustment = Gtk.Adjustment(value=self.frame_height, lower=1, upper=32, step_incr=1)
        self.size_adjustment.connect('value-changed', self.set_frame_height)
        self.size_adjustment.connect('value-changed', self.timeline_widget.resize)
        
        
        self.grid.attach(self.scroll_layer, 1, 0, 1, 1)
        self.grid.attach(self.scroll_frame, 0, 1, 1, 1)
        self.grid.attach(self.scroll_timeline, 1, 1, 1, 1)
        self.grid.set_property('margin', 3)


        # layer controls:
        from layerswindow import make_composite_op_model
        from widgets import SPACING_CRAMPED
        self.tooltip_format = _("<b>{blendingmode_name}</b>\n{blendingmode_description}")

        layer_ctrls_table = Gtk.Table()
        layer_ctrls_table.set_row_spacings(SPACING_CRAMPED)
        layer_ctrls_table.set_col_spacings(SPACING_CRAMPED)
        row = 0

        layer_mode_lbl = Gtk.Label(_('Mode:'))
        layer_mode_lbl.set_tooltip_text(
          _("Blending mode: how the current layer combines with the "
            "layers underneath it."))
        layer_mode_lbl.set_alignment(0, 0.5)
        self.layer_mode_model = make_composite_op_model()
        self.layer_mode_combo = Gtk.ComboBox()
        self.layer_mode_combo.set_model(self.layer_mode_model)
        cell1 = Gtk.CellRendererText()
        self.layer_mode_combo.pack_start(cell1)
        self.layer_mode_combo.add_attribute(cell1, "text", 1)
        layer_ctrls_table.attach(layer_mode_lbl, 0, 1, row, row+1, Gtk.FILL)
        layer_ctrls_table.attach(self.layer_mode_combo, 1, 2, row, row+1, Gtk.FILL|Gtk.EXPAND)
        row += 1

        opacity_lbl = Gtk.Label(_('Opacity:'))
        opacity_lbl.set_tooltip_text(
          _("Layer opacity: how much of the current layer to use. Smaller "
            "values make it more transparent."))
        opacity_lbl.set_alignment(0, 0.5)
        adj = Gtk.Adjustment(lower=0, upper=100, step_incr=1, page_incr=10)
        self.opacity_scale = Gtk.HScale(adj)
        self.opacity_scale.set_draw_value(False)
        layer_ctrls_table.attach(opacity_lbl, 0, 1, row, row+1, Gtk.FILL)
        layer_ctrls_table.attach(self.opacity_scale, 1, 2, row, row+1, Gtk.FILL|Gtk.EXPAND)

        self.opacity_scale.connect('value-changed', self.on_opacity_changed)
        self.layer_mode_combo.connect('changed', self.on_layer_mode_changed)


        # playback controls:
        self.play_button = stock_button(Gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect('clicked', self.on_animation_play)
        self.play_button.set_tooltip_text(_('Play animation'))
        
        self.pause_button = stock_button(Gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect('clicked', self.on_animation_pause)
        self.pause_button.set_tooltip_text(_('Pause animation'))

        self.stop_button = stock_button(Gtk.STOCK_MEDIA_STOP)
        self.stop_button.connect('clicked', self.on_animation_stop)
        self.stop_button.set_tooltip_text(_('Stop animation'))

        # frames edit controls:
        cut_button = stock_button(Gtk.STOCK_CUT)
        cut_button.connect('clicked', self.on_cut)
        cut_button.set_tooltip_text(_('Cut cel'))
        self.cut_button = cut_button

        copy_button = stock_button(Gtk.STOCK_COPY)
        copy_button.connect('clicked', self.on_copy)
        copy_button.set_tooltip_text(_('Copy cel'))
        self.copy_button = copy_button

        paste_button = stock_button(Gtk.STOCK_PASTE)
        paste_button.connect('clicked', self.on_paste)
        paste_button.set_tooltip_text(_('Paste cel'))
        self.paste_button = paste_button

        framebuttons_hbox = Gtk.HBox()
        framebuttons_hbox.pack_start(self.play_button)
        framebuttons_hbox.pack_start(self.pause_button)
        framebuttons_hbox.pack_start(self.stop_button)
        framebuttons_hbox.pack_start(cut_button)
        framebuttons_hbox.pack_start(copy_button)
        framebuttons_hbox.pack_start(paste_button)


        self.pack_start(layer_ctrls_table, expand=False)
        self.pack_start(self.grid)
        self.pack_start(framebuttons_hbox, expand=False)
        self.set_size_request(200, -1)

        self.doc.doc_observers.append(self.update)
        self.doc.doc_observers.append(self.sort_layers)

    def update(self, doc=None):
        self.data.cleanup()

        current_layer = self.doc.ani.timeline.layer
        # Update the common widgets
        self.opacity_scale.set_value(current_layer.opacity*100)
        self.update_opacity_tooltip()
        mode = current_layer.composite
        def find_iter(model, path, iter, data):
            md = model.get_value(iter, 0)
            md_name = model.get_value(iter, 1)
            md_desc = model.get_value(iter, 2)
            if md == mode:
                self.layer_mode_combo.set_active_iter(iter)
                tooltip = self.tooltip_format.format(
                    blendingmode_name = escape(md_name),
                    blendingmode_description = escape(md_desc))
                self.layer_mode_combo.set_tooltip_markup(tooltip)
        self.layer_mode_model.foreach(find_iter, None)

        self._update_buttons_sensitive()
        if self.ani.cleared == True:
            self.ani.cleared = False
            self.update_digits()
            self.timeline_widget.resize()

        self.scroll_to(self.ani.timeline.idx)
        self.emit('update')

    def on_scroll_zoom(self, window, event, *args):
        if event.get_state() != 0:
            val = self.size_adjustment.get_value()
            dval = event.get_scroll_deltas()[2] / 2
            self.size_adjustment.set_value(val - dval)
            self.update_digits()
            return True

    def on_scrolled(self, *args):
        self.update_digits()
        self.timeline_widget.resize()

    def update_digits(self):
        import math
        digits = 7*(int(math.log( \
                    self.get_last()/self.frame_height, \
                    10))+1)+16
        self.scroll_frame.set_min_content_width(digits)

    def scroll_to(self, idx):
        if idx < 0: idx = 0
        adj = self.scroll_timeline.get_vadjustment()
        fh = self.frame_height
        wh = self.scroll_timeline.get_allocation().height
        sh = idx * fh
        ah = adj.get_value()
        while not ah <= sh <= ah + wh - 2*fh:
            if sh > ah:
                ah += 1
            elif sh < ah:
                ah -= 1
            elif sh == ah:
                break
        adj.set_value(ah)
        
    def send_scroll(self, dx, dy):
        hadj = self.scroll_timeline.get_hadjustment()
        vadj = self.scroll_timeline.get_vadjustment()
        x, y = hadj.get_value(), vadj.get_value()
        hadj.set_value(x + dx)
        vadj.set_value(y + dy)

    def sort_layers(self, doc=None):
        self.ani.sort_layers()

    def tool_widget_properties(self):
        d = TimelinePropertiesDialog(self, self.app)
        d.run()
        d.destroy()

        
    def set_frame_height(self, adj):
        self.frame_height = int(adj.props.value)
        self.emit('update')
        
    def do_change_current_frame(self, n):
        #self.current = max(n, 0)
        self.ani.select(n)
        self.emit('update')
        
    def do_change_selected_layer(self, n):
        if 0 <= n < len(self.data):
            self.ani.select_layer(n)
            self.emit('update')

    def do_scroll_amount(self, x, y):
        self.send_scroll(x, y)
        
    def convert_layer(self, x):
        if x > (self.data.layer_idx + 1) * self.frame_width:
            return int((x - self.frame_width_active + self.frame_width)/self.frame_width)
        else:
            return int((x)/self.frame_width)

    def get_last(self):
        fh = self.frame_height
        sh = self.scroll_timeline.get_allocation().height
        return int(max((self.data.get_length() + 1) * fh,
                   (self.data.idx + 2) * fh,
                   self.scroll_timeline.get_vadjustment().get_value() + sh + fh))
        
    def _change_player_buttons(self):
        if self.is_playing:
            self.play_button.hide()
            self.pause_button.show()
        else:
            self.play_button.show()
            self.pause_button.hide()
        self.stop_button.set_sensitive(self.is_playing)

    def _update_buttons_sensitive(self):
        self.cut_button.set_sensitive(self.ani.can_cutcopy())
        self.copy_button.set_sensitive(self.ani.can_cutcopy())
        self.paste_button.set_sensitive(self.ani.can_paste())
        self._change_player_buttons()

    def _call_player(self, use_lightbox=False):
        self.ani.player_next(use_lightbox)
        keep_playing = True
        if self.ani.player_state == "stop":
            self.ani.select_without_undo(self.beforeplay_frame)
            keep_playing = False
            self.is_playing = False
            self._change_player_buttons()
            self.ani.player_state = None
            self.update()
        elif self.ani.player_state == "pause":
            keep_playing = False
            self.is_playing = False
            self._change_player_buttons()
            self.ani.player_state = None
            self.update()
        return keep_playing

    def _play_animation(self, from_first_frame=True, use_lightbox=False):
        self.is_playing = True
        self.beforeplay_frame = self.ani.timeline.idx
        if from_first_frame:
            self.ani.timeline.select(self.ani.timeline.get_first())
        self._change_player_buttons()
        self.ani.hide_all_frames()
        # animation timer
        ms_per_frame = int(round(1000.0/self.ani.timeline.fps))

        # show first frame immediately, otherwise there's a single frame delay
        # @TODO: it seems to wait one frame before stopping too
        self._call_player(use_lightbox)

        GObject.timeout_add(ms_per_frame, self._call_player, use_lightbox)


    def on_animation_play(self, button):
        self.ani.play_animation()

    def on_animation_pause(self, button):
        self.ani.pause_animation()

    def on_animation_stop(self, button):
        self.ani.stop_animation()

    def on_cut(self, button):
        self.ani.cutcopy_cel('cut')

    def on_copy(self, button):
        self.ani.cutcopy_cel('copy')

    def on_paste(self, button):
        self.ani.paste_cel()


    def update_opacity_tooltip(self):
        scale = self.opacity_scale
        scale.set_tooltip_text(_("Layer opacity: %d%%" % (scale.get_value(),)))


    def on_opacity_changed(self, *ignore):
        doc = self.app.doc.model
        doc.ani.set_layer_opacity(self.opacity_scale.get_value()/100.0)
        self.update_opacity_tooltip()

    def on_layer_mode_changed(self, *ignored):
        doc = self.app.doc.model
        i = self.layer_mode_combo.get_active_iter()
        mode_name, display_name, desc = self.layer_mode_model.get(i, 0, 1, 2)
        doc.ani.set_layer_composite(mode_name)
        tooltip = self.tooltip_format.format(
            blendingmode_name = escape(display_name),
            blendingmode_description = escape(desc))
        self.layer_mode_combo.set_tooltip_markup(tooltip)


    def get_divisions(self):
        fps = self.data.fps
        div_li = [1]
        for i in range(2, fps):
            if fps % i == 0 and i % div_li[-1] == 0:
                div_li.append(i)
        return div_li



class TimelinePropertiesDialog(Gtk.Dialog):
    def __init__(self, timeline, app):
        Gtk.Dialog.__init__(self, 'Animation Properties')
        self.app = app
        self.ani = app.doc.ani.model
        self.timeline = timeline

        adj = Gtk.Adjustment(lower=0, upper=100, step_incr=1, page_incr=10)
        self.opacity_scale = Gtk.HScale(adj)
        opa = self.app.preferences.get('lightbox.factor', 100)
        self.opacity_scale.set_value(opa)
        self.opacity_scale.set_value_pos(Gtk.POS_LEFT)
        opacity_lbl = Gtk.Label(_('Opacity:'))
        opacity_hbox = Gtk.HBox()
        opacity_hbox.pack_start(opacity_lbl, expand=False)
        opacity_hbox.pack_start(self.opacity_scale, expand=True)
        self.opacity_scale.connect('value-changed',
                                   self.on_opacityfactor_changed)

        def opacity_checkbox(attr, label, tooltip=None):
            cb = Gtk.CheckButton(label)
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            cb.set_active(self.app.preferences.get(pref, default))
            cb.connect('toggled', self.on_opacity_toggled, attr)
            if tooltip is not None:
                cb.set_tooltip_text(tooltip)
            opacityopts_vbox.pack_start(cb, expand=False)

        opacityopts_vbox = Gtk.VBox()
        opacity_checkbox('cel', _('Inmediate'), _("Show the inmediate next and previous cels."))
        opacity_checkbox('key', _('Inmediate keys'), _("Show the cel keys that are after and before the current cel."))
        opacity_checkbox('inbetweens', _('Inbetweens'), _("Show the cels that are between the inmediate key cels."))
        opacity_checkbox('other keys', _('Other keys'), _("Show the other keys cels."))
        opacity_checkbox('other', _('Other'), _("Show the rest of the cels."))

        self.framerate_adjustment = Gtk.Adjustment(value=self.ani.timeline.fps, lower=1, upper=120, step_incr=1)
        self.framerate_adjustment.connect("value-changed", self.on_framerate_changed)
        self.framerate_entry = Gtk.SpinButton(adjustment=self.framerate_adjustment, digits=0, climb_rate=1.5)
        framerate_lbl = Gtk.Label(_('Frame rate:'))
        framerate_hbox = Gtk.HBox()
        framerate_hbox.pack_start(framerate_lbl, False, False)
        framerate_hbox.pack_start(self.framerate_entry, False, False)

        play_lightbox_cb = Gtk.CheckButton(_("Play with lightbox on"))
        play_lightbox_cb.set_active(self.app.preferences.get("xsheet.play_lightbox", False))
        play_lightbox_cb.connect('toggled', self.on_playlightbox_toggled)
        play_lightbox_cb.set_tooltip_text(_("Show other frames while playing, this is slower."))

        showprev_cb = Gtk.CheckButton(_("Lightbox show previous"))
        showprev_cb.set_active(self.app.preferences.get("xsheet.lightbox_show_previous", True))
        showprev_cb.connect('toggled', self.on_shownextprev_toggled, 'previous')
        showprev_cb.set_tooltip_text(_("Show previous cels in the lightbox."))

        shownext_cb = Gtk.CheckButton(_("Lightbox show next"))
        shownext_cb.set_active(self.app.preferences.get("xsheet.lightbox_show_next", False))
        shownext_cb.connect('toggled', self.on_shownextprev_toggled, 'next')
        shownext_cb.set_tooltip_text(_("Show next cels in the lightbox."))

        self.vbox.pack_start(framerate_hbox, expand=False)
        self.vbox.pack_start(play_lightbox_cb, expand=False)
        self.vbox.pack_start(showprev_cb, expand=False)
        self.vbox.pack_start(shownext_cb, expand=False)
        self.vbox.pack_start(opacity_hbox, expand=False)
        self.vbox.pack_start(opacityopts_vbox, expand=False)
        self.vbox.show_all()

        self.set_size_request(200, -1)

    def on_opacityfactor_changed(self, *ignore):
        opa = self.opacity_scale.get_value()
        self.app.preferences["lightbox.factor"] = opa
        self.ani.change_opacityfactor(opa/100.0)
        self.queue_draw()

    def on_opacity_toggled(self, checkbox, attr):
        pref = "lightbox.%s" % (attr,)
        self.app.preferences[pref] = checkbox.get_active()
        self.ani.toggle_opacity(attr, checkbox.get_active())
        self.queue_draw()

    def on_framerate_changed(self, adj):
        self.ani.timeline.fps = int(adj.get_value())
        self.timeline.emit('update')
        
    def on_playlightbox_toggled(self, checkbox):
        self.app.preferences["xsheet.play_lightbox"] = checkbox.get_active()

    def on_shownextprev_toggled(self, checkbox, nextprev):
        self.app.preferences["xsheet.lightbox_show_" + nextprev] = checkbox.get_active()
        self.ani.toggle_nextprev(nextprev, checkbox.get_active())

