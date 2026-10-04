"""Smart Campus AI engine: preprocessing, features, models, detection, risk scoring."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "data" / "results"
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / "anomaly_model.pkl"
