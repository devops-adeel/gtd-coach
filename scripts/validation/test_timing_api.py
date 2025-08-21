#!/usr/bin/env python3
"""
Debug Timing API authentication
"""

import os
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

api_key = os.getenv('TIMING_API_KEY')
print(f"API Key present: {bool(api_key)}")
print(f"API Key length: {len(api_key) if api_key else 0}")

# Test 1: List projects (GET request)
print("\n1. Testing GET /projects...")
response = requests.get(
    "https://web.timingapp.com/api/v1/projects",
    headers={
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    },
    timeout=5
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Success! Found {len(data.get('data', []))} projects")
else:
    print(f"Error: {response.text[:200]}")

# Test 2: Get report (different endpoint)
print("\n2. Testing GET /report...")
response = requests.get(
    "https://web.timingapp.com/api/v1/report",
    headers={
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    },
    params={
        'start_date_min': '2025-01-01',
        'start_date_max': '2025-01-31'
    },
    timeout=5
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("Success! Report endpoint works")
else:
    print(f"Error: {response.text[:200]}")

# Test 3: Try to create a project (POST request)
print("\n3. Testing POST /projects...")
test_project = {
    "title": "Test Project",
    "color": "#00AA00",
    "productivity_score": 1
}

response = requests.post(
    "https://web.timingapp.com/api/v1/projects",
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    json=test_project,
    timeout=5
)
print(f"Status: {response.status_code}")
if response.status_code in [200, 201]:
    print("Success! Project created")
    print(f"Response: {response.json()}")
elif response.status_code == 401:
    print("401 Unauthorized - API key may not have write permissions")
    print(f"Response: {response.text[:500]}")
elif response.status_code == 403:
    print("403 Forbidden - Project creation may be disabled")
    print(f"Response: {response.text[:500]}")
else:
    print(f"Error {response.status_code}: {response.text[:500]}")

print("\n" + "="*50)
print("Diagnosis:")
if response.status_code == 401:
    print("- Your API key is valid for reading data (GET requests work)")
    print("- But it cannot create projects (POST requests fail)")
    print("- This might be a permissions issue with your Timing API key")
    print("- Check if your Timing subscription allows API project creation")
    print("\nWorkaround: Create the 3 projects manually in Timing app:")
    print("  1. 'Deep Work - Week XX' (Green)")
    print("  2. 'Admin & Communication' (Orange)")  
    print("  3. 'Reactive & Urgent' (Red)")