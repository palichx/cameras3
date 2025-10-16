from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid

# ============ CAMERA MODELS ============

class MOG2Settings(BaseModel):
    history: int = Field(default=500, description="Кол-во кадров в истории фона")
    var_threshold: float = Field(default=16.0, description="Порог дисперсии для определения движения")
    detect_shadows: bool = Field(default=True, description="Детектировать тени")
    learning_rate: float = Field(default=-1, description="Скорость обучения фона (-1 = автоматически)")
    n_mixtures: int = Field(default=5, description="Количество гауссовых компонент")

class MotionSettings(BaseModel):
    enabled: bool = Field(default=False, description="Включить детекцию движения")
    mog2: MOG2Settings = Field(default_factory=MOG2Settings)
    min_area: int = Field(default=500, description="Минимальная площадь объекта")
    min_duration_seconds: int = Field(default=1, description="Игнорировать движения короче X секунд (0-10)")
    pre_record_seconds: int = Field(default=5, description="Предзапись (сек) - запись начнется за N секунд до движения")
    post_record_seconds: int = Field(default=10, description="Постзапись (сек) - запись продолжится N секунд после движения")
    exclusion_zones: List[List[List[int]]] = Field(
        default_factory=list,
        description="Зоны исключения из детекции [[x1,y1], [x2,y2], ...]"
    )

class RecordingSettings(BaseModel):
    continuous: bool = Field(default=False, description="Непрерывная запись")
    on_motion: bool = Field(default=True, description="Запись по движению")
    storage_path: str = Field(default="/app/recordings", description="Путь для сохранения")
    max_file_duration_minutes: int = Field(default=60, description="Максимальная длительность файла")

class TelegramSettings(BaseModel):
    send_alerts: bool = Field(default=False, description="Отправлять уведомления о движении")
    send_video_clips: bool = Field(default=False, description="Отправлять видео клипы")

class CameraCreate(BaseModel):
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    motion: MotionSettings = Field(default_factory=MotionSettings)
    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

class Camera(CameraCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field(default="inactive", description="Status: active, inactive, error")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_motion_at: Optional[str] = None

# ============ RECORDING MODELS ============

class Recording(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    camera_id: str
    camera_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    record_type: str = Field(description="continuous or motion")
    file_path: str
    file_size: int = Field(default=0)
    thumbnail_path: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ GLOBAL SETTINGS MODELS ============

class PerformanceProfile(BaseModel):
    name: str
    description: str
    max_resolution_width: int
    target_fps: int
    jpeg_quality: int
    motion_check_interval: float  # seconds

class GlobalSettings(BaseModel):
    id: str = Field(default="global")
    performance_profile: str = Field(
        default="medium",
        description="Профиль производительности: low, medium, high"
    )
    profiles: Dict[str, PerformanceProfile] = Field(
        default_factory=lambda: {
            "low": PerformanceProfile(
                name="Слабые системы",
                description="Минимальная нагрузка на CPU",
                max_resolution_width=640,
                target_fps=10,
                jpeg_quality=50,
                motion_check_interval=0.2
            ),
            "medium": PerformanceProfile(
                name="Средние системы",
                description="Сбалансированная производительность",
                max_resolution_width=1280,
                target_fps=15,
                jpeg_quality=70,
                motion_check_interval=0.1
            ),
            "high": PerformanceProfile(
                name="Мощные системы",
                description="Максимальное качество",
                max_resolution_width=1920,
                target_fps=25,
                jpeg_quality=85,
                motion_check_interval=0.05
            )
        }
    )
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    default_storage_path: str = Field(default="/app/recordings")

class GlobalSettingsUpdate(BaseModel):
    performance_profile: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    default_storage_path: Optional[str] = None
