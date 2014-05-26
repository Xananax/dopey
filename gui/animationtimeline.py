from gi.repository import Gtk, GObject
from gi.repository import Gdk, GdkPixbuf

import cairo


class Timeline(GObject.GObject):
    ''' timeline is a gobject containing the layers
        and information like fps, current frame or layer
    '''
    __gsignals__ = {
        'change_current_frame': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'change_selected_layer': (GObject.SIGNAL_RUN_FIRST, None,(int,)),
        'update': (GObject.SIGNAL_RUN_FIRST, None,())
    }
    def __init__(self, layers=[], current=0):
        GObject.GObject.__init__(self)
        self.layers = layers
        self.current = current
        self.selected_layer = 0
        self.fps = 12
        self.frame_width = 50
        self.frame_height = 32
        self.frame_height_li = [8, 16, 24, 32]
        self.frame_height_n = 3
        self.margin_top = 11
        
    def get_layer(self, n):
        return self.layers[n]
        
    def set_frame_height(self, adj):
        n = int(adj.props.value)
        self.frame_height = self.frame_height_li[n]
        self.emit('update')
        
    def do_change_current_frame(self, n):
        self.current = max(n, 0)
        self.emit('update')
        
    def do_change_selected_layer(self, n):
        if 0 <= n < len(self.layers):
            self.selected_layer = n
            self.emit('update')
        
    def frame_count(self):
        return max([len(l) for l in self.layers])
        
        
class LayerWidget(Gtk.DrawingArea):
    __gtype_name__ = 'LayerWidget'

    def __init__(self, timeline):
        Gtk.Widget.__init__(self)
        self.timeline = timeline

        self.set_size_request(100, 40)
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
        fw = self.timeline.frame_width
        
        cr.rectangle(0, 1, 1, wh-1)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
        for nl, l in enumerate(self.timeline.layers):
            x = nl * fw
            cr.rectangle(x+1, 1, fw-1, wh)
            if self.timeline.selected_layer == nl:
                cr.set_source_rgb(0.9, 0.9, 0.9)
            else:
                cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.fill();
            cr.rectangle(x+fw, 1, 1, wh-1)
            cr.rectangle(x+1, 0, fw-1, 1)
            cr.set_source_rgb(0, 0, 0)
            cr.fill();
    
    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            print('clic')
            self.timeline.emit('change_selected_layer', 
                               int((event.x)/self.timeline.frame_width))
        return True
        
    def move(self, widget, event):
        self.timeline.emit('change_selected_layer', 
                           int((event.x)/self.timeline.frame_width))
        print('mooove')

    def release(self, widget, event):
        print('releaaaase')
        
        
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
        cr.rectangle(1, self.timeline.current*fh+m, 29, fh)
        cr.fill();
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, self.timeline.current*fh+m, ww, 1)
        cr.rectangle(0, self.timeline.current*fh+fh+m, ww, 1)
        cr.fill();
        
        cr.set_font_size(10)
        cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        for f, i in enumerate(range(0, wh, fh), 1):
            cr.rectangle(24, i+m, 6, 1)
            if f % self.timeline.fps == 0:
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.move_to(8, i+fh+m-(fh/4))
                cr.show_text(str(f))
                cr.select_font_face('sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            elif fh == 8:
                if f % 2 == 0:
                    cr.move_to(8, i+fh+m-(fh/4))
                    cr.show_text(str(f))
            else:
                cr.move_to(8, i+fh+m-(fh/4))
                cr.show_text(str(f))
        cr.fill();

    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            print('clic')
            self.timeline.emit('change_current_frame', 
                               int((event.y-1)/self.timeline.frame_height))
        return True
        
    def move(self, widget, event):
        self.timeline.emit('change_current_frame', 
                           int((event.y-1)/self.timeline.frame_height))
        print('mooove')

    def release(self, widget, event):
        print('releaaaase')
        
        
class TimelineWidget(Gtk.DrawingArea):
    __gtype_name__ = 'TimelineWidget'
    __gsignals__ = {
        'size_changed': (GObject.SIGNAL_RUN_FIRST, None,(int, int))
    }
    def __init__(self, timeline):
        Gtk.Widget.__init__(self)
        self.timeline = timeline
        self.layer = timeline.get_layer(0)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect('button-press-event', self.clic)
        self.connect('motion-notify-event', self.move)
        self.connect('button-release-event', self.release)
        self.timeline.connect('update', self.update)
        
        self.sh = cairo.ImageSurface.create_from_png('sheet.png')
        self.nosh = cairo.ImageSurface.create_from_png('nosheet.png')
        
        self.strech_box_list = []
        self.strech_frame = False
        self.connect('show', self.resize)
        
    def update(self, *args):
        self.queue_draw()
        
    def resize(self, *arg):
        w = self.timeline.frame_width * len(self.timeline.layers)
        h = (self.timeline.frame_height * self.timeline.frame_count()) + (self.timeline.margin_top * 2) + 20
        ww, wh = self.get_allocation().width, self.get_allocation().height
        if ww != w or wh != h:
            self.set_size_request(w, h)
            self.emit('size_changed', w, h)
            print(w, h)
        
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
        cr.set_source_rgb(1, 1, 1)
        cr.fill()
        self.strech_box_list[l].append((x, y, 12, 12))
        
    def do_draw(self, cr):
        # widget size
        ww, wh = self.get_allocation().width, self.get_allocation().height
        # frame size
        fw, fh = self.timeline.frame_width, self.timeline.frame_height
        m = self.timeline.margin_top
        cr.set_source_rgba(0, 0, 0, 0.1)
        cr.paint()
        # draw layers
        self.strech_box_list = []
        for nl, l in enumerate(self.timeline.layers):
            self.strech_box_list.append([])
            x = nl * fw + 1
            lenn = len(l)-1
            first = True
            for nf, f in enumerate(l):
                y = nf*fh+m
                if f:
                    first = False
                    self.draw_mask(cr, self.sh, x, y, 50, fh)
                    cr.rectangle(x, y, 50, 1)
                    cr.set_source_rgb(0, 0, 0)
                    cr.fill()
                    self.draw_strech(cr, x+fw-12, y-11, nl)
                elif not first:
                    self.draw_mask(cr, self.nosh, x, y, 50, fh)
                # draw last line and strech
                if nf == lenn:
                    cr.rectangle(x, y+fh, 50, 1)
                    cr.set_source_rgb(0, 0, 0)
                    cr.fill()
                    self.draw_strech(cr, x+fw-12, y+fh-11, nl)
                        
            # between layer
            cr.rectangle(x+fw-1, 0, 1, wh)
            cr.set_source_rgb(0, 0, 0)
            cr.fill();
        # before layer
        cr.rectangle(0, 0, 1, wh)
        cr.set_source_rgb(0, 0, 0)
        cr.fill();
        # border
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, ww, 1)
        cr.fill();
        # current frame
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, self.timeline.current*fh+m, ww, 1)
        cr.rectangle(0, self.timeline.current*fh+fh+m, ww, 1)
        cr.fill();
    
    def clic(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            frame = (int(event.y)-1-self.timeline.margin_top)//self.timeline.frame_height
            print(frame)
            print('clic')
            x, y = event.x, event.y
            self.strech_frame = False
            for l, i in enumerate(self.strech_box_list):
                for f, j in enumerate(i):
                    if j[0] < x < j[0]+j[2] and j[1] < y < j[1]+j[3]:
                        self.strech_frame = (l, frame, False)
                        print('streeeeech')
                        return True
            self.timeline.emit('change_current_frame', frame)
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
                self.timeline.layers[sl].insert(sf+1, 0)
                sf += 1
            while f < sf:
                if not self.timeline.layers[sl][sf]:
                    self.timeline.layers[sl].pop(sf)
                    sf -= 1
                else:
                    break
            self.strech_frame = (sl, sf, True)
            
        self.resize()
        self.timeline.emit('change_current_frame', f)
        print('mooove')

    def release(self, widget, event):
        print('releaaaase')
        print('what')
        self.strech_frame = False


class Gridd(Gtk.Grid):
    
    def __init__(self):
        Gtk.Grid.__init__(self)
        li = [[0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0], [1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0]]
        self.timeline = Timeline(li)
        self.timeline_widget = TimelineWidget(self.timeline)
        self.scroll_timeline = Gtk.ScrolledWindow()
        self.scroll_timeline.add(self.timeline_widget)
        self.scroll_timeline.set_hexpand(True)
        self.scroll_timeline.set_vexpand(True)
        self.scroll_timeline.set_min_content_height(600)
        self.scroll_timeline.set_min_content_width(100)
        
        self.frame_widget = FrameWidget(self.timeline)
        self.scroll_frame = Gtk.ScrolledWindow()
        self.scroll_frame.set_vadjustment(self.scroll_timeline.get_vadjustment())
        self.scroll_frame.get_vscrollbar().hide()
        self.scroll_frame.get_hscrollbar().hide()
        self.scroll_frame.add(self.frame_widget)
        self.scroll_frame.set_min_content_width(30)
        self.scroll_frame.set_vexpand(True)
        self.timeline_widget.connect('size_changed', self.frame_widget.resize)
        
        self.layer_widget = LayerWidget(self.timeline)
        self.scroll_layer = Gtk.ScrolledWindow()
        self.scroll_layer.set_hadjustment(self.scroll_timeline.get_hadjustment())
        self.scroll_layer.get_vscrollbar().hide()
        self.scroll_layer.get_hscrollbar().hide()
        self.scroll_layer.add(self.layer_widget)
        self.scroll_layer.set_min_content_height(40)
        self.scroll_layer.set_hexpand(True)
        self.timeline_widget.connect('size_changed', self.layer_widget.resize)
        
        # try to use wheel value
        self.scroll_timeline.add_events(Gdk.EventMask.SCROLL_MASK)
        self.scroll_timeline.connect('scroll_event', self.send_scroll)
        
        self.size_adjustment = Gtk.Adjustment(value=self.timeline.frame_height, lower=0, upper=3, step_incr=1)
        self.scale = Gtk.Scale(orientation=0, adjustment=self.size_adjustment)
        # how to hide value without lose increment
        #~ self.scale.set_property('draw_value', False)
        self.scale.set_property('digits', 0)
        self.size_adjustment.connect('value-changed', self.timeline.set_frame_height)
        
        
        self.attach(self.scale, 0, 0, 2, 1)
        self.attach(self.scroll_layer, 1, 1, 1, 1)
        self.attach(self.scroll_frame, 0, 2, 1, 1)
        self.attach(self.scroll_timeline, 1, 2, 1, 1)
        self.set_property('margin', 10)
        
    def send_scroll(self, ar, gs):
        pass
        #~ self.vscroll.emit('scroll_event', gs)


class Window(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self, title='timeline')
        grid = Gridd()
        self.add(grid)
        
win = Window()
win.connect('delete-event', Gtk.main_quit)
win.show_all()
Gtk.main()

