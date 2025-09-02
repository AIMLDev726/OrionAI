"""
Human-Written Complex Code for AI Review Testing
===============================================
This file contains real human-written code with various complexity patterns,
security vulnerabilities, and performance issues for testing the AI code reviewer.
"""

import os
import sys
import sqlite3
import hashlib
import threading
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set your Google API key here
os.environ['GOOGLE_API_KEY'] = input('your_google_api_key_here')

from orionai.python import AIPython

class UserManager:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.session_cache = {}
        self.failed_attempts = {}
        self.lock = threading.Lock()
        self._setup_database()
    
    def _setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()
    
    def create_user(self, username: str, password: str, email: str = None):
        # Hash password with salt
        salt = os.urandom(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        stored_password = salt + password_hash
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                (username, stored_password.hex(), email)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return {"success": True, "user_id": user_id}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Username already exists"}
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str):
        # Check failed attempts (basic rate limiting)
        with self.lock:
            if username in self.failed_attempts:
                if self.failed_attempts[username]['count'] >= 5:
                    if datetime.now() - self.failed_attempts[username]['last_attempt'] < timedelta(minutes=15):
                        return {"success": False, "error": "Account temporarily locked"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ? AND is_active = 1", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            self._record_failed_attempt(username)
            return {"success": False, "error": "Invalid credentials"}
        
        user_id, stored_password_hex = result
        stored_password = bytes.fromhex(stored_password_hex)
        salt = stored_password[:32]
        stored_hash = stored_password[32:]
        
        # Verify password
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        if password_hash == stored_hash:
            # Clear failed attempts on successful login
            with self.lock:
                if username in self.failed_attempts:
                    del self.failed_attempts[username]
            
            session_id = self._create_session(user_id)
            return {"success": True, "user_id": user_id, "session_id": session_id}
        else:
            self._record_failed_attempt(username)
            return {"success": False, "error": "Invalid credentials"}
    
    def _record_failed_attempt(self, username: str):
        with self.lock:
            if username not in self.failed_attempts:
                self.failed_attempts[username] = {"count": 0, "last_attempt": None}
            self.failed_attempts[username]['count'] += 1
            self.failed_attempts[username]['last_attempt'] = datetime.now()
    
    def _create_session(self, user_id: int):
        session_id = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, user_id, expires_at)
        )
        conn.commit()
        conn.close()
        
        self.session_cache[session_id] = {"user_id": user_id, "expires_at": expires_at}
        return session_id
    
    def validate_session(self, session_id: str):
        # Check cache first
        if session_id in self.session_cache:
            session_data = self.session_cache[session_id]
            if datetime.now() < session_data['expires_at']:
                return {"valid": True, "user_id": session_data['user_id']}
            else:
                # Remove expired session from cache
                del self.session_cache[session_id]
        
        # Check database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM user_sessions WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id, expires_at_str = result
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now() < expires_at:
                # Update cache
                self.session_cache[session_id] = {"user_id": user_id, "expires_at": expires_at}
                return {"valid": True, "user_id": user_id}
        
        return {"valid": False}

class DataProcessor:
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file) if config_file else {}
        self.cache = {}
        self.processing_stats = {"total_processed": 0, "errors": 0}
        
    def _load_config(self, config_file: str):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    @lru_cache(maxsize=128)
    def expensive_calculation(self, data_hash: str, complexity: int):
        time.sleep(0.1 * complexity)  # Simulate processing time
        result = sum(ord(c) for c in data_hash) * complexity
        return result
    
    def process_data_batch(self, data_list: List[Dict], parallel: bool = True):
        if not data_list:
            return []
        
        if parallel and len(data_list) > 10:
            return self._process_parallel(data_list)
        else:
            return self._process_sequential(data_list)
    
    def _process_sequential(self, data_list: List[Dict]):
        results = []
        for item in data_list:
            try:
                processed = self._process_single_item(item)
                results.append(processed)
                self.processing_stats["total_processed"] += 1
            except Exception as e:
                self.processing_stats["errors"] += 1
                results.append({"error": str(e), "original": item})
        return results
    
    def _process_parallel(self, data_list: List[Dict]):
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_item = {
                executor.submit(self._process_single_item, item): item 
                for item in data_list
            }
            
            for future in future_to_item:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                    self.processing_stats["total_processed"] += 1
                except Exception as e:
                    self.processing_stats["errors"] += 1
                    original_item = future_to_item[future]
                    results.append({"error": str(e), "original": original_item})
        
        return results
    
    def _process_single_item(self, item: Dict):
        # Complex processing logic with multiple steps
        if not isinstance(item, dict):
            raise ValueError("Item must be a dictionary")
        
        # Data validation
        required_fields = ['id', 'data']
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Process data
        data = item['data']
        if isinstance(data, str):
            data_hash = hashlib.md5(data.encode()).hexdigest()
            complexity = len(data) // 100 + 1
        else:
            data_hash = hashlib.md5(str(data).encode()).hexdigest()
            complexity = 1
        
        # Use expensive calculation with caching
        calculated_value = self.expensive_calculation(data_hash, complexity)
        
        # Transform data
        transformed = {
            "id": item['id'],
            "original_data": data,
            "hash": data_hash,
            "calculated_value": calculated_value,
            "processed_at": datetime.now().isoformat(),
            "complexity_score": complexity
        }
        
        # Apply additional transformations based on config
        if 'transformations' in self.config:
            for transform in self.config['transformations']:
                transformed = self._apply_transformation(transformed, transform)
        
        return transformed
    
    def _apply_transformation(self, data: Dict, transformation: Dict):
        transform_type = transformation.get('type')
        
        if transform_type == 'multiply':
            field = transformation.get('field', 'calculated_value')
            multiplier = transformation.get('multiplier', 1)
            if field in data and isinstance(data[field], (int, float)):
                data[field] = data[field] * multiplier
        
        elif transform_type == 'add_field':
            field_name = transformation.get('name')
            field_value = transformation.get('value')
            if field_name:
                data[field_name] = field_value
        
        return data

class APIClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = None
        
        # Set default headers
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        self.session.headers.update({'User-Agent': 'DataProcessor/1.0'})
    
    def _rate_limit(self, min_interval: float = 0.1):
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
    
    def fetch_data(self, endpoint: str, params: Dict = None, timeout: int = 30):
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            self.request_count += 1
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            elif response.status_code == 429:
                # Rate limited - wait and retry once
                time.sleep(2)
                response = self.session.get(url, params=params, timeout=timeout)
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
            
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code
            }
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection error"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def post_data(self, endpoint: str, data: Dict, files: Dict = None):
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if files:
                response = self.session.post(url, data=data, files=files, timeout=60)
            else:
                response = self.session.post(url, json=data, timeout=30)
            
            self.request_count += 1
            
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

def complex_algorithm(data_matrix: List[List[float]], weights: List[float] = None):
    if not data_matrix or not data_matrix[0]:
        return None
    
    rows, cols = len(data_matrix), len(data_matrix[0])
    
    if weights is None:
        weights = [1.0] * cols
    
    # Calculate weighted sums for each row
    weighted_sums = []
    for i in range(rows):
        row_sum = 0
        for j in range(cols):
            # Nested calculation with potential performance issues
            value = data_matrix[i][j]
            weight = weights[j] if j < len(weights) else 1.0
            
            # Complex transformation
            if value > 0:
                transformed = (value ** 0.5) * weight
            else:
                transformed = abs(value) * weight * 0.5
            
            row_sum += transformed
        
        weighted_sums.append(row_sum)
    
    # Find patterns in the data
    patterns = []
    for i in range(rows - 1):
        for j in range(i + 1, rows):
            # Calculate similarity between rows
            similarity = 0
            for k in range(cols):
                diff = abs(data_matrix[i][k] - data_matrix[j][k])
                similarity += 1 / (1 + diff)  # Similarity metric
            
            if similarity > cols * 0.8:  # High similarity threshold
                patterns.append({
                    "row1": i,
                    "row2": j,
                    "similarity": similarity / cols
                })
    
    # Statistical calculations
    total_sum = sum(weighted_sums)
    mean = total_sum / len(weighted_sums)
    variance = sum((x - mean) ** 2 for x in weighted_sums) / len(weighted_sums)
    std_dev = variance ** 0.5
    
    return {
        "weighted_sums": weighted_sums,
        "patterns": patterns,
        "statistics": {
            "mean": mean,
            "variance": variance,
            "std_dev": std_dev,
            "total": total_sum
        },
        "metadata": {
            "rows": rows,
            "cols": cols,
            "pattern_count": len(patterns)
        }
    }

def test_ai_code_review():
    
    # Initialize AI reviewer
    ai = AIPython(
        provider="google",
        model="gemini-1.5-pro",
        verbose=False,
        ask_permission=False
    )
    
    # Read this file's content for review
    current_file = Path(__file__)
    with open(current_file, 'r', encoding='utf-8') as f:
        code_content = f.read()
    
    # AI code review prompt
    review_prompt = f"""
You are an expert code reviewer. Analyze this Python code for:

1. Security vulnerabilities
2. Performance issues  
3. Code quality problems
4. Best practice violations
5. Potential bugs

Code to review:
```python
{code_content}
```

Provide detailed feedback with specific line numbers where possible.
Focus on real issues that would matter in production code.
"""
    
    try:
        review_result = ai.llm_provider.generate(review_prompt)
        
        # Save review results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_file = f"code_review_results_{timestamp}.md"
        
        with open(review_file, 'w', encoding='utf-8') as f:
            f.write(f"# Code Review Results - {timestamp}\n\n")
            f.write(f"**File:** {current_file.name}\n")
            f.write(f"**Lines of Code:** {len(code_content.splitlines())}\n")
            f.write(f"**Review Date:** {datetime.now().isoformat()}\n\n")
            f.write("## AI Review Results\n\n")
            f.write(review_result)
        
        return {
            "success": True,
            "review_file": review_file,
            "lines_analyzed": len(code_content.splitlines()),
            "review_summary": review_result[:500] + "..." if len(review_result) > 500 else review_result
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    result = test_ai_code_review()
    
    if result["success"]:
        print(f"✅ Code review completed successfully!")
        print(f"📄 Review saved to: {result['review_file']}")
        print(f"📊 Lines analyzed: {result['lines_analyzed']}")
        print(f"\n📝 Review Preview:")
        print(result['review_summary'])
    else:
        print(f"❌ Code review failed: {result['error']}")
        print("💡 Make sure to set your GOOGLE_API_KEY in the file or environment variable")
