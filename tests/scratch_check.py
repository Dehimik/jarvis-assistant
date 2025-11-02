from assistant.audio.stt.registry import discover, list_registered
discover("configs/plugins.d/voice")
print(list_registered())
