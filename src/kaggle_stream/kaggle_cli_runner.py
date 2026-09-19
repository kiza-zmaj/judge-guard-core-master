#!/usr/bin/env python3
"""
Kaggle CLI Runner
=================
Execution engine (AKCIONI MOTOR) for managing Kaggle CLI interactions:
environment verification, dataset download, automated submission, and leaderboard polling.
"""

import json
import logging
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class KaggleCLIRunner:
    """
    Manages local Kaggle CLI execution with safety checks and error handling.
    """
    def __init__(self, kaggle_config_dir: Optional[str] = None, kaggle_bin: str = "kaggle"):
        self.config_dir = Path(kaggle_config_dir or os.path.expanduser("~/.kaggle"))
        self.kaggle_bin = kaggle_bin

    def check_environment(self) -> Dict[str, Any]:
        """
        Verify that ~/.kaggle/kaggle.json exists, contains valid credentials, and permissions are secure.
        """
        credentials_file = self.config_dir / "kaggle.json"
        
        if not credentials_file.exists():
            return {
                "status": "MISSING_CREDENTIALS",
                "ready": False,
                "message": f"Kaggle credentials not found at {credentials_file}. Place your kaggle.json token there.",
                "username": None
            }

        try:
            with open(credentials_file, "r") as f:
                creds = json.load(f)
            
            username = creds.get("username")
            key = creds.get("key")
            
            if not username or not key:
                return {
                    "status": "INVALID_FORMAT",
                    "ready": False,
                    "message": "kaggle.json must contain 'username' and 'key' fields.",
                    "username": None
                }

            # Check permissions (on Unix/Linux should ideally be 600)
            try:
                st_mode = oct(credentials_file.stat().st_mode & 0o777)
            except Exception:
                st_mode = "unknown"

            return {
                "status": "READY",
                "ready": True,
                "username": username,
                "permissions": st_mode,
                "path": str(credentials_file)
            }
        except json.JSONDecodeError:
            return {
                "status": "CORRUPTED_JSON",
                "ready": False,
                "message": f"Failed to parse JSON in {credentials_file}.",
                "username": None
            }

    def list_competitions(self, search: Optional[str] = None) -> Dict[str, Any]:
        """
        Search or list active Kaggle competitions.
        """
        cmd = [self.kaggle_bin, "competitions", "list"]
        if search:
            cmd.extend(["-s", search])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "success": True,
                "output": res.stdout.strip(),
                "error": None
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def download_competition_data(self, competition_id: str, target_dir: str) -> Dict[str, Any]:
        """
        Download and unpack competition data into target_dir.
        """
        dest_path = Path(target_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        cmd = [self.kaggle_bin, "competitions", "download", "-c", competition_id, "-p", str(dest_path)]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Find any downloaded zip files and extract them
            extracted_files = []
            for item in dest_path.glob("*.zip"):
                with zipfile.ZipFile(item, "r") as zip_ref:
                    zip_ref.extractall(dest_path)
                    extracted_files.extend(zip_ref.namelist())
                item.unlink() # Cleanup archive
                
            return {
                "success": True,
                "competition_id": competition_id,
                "target_dir": str(dest_path),
                "extracted_files": extracted_files or [f.name for f in dest_path.iterdir() if f.is_file()],
                "error": None
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "success": False,
                "competition_id": competition_id,
                "target_dir": str(dest_path),
                "extracted_files": [],
                "error": str(e)
            }

    def submit_prediction(self, competition_id: str, file_path: str, message: str) -> Dict[str, Any]:
        """
        Submit a predictions file to Kaggle.
        """
        file_p = Path(file_path)
        if not file_p.exists():
            return {
                "success": False,
                "error": f"Submission file not found at {file_path}",
                "output": ""
            }

        cmd = [
            self.kaggle_bin, "competitions", "submit",
            "-c", competition_id,
            "-f", str(file_p),
            "-m", message
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "success": True,
                "competition_id": competition_id,
                "file": str(file_p),
                "message": message,
                "output": res.stdout.strip(),
                "error": None
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "success": False,
                "competition_id": competition_id,
                "file": str(file_p),
                "error": str(e),
                "output": getattr(e, "stdout", "")
            }

    def poll_submission_status(self, competition_id: str, max_retries: int = 5, delay_sec: float = 2.0) -> Dict[str, Any]:
        """
        Poll submission status until complete or max_retries reached.
        """
        cmd = [self.kaggle_bin, "competitions", "submissions", "-c", competition_id]
        
        for attempt in range(max_retries):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output = res.stdout.strip()
                
                # Check if latest submission is complete
                if "complete" in output.lower() or "success" in output.lower():
                    return {
                        "status": "SCORED",
                        "completed": True,
                        "raw_output": output,
                        "attempts": attempt + 1
                    }
                elif "pending" in output.lower():
                    time.sleep(delay_sec)
                    continue
                else:
                    return {
                        "status": "RECORDED",
                        "completed": True,
                        "raw_output": output,
                        "attempts": attempt + 1
                    }
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                return {
                    "status": "ERROR",
                    "completed": False,
                    "error": str(e),
                    "attempts": attempt + 1
                }
                
        return {
            "status": "TIMEOUT",
            "completed": False,
            "message": f"Polling timed out after {max_retries} attempts.",
            "attempts": max_retries
        }

    def get_leaderboard_position(self, competition_id: str) -> Dict[str, Any]:
        """
        Retrieve the current leaderboard for the competition.
        """
        cmd = [self.kaggle_bin, "competitions", "leaderboard", "-c", competition_id, "--show"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "success": True,
                "competition_id": competition_id,
                "leaderboard": res.stdout.strip(),
                "error": None
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "success": False,
                "competition_id": competition_id,
                "leaderboard": "",
                "error": str(e)
            }
