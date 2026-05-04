import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import mido

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class MidiToLmms:
    def __init__(self, midi_path):
        self.midi_path = midi_path
        self.mid = mido.MidiFile(midi_path)
        self.ppq = 192  # LMMS standard PPQ
        self.midi_ticks_per_beat = self.mid.ticks_per_beat
        self.conversion_factor = self.ppq / self.midi_ticks_per_beat
        self.vestige_plugin_path = "/media/master/ssd/vts3/plugin/build/libvst3instrument_core.so"

    def is_drum_track(self, track_name, channel):
        if channel == 9: # MIDI channel 10 is 9 in 0-indexed
            return True
        keywords = ["drum", "kick", "snare", "hihat", "clap", "percussion", "perc", "ride", "crash", "tom"]
        name_lower = track_name.lower()
        return any(kw in name_lower for kw in keywords)

    def ticks_to_lmms(self, ticks):
        return int(ticks * self.conversion_factor)

    def create_instrument_track(self, parent, name, plugin_type, plugin_path=None):
        it = ET.SubElement(parent, 'track', name=name, type="0", muted="0", solo="0")
        inst = ET.SubElement(it, 'instrument', name=plugin_type)
        
        if plugin_type == "sf2player":
            ET.SubElement(inst, 'sf2player', src=plugin_path or "", patch="0", bank="0", gain="1")
        elif plugin_type == "vestige":
            # For Vestige, we usually point to a VST file
            ET.SubElement(inst, 'vestige', executable=self.vestige_plugin_path)
        elif plugin_type == "audiofileprocessor":
            ET.SubElement(inst, 'audiofileprocessor', src=plugin_path or "")
        else:
            # Default to some basic instrument if unknown
            ET.SubElement(inst, plugin_type)
            
        return it

    def convert(self, output_path, global_plugin_choice=None):
        root = ET.Element('lmms-project', version="1.0", creator="MidiToLmmsExporter")
        head = ET.SubElement(root, 'head')
        
        song = ET.SubElement(root, 'song', type="0")
        
        # Main track containers
        song_tc = ET.SubElement(song, 'trackcontainer', type="song", x="5", y="5", width="600", height="300")
        bb_tc = ET.SubElement(song, 'trackcontainer', type="bbtrackcontainer", x="5", y="310", width="600", height="300")
        
        # We also need a BB track in the song container to trigger the BB container
        bb_trigger_track = ET.SubElement(song_tc, 'track', name="Beat/Bassline 0", type="2", muted="0", solo="0")
        bb_pattern = ET.SubElement(bb_trigger_track, 'pattern', name="Pattern 0", pos="0", len=str(self.ticks_to_lmms(self.mid.length * self.mid.ticks_per_beat)))

        for i, track in enumerate(self.mid.tracks):
            track_name = track.name if track.name else f"Track {i}"
            
            # Extract notes
            notes = []
            current_tick = 0
            pending_notes = {}
            
            is_drum = False
            channel = 0
            
            for msg in track:
                current_tick += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    channel = msg.channel
                    if self.is_drum_track(track_name, channel):
                        is_drum = True
                    pending_notes[msg.note] = (current_tick, msg.velocity)
                elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in pending_notes:
                        start_tick, velocity = pending_notes.pop(msg.note)
                        duration = current_tick - start_tick
                        notes.append({
                            'pos': self.ticks_to_lmms(start_tick),
                            'len': self.ticks_to_lmms(duration),
                            'key': msg.note,
                            'vol': int(velocity / 127 * 100)
                        })

            if not notes:
                continue

            # Determine plugin
            if is_drum:
                target_container = bb_tc
                plugin_type = "audiofileprocessor" # Default for drums in BB
                plugin_path = ""
            else:
                target_container = song_tc
                if global_plugin_choice == "sf2":
                    plugin_type = "sf2player"
                    plugin_path = ""
                elif global_plugin_choice == "vestige":
                    plugin_type = "vestige"
                    plugin_path = self.vestige_plugin_path
                else:
                    print(f"\nTrack: {track_name}")
                    print("1. Sf2Player")
                    print("2. Vestige (Vestige3 Bridge)")
                    print("3. AudioFileProcessor")
                    choice = input("Choose plugin (1-3): ")
                    if choice == "1":
                        plugin_type = "sf2player"
                        plugin_path = ""
                    elif choice == "2":
                        plugin_type = "vestige"
                        plugin_path = self.vestige_plugin_path
                    else:
                        plugin_type = "audiofileprocessor"
                        plugin_path = ""

            it_track = self.create_instrument_track(target_container, track_name, plugin_type, plugin_path)
            
            # For BB tracks, patterns work a bit differently, but LMMS can still read them.
            # In song editor, we need a pattern.
            pattern_len = max(n['pos'] + n['len'] for n in notes)
            pattern = ET.SubElement(it_track, 'pattern', name=track_name, pos="0", len=str(pattern_len))
            
            for n in notes:
                ET.SubElement(pattern, 'note', pos=str(n['pos']), len=str(n['len']), key=str(n['key']), vol=str(n['vol']))

        indent(root)
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"Exported to {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python midi_to_lmms.py <input.mid> [output.mmp]")
        return

    midi_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else midi_path.replace(".mid", ".mmp")
    
    if not os.path.exists(midi_path):
        print(f"Error: File {midi_path} not found.")
        return

    exporter = MidiToLmms(midi_path)
    
    print("Welcome to MIDI to LMMS Exporter")
    print("How would you like to map melodic tracks?")
    print("1. All to Sf2Player")
    print("2. All to Vestige3 (vts3)")
    print("3. Choose one by one")
    
    choice = input("Select option (1-3): ")
    global_choice = None
    if choice == "1":
        global_choice = "sf2"
    elif choice == "2":
        global_choice = "vestige"
    
    exporter.convert(output_path, global_choice)

if __name__ == "__main__":
    main()
