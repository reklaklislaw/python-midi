from pprint import pformat, pprint
from copy import copy

import midi

class Pattern(list):
    def __init__(self, tracks=[], resolution=220, format=1):
        self.format = format
        self.resolution = resolution
        super(Pattern, self).__init__(tracks)

    def __repr__(self):
        return "midi.Pattern(format=%r, resolution=%r, tracks=\\\n%s)" % \
            (self.format, self.resolution, pformat(list(self)))

    def make_ticks_abs(self):
        for track in self:
            track.make_ticks_abs()

    def make_ticks_rel(self):
        for track in self:
            track.make_ticks_rel()
            
    def __getitem__(self, item):
        if isinstance(item, slice):
            indices = item.indices(len(self))
            return Pattern(resolution=self.resolution, format=self.format,
                            tracks=(super(Pattern, self).__getitem__(i) for i in range(*indices)))
        else:
            return super(Pattern, self).__getitem__(item)
            
    def __getslice__(self, i, j):
        # The deprecated __getslice__ is still called when subclassing built-in types
        # for calls of the form List[i:j]
        return self.__getitem__(slice(i,j))

class Track(list):
    def make_ticks_abs(self):
        running_tick = 0
        for event in self:
            event.tick += running_tick
            running_tick = event.tick

    def make_ticks_rel(self):
        running_tick = 0
        for event in self:
            event.tick -= running_tick
            running_tick += event.tick

    def __getitem__(self, item):
        if isinstance(item, slice):
            indices = item.indices(len(self))
            return Track((super(Track, self).__getitem__(i) for i in range(*indices)))
        else:
            return super(Track, self).__getitem__(item)
            
    def __getslice__(self, i, j):
        # The deprecated __getslice__ is still called when subclassing built-in types
        # for calls of the form List[i:j]
        return self.__getitem__(slice(i,j))

    def __repr__(self):
        return "midi.Track(\\\n  %s)" % (pformat(list(self)).replace('\n', '\n  '), )

    def align_to_note(self, track, note_pos, self_pos=0):
        note_pos -= 1
        note_pos *= 2 #double the value to account for off events
        note_pos_tick = track[note_pos].tick
        tick_diff = self[self_pos].tick - note_pos_tick
        for num, event in enumerate(self):
            event.tick -= tick_diff
                    
    def transpose(self, interval):
        new_track = Track()
        for num, event in enumerate(self):
            etype = type(event).__name__
            if etype == 'EndOfTrackEvent':
                eot = midi.EndOfTrackEvent(tick=1)
                new_track.append(eot)
                continue
            else:
                EventObj = getattr(midi, etype)
            new_event = EventObj(channel=event.channel,
                                 tick=event.tick,
                                 data=copy(event.data))
            new_track.append(new_event)
            data = new_track[num].data
            if not data:
                continue
            pitch, velocity = data
            pitch += interval
            if pitch not in range(0, 144):
                raise Exception('Transposition results in notes out of range.')
            else:
                data[0] = pitch
        return new_track

