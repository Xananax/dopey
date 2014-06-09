from gi.repository import Gtk, GObject
from gi.repository import Gdk, GdkPixbuf

import cairo
import textwrap

import anidialogs
from gettext import gettext as _

from lib.timeline import DEFAULT_ACTIVE_CELS

class Timeline(GObject.GObject):
    ''' timeline is a gobject containing the layers
        and information like fps, current frame or layer
    '''
    __gsignals__ = {
        'change_current_frame': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'change_selected_layer': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'addremove_layer': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'update': (GObject.SIGNAL_RUN_FIRST, None,())
    }
    def __init__(self, layers=[], current=0):
        GObject.GObject.__init__(self)
        from application import get_app
        app = get_app()
        self.app = app
        self.ani = app.doc.ani.model
        self.data = self.ani.timeline

        self.frame_width = 22
        self.frame_width_active = 70
        self.frame_height = 32
        self.frame_height_n = 3
        self.margin_top = 11

        self.app.doc.model.doc_observers.append(self.update)

    def update(self, *args):
        self.data.cleanup()
        self.emit('update')
        
    def set_frame_height(self, adj):
#        n = int(adj.props.value)
        self.frame_height = int(adj.props.value)
#        self.frame_height = self.frame_height_li[n]
        self.emit('update')
        
    def do_change_current_frame(self, n):
        #self.current = max(n, 0)
        self.ani.select(n)
        self.emit('update')
        
    def do_addremove_layer(self, n):
        if 0 <= n < len(self.data):
            self.ani.remove_layer(n)
            self.emit('update')
        else:
            self.ani.add_layer(len(self.data))
            self.data.layer_idx = len(self.data) - 1
            self.emit('update')
        
    def do_change_selected_layer(self, n):
        if 0 <= n < len(self.data):
            self.data.layer_idx = n
            self.emit('update')
        
    def convert_layer(self, x):
        if x > (self.data.layer_idx + 1) * self.frame_width:
            return int((x - self.frame_width_active + self.frame_width)/self.frame_width)
        else:
            return int((x)/self.frame_width)
        
        
class LayerWidget(Gtk.DrawingArea):
    __gtype_name__ = 'LayerWidget'

    def __init__(self, timeline, app):
        Gtk.Widget.__init__(self)
        self.ani = app.doc.ani.model
        self.timeline = timeline
        self.move_layer = False

        self.set_size_request(100, 25)
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
        if ww < w:
            self.set_size_request(w, wh)
            self.queue_draw()
        
    def do_draw(self, cr):
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
        # frame size
        fw, fwa = self.timeline.frame_width, self.timeline.frame_width_active
        
        cr.rectangle(0, 1, 1, wh-1)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
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
                cr.rectangle(x+fwa, 1, 1, wh-1)
                cr.rectangle(x+1, 0, fwa-1, 1)
            else:
                cr.rectangle(x+fw, 1, 1, wh-1)
                cr.rectangle(x+1, 0, fw-1, 1)
            cr.set_source_rgb(0, 0, 0)
            cr.fill();
    
    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            layer = self.timeline.convert_layer(event.x)
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.timeline.emit('addremove_layer', layer)
            else:
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
                self.ani.move_frame(sl, 1)
                sl += 1
            while l < sl and sl > 0:
                self.ani.move_frame(sl, -1)
                sl -= 1
            self.move_layer = sl
        self.timeline.emit('change_selected_layer', l)
        #print('mooove')

    def release(self, widget, event):
        #print('releaaaase')
        pass
        
        
class FrameWidget(Gtk.DrawingArea):
    __gtype_name__ = 'FrameWidget'

    def __init__(self, timeline):
        Gtk.Widget.__init__(self)
        self.timeline = timeline

        self.set_size_request(30, 600)
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
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
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
        cr.rectangle(1, self.timeline.data.idx*fh+m, 29, fh)
        cr.fill();
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, self.timeline.data.idx*fh+m, ww, 1)
        cr.rectangle(0, self.timeline.data.idx*fh+fh+m, ww, 1)
        cr.fill();
        
        cr.set_font_size(10)
        cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        for f, i in enumerate(range(0, wh, fh), 1):
            cr.rectangle(24, i+m, 6, 1)
            if f % self.timeline.data.fps == 0:
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.move_to(8, i+fh+m-(fh/4))
                cr.show_text(str(f))
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            elif fh <= 8:
                if f % 2 == 0:
                    cr.move_to(8, i+fh+m-(fh/4))
                    cr.show_text(str(f))
            else:
                cr.move_to(8, i+fh+m-(fh/4))
                cr.show_text(str(f))
        cr.fill();

    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            #print('clic')
            self.timeline.emit('change_current_frame', 
                               int((event.y-1)/self.timeline.frame_height))
        return True
        
    def move(self, widget, event):
        self.timeline.emit('change_current_frame', 
                           int((event.y-1)/self.timeline.frame_height))
        #print('mooove')

    def release(self, widget, event):
        #print('releaaaase')
        pass
        
        
class TimelineWidget(Gtk.DrawingArea):
    __gtype_name__ = 'TimelineWidget'
    __gsignals__ = {
        'size_changed': (GObject.SIGNAL_RUN_FIRST, None,(int, int))
    }
    def __init__(self, timeline):
        Gtk.Widget.__init__(self)
        from application import get_app
        app = get_app()
        self.app = app
        self.ani = app.doc.ani.model

        self.timeline = timeline

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect('button-press-event', self.clic)
        self.connect('motion-notify-event', self.move)
        self.connect('button-release-event', self.release)
        self.timeline.connect('update', self.update)
        
        #self.sh = getattr(self.app.pixmaps, 'frame_small')
        self.sh = cairo.ImageSurface.create_from_png('sheet.png')
        
        self.strech_box_list = []
        self.strech_frame = False
        self.h = [0, 0]
        self.connect('show', self.resize)

    def update(self, *args):
        self.queue_draw()
        
    def resize(self, *args, **delay):
        w = self.timeline.frame_width * (len(self.timeline.data) - 1) + self.timeline.frame_width_active + 8
        h = max(
                self.ani.timeline.get_length() + 1,
                self.ani.timeline.idx + 2
                ) * self.timeline.frame_height + (self.timeline.margin_top * 2) + 24
        if h < self.h[0] and 'delayed' in delay:
            self.h[1] += 1
            if self.h[1] >= 3:
                self.h[0] -= self.timeline.frame_height
                self.h[1] -= 1
            h = self.h[0]
        else:
            self.h = [h, 0]
        ww, wh = self.get_allocation().width, self.get_allocation().height
        if ww != w or wh != h:
            self.set_size_request(w, h)
            self.emit('size_changed', w, h)
            #print(w, h)
        
    def draw_mask(self, cr, im, x, y, w, h):
        cr.rectangle(x, y, w, h)
        cr.save()
        cr.clip()
        cr.set_source_surface(im, x, y)
        cr.paint()
        cr.restore()
    
    def draw_strech(self, cr, x, y, l):
        cr.rectangle(x, y, 12, 12)
        cr.set_source_rgb(0, 0, 0)
        cr.fill()
        cr.rectangle(x+1, y+1, 10, 10)
        cr.set_source_rgb(1, .67, .67)
        cr.fill()
        self.strech_box_list[l].append((x, y, 12, 12))
        
    def do_draw(self, cr):
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
        # frame size
        fw, fwa, fh = self.timeline.frame_width, self.timeline.frame_width_active, self.timeline.frame_height
        m = self.timeline.margin_top
        cr.set_source_rgba(0, 0, 0, 0.1)
        cr.paint()
        # current frame
        cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.rectangle(0, self.timeline.data.idx*fh+m, ww, fh+1)
        cr.fill();
        cr.set_source_rgb(0, 0, 0)
        # draw layers
        self.strech_box_list = []
        #line marking seconds
        for i in range(0, self.ani.timeline.get_length() + self.timeline.data.fps, self.timeline.data.fps):
            y = i*fh+m
            cr.rectangle(0, y, ww, 1)
        for nl, l in enumerate(self.timeline.data):
            self.strech_box_list.append([])
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
            cr.set_source_rgb(0, 0, 0)
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
                    cr.fill();
                    #self.draw_mask(cr, self.sh, x, y, fwa, fh)
                    cr.rectangle(x, y, fwa, 1)
                    cr.rectangle(x, y+fh, fwa, 1)
                    cr.set_source_rgb(0, 0, 0)
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
                    self.draw_strech(cr, x+fwa-9, y-3, nl)
                    cr.fill();
                else:
                    if nf == self.timeline.data.idx:
                        cr.set_source_rgb(0.91, 0.91, 0.91)
                    else:
                        cr.set_source_rgb(0.84, 0.84, 0.84)
                    cr.rectangle(x, y, fw - 1, fh)
                    cr.fill();
                    #self.draw_mask(cr, self.sh, x, y, fw, fh)
                    cr.rectangle(x, y, fw, 1)
                    cr.rectangle(x, y+fh, fw, 1)
                    cr.set_source_rgb(0, 0, 0)
                    cr.fill()
                    self.draw_strech(cr, x+fw-12, y, nl)
        # before layer
        cr.rectangle(0, 0, 1, wh)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
        # border
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, ww, 1)
        cr.fill();
    
    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            frame = (int(event.y)-1-self.timeline.margin_top)//self.timeline.frame_height
            layer = self.timeline.convert_layer(event.x)
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                if frame in self.timeline.data[layer]:
                    for l, i in enumerate(self.strech_box_list):
                        for f, j in enumerate(i):
                            if j[0] < event.x < j[0]+j[2] and j[1] < event.y < j[1]+j[3]:
                                self.ani.remove_frame(layer, frame)
                                return True
                    description = anidialogs.ask_for(self, _("Change description"),
                        _("Description"), self.timeline.data[layer][frame].description)
                    if description:
                        self.ani.change_description(description, self.timeline.data[layer][frame])
                else:
                    self.ani.add_cel(layer, frame)
                self.resize(delayed=True)
            else:
                self.strech_frame = False
                if layer < len(self.timeline.data) and frame in self.timeline.data[layer]:
                    self.strech_frame = (layer, frame, False)
                self.timeline.emit('change_current_frame', frame)
                self.timeline.emit('change_selected_layer', layer)
        return True
                    
    def move(self, widget, event):
        f = int((event.y-1-self.timeline.margin_top)/self.timeline.frame_height)
        if self.strech_frame:
            sl, sf = self.strech_frame[0], self.strech_frame[1]
            if f == sf:
                return
            #~ if not self.strechFrame[2]:
                #~ self.parent.project.saveToUndo('frames')
            while f > sf:
                if sf+1 not in self.timeline.data[sl]:
                    self.timeline.data[sl][sf+1] = self.timeline.data[sl].pop(sf)
                else:
                    self.timeline.data[sl][sf+1], self.timeline.data[sl][sf] = self.timeline.data[sl].pop(sf), self.timeline.data[sl].pop(sf+1)
                sf += 1
            while f < sf and 0 < sf:
                if sf-1 not in self.timeline.data[sl]:
                    self.timeline.data[sl][sf-1] = self.timeline.data[sl].pop(sf)
                else:
                    self.timeline.data[sl][sf-1], self.timeline.data[sl][sf] = self.timeline.data[sl].pop(sf), self.timeline.data[sl].pop(sf-1)
                sf -= 1
            self.strech_frame = (sl, sf, True)
            
        self.resize(delayed=True)
        self.timeline.emit('change_current_frame', f)
        #print('mooove')

    def release(self, widget, event):
        #print('releaaaase')
        #print('what')
        self.strech_frame = False


class Gridd(Gtk.Grid):
    
    def __init__(self):
        Gtk.Grid.__init__(self)
        from application import get_app
        app = get_app()
        self.app = app
        self.ani = app.doc.ani.model
        self.app.doc.model.doc_observers.append(self.sort_layers)

        li = self.ani.timeline
        self.timeline = Timeline(li)
        self.timeline_widget = TimelineWidget(self.timeline)
        self.timeline_view = Gtk.Viewport()
        self.timeline_view.add(self.timeline_widget)
        self.scroll_timeline = Gtk.ScrolledWindow()
        self.scroll_timeline.add(self.timeline_view)
        self.scroll_timeline.set_hexpand(True)
        self.scroll_timeline.set_vexpand(True)
        self.scroll_timeline.set_min_content_height(300)
        self.scroll_timeline.set_min_content_width(100)
        
        self.frame_widget = FrameWidget(self.timeline)
        self.scroll_frame = Gtk.ScrolledWindow()
        self.scroll_frame.set_vadjustment(self.scroll_timeline.get_vadjustment())
        self.scroll_frame.get_vscrollbar().hide()
        self.scroll_frame.get_hscrollbar().hide()
        self.scroll_frame.add(self.frame_widget)
        self.scroll_frame.set_min_content_width(24)
        self.scroll_frame.set_vexpand(True)
        self.timeline_widget.connect('size_changed', self.frame_widget.resize)
        
        self.layer_widget = LayerWidget(self.timeline, self.app)
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
        self.scroll_timeline.connect('scroll_event', self.send_scroll)
        
        self.size_adjustment = Gtk.Adjustment(value=self.timeline.frame_height, lower=6, upper=32, step_incr=1)
        self.scale = Gtk.Scale(orientation=0, adjustment=self.size_adjustment)
        # how to hide value without lose increment
        self.scale.set_property('draw_value', False)
        self.size_adjustment.connect('value-changed', self.timeline.set_frame_height)
        self.size_adjustment.connect('value-changed', self.timeline_widget.resize)
        
        
        self.attach(self.scale, 0, 0, 2, 1)
        self.attach(self.scroll_layer, 1, 1, 1, 1)
        self.attach(self.scroll_frame, 0, 2, 1, 1)
        self.attach(self.scroll_timeline, 1, 2, 1, 1)
        self.set_property('margin', 10)

        self.app.doc.model.doc_observers.append(self.update_size)

    def update_size(self, *args):
        import math
        if self.ani.cleared == True:
            self.scroll_frame.set_min_content_width(
                                                    8*(int(math.log(max(
                                                    self.timeline.data.get_length() + 2,
                                                    self.ani.timeline.idx + 3
                                                    ),10))+1)+18)
            self.timeline.set_frame_height(self.size_adjustment)
            self.timeline_widget.resize()
            self.ani.cleared = False
        self.set_scroll(self.ani.timeline.idx)

    def set_scroll(self, idx):
        if idx < 0: return
        adj = self.scroll_timeline.get_vadjustment()
        fh = self.timeline.frame_height
        wh = self.timeline_view.get_allocation().height
        sh = idx * fh
        ah = adj.get_value()
        while not ah <= sh <= ah + wh - 2*fh:
            if sh > ah:
                adj.set_value(ah+fh)
            elif sh < ah:
                adj.set_value(ah-fh)
            ah = adj.get_value()
        
    def send_scroll(self, ar, gs):
        pass
        #~ self.vscroll.emit('scroll_event', gs)

    def sort_layers(self, doc=None):
        self.ani.sort_layers()

class TimelinePropertiesDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self, 'Animation Properties')
        from application import get_app
        app = get_app()
        self.app = app
        self.ani = app.doc.ani.model

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

        self.framerate_adjustment = Gtk.Adjustment(value=self.ani.framerate, lower=1, upper=120, step_incr=1)
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
        self.ani.framerate = adj.get_value()
        
    def on_playlightbox_toggled(self, checkbox):
        self.app.preferences["xsheet.play_lightbox"] = checkbox.get_active()

    def on_shownextprev_toggled(self, checkbox, nextprev):
        self.app.preferences["xsheet.lightbox_show_" + nextprev] = checkbox.get_active()
        self.ani.toggle_nextprev(nextprev, checkbox.get_active())



class TimelineTool(Gtk.VBox):

    stock_id = 'mypaint-tool-animation'

    tool_widget_icon_name = "mypaint-tool-timeline"
    tool_widget_title = _("Timeline")
    tool_widget_description = _("Create cel-based animation")

    __gtype_name__ = 'MyPaintTimelineTool'
    
    def __init__(self):
        Gtk.VBox.__init__(self)

        grid = Gridd()
        self.add(grid)

    def tool_widget_properties(self):
        d = TimelinePropertiesDialog()
        d.run()
        d.destroy()

