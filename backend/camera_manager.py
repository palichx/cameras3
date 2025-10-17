import asyncio
import cv2
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import logging
import base64
from typing import Dict, Optional, AsyncGenerator
import aiofiles
from models import Camera, Recording, GlobalSettings
import os
from telegram import Bot
import tempfile
from collections import deque

logger = logging.getLogger(__name__)

class CameraProcessor:
    """Processes a single camera stream"""
    
    def __init__(self, camera: Camera, db, settings: GlobalSettings):
        self.camera = camera
        self.db = db
        self.settings = settings
        self.cap = None
        self.running = False
        self.mog2 = None
        self.current_recording = None
        self.video_writer = None
        self.last_frame = None
        self.motion_start_time = None
        self.motion_detected = False
        self.telegram_bot = None
        
        # Pre/Post recording buffer
        self.frame_buffer = deque(maxlen=int(camera.motion.pre_record_seconds * 15))  # 15 fps buffer
        self.post_motion_timer = 0
        
        # Get performance profile
        profile_name = settings.performance_profile
        self.profile = settings.profiles.get(profile_name, settings.profiles['medium'])
        
        # Initialize MOG2 if motion detection enabled
        if camera.motion.enabled:
            self.mog2 = cv2.createBackgroundSubtractorMOG2(
                history=camera.motion.mog2.history,
                varThreshold=camera.motion.mog2.var_threshold,
                detectShadows=camera.motion.mog2.detect_shadows
            )
        
        # Initialize Telegram bot
        if settings.telegram_bot_token:
            try:
                self.telegram_bot = Bot(token=settings.telegram_bot_token)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def connect(self) -> bool:
        """Connect to camera stream"""
        try:
            # Build URL with credentials if provided
            url = self.camera.url
            if self.camera.username and self.camera.password:
                # Parse URL and inject credentials
                if '://' in url:
                    protocol, rest = url.split('://', 1)
                    url = f"{protocol}://{self.camera.username}:{self.camera.password}@{rest}"
            
            self.cap = cv2.VideoCapture(url)
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera.id}")
                return False
            
            # Set buffer size to minimize latency - smaller buffer = less delay
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            logger.info(f"Connected to camera {self.camera.id} - {self.camera.name}")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to camera {self.camera.id}: {e}")
            return False
    
    def resize_frame(self, frame):
        """Resize frame based on performance profile"""
        height, width = frame.shape[:2]
        max_width = self.profile.max_resolution_width
        
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            # Use faster interpolation method for performance
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        return frame
    
    def apply_exclusion_zones(self, mask):
        """Apply exclusion zones to motion mask"""
        if not self.camera.motion.exclusion_zones:
            return mask
        
        for zone in self.camera.motion.exclusion_zones:
            if len(zone) >= 3:  # Need at least 3 points for polygon
                points = np.array(zone, dtype=np.int32)
                cv2.fillPoly(mask, [points], 0)
        
        return mask
    
    def detect_motion(self, frame) -> bool:
        """Detect motion in frame using MOG2"""
        if not self.mog2:
            return False
        
        # Use adaptive learning rate for better performance
        learning_rate = self.camera.motion.mog2.learning_rate
        if learning_rate == -1:
            # Auto mode: use faster learning rate for performance
            learning_rate = 0.01
        
        # Apply MOG2
        fg_mask = self.mog2.apply(frame, learningRate=learning_rate)
        
        # Apply exclusion zones
        fg_mask = self.apply_exclusion_zones(fg_mask)
        
        # Simplified morphological operations for performance
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Smaller kernel
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Find contours - use simpler approximation
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Quick check: if total white pixels is low, no motion
        if cv2.countNonZero(fg_mask) < self.camera.motion.min_area:
            return False
        
        # Check if any contour is large enough
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.camera.motion.min_area:
                return True
        
        return False
    
    async def start_recording(self, record_type: str):
        """Start video recording"""
        if self.video_writer:
            return
        
        try:
            # Create storage directory
            storage_path = Path(self.camera.recording.storage_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename - use .avi for MJPEG
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{self.camera.id}_{timestamp}_{record_type}.avi"
            filepath = storage_path / filename
            
            # Get frame dimensions
            if self.last_frame is None:
                return
            
            height, width = self.last_frame.shape[:2]
            
            # Initialize video writer - use MJPEG for compatibility
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            fps = self.profile.target_fps
            self.video_writer = cv2.VideoWriter(str(filepath.with_suffix('.avi')), fourcc, fps, (width, height))
            
            # Update file path to .avi
            filepath = filepath.with_suffix('.avi')
            
            # Write buffered frames (pre-record)
            if record_type == "motion" and self.frame_buffer:
                for buffered_frame in self.frame_buffer:
                    self.video_writer.write(buffered_frame)
            
            # Create recording entry
            recording = Recording(
                camera_id=self.camera.id,
                camera_name=self.camera.name,
                start_time=datetime.now(timezone.utc).isoformat(),
                record_type=record_type,
                file_path=str(filepath)
            )
            
            doc = recording.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await self.db.recordings.insert_one(doc)
            
            self.current_recording = recording
            logger.info(f"Started {record_type} recording for camera {self.camera.name}")
        
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
    
    async def stop_recording(self):
        """Stop video recording"""
        if not self.video_writer:
            return
        
        try:
            self.video_writer.release()
            self.video_writer = None
            
            if self.current_recording:
                # Update recording metadata
                end_time = datetime.now(timezone.utc).isoformat()
                start = datetime.fromisoformat(self.current_recording.start_time)
                end = datetime.fromisoformat(end_time)
                duration = int((end - start).total_seconds())
                
                # Get file size
                file_path = Path(self.current_recording.file_path)
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                await self.db.recordings.update_one(
                    {"id": self.current_recording.id},
                    {
                        "$set": {
                            "end_time": end_time,
                            "duration_seconds": duration,
                            "file_size": file_size
                        }
                    }
                )
                
                logger.info(f"Stopped recording for camera {self.camera.name} - Duration: {duration}s")
                
                # Send to Telegram if enabled and motion recording
                if (self.current_recording.record_type == "motion" and 
                    self.camera.telegram.send_video_clips and 
                    self.telegram_bot and 
                    self.settings.telegram_chat_id):
                    asyncio.create_task(self.send_telegram_video(file_path))
                
                self.current_recording = None
        
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
    
    async def send_telegram_alert(self):
        """Send motion alert to Telegram"""
        if not self.telegram_bot or not self.settings.telegram_chat_id:
            return
        
        try:
            message = f"🚨 Движение обнаружено!\n\nКамера: {self.camera.name}\nВремя: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            await self.telegram_bot.send_message(
                chat_id=self.settings.telegram_chat_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    async def send_telegram_video(self, video_path: Path):
        """Send video clip to Telegram (compressed and sped up)"""
        if not self.telegram_bot or not self.settings.telegram_chat_id:
            return
        
        try:
            # Create temporary compressed video
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Use ffmpeg to compress and speed up (2x speed, lower resolution)
            cmd = f'ffmpeg -i "{video_path}" -vf "setpts=0.5*PTS,scale=640:-1" -c:v libx264 -crf 28 -y "{tmp_path}"'
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Send video
            async with aiofiles.open(tmp_path, 'rb') as f:
                video_data = await f.read()
            
            await self.telegram_bot.send_video(
                chat_id=self.settings.telegram_chat_id,
                video=video_data,
                caption=f"📹 Запись движения - {self.camera.name}"
            )
            
            # Clean up temp file
            os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"Error sending Telegram video: {e}")
    
    async def process_frame(self, frame, check_motion=True):
        """Process a single frame"""
        try:
            # Resize frame
            frame = self.resize_frame(frame)
            # Store frame for live view (must copy to avoid race conditions)
            self.last_frame = frame.copy()
            
            # Add to buffer for pre-recording (only if motion enabled and we're checking motion this frame)
            if self.camera.motion.enabled and self.camera.recording.on_motion and check_motion:
                self.frame_buffer.append(frame.copy())
            
            # Detect motion if enabled and this frame should be checked
            if self.camera.motion.enabled and check_motion:
                motion = self.detect_motion(frame)
                
                if motion:
                    if not self.motion_detected:
                        # Motion started
                        self.motion_detected = True
                        self.motion_start_time = datetime.now(timezone.utc)
                        self.post_motion_timer = 0
                        
                        # Send Telegram alert
                        if self.camera.telegram.send_alerts:
                            asyncio.create_task(self.send_telegram_alert())
                        
                        # Start motion recording only if not in continuous mode
                        if self.camera.recording.on_motion and not self.camera.recording.continuous:
                            await self.start_recording("motion")
                    else:
                        # Motion continues - reset post timer
                        self.post_motion_timer = 0
                else:
                    if self.motion_detected:
                        # Increment post-motion timer
                        self.post_motion_timer += 1
                        
                        # Check if post-record period is over (adjust for motion check interval)
                        post_frames = (self.camera.motion.post_record_seconds * self.profile.target_fps) // self.profile.motion_check_interval_frames
                        if self.post_motion_timer >= post_frames:
                            # Check minimum duration
                            duration = (datetime.now(timezone.utc) - self.motion_start_time).total_seconds()
                            if duration >= self.camera.motion.min_duration_seconds:
                                # Valid motion ended - stop only motion recordings, not continuous
                                if self.camera.recording.on_motion and not self.camera.recording.continuous and self.video_writer:
                                    await self.stop_recording()
                            
                            self.motion_detected = False
                            self.motion_start_time = None
                            self.post_motion_timer = 0
            
            # Write frame to recording
            if self.video_writer:
                self.video_writer.write(frame)
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
    
    async def run(self):
        """Main processing loop"""
        try:
            self.running = True
            
            # Start continuous recording if enabled
            if self.camera.recording.continuous:
                await self.start_recording("continuous")
            
            # Use motion check interval from profile for optimization
            frame_interval = 1.0 / self.profile.target_fps
            motion_check_interval = self.profile.motion_check_interval_frames
            frame_counter = 0
            
            logger.info(f"Starting frame processing loop for camera {self.camera.name}, FPS: {self.profile.target_fps}, interval: {frame_interval}")
            
            while self.running:
            try:
                # Try to read frame with retry mechanism
                ret = False
                frame = None
                retries = 3
                
                for attempt in range(retries):
                    # Clear buffer with grab() before read()
                    self.cap.grab()
                    ret, frame = self.cap.read()
                    
                    if ret:
                        break
                    else:
                        if attempt < retries - 1:
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                
                if not ret:
                    if frame_counter % 30 == 0:  # Log every 30 failures
                        logger.warning(f"Failed to read frame from camera {self.camera.name} after {retries} retries")
                    await asyncio.sleep(1)
                    frame_counter += 1
                    continue
                
                # Log first few frames
                if frame_counter < 5:
                    logger.info(f"Processing frame {frame_counter} for camera {self.camera.name}")
                
                # Process frame with motion detection only every N frames to reduce CPU
                check_motion_this_frame = (frame_counter % motion_check_interval == 0)
                await self.process_frame(frame, check_motion=check_motion_this_frame)
                
                # For continuous recording, ensure writer is always active
                if self.camera.recording.continuous and not self.video_writer:
                    await self.start_recording("continuous")
                
                frame_counter += 1
                await asyncio.sleep(frame_interval)
            
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Fatal error in camera run() for {self.camera.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Clean up
            if self.video_writer:
                await self.stop_recording()
    
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
        """Stop processing"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.video_writer:
            await self.stop_recording()


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
        """Test camera connection"""
        try:
            url = camera.url
            if camera.username and camera.password:
                if '://' in url:
                    protocol, rest = url.split('://', 1)
                    url = f"{protocol}://{camera.username}:{camera.password}@{rest}"
            
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                return {"success": False, "message": "Не удалось подключиться к камере"}
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return {"success": False, "message": "Не удалось получить кадр с камеры"}
            
            return {"success": True, "message": "Подключение успешно", "frame_size": frame.shape}
        
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
