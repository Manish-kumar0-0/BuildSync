from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings
from app.services.vision.opencv_service import PreparedImage


class YOLOError(RuntimeError):
    """A safe YOLO configuration or inference error."""


@dataclass(frozen=True)
class Detection:
    class_name: str
    confidence: float
    bbox: dict[str, int]


@dataclass(frozen=True)
class ModelMetadata:
    filename: str
    model_type: str
    available_classes: list[str]


_model = None
_model_path: str | None = None
_model_metadata: ModelMetadata | None = None
_model_lock = Lock()


def _load_model():
    global _model, _model_path, _model_metadata
    model_path = settings.yolo_model_path
    if not model_path:
        raise YOLOError("YOLO_MODEL_PATH is not configured")
    path = Path(model_path)
    if not path.is_file():
        raise YOLOError("Configured YOLO model is unavailable")
    if _model is None or _model_path != str(path):
        with _model_lock:
            if _model is None or _model_path != str(path):
                try:
                    from ultralytics import YOLO
                    _model = YOLO(str(path))
                    _model_path = str(path)
                    classes = _class_names(_model)
                    invalid_classes = sorted(
                        set(settings.yolo_classes) - set(classes)
                    )
                    if invalid_classes:
                        _model = None
                        _model_path = None
                        raise YOLOError(
                            "YOLO_CLASSES contains classes unavailable in the "
                            f"configured model: {', '.join(invalid_classes)}"
                        )
                    _model_metadata = ModelMetadata(
                        filename=path.name,
                        model_type=str(getattr(_model, "task", "unknown")),
                        available_classes=classes,
                    )
                except ImportError as exc:
                    raise YOLOError("YOLO provider is not installed") from exc
                except YOLOError:
                    raise
                except Exception as exc:
                    raise YOLOError("Configured YOLO model could not be loaded") from exc
    return _model


def _class_names(model: Any) -> list[str]:
    names = model.names
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names)]
    return [str(name) for name in names]


def _configured_classes(model: Any) -> set[str]:
    available = set(_class_names(model))
    invalid = sorted(set(settings.yolo_classes) - available)
    if invalid:
        raise YOLOError(
            "YOLO_CLASSES contains classes unavailable in the configured "
            f"model: {', '.join(invalid)}"
        )
    return set(settings.yolo_classes)


def detect(prepared: PreparedImage) -> list[dict]:
    model = _load_model()
    try:
        results = model.predict(source=prepared.image, verbose=False)
        names = model.names
        allowed = _configured_classes(model)
        detections: list[dict] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box, confidence, class_id in zip(
                boxes.xyxy.tolist(),
                boxes.conf.tolist(),
                boxes.cls.tolist(),
            ):
                class_name = str(names[int(class_id)])
                if allowed and class_name not in allowed:
                    continue
                detections.append(asdict(Detection(
                    class_name=class_name,
                    confidence=round(float(confidence), 4),
                    bbox={
                        "x1": int(box[0]), "y1": int(box[1]),
                        "x2": int(box[2]), "y2": int(box[3]),
                    },
                )))
        return detections
    except YOLOError:
        raise
    except Exception as exc:
        raise YOLOError("YOLO inference could not be completed") from exc


def supported_classes() -> list[str]:
    return list(model_metadata().available_classes)


def model_metadata() -> ModelMetadata:
    _load_model()
    if _model_metadata is None:
        raise YOLOError("YOLO model metadata is unavailable")
    return _model_metadata


def detection_counts(detections: list[dict]) -> Counter[str]:
    return Counter(item["class_name"] for item in detections)
