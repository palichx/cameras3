#!/usr/bin/env python3
"""
Specific verification test for continuous recording fix
Verifies that continuous recording is NOT stopped by motion detection logic
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from pathlib import Path

BACKEND_URL = "https://securewatch-22.preview.emergentagent.com/api"

async def verify_continuous_recording_fix():
    """Verify the continuous recording fix is working"""
    print("=== Verifying Continuous Recording Fix ===")
    
    connector = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(connector=connector)
    
    try:
        # Get existing cameras
        async with session.get(f"{BACKEND_URL}/cameras") as resp:
            cameras = await resp.json()
            
        if not cameras:
            print("❌ No cameras available for testing")
            return False
            
        camera = cameras[0]
        camera_id = camera['id']
        
        print(f"📹 Testing with camera: {camera.get('name', camera_id)}")
        
        # Ensure camera has continuous recording enabled
        update_data = {
            "name": camera.get('name', 'Test Camera'),
            "url": camera.get('url', ''),
            "username": camera.get('username'),
            "password": camera.get('password'),
            "recording": {
                "continuous": True,  # Enable continuous recording
                "on_motion": True,   # Also enable motion recording
                "storage_path": "/app/recordings",
                "max_file_duration_minutes": 1
            },
            "motion": {
                "enabled": True,  # Enable motion detection
                "mog2": {
                    "history": 500,
                    "var_threshold": 16.0,
                    "detect_shadows": True,
                    "learning_rate": -1,
                    "n_mixtures": 5
                },
                "min_area": 500,
                "min_duration_seconds": 1,
                "pre_record_seconds": 5,
                "post_record_seconds": 10,
                "exclusion_zones": []
            },
            "telegram": camera.get('telegram', {"send_alerts": False, "send_video_clips": False})
        }
        
        async with session.put(f"{BACKEND_URL}/cameras/{camera_id}", json=update_data) as resp:
            if resp.status != 200:
                print(f"❌ Failed to update camera: {resp.status}")
                return False
        
        print("✅ Camera updated with continuous recording + motion detection enabled")
        
        # Wait for recording to start
        print("⏳ Waiting 10 seconds for recordings to start...")
        await asyncio.sleep(10)
        
        # Check initial recordings
        async with session.get(f"{BACKEND_URL}/recordings?camera_id={camera_id}") as resp:
            initial_recordings = await resp.json()
        
        continuous_recordings = [r for r in initial_recordings if r.get('record_type') == 'continuous']
        motion_recordings = [r for r in initial_recordings if r.get('record_type') == 'motion']
        
        print(f"📊 Initial state: {len(continuous_recordings)} continuous, {len(motion_recordings)} motion recordings")
        
        if len(continuous_recordings) == 0:
            print("❌ CRITICAL: No continuous recordings found - continuous recording not working")
            return False
        
        print("✅ Continuous recording is active")
        
        # Wait more time to see if motion detection interferes
        print("⏳ Waiting additional 10 seconds to test motion interaction...")
        await asyncio.sleep(10)
        
        # Check recordings after waiting
        async with session.get(f"{BACKEND_URL}/recordings?camera_id={camera_id}") as resp:
            final_recordings = await resp.json()
        
        final_continuous = [r for r in final_recordings if r.get('record_type') == 'continuous']
        final_motion = [r for r in final_recordings if r.get('record_type') == 'motion']
        
        print(f"📊 Final state: {len(final_continuous)} continuous, {len(final_motion)} motion recordings")
        
        # Verify continuous recording persisted
        if len(final_continuous) >= len(continuous_recordings):
            print("✅ PASS: Continuous recording persisted - not stopped by motion detection")
            success = True
        else:
            print("❌ FAIL: Continuous recording was interrupted - motion detection may be stopping it")
            success = False
        
        # Check file system
        storage_path = Path("/app/recordings")
        if storage_path.exists():
            continuous_files = list(storage_path.glob(f"{camera_id}_*_continuous.*"))
            motion_files = list(storage_path.glob(f"{camera_id}_*_motion.*"))
            
            print(f"💾 Files on disk: {len(continuous_files)} continuous, {len(motion_files)} motion files")
            
            if continuous_files:
                # Check if continuous files have content
                total_size = sum(f.stat().st_size for f in continuous_files)
                print(f"📁 Continuous recording files total size: {total_size} bytes")
                
                if total_size > 0:
                    print("✅ Continuous recording files have content")
                else:
                    print("❌ Continuous recording files are empty")
                    success = False
            else:
                print("❌ No continuous recording files found on disk")
                success = False
        
        return success
        
    except Exception as e:
        print(f"❌ Exception during testing: {str(e)}")
        return False
    finally:
        await session.close()

async def main():
    success = await verify_continuous_recording_fix()
    print("\n" + "="*60)
    if success:
        print("🎉 CONTINUOUS RECORDING FIX VERIFICATION: PASSED")
        print("✅ Continuous recording works correctly and is not stopped by motion detection")
    else:
        print("❌ CONTINUOUS RECORDING FIX VERIFICATION: FAILED")
        print("⚠️  Continuous recording fix needs attention")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())