import logging
import re

import evdev
import evdev.ecodes

LOGGER = logging.getLogger(__name__)


class NoInputDevice(Exception):
    pass


class EventListener(object):
    def __init__(self, device_path=None, device_match=None, exclusive=False):
        self.device = None

        if device_path:
            self.device_path = device_path
            self.device = evdev.InputDevice(device_path)
        elif device_match:
            for device in [evdev.InputDevice(f) for f in evdev.list_devices()]:
                LOGGER.debug('Matching "%s" on "%s"' % (
                    device_match, device.name))

                if re.match('.*%s.*' % device_match, device.name):
                    LOGGER.debug('Matched %s' % device.name)
                    self.device = device

        if not self.device:
            raise NoInputDevice('no device found')

        if exclusive:
            self.device.grab()

    def get_events(self):
        mods = {'ctrl': False,
                'alt': False,
                'shift': False}

        for event in self.device.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                code = event.code
                value = event.value

                if value == 0:
                    state = 'up'
                elif value == 1:
                    state = 'down'
                elif value == 2:
                    state = 'hold'
                else:
                    continue

                key = evdev.ecodes.bytype[evdev.ecodes.EV_KEY][code]
                key = key.split('_', 1)[1].lower()

                emit = True
                for mod in mods:
                    if mod in key:
                        mods[mod] = (state == 'down')
                        emit = False

                active = [k for k, v in mods.iteritems() if v]
                mod = '-'.join(sorted(active))

                if mod:
                    key = '%s-%s' % (mod, key)

                if emit:
                    yield (key, state)

    @classmethod
    def dump_inputs(self):
        for device in [evdev.InputDevice(f) for f in evdev.list_devices()]:
            print '%-20s %-20s' % (
                device.fn, device.name)
