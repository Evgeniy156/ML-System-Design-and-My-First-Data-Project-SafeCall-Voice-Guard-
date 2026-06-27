"""SafeCall ML inference — ported from safecall_train/predict.py (ДЗ7).

Changes vs original:
- MODEL_DIR: hardcoded Windows path → os.environ["MODEL_PATH"]
- XLSR backbone: local_files_only removed (download/cache on first run in Docker)
- MAX_DURATION: 5.0 → 10.0 (production)
- SpoofClassifier: embedded (from train_xlsr_head.py)
- Precision: fp16 on CUDA, fp32 on CPU

Original metrics (ДЗ7):
- F1 = 0.927 (eval), Recall = 0.969, Precision = 0.871
- Threshold = 0.37 (cost-optimized for FN reduction)
"""
import os
import logging
import subprocess
import tempfile
import shutil
import torch
import torch.nn as nn
import torchaudio
import soundfile as sf
from transformers import Wav2Vec2Model, Wav2Vec2FeatureExtractor
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = Path(os.environ.get("MODEL_PATH", "/app/weights/best_xlsr_head.pth"))
THRESHOLD = float(os.environ.get("THRESHOLD", "0.37"))
XLSR_NAME = "facebook/wav2vec2-large-xlsr-53"
TARGET_SR = 16000
MAX_DURATION = 10.0
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
USE_HALF_PRECISION = DEVICE.type == "cuda"


def get_ffmpeg_executable() -> str:
    """Use system ffmpeg when present; otherwise use bundled imageio-ffmpeg."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


class SpoofClassifier(nn.Module):
    """MLP head: 1024 -> 256 -> 128 -> 1 (from train_xlsr_head.py, ДЗ7).

    Architecture: frozen XLSR-53 backbone extracts 1024-dim embeddings,
    this head classifies spoof vs bonafide.
    """

    def __init__(self, input_dim=1024, hidden_dim=256, dropout=0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class SafeCallPredictor:
    """Audio deepfake detector using XLSR-53 + MLP head.

    Loads model once at startup. Thread-safe for inference.
    """

    def __init__(self):
        logger.info(f"Loading model from {MODEL_PATH} (device={DEVICE})")
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model head not found: {MODEL_PATH}. "
                "Put best_xlsr_head.pth into ml_worker/weights and rebuild the image."
            )

        # Feature extractor — try local cache first, then download
        local_fe = MODEL_PATH.parent / "xlsr_feature_extractor"
        fe_path = str(local_fe) if local_fe.exists() else XLSR_NAME
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(fe_path)

        # XLSR-53 backbone (frozen; fp16 only on CUDA, fp32 on CPU)
        self.backbone = Wav2Vec2Model.from_pretrained(XLSR_NAME).to(DEVICE)
        self.backbone.eval()
        if USE_HALF_PRECISION:
            self.backbone.half()

        # Classification head (1.1 MB weights from ДЗ7 training)
        self.head = SpoofClassifier().to(DEVICE)
        self.head.load_state_dict(
            torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True),
            strict=False,
        )
        self.head.eval()
        self.threshold = THRESHOLD
        logger.info(f"Model loaded. Threshold={self.threshold}")

    def _read_audio(self, path: Path) -> tuple[torch.Tensor, int]:
        """Load audio via soundfile; mp3/ogg/m4a converted with ffmpeg."""
        ext = path.suffix.lower()
        if ext in (".wav", ".flac"):
            data, sr = sf.read(str(path), dtype="float32", always_2d=True)
            waveform = torch.from_numpy(data.T.copy())
            return waveform, sr

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(
                [
                    get_ffmpeg_executable(), "-y", "-i", str(path),
                    "-ac", "1", "-ar", str(TARGET_SR), tmp_path,
                ],
                check=True,
                capture_output=True,
            )
            data, sr = sf.read(tmp_path, dtype="float32", always_2d=True)
            waveform = torch.from_numpy(data.T.copy())
            return waveform, sr
        finally:
            os.unlink(tmp_path)

    def load_audio(self, path):
        """Load and preprocess audio: mono, 16kHz, max duration."""
        audio_path = Path(path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        waveform, sr = self._read_audio(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != TARGET_SR:
            waveform = torchaudio.functional.resample(waveform, sr, TARGET_SR)
        max_samples = int(MAX_DURATION * TARGET_SR)
        if waveform.shape[1] > max_samples:
            waveform = waveform[:, :max_samples]
        return waveform.squeeze(0), waveform.shape[1] / TARGET_SR

    @torch.no_grad()
    def predict(self, audio_path):
        """Run inference on a single audio file.

        Returns dict with verdict, probability, confidence.
        """
        import time

        start = time.time()
        waveform, duration = self.load_audio(audio_path)
        inputs = self.feature_extractor(
            waveform.numpy(),
            sampling_rate=TARGET_SR,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs.input_values.to(DEVICE)
        if USE_HALF_PRECISION:
            input_values = input_values.half()
        embedding = self.backbone(input_values).last_hidden_state.mean(dim=1)
        prob_spoof = torch.sigmoid(self.head(embedding.float())).item()
        is_spoof = prob_spoof >= self.threshold
        elapsed_ms = (time.time() - start) * 1000

        return {
            "verdict": "SPOOF" if is_spoof else "REAL",
            "is_spoof": is_spoof,
            "spoof_probability": round(prob_spoof, 4),
            "confidence": round(prob_spoof if is_spoof else (1 - prob_spoof), 4),
            "duration": round(duration, 2),
            "threshold": self.threshold,
            "processing_time_ms": round(elapsed_ms, 1),
            "model_version": "xlsr-53-head-v1",
        }
