"""
Download and install Microsoft Edge WebDriver to PATH
This avoids the need for internet access during scraping
"""

import os
import requests
import zipfile
import subprocess
from pathlib import Path


def get_edge_version():
    """Get installed Microsoft Edge version"""
    edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    
    if not os.path.exists(edge_path):
        edge_path = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    
    if not os.path.exists(edge_path):
        print("❌ Microsoft Edge not found")
        return None
    
    try:
        result = subprocess.run(
            [edge_path, '--version'],
            capture_output=True,
            text=True
        )
        version = result.stdout.strip().split()[-1]
        print(f"✓ Edge version: {version}")
        return version
    except Exception as e:
        print(f"❌ Could not get Edge version: {e}")
        return None


def download_edge_driver(version):
    """Download matching Edge WebDriver"""
    major_version = version.split('.')[0]
    
    # Edge driver download URL
    url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_win64.zip"
    
    print(f"Downloading Edge WebDriver {version}...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        zip_path = "edgedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Downloaded {len(response.content)} bytes")
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        os.remove(zip_path)
        
        print("✓ Edge WebDriver extracted: msedgedriver.exe")
        print("\nNext steps:")
        print("1. Move msedgedriver.exe to a directory in your PATH")
        print("   OR")
        print("2. Add current directory to PATH")
        print("   OR")
        print("3. Keep it here and the scraper will find it")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")
        print("\nAlternative: Download manually from:")
        print(f"https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Edge WebDriver Installer")
    print("=" * 60)
    
    version = get_edge_version()
    if version:
        download_edge_driver(version)
    else:
        print("\nPlease install Microsoft Edge first")
