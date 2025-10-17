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
    """Simple camera stream processor using FFmpeg - Live view only"""
    
    def __init__(self, camera: Camera, db, settings: GlobalSettings):
        self.camera = camera
        self.db = db
        self.settings = settings
        self.ffmpeg_process = None
        self.running = False
        self.last_frame = None
        
        # FFmpeg frame reading
        self.frame_width = None
        self.frame_height = None
        self.frame_size = None
        
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
        """Start FFmpeg process for frame extraction"""
        try:
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',  # TCP for stability
                '-i', url,
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
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
    
    # All recording, motion detection, and Telegram methods removed - live view only
    
    async def process_frame(self, frame):
        """Store frame for live view - no processing"""
        try:
            # Simply store frame for live view (copy to avoid race conditions)
            self.last_frame = frame.copy()
        
        except Exception as e:
            logger.error(f"Error storing frame: {e}")
    
    async def run(self):
        """Simple live view loop with FFmpeg - no recording, no processing"""
        try:
            self.running = True
            frame_counter = 0
            reconnect_attempts = 0
            max_reconnects = 5
            
            logger.info(f"Starting FFmpeg live stream for camera {self.camera.name}, resolution: {self.frame_width}x{self.frame_height}")
            
            while self.running:
                try:
                    # Check if FFmpeg process is alive
                    if not self.ffmpeg_process or self.ffmpeg_process.returncode is not None:
                        logger.warning(f"FFmpeg process died for camera {self.camera.name}, attempting reconnect ({reconnect_attempts}/{max_reconnects})")
                        
                        if reconnect_attempts >= max_reconnects:
                            logger.error(f"Max reconnection attempts reached for camera {self.camera.name}")
                            break
                        
                        # Reconnect
                        url = self.camera.url
                        if self.camera.username and self.camera.password:
                            if '://' in url:
                                protocol, rest = url.split('://', 1)
                                url = f"{protocol}://{self.camera.username}:{self.camera.password}@{rest}"
                        
                        self.ffmpeg_process = await self._start_ffmpeg(url)
                        if not self.ffmpeg_process:
                            await asyncio.sleep(5)
                            reconnect_attempts += 1
                            continue
                        
                        reconnect_attempts = 0
                        logger.info(f"Successfully reconnected camera {self.camera.name}")
                    
                    # Read raw frame from FFmpeg stdout (read until we have full frame)
                    raw_frame = b''
                    while len(raw_frame) < self.frame_size:
                        chunk = await self.ffmpeg_process.stdout.read(self.frame_size - len(raw_frame))
                        if not chunk:
                            break
                        raw_frame += chunk
                    
                    if len(raw_frame) != self.frame_size:
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Convert raw bytes to numpy array
                    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((self.frame_height, self.frame_width, 3))
                    
                    # Log first few frames
                    if frame_counter < 3:
                        logger.info(f"Received frame {frame_counter} for camera {self.camera.name}")
                    
                    # Simply store frame for live view
                    await self.process_frame(frame)
                    
                    frame_counter += 1
                
                except asyncio.CancelledError:
                    logger.info(f"Camera processing cancelled for {self.camera.name}")
                    break
                except Exception as e:
                    logger.error(f"Error in camera loop for {self.camera.name}: {e}")
                    await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Fatal error in camera run() for {self.camera.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_current_frame_jpeg(self) -> Optional[str]:
        """Get current frame as base64 JPEG"""
        if self.last_frame is None:
            return None
        
        try:
            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', self.last_frame, 
                [cv2.IMWRITE_JPEG_QUALITY, self.profile.jpeg_quality])
            jpg_base64 = base64.b64encode(buffer).decode('utf-8')
            return jpg_base64
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
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
            
            # Start processing task
            self.processors[camera_id] = processor
            self.active_cameras[camera_id] = True
            self.tasks[camera_id] = asyncio.create_task(processor.run())
            
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
    
    async def get_live_stream(self, camera_id: str) -> AsyncGenerator:
        """Get live stream frames for a camera"""
        if camera_id not in self.processors:
            logger.warning(f"Camera {camera_id} not found in processors")
            return
        
        logger.info(f"Starting live stream for camera {camera_id}")
        frame_count = 0
        
        while camera_id in self.processors:
            processor = self.processors[camera_id]
            frame_data = processor.get_current_frame_jpeg()
            
            if frame_data:
                frame_count += 1
                if frame_count % 30 == 0:  # Log every 30 frames
                    logger.info(f"Streaming frame {frame_count} for camera {camera_id}")
                
                yield {
                    "frame": frame_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                if frame_count % 10 == 0:
                    logger.warning(f"No frame data available for camera {camera_id}")
            
            await asyncio.sleep(0.05)  # Reduced delay for lower latency
