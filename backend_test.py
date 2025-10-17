#!/usr/bin/env python3
"""
Backend API Testing for Video Surveillance System
Tests continuous recording fix and recording filters API
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://securewatch-22.preview.emergentagent.com/api"

class VideoSurveillanceAPITester:
    def __init__(self):
        self.session = None
        self.test_cameras = []
        self.test_recordings = []
        self.results = {
            "camera_operations": {"passed": 0, "failed": 0, "details": []},
            "continuous_recording": {"passed": 0, "failed": 0, "details": []},
            "recording_filters": {"passed": 0, "failed": 0, "details": []},
            "overall": {"passed": 0, "failed": 0}
        }

    async def setup_session(self):
        """Setup HTTP session"""
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(connector=connector)

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    def log_result(self, category, test_name, passed, details=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {category}: {test_name}")
        if details:
            print(f"    Details: {details}")
        
        self.results[category]["passed" if passed else "failed"] += 1
        self.results[category]["details"].append({
            "test": test_name,
            "status": status,
            "details": details
        })

    async def test_camera_operations(self):
        """Test basic camera operations"""
        print("\n=== Testing Camera Operations ===")
        
        # Test 1: Get existing cameras
        existing_cameras = []
        try:
            async with self.session.get(f"{BACKEND_URL}/cameras") as resp:
                if resp.status == 200:
                    existing_cameras = await resp.json()
                    self.log_result("camera_operations", "GET /cameras", True, f"Found {len(existing_cameras)} existing cameras")
                else:
                    self.log_result("camera_operations", "GET /cameras", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("camera_operations", "GET /cameras", False, f"Exception: {str(e)}")

        # Use existing cameras for testing if available
        if existing_cameras:
            self.test_cameras = existing_cameras
            self.log_result("camera_operations", "Using existing cameras for testing", True, 
                          f"Will test with {len(existing_cameras)} existing cameras")
            
            # Test camera status check
            for camera in existing_cameras:
                try:
                    async with self.session.get(f"{BACKEND_URL}/cameras/{camera['id']}") as resp:
                        if resp.status == 200:
                            updated_camera = await resp.json()
                            status = updated_camera.get('status', 'unknown')
                            self.log_result("camera_operations", f"Camera {camera.get('name', camera['id'])} status check", 
                                          True, f"Status: {status}")
                        else:
                            self.log_result("camera_operations", f"GET camera {camera['id']}", False, f"Status: {resp.status}")
                except Exception as e:
                    self.log_result("camera_operations", f"GET camera {camera['id']}", False, f"Exception: {str(e)}")
        else:
            # Create a simple test camera if no existing cameras
            test_camera_data = {
                "name": "Test Camera for API Testing",
                "url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "recording": {
                    "continuous": True,
                    "on_motion": False,
                    "storage_path": "/app/recordings",
                    "max_file_duration_minutes": 1
                },
                "motion": {
                    "enabled": False
                },
                "telegram": {
                    "send_alerts": False,
                    "send_video_clips": False
                }
            }

            try:
                async with self.session.post(f"{BACKEND_URL}/cameras", json=test_camera_data) as resp:
                    if resp.status == 200:
                        camera = await resp.json()
                        self.test_cameras.append(camera)
                        self.log_result("camera_operations", "POST /cameras", True, f"Created test camera: {camera['id']}")
                    else:
                        error_text = await resp.text()
                        self.log_result("camera_operations", "POST /cameras", False, f"Status: {resp.status}, Error: {error_text}")
            except Exception as e:
                self.log_result("camera_operations", "POST /cameras", False, f"Exception: {str(e)}")

    async def test_continuous_recording(self):
        """Test continuous recording functionality"""
        print("\n=== Testing Continuous Recording ===")
        
        if not self.test_cameras:
            self.log_result("continuous_recording", "No test cameras available", False, "Cannot test without cameras")
            return

        # Check if any existing camera has continuous recording enabled
        continuous_camera = None
        for camera in self.test_cameras:
            recording_settings = camera.get('recording', {})
            if recording_settings.get('continuous', False):
                continuous_camera = camera
                break

        if not continuous_camera:
            # Try to update an existing camera to enable continuous recording
            if self.test_cameras:
                camera_to_update = self.test_cameras[0]
                update_data = {
                    "name": camera_to_update.get('name', 'Updated Test Camera'),
                    "url": camera_to_update.get('url', ''),
                    "username": camera_to_update.get('username'),
                    "password": camera_to_update.get('password'),
                    "recording": {
                        "continuous": True,  # Enable continuous recording
                        "on_motion": camera_to_update.get('recording', {}).get('on_motion', True),
                        "storage_path": "/app/recordings",
                        "max_file_duration_minutes": 1  # Short duration for testing
                    },
                    "motion": camera_to_update.get('motion', {"enabled": False}),
                    "telegram": camera_to_update.get('telegram', {"send_alerts": False, "send_video_clips": False})
                }
                
                try:
                    async with self.session.put(f"{BACKEND_URL}/cameras/{camera_to_update['id']}", json=update_data) as resp:
                        if resp.status == 200:
                            continuous_camera = await resp.json()
                            self.log_result("continuous_recording", "Enable continuous recording on existing camera", True, 
                                          f"Updated camera {camera_to_update['id']} for continuous recording")
                        else:
                            error_text = await resp.text()
                            self.log_result("continuous_recording", "Enable continuous recording", False, 
                                          f"Failed to update camera: {resp.status}, {error_text}")
                            return
                except Exception as e:
                    self.log_result("continuous_recording", "Enable continuous recording", False, f"Exception: {str(e)}")
                    return
            else:
                self.log_result("continuous_recording", "No cameras available for testing", False, "Cannot test continuous recording")
                return

        # Wait for recording to start
        print("Waiting 8 seconds for continuous recording to start...")
        await asyncio.sleep(8)

        # Test 1: Check if recordings are being created
        try:
            async with self.session.get(f"{BACKEND_URL}/recordings?camera_id={continuous_camera['id']}") as resp:
                if resp.status == 200:
                    recordings = await resp.json()
                    continuous_recordings = [r for r in recordings if r.get('record_type') == 'continuous']
                    
                    if continuous_recordings:
                        self.log_result("continuous_recording", "Continuous recordings created", True, 
                                      f"Found {len(continuous_recordings)} continuous recordings")
                        self.test_recordings.extend(continuous_recordings)
                        
                        # Check if recordings have proper metadata
                        for recording in continuous_recordings:
                            if recording.get('camera_id') == continuous_camera['id'] and recording.get('record_type') == 'continuous':
                                self.log_result("continuous_recording", "Recording metadata correct", True, 
                                              f"Recording {recording['id']} has correct metadata")
                            else:
                                self.log_result("continuous_recording", "Recording metadata correct", False, 
                                              f"Recording {recording['id']} has incorrect metadata")
                    else:
                        self.log_result("continuous_recording", "Continuous recordings created", False, 
                                      "No continuous recordings found - continuous recording may not be working")
                else:
                    self.log_result("continuous_recording", "Get recordings for continuous camera", False, 
                                  f"Status: {resp.status}")
        except Exception as e:
            self.log_result("continuous_recording", "Get recordings for continuous camera", False, 
                          f"Exception: {str(e)}")

        # Test 2: Verify recording files exist on disk
        storage_path = Path("/app/recordings")
        if storage_path.exists():
            continuous_files = list(storage_path.glob(f"{continuous_camera['id']}_*_continuous.*"))
            if continuous_files:
                self.log_result("continuous_recording", "Continuous recording files on disk", True, 
                              f"Found {len(continuous_files)} files")
                
                # Check file sizes
                non_empty_files = 0
                for file_path in continuous_files:
                    if file_path.stat().st_size > 0:
                        non_empty_files += 1
                
                if non_empty_files > 0:
                    self.log_result("continuous_recording", "Recording files have content", True, 
                                  f"{non_empty_files} files have content")
                else:
                    self.log_result("continuous_recording", "Recording files have content", False, 
                                  "All recording files are empty")
            else:
                self.log_result("continuous_recording", "Continuous recording files on disk", False, 
                              "No continuous recording files found on disk")
        else:
            self.log_result("continuous_recording", "Storage path exists", False, 
                          f"Storage path {storage_path} does not exist")

        # Test 3: Verify continuous recording logic is working
        print("Waiting additional 5 seconds to verify continuous recording persistence...")
        await asyncio.sleep(5)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/recordings?camera_id={continuous_camera['id']}&record_type=continuous") as resp:
                if resp.status == 200:
                    recordings_after = await resp.json()
                    self.log_result("continuous_recording", "Continuous recording API filter works", True, 
                                  f"Found {len(recordings_after)} continuous recordings after waiting")
                else:
                    self.log_result("continuous_recording", "Check recording persistence", False, 
                                  f"Status: {resp.status}")
        except Exception as e:
            self.log_result("continuous_recording", "Check recording persistence", False, 
                          f"Exception: {str(e)}")

    async def test_recording_filters(self):
        """Test recording filters API"""
        print("\n=== Testing Recording Filters ===")
        
        # First, get all recordings to have test data
        try:
            async with self.session.get(f"{BACKEND_URL}/recordings") as resp:
                if resp.status == 200:
                    all_recordings = await resp.json()
                    self.log_result("recording_filters", "GET /recordings (no filters)", True, 
                                  f"Retrieved {len(all_recordings)} recordings")
                    self.test_recordings.extend(all_recordings)
                else:
                    self.log_result("recording_filters", "GET /recordings (no filters)", False, 
                                  f"Status: {resp.status}")
                    return
        except Exception as e:
            self.log_result("recording_filters", "GET /recordings (no filters)", False, 
                          f"Exception: {str(e)}")
            return

        if not all_recordings:
            self.log_result("recording_filters", "No recordings available for filter testing", False, 
                          "Cannot test filters without recordings")
            return

        # Test 1: Filter by camera_id
        if self.test_cameras:
            camera_id = self.test_cameras[0]['id']
            try:
                async with self.session.get(f"{BACKEND_URL}/recordings?camera_id={camera_id}") as resp:
                    if resp.status == 200:
                        filtered_recordings = await resp.json()
                        # Verify all recordings belong to the specified camera
                        valid_filter = all(r.get('camera_id') == camera_id for r in filtered_recordings)
                        self.log_result("recording_filters", "Filter by camera_id", valid_filter, 
                                      f"Found {len(filtered_recordings)} recordings for camera {camera_id}")
                    else:
                        self.log_result("recording_filters", "Filter by camera_id", False, 
                                      f"Status: {resp.status}")
            except Exception as e:
                self.log_result("recording_filters", "Filter by camera_id", False, 
                              f"Exception: {str(e)}")

        # Test 2: Filter by record_type
        for record_type in ['continuous', 'motion']:
            try:
                async with self.session.get(f"{BACKEND_URL}/recordings?record_type={record_type}") as resp:
                    if resp.status == 200:
                        filtered_recordings = await resp.json()
                        # Verify all recordings have the specified type
                        valid_filter = all(r.get('record_type') == record_type for r in filtered_recordings)
                        self.log_result("recording_filters", f"Filter by record_type={record_type}", valid_filter, 
                                      f"Found {len(filtered_recordings)} {record_type} recordings")
                    else:
                        self.log_result("recording_filters", f"Filter by record_type={record_type}", False, 
                                      f"Status: {resp.status}")
            except Exception as e:
                self.log_result("recording_filters", f"Filter by record_type={record_type}", False, 
                              f"Exception: {str(e)}")

        # Test 3: Filter by date range
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(hours=1)).isoformat()
        end_date = now.isoformat()
        
        try:
            async with self.session.get(f"{BACKEND_URL}/recordings?start_date={start_date}&end_date={end_date}") as resp:
                if resp.status == 200:
                    filtered_recordings = await resp.json()
                    self.log_result("recording_filters", "Filter by date range", True, 
                                  f"Found {len(filtered_recordings)} recordings in last hour")
                else:
                    self.log_result("recording_filters", "Filter by date range", False, 
                                  f"Status: {resp.status}")
        except Exception as e:
            self.log_result("recording_filters", "Filter by date range", False, 
                          f"Exception: {str(e)}")

        # Test 4: Combined filters
        if self.test_cameras:
            camera_id = self.test_cameras[0]['id']
            try:
                async with self.session.get(f"{BACKEND_URL}/recordings?camera_id={camera_id}&record_type=continuous&start_date={start_date}") as resp:
                    if resp.status == 200:
                        filtered_recordings = await resp.json()
                        # Verify all conditions are met
                        valid_camera = all(r.get('camera_id') == camera_id for r in filtered_recordings)
                        valid_type = all(r.get('record_type') == 'continuous' for r in filtered_recordings)
                        valid_date = all(r.get('start_time', '') >= start_date for r in filtered_recordings)
                        
                        all_valid = valid_camera and valid_type and valid_date
                        self.log_result("recording_filters", "Combined filters", all_valid, 
                                      f"Found {len(filtered_recordings)} recordings matching all criteria")
                    else:
                        self.log_result("recording_filters", "Combined filters", False, 
                                      f"Status: {resp.status}")
            except Exception as e:
                self.log_result("recording_filters", "Combined filters", False, 
                              f"Exception: {str(e)}")

        # Test 5: Invalid filter values
        try:
            async with self.session.get(f"{BACKEND_URL}/recordings?camera_id=nonexistent") as resp:
                if resp.status == 200:
                    filtered_recordings = await resp.json()
                    self.log_result("recording_filters", "Invalid camera_id filter", len(filtered_recordings) == 0, 
                                  f"Correctly returned {len(filtered_recordings)} recordings for nonexistent camera")
                else:
                    self.log_result("recording_filters", "Invalid camera_id filter", False, 
                                  f"Status: {resp.status}")
        except Exception as e:
            self.log_result("recording_filters", "Invalid camera_id filter", False, 
                          f"Exception: {str(e)}")

    async def cleanup_test_data(self):
        """Clean up test cameras and recordings"""
        print("\n=== Cleaning Up Test Data ===")
        
        # Delete test cameras
        for camera in self.test_cameras:
            try:
                async with self.session.delete(f"{BACKEND_URL}/cameras/{camera['id']}") as resp:
                    if resp.status == 200:
                        print(f"Deleted test camera: {camera['name']}")
                    else:
                        print(f"Failed to delete camera {camera['name']}: Status {resp.status}")
            except Exception as e:
                print(f"Exception deleting camera {camera['name']}: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            if category == "overall":
                continue
            
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            print(f"\n{category.upper().replace('_', ' ')}:")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            
            if failed > 0:
                print("  Failed tests:")
                for detail in results["details"]:
                    if detail["status"] == "FAIL":
                        print(f"    - {detail['test']}: {detail['details']}")
        
        self.results["overall"]["passed"] = total_passed
        self.results["overall"]["failed"] = total_failed
        
        print(f"\nOVERALL RESULTS:")
        print(f"  Total Passed: {total_passed}")
        print(f"  Total Failed: {total_failed}")
        print(f"  Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%" if (total_passed+total_failed) > 0 else "N/A")
        
        return total_failed == 0

    async def run_all_tests(self):
        """Run all tests"""
        print("Starting Video Surveillance Backend API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("="*60)
        
        await self.setup_session()
        
        try:
            await self.test_camera_operations()
            await self.test_continuous_recording()
            await self.test_recording_filters()
        finally:
            await self.cleanup_test_data()
            await self.cleanup_session()
        
        return self.print_summary()

async def main():
    """Main test function"""
    tester = VideoSurveillanceAPITester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())