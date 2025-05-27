import os
import json
import requests
from typing import Dict, Optional, List
from datetime import datetime
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SyncHandler:
    def __init__(self, api_base_url: str = "https://localhost:5000/api"):
        self.api_base_url = api_base_url.rstrip('/')
        self.auth_token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        # Disable SSL verification for self-signed certificates
        self.session.verify = False
        self.data_folder = "data"
        os.makedirs(self.data_folder, exist_ok=True)

    def register(self, username: str, password: str) -> Dict:
        try:
            response = self.session.post(
                f"{self.api_base_url}/register",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 201:
                return response.json()
                
            try:
                error_data = response.json()
                return {
                    "error": f"Registration failed ({response.status_code}): {error_data.get('error', 'Unknown error')}",
                    "status_code": response.status_code,
                    "details": error_data
                }
            except ValueError:
                return {
                    "error": f"Registration failed ({response.status_code}): {response.text}",
                    "status_code": response.status_code,
                    "details": response.text
                }
                
        except requests.exceptions.SSLError as e:
            return {
                "error": f"SSL error during registration: {str(e)}",
                "exception_type": type(e).__name__,
                "details": "Try checking if the server is running with HTTPS"
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error during registration: {str(e)}",
                "exception_type": type(e).__name__,
                "details": str(e)
            }

    def login(self, username: str, password: str) -> Dict:
        try:
            response = self.session.post(
                f"{self.api_base_url}/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                self.user_id = data.get('user_id')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                return data
                
            try:
                error_data = response.json()
                return {
                    "error": f"Login failed ({response.status_code}): {error_data.get('error', 'Unknown error')}",
                    "status_code": response.status_code,
                    "details": error_data
                }
            except ValueError:
                return {
                    "error": f"Login failed ({response.status_code}): {response.text}",
                    "status_code": response.status_code,
                    "details": response.text
                }
                
        except requests.exceptions.SSLError as e:
            return {
                "error": f"SSL error during login: {str(e)}",
                "exception_type": type(e).__name__,
                "details": "Try checking if the server is running with HTTPS"
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error during login: {str(e)}",
                "exception_type": type(e).__name__,
                "details": str(e)
            }

    def logout(self) -> None:
        self.auth_token = None
        self.user_id = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']

    def upload_data(self) -> Dict:
        if not self.auth_token:
            return {"error": "Not authenticated", "details": "No auth token available"}
            
        try:
            summary_file = os.path.join(self.data_folder, "chat_summary.jsonl")
            embeddings_file = os.path.join(self.data_folder, "chat_embeddings.jsonl")
            
            summaries = []
            embeddings = []
            
            if os.path.exists(summary_file):
                with open(summary_file, "r", encoding="utf-8") as f:
                    summaries = [json.loads(line) for line in f if line.strip()]
            
            if os.path.exists(embeddings_file):
                with open(embeddings_file, "r", encoding="utf-8") as f:
                    embeddings = [json.loads(line) for line in f if line.strip()]
            
            data = []
            min_length = min(len(summaries), len(embeddings))
            for i in range(min_length):
                summary = summaries[i]
                embedding = embeddings[i]
                
                if (summary.get("start_timestamp") == embedding.get("start_timestamp") and 
                    summary.get("end_timestamp") == embedding.get("end_timestamp")):
                    data.append({
                        "start_timestamp": summary["start_timestamp"],
                        "end_timestamp": summary["end_timestamp"],
                        "summary": summary["summary"],
                        "embedding": embedding["embedding"]
                    })
            
            if not data:
                return {"error": "No conversation data available to upload", "details": "No valid summaries found"}
            
            response = self.session.post(
                f"{self.api_base_url}/upload",
                json={"user_id": self.user_id, "data": data},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
                
            try:
                error_data = response.json()
                return {
                    "error": f"Upload failed ({response.status_code}): {error_data.get('error', 'Unknown error')}",
                    "status_code": response.status_code,
                    "details": error_data
                }
            except ValueError:
                return {
                    "error": f"Upload failed ({response.status_code}): {response.text}",
                    "status_code": response.status_code,
                    "details": response.text
                }
                
        except requests.exceptions.SSLError as e:
            return {
                "error": f"SSL error during upload: {str(e)}",
                "exception_type": type(e).__name__,
                "details": "Try checking if the server is running with HTTPS"
            }
        except Exception as e:
            return {
                "error": f"Upload processing failed: {str(e)}",
                "exception_type": type(e).__name__,
                "details": str(e)
            }

    def download_data(self) -> Dict:
        if not self.auth_token:
            return {"error": "Not authenticated", "details": "No auth token available"}
        
        try:
            response = self.session.get(
                f"{self.api_base_url}/download",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"data": []}
            else:
                return {
                    "error": f"Server returned {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.SSLError as e:
            return {
                "error": f"SSL error during download: {str(e)}",
                "exception_type": type(e).__name__,
                "details": "Try checking if the server is running with HTTPS"
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": "Network error during download",
                "details": str(e)
            }

    def save_downloaded_data(self, data: Dict) -> bool:
        temp_summary = None
        temp_embeddings = None
        
        try:
            if not data or not isinstance(data.get('data'), list):
                raise ValueError("Invalid data format received")
            
            summary_file = os.path.join(self.data_folder, "chat_summary.jsonl")
            embeddings_file = os.path.join(self.data_folder, "chat_embeddings.jsonl")

            temp_summary = f"{summary_file}.tmp"
            temp_embeddings = f"{embeddings_file}.tmp"
            
            with open(temp_summary, "w", encoding="utf-8") as sf, \
                open(temp_embeddings, "w", encoding="utf-8") as ef:
                
                for item in data['data']:
                    if all(k in item for k in ['start_timestamp', 'end_timestamp', 'summary']):
                        sf.write(json.dumps({
                            "start_timestamp": item["start_timestamp"],
                            "end_timestamp": item["end_timestamp"],
                            "summary": item["summary"]
                        }, ensure_ascii=False) + "\n")
                    
                    if all(k in item for k in ['start_timestamp', 'end_timestamp', 'embedding']):
                        ef.write(json.dumps({
                            "start_timestamp": item["start_timestamp"],
                            "end_timestamp": item["end_timestamp"],
                            "embedding": item["embedding"]
                        }, ensure_ascii=False) + "\n")
            
            if not (os.path.exists(temp_summary) and os.path.exists(temp_embeddings)):
                raise IOError("Temporary files not created properly")
            
            os.replace(temp_summary, summary_file)
            os.replace(temp_embeddings, embeddings_file)
            
            return True
            
        except Exception as e:
            print(f"Error saving downloaded data: {str(e)}")
            return False
            
        finally:
            if temp_summary and os.path.exists(temp_summary):
                os.remove(temp_summary)
            if temp_embeddings and os.path.exists(temp_embeddings):
                os.remove(temp_embeddings)