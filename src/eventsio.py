import time
from copy import copy

import midi
import midi.sequencer.sequencer_alsa as S
from .sequencer import Sequencer, SequencerRead, SequencerWrite
from .containers import Track

class CustomSequencer(Sequencer):
    """ modified version to set notes of 0 velocity as 'NoteOffEvent's"""
    def __init__(self, **kwargs):
        super(CustomSequencer, self).__init__(**kwargs)

    def event_read(self):
        ev = S.event_input(self.client)
        #print (dir(ev))
        #if ev and (ev < 0): self._error(ev)
        if ev and ev.type in (S.SND_SEQ_EVENT_NOTEON, S.SND_SEQ_EVENT_NOTEOFF):
            if ev.type == S.SND_SEQ_EVENT_NOTEON and ev.data.note.velocity > 0:
                mev = midi.NoteOnEvent()
                mev.channel = ev.data.note.channel
                mev.pitch = ev.data.note.note
                mev.velocity = ev.data.note.velocity
            elif ev.type == S.SND_SEQ_EVENT_NOTEOFF or ev.data.note.velocity == 0:
                mev = midi.NoteOffEvent()
                mev.channel = ev.data.note.channel
                mev.pitch = ev.data.note.note
                mev.velocity = ev.data.note.velocity
            if ev.time.time.tv_nsec:
                # convert to ms
                mev.msdeay = \
                    (ev.time.time.tv_nsec / 1e6) + (ev.time.time.tv_sec * 1e3)
            else:
                mev.tick = ev.time.tick
            return mev
        else:
            return None


class CustomSequencerRead(CustomSequencer):
    DefaultArguments = {
      'sequencer_name':'__SequencerRead__',
      'sequencer_stream':not S.SND_SEQ_NONBLOCK,
      'alsa_port_caps':S.SND_SEQ_PORT_CAP_WRITE | S.SND_SEQ_PORT_CAP_SUBS_WRITE,
    }

    def __init__(self, **kwargs):
        super(CustomSequencerRead, self).__init__(**kwargs)

    def subscribe_port(self, client, port):
        sender = self._new_address(client, port)
        dest = self._my_address()
        subscribe = self._new_subscribe(sender, dest, read=True)
        S.snd_seq_port_subscribe_set_time_update(subscribe, True)
        #S.snd_seq_port_subscribe_set_time_real(subscribe, True)
        self._subscribe_port(subscribe)


class EventIO(object):
    
    def __init__(self, client=20, port=1):
        self.client = client
        self.port = port
        
    def listen(self, resolution=220):
        seq = CustomSequencerRead(sequencer_resolution=resolution)
        seq.subscribe_port(self.client, self.port)
        seq.start_sequencer()
        track = Track()
        try:
            while True:
                event = seq.event_read()
                if event is not None:
                    track.append(event)
        except KeyboardInterrupt:
            eot = midi.EndOfTrackEvent(tick=1)
            track.append(eot)
            return track

    def play(self, pattern):
        seq = SequencerWrite(sequencer_resolution=pattern.resolution)
        seq.subscribe_port(self.client, self.port)
        seq.start_sequencer()
        for track in pattern:
            for num, event in enumerate(track):               
                buf = seq.event_write(event, False, False, True)
                if buf == None:
                    continue
                elif buf < 1000:
                    time.sleep(0.5)
                if num == len(track)-2:
                    ticks = event.tick
        seconds = ticks_to_seconds(seq.sequencer_tempo, 
                                   pattern.resolution, ticks)
        time.sleep(seconds)
            
def ticks_to_seconds(tempo, resolution, ticks):
    milliseconds = float(60 * 10000) / tempo
    seconds = ((milliseconds/resolution) / 10000.0) * ticks
    return seconds


    
