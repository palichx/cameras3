import asyncio
import cv2
import numpy as np
from datetime import datetime, timezone
import logging
import base64
from typing import Dict, Optional, AsyncGenerator
from models import Camera, GlobalSettings

logger = logging.getLogger(__name__)

class CameraProcessor:
    """FFmpeg MJPEG stream processor - Direct video stream"""
    
    def __init__(self, camera: Camera, db, settings: GlobalSettings):
        self.camera = camera
        self.db = db
        self.settings = settings
        self.ffmpeg_process = None
        
        # Stream dimensions
        self.frame_width = None
        self.frame_height = None
        
        # Get performance profile
        profile_name = settings.performance_profile
        self.profile = settings.profiles.get(profile_name, settings.profiles['medium'])
    
    async def connect(self) -> bool:
        """Connect to camera stream using FFmpeg"""
        try:
            # Build URL with credentials if provided
            url = self.camera.url
            if self.camera.username and self.camera.password:
                # Parse URL and inject credentials
                if '://' in url:
                    protocol, rest = url.split('://', 1)
                    url = f"{protocol}://{self.camera.username}:{self.camera.password}@{rest}"
            
            # First, probe the stream to get dimensions
            probe_success = await self._probe_stream(url)
            if not probe_success:
                logger.error(f"Failed to probe camera stream {self.camera.id}")
                return False
            
            # Start FFmpeg process
            self.ffmpeg_process = await self._start_ffmpeg(url)
            if not self.ffmpeg_process:
                logger.error(f"Failed to start FFmpeg for camera {self.camera.id}")
                return False
            
            logger.info(f"Connected to camera {self.camera.id} - {self.camera.name} via FFmpeg ({self.frame_width}x{self.frame_height})")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to camera {self.camera.id}: {e}")
            return False
    
    async def _probe_stream(self, url: str) -> bool:
        """Probe stream to get video dimensions"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0',
                '-rtsp_transport', 'tcp',
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            
            if process.returncode == 0 and stdout:
                dimensions = stdout.decode().strip().split(',')
                if len(dimensions) == 2:
                    self.frame_width = int(dimensions[0])
                    self.frame_height = int(dimensions[1])
                    
                    # Apply resolution limit from profile
                    if self.frame_width > self.profile.max_resolution_width:
                        ratio = self.profile.max_resolution_width / self.frame_width
                        self.frame_width = self.profile.max_resolution_width
                        self.frame_height = int(self.frame_height * ratio)
                    
                    self.frame_size = self.frame_width * self.frame_height * 3  # BGR
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error probing stream: {e}")
            return False
    
    async def _start_ffmpeg(self, url: str):
        """Start FFmpeg process for MJPEG stream output"""
        try:
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',  # TCP for stability
                '-i', url,
                '-f', 'mjpeg',  # MJPEG output format
                '-q:v', '5',  # Quality (2-31, lower is better)
                '-an',  # No audio
                '-fflags', 'nobuffer',  # Minimal buffering
                '-flags', 'low_delay',
                '-probesize', '32',
                '-analyzeduration', '0',
                '-vf', f'scale={self.frame_width}:{self.frame_height}',
                '-r', str(self.profile.target_fps),  # Target FPS
                'pipe:1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            return process
            
        except Exception as e:
            logger.error(f"Error starting FFmpeg: {e}")
            return None
    
    # No run() or process_frame() needed - FFmpeg streams directly to HTTP endpoint
    
    async def get_stream(self):
        """Get MJPEG stream generator from FFmpeg stdout"""
        if not self.ffmpeg_process:
            logger.error(f"FFmpeg process not started for camera {self.camera.name}")
            return
        
        try:
            logger.info(f"Starting MJPEG stream for camera {self.camera.name}")
            
            while True:
                # Read MJPEG frame from FFmpeg
                # MJPEG format: each frame starts with FFD8 (JPEG SOI marker)
                chunk = await self.ffmpeg_process.stdout.read(65536)  # 64KB chunks
                
                if not chunk:
                    logger.warning(f"Stream ended for camera {self.camera.name}")
                    break
                
                yield chunk
                
        except Exception as e:
            logger.error(f"Error streaming from camera {self.camera.name}: {e}")
    
    async def stop(self):
        """Stop live stream"""
        self.running = False
        
        # Terminate FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.ffmpeg_process.kill()
                await self.ffmpeg_process.wait()
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")


class CameraManager:
    """Manages all camera processors"""
    
    def __init__(self, db):
        self.db = db
        self.processors: Dict[str, CameraProcessor] = {}
        self.active_cameras: Dict[str, bool] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def get_settings(self) -> GlobalSettings:
        """Get global settings"""
        settings = await self.db.settings.find_one({"id": "global"}, {"_id": 0})
        if not settings:
            return GlobalSettings()
        return GlobalSettings(**settings)
    
    async def start_camera(self, camera_id: str, camera: Camera):
        """Start processing a camera"""
        # Stop if already running
        if camera_id in self.processors:
            await self.stop_camera(camera_id)
        
        try:
            # Get settings
            settings = await self.get_settings()
            
            # Create processor
            processor = CameraProcessor(camera, self.db, settings)
            
            # Connect to camera
            connected = await processor.connect()
            if not connected:
                await self.db.cameras.update_one(
                    {"id": camera_id},
                    {"$set": {"status": "error"}}
                )
                return
            
            # Store processor (no task needed - streaming on demand)
            self.processors[camera_id] = processor
            self.active_cameras[camera_id] = True
            
            # Update camera status
            await self.db.cameras.update_one(
                {"id": camera_id},
                {"$set": {"status": "active"}}
            )
            
            logger.info(f"Camera {camera.name} started successfully")
        
        except Exception as e:
            logger.error(f"Error starting camera {camera_id}: {e}")
            await self.db.cameras.update_one(
                {"id": camera_id},
                {"$set": {"status": "error"}}
            )
    
    async def stop_camera(self, camera_id: str):
        """Stop processing a camera"""
        if camera_id in self.processors:
            processor = self.processors[camera_id]
            await processor.stop()
            
            # Cancel task
            if camera_id in self.tasks:
                self.tasks[camera_id].cancel()
                try:
                    await self.tasks[camera_id]
                except asyncio.CancelledError:
                    pass
                del self.tasks[camera_id]
            
            del self.processors[camera_id]
            del self.active_cameras[camera_id]
            
            # Update status
            await self.db.cameras.update_one(
                {"id": camera_id},
                {"$set": {"status": "inactive"}}
            )
            
            logger.info(f"Camera {camera_id} stopped")
    
    async def stop_all(self):
        """Stop all cameras"""
        camera_ids = list(self.processors.keys())
        for camera_id in camera_ids:
            await self.stop_camera(camera_id)
    
    async def test_connection(self, camera: Camera) -> dict:
        """Test camera connection using FFprobe"""
        try:
            url = camera.url
            if camera.username and camera.password:
                if '://' in url:
                    protocol, rest = url.split('://', 1)
                    url = f"{protocol}://{camera.username}:{camera.password}@{rest}"
            
            # Use ffprobe to test connection
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,codec_name',
                '-of', 'json',
                '-rtsp_transport', 'tcp',
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            except asyncio.TimeoutError:
                return {"success": False, "message": "Timeout при подключении к камере"}
            
            if process.returncode == 0 and stdout:
                import json
                data = json.loads(stdout.decode())
                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]
                    return {
                        "success": True,
                        "message": "Подключение успешно",
                        "resolution": f"{stream.get('width')}x{stream.get('height')}",
                        "codec": stream.get('codec_name')
                    }
            
            error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
            return {"success": False, "message": f"Не удалось подключиться: {error_msg[:100]}"}
        
        except Exception as e:
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    # get_live_stream removed - streaming now handled directly by HTTP endpoint
