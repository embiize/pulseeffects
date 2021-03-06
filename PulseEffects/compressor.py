# -*- coding: utf-8 -*-

import logging
import os

import gi
import numpy as np
gi.require_version('Gst', '1.0')
gi.require_version('GstInsertBin', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GObject, Gst, GstInsertBin, Gtk

Gst.init(None)


class Compressor():

    def __init__(self):
        self.settings = None
        self.module_path = os.path.dirname(__file__)

        self.log = logging.getLogger('PulseEffects')

        if Gst.ElementFactory.make('calf-sourceforge-net-plugins-Compressor'):
            self.is_installed = True
        else:
            self.is_installed = False

            self.log.warn('Compressor plugin was not found. Disabling it!')

        self.build_bin()

    def on_filter_added(self, bin, element, success, user_data):
        pass

    def build_bin(self):
        self.compressor = Gst.ElementFactory.make(
            'calf-sourceforge-net-plugins-Compressor', None)
        self.input_level = Gst.ElementFactory.make('level',
                                                   'compressor_input_level')
        self.output_level = Gst.ElementFactory.make('level',
                                                    'compressor_output_level')

        self.bin = GstInsertBin.InsertBin.new('compressor_bin')

        if self.is_installed:
            # booleans are inverted in GStreamer versions older than 1.12.5

            registry = Gst.Registry().get()
            self.use_workaround = not registry\
                .check_feature_version('pulsesrc', 1, 12, 5)

            if self.use_workaround:
                self.compressor.set_property('bypass', True)
            else:
                self.compressor.set_property('bypass', False)

            self.bin.append(self.input_level, self.on_filter_added, None)
            self.bin.append(self.compressor, self.on_filter_added, None)
            self.bin.append(self.output_level, self.on_filter_added, None)

    def post_messages(self, state):
        self.input_level.set_property('post-messages', state)
        self.output_level.set_property('post-messages', state)

    def init_ui(self):
        self.builder = Gtk.Builder.new_from_file(self.module_path +
                                                 '/ui/compressor.glade')
        self.builder.connect_signals(self)

        self.ui_window = self.builder.get_object('window')
        self.ui_controls = self.builder.get_object('controls')
        self.ui_listbox_control = self.builder.get_object('listbox_control')

        self.ui_enable = self.builder.get_object('enable')
        self.ui_img_state = self.builder.get_object('img_state')
        self.ui_compressor_detection_rms = self.builder.get_object(
            'detection_rms')
        self.ui_compressor_detection_peak = self.builder.get_object(
            'detection_peak')
        self.ui_stereo_link_average = self.builder.get_object(
            'stereo_link_average')
        self.ui_stereo_link_maximum = self.builder.get_object(
            'stereo_link_maximum')
        self.ui_mix = self.builder.get_object('mix')
        self.ui_attack = self.builder.get_object('attack')
        self.ui_release = self.builder.get_object('release')
        self.ui_threshold = self.builder.get_object('threshold')
        self.ui_ratio = self.builder.get_object('ratio')
        self.ui_knee = self.builder.get_object('knee')
        self.ui_makeup = self.builder.get_object('makeup')

        self.ui_input_level_left = self.builder.get_object('input_level_left')
        self.ui_input_level_right = self.builder.get_object(
            'input_level_right')
        self.ui_output_level_left = self.builder.get_object(
            'output_level_left')
        self.ui_output_level_right = self.builder.get_object(
            'output_level_right')
        self.ui_compression_levelbar = self.builder.get_object(
            'compression_levelbar')

        self.ui_input_level_left_label = self.builder.get_object(
            'input_level_left_label')
        self.ui_input_level_right_label = self.builder.get_object(
            'input_level_right_label')
        self.ui_output_level_left_label = self.builder.get_object(
            'output_level_left_label')
        self.ui_output_level_right_label = self.builder.get_object(
            'output_level_right_label')
        self.ui_compression_level_label = self.builder.get_object(
            'compression_level_label')

    def bind(self):
        # binding ui widgets to gsettings

        flag = Gio.SettingsBindFlags.DEFAULT

        self.settings.bind('state', self.ui_enable, 'active', flag)
        self.settings.bind('state', self.ui_img_state, 'visible', flag)
        self.settings.bind('state', self.ui_controls, 'sensitive',
                           Gio.SettingsBindFlags.GET)

        self.settings.bind('detection-rms', self.ui_compressor_detection_rms,
                           'active', flag)
        self.settings.bind('detection-rms', self.ui_compressor_detection_peak,
                           'active',
                           flag | Gio.SettingsBindFlags.INVERT_BOOLEAN)

        self.settings.bind('stereo-link-average',
                           self.ui_stereo_link_average, 'active', flag)
        self.settings.bind('stereo-link-average',
                           self.ui_stereo_link_maximum, 'active',
                           flag | Gio.SettingsBindFlags.INVERT_BOOLEAN)

        self.settings.bind('mix', self.ui_mix, 'value', flag)
        self.settings.bind('attack', self.ui_attack, 'value', flag)
        self.settings.bind('release', self.ui_release, 'value', flag)
        self.settings.bind('threshold', self.ui_threshold, 'value', flag)
        self.settings.bind('ratio', self.ui_ratio, 'value', flag)
        self.settings.bind('knee', self.ui_knee, 'value', flag)
        self.settings.bind('makeup', self.ui_makeup, 'value', flag)

        # binding ui widgets to gstreamer plugins

        flag = GObject.BindingFlags.BIDIRECTIONAL | \
            GObject.BindingFlags.SYNC_CREATE

        self.ui_attack.bind_property('value', self.compressor, 'attack', flag)
        self.ui_release.bind_property(
            'value', self.compressor, 'release', flag)
        self.ui_ratio.bind_property('value', self.compressor, 'ratio', flag)

    def on_threshold_value_changed(self, obj):
        value_db = obj.get_value()
        value_linear = 10**(value_db / 20.0)

        self.compressor.set_property('threshold', value_linear)

    def on_knee_value_changed(self, obj):
        value_db = obj.get_value()
        value_linear = 10**(value_db / 20.0)

        self.compressor.set_property('knee', value_linear)

    def on_makeup_value_changed(self, obj):
        value_db = obj.get_value()
        value_linear = 10**(value_db / 20.0)

        self.compressor.set_property('makeup', value_linear)

    def on_mix_value_changed(self, obj):
        value_db = obj.get_value()
        value_linear = 10**(value_db / 20.0)

        self.compressor.set_property('mix', value_linear)

    def on_new_detection_type(self, obj):
        if obj.get_active():
            label = obj.get_label()

            if label == 'rms':
                self.compressor.set_property('detection', 'RMS')
            elif label == 'peak':
                self.compressor.set_property('detection', 'Peak')

    def on_new_stereo_link_type(self, obj):
        if obj.get_active():
            label = obj.get_label()

            if label == 'average':
                self.compressor.set_property('stereo-link', 'Average')
            elif label == 'maximum':
                self.compressor.set_property('stereo-link', 'Maximum')

    def ui_update_level(self, widgets, peak):
        left, right = peak[0], peak[1]

        widget_level_left = widgets[0]
        widget_level_right = widgets[1]
        widget_level_left_label = widgets[2]
        widget_level_right_label = widgets[3]

        if left >= -99:
            l_value = 10**(left / 10)
            widget_level_left.set_value(l_value)
            widget_level_left_label.set_text(str(round(left)))
        else:
            widget_level_left.set_value(0)
            widget_level_left_label.set_text('-99')

        if right >= -99:
            r_value = 10**(right / 10)
            widget_level_right.set_value(r_value)
            widget_level_right_label.set_text(str(round(right)))
        else:
            widget_level_right.set_value(0)
            widget_level_right_label.set_text('-99')

    def ui_update_input_level(self, peak):
        widgets = [self.ui_input_level_left, self.ui_input_level_right,
                   self.ui_input_level_left_label,
                   self.ui_input_level_right_label]

        self.ui_update_level(widgets, peak)

    def ui_update_output_level(self, peak):
        widgets = [self.ui_output_level_left, self.ui_output_level_right,
                   self.ui_output_level_left_label,
                   self.ui_output_level_right_label]

        self.ui_update_level(widgets, peak)

        compression = self.compressor.get_property('compression')

        self.ui_compression_levelbar.set_value(1 - compression)

        if compression > 0:
            compression = 20 * np.log10(compression)

            self.ui_compression_level_label.set_text(
                str(round(compression, 1)))

    def reset(self):
        self.settings.reset('state')
        self.settings.reset('detection-rms')
        self.settings.reset('stereo-link-average')
        self.settings.reset('mix')
        self.settings.reset('attack')
        self.settings.reset('release')
        self.settings.reset('threshold')
        self.settings.reset('ratio')
        self.settings.reset('knee')
        self.settings.reset('makeup')
