from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import json
import base64
from camera_manager import CameraManager
from models import Camera, CameraCreate, Recording, GlobalSettings, GlobalSettingsUpdate

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize camera manager
camera_manager = CameraManager(db)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CAMERA ENDPOINTS ============

@api_router.get("/cameras", response_model=List[Camera])
async def get_cameras():
    """Get all cameras"""
    cameras = await db.cameras.find({}, {"_id": 0}).to_list(1000)
    return cameras

@api_router.get("/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str):
    """Get camera by ID"""
    camera = await db.cameras.find_one({"id": camera_id}, {"_id": 0})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@api_router.post("/cameras", response_model=Camera)
async def create_camera(camera_data: CameraCreate):
    """Add new camera"""
    # Check camera limit
    count = await db.cameras.count_documents({})
    if count >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 cameras allowed")
    
    camera_dict = camera_data.model_dump()
    camera_obj = Camera(**camera_dict)
    doc = camera_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.cameras.insert_one(doc)
    
    # Start camera processing
    await camera_manager.start_camera(camera_obj.id, camera_obj)
    
    return camera_obj

@api_router.put("/cameras/{camera_id}", response_model=Camera)
async def update_camera(camera_id: str, camera_data: CameraCreate):
    """Update camera settings"""
    camera = await db.cameras.find_one({"id": camera_id}, {"_id": 0})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Stop current processing
    await camera_manager.stop_camera(camera_id)
    
    # Update camera
    camera_dict = camera_data.model_dump()
    camera_dict['id'] = camera_id
    camera_dict['created_at'] = camera['created_at']
    
    camera_obj = Camera(**camera_dict)
    doc = camera_obj.model_dump()
    doc['created_at'] = doc['created_at'] if isinstance(doc['created_at'], str) else doc['created_at'].isoformat()
    
    await db.cameras.replace_one({"id": camera_id}, doc)
    
    # Restart camera processing
    await camera_manager.start_camera(camera_id, camera_obj)
    
    return camera_obj

@api_router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete camera"""
    result = await db.cameras.delete_one({"id": camera_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Stop camera processing
    await camera_manager.stop_camera(camera_id)
    
    return {"message": "Camera deleted"}

@api_router.post("/cameras/{camera_id}/test")
async def test_camera_connection(camera_id: str):
    """Test camera connection"""
    camera = await db.cameras.find_one({"id": camera_id}, {"_id": 0})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    result = await camera_manager.test_connection(Camera(**camera))
    return result

# ============ LIVE VIEW ENDPOINTS ============

@api_router.websocket("/live/{camera_id}")
async def websocket_live_stream(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for live camera stream"""
    await websocket.accept()
    
    try:
        camera = await db.cameras.find_one({"id": camera_id}, {"_id": 0})
        if not camera:
            await websocket.send_json({"error": "Camera not found"})
            await websocket.close()
            return
        
        # Subscribe to camera frames
        async for frame_data in camera_manager.get_live_stream(camera_id):
            if frame_data:
                await websocket.send_json({
                    "frame": frame_data["frame"],
                    "timestamp": frame_data["timestamp"]
                })
            await asyncio.sleep(0.033)  # ~30 fps
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for camera {camera_id}")
    except Exception as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await websocket.close()

# ============ RECORDING ENDPOINTS ============

@api_router.get("/recordings", response_model=List[Recording])
async def get_recordings(
    camera_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    record_type: Optional[str] = None
):
    """Get recordings with filters"""
    query = {}
    if camera_id:
        query['camera_id'] = camera_id
    if record_type:
        query['record_type'] = record_type
    if start_date or end_date:
        query['start_time'] = {}
        if start_date:
            query['start_time']['$gte'] = start_date
        if end_date:
            query['start_time']['$lte'] = end_date
    
    recordings = await db.recordings.find(query, {"_id": 0}).sort("start_time", -1).to_list(1000)
    return recordings

@api_router.get("/recordings/{recording_id}", response_model=Recording)
async def get_recording(recording_id: str):
    """Get recording by ID"""
    recording = await db.recordings.find_one({"id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording

@api_router.get("/recordings/{recording_id}/video")
async def get_recording_video(recording_id: str, speed: Optional[float] = 1.0):
    """Stream recording video"""
    recording = await db.recordings.find_one({"id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    file_path = Path(recording['file_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(file_path, media_type="video/mp4")

@api_router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete recording"""
    recording = await db.recordings.find_one({"id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Delete file
    file_path = Path(recording['file_path'])
    if file_path.exists():
        file_path.unlink()
    
    # Delete from database
    await db.recordings.delete_one({"id": recording_id})
    
    return {"message": "Recording deleted"}

# ============ GLOBAL SETTINGS ENDPOINTS ============

@api_router.get("/settings", response_model=GlobalSettings)
async def get_settings():
    """Get global settings"""
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not settings:
        # Create default settings
        default_settings = GlobalSettings()
        doc = default_settings.model_dump()
        await db.settings.insert_one(doc)
        return default_settings
    return GlobalSettings(**settings)

@api_router.put("/settings", response_model=GlobalSettings)
async def update_settings(settings_data: GlobalSettingsUpdate):
    """Update global settings"""
    current_settings = await db.settings.find_one({"id": "global"}, {"_id": 0})
    
    if current_settings:
        settings_dict = settings_data.model_dump(exclude_unset=True)
        settings_dict['id'] = 'global'
        await db.settings.replace_one({"id": "global"}, {**current_settings, **settings_dict})
        updated = await db.settings.find_one({"id": "global"}, {"_id": 0})
        return GlobalSettings(**updated)
    else:
        settings_obj = GlobalSettings(**settings_data.model_dump(exclude_unset=True))
        doc = settings_obj.model_dump()
        await db.settings.insert_one(doc)
        return settings_obj

# ============ STATISTICS ENDPOINTS ============

@api_router.get("/stats")
async def get_stats():
    """Get system statistics"""
    total_cameras = await db.cameras.count_documents({})
    active_cameras = len(camera_manager.active_cameras)
    total_recordings = await db.recordings.count_documents({})
    
    # Calculate total storage used
    recordings = await db.recordings.find({}, {"file_size": 1, "_id": 0}).to_list(10000)
    total_storage = sum(r.get('file_size', 0) for r in recordings)
    
    return {
        "total_cameras": total_cameras,
        "active_cameras": active_cameras,
        "total_recordings": total_recordings,
        "total_storage_bytes": total_storage,
        "storage_available": True
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start all cameras on startup"""
    logger.info("Starting camera manager...")
    cameras = await db.cameras.find({}, {"_id": 0}).to_list(1000)
    for camera_data in cameras:
        camera = Camera(**camera_data)
        asyncio.create_task(camera_manager.start_camera(camera.id, camera))
    logger.info(f"Started {len(cameras)} cameras")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop all cameras on shutdown"""
    logger.info("Stopping camera manager...")
    await camera_manager.stop_all()
    client.close()
