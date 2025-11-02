from assistant.audio.recorder import Recorder as recorder
import sounddevice as sd

print("Available devices:")
for idx, dev in enumerate(sd.query_devices()):
    if dev.get("max_input_channels", 0) > 0:
        sr = int(dev.get("default_samplerate", 0))
        print(f"[{idx}] {dev.get('name', '?')}  (in: {dev.get('max_input_channels')}, sr: {sr})")

idx = int(input("Pick device index: "))
rec = recorder(device_index=idx, frame_length=1024)
rec.start()
print("OK: started")
rec.stop()
print("OK: stopped/deleted")
