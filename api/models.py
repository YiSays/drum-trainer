"""
API 数据模型
"""

from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class TrackInfo(BaseModel):
    """音轨信息模型"""
    name: str
    path: str
    size: int
    duration: float
    samplerate: int
    channels: int
    extension: str


class TrackListResponse(BaseModel):
    """音轨列表响应模型"""
    tracks: List[TrackInfo]


class AudioInfo(BaseModel):
    """音频文件信息模型"""
    name: str
    size: int
    samplerate: int
    channels: int
    duration: float
    format: Optional[str] = None
    subtype: Optional[str] = None


class AnalysisResult(BaseModel):
    """分析结果模型"""
    style: str
    bpm: int
    energy: float
    key: str
    mood: str
    structure: List[Dict]
    rhythm_profile: Dict
    timestamp: Optional[str] = None


class ProcessResponse(BaseModel):
    """处理响应模型"""
    status: str
    analysis: Optional[AnalysisResult] = None
    files: Optional[Dict[str, str]] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    device: str
    model_loaded: bool
    default_model: Optional[str] = None
    shifts: Optional[int] = None
