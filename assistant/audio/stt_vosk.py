import vosk, json, struct

class VoskSTT:
    def __init__(self, model_path: str, sample_rate: int = 16000):
        self.model = vosk.Model(model_path)
        self.sr = sample_rate
        self.rec = vosk.KaldiRecognizer(self.model, self.sr)

    def accept(self, pcm) -> dict | None:
        sp = struct.pack("h" * len(pcm), *pcm)
        if self.rec.AcceptWaveform(sp):
            res = json.loads(self.rec.Result())
            return res
        return None

    def partial(self) -> dict:
        return json.loads(self.rec.PartialResult())