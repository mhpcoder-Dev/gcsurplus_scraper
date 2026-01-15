"""
Test Microsoft Edge WebDriver configuration
Tests different configurations to find what works
"""

import sys
import time


def test_1_basic_edge():
    """Test 1: Basic Edge without any options"""
    print("\n" + "="*60)
    print("TEST 1: Basic Edge (no options)")
    print("="*60)
    try:
        from selenium import webdriver
        
        print("Initializing Edge WebDriver...")
        driver = webdriver.Edge()
        print("✓ Driver initialized!")
        
        print("Navigating to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_2_edge_headless_new():
    """Test 2: Edge with --headless=new"""
    print("\n" + "="*60)
    print("TEST 2: Edge with --headless=new")
    print("="*60)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless=new')
        
        print("Initializing Edge WebDriver (headless=new)...")
        driver = webdriver.Edge(options=edge_options)
        print("✓ Driver initialized!")
        
        print("Navigating to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_3_edge_headless_old():
    """Test 3: Edge with old --headless flag"""
    print("\n" + "="*60)
    print("TEST 3: Edge with old --headless")
    print("="*60)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless')
        
        print("Initializing Edge WebDriver (headless)...")
        driver = webdriver.Edge(options=edge_options)
        print("✓ Driver initialized!")
        
        print("Navigating to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_4_edge_full_config():
    """Test 4: Edge with full configuration (as used in scraper)"""
    print("\n" + "="*60)
    print("TEST 4: Edge with full configuration")
    print("="*60)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless=new')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--window-size=1920,1080')
        edge_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        print("Initializing Edge WebDriver (full config)...")
        driver = webdriver.Edge(options=edge_options)
        print("✓ Driver initialized!")
        
        print("Navigating to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_5_edge_gsa_page():
    """Test 5: Load actual GSA auction page"""
    print("\n" + "="*60)
    print("TEST 5: Load GSA auction detail page")
    print("="*60)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        import re
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless=new')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--window-size=1920,1080')
        edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        print("Initializing Edge WebDriver...")
        driver = webdriver.Edge(options=edge_options)
        print("✓ Driver initialized!")
        
        url = "https://www.gsaauctions.gov/auctions/preview/348166"
        print(f"Loading GSA page: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        print(f"✓ Page loaded: {driver.title}")
        print(f"  Page source length: {len(driver.page_source)} bytes")
        
        # Try to find closing time
        # Format: <b>Closing Time </b>...</span>01/13/2026 02:04PM CT</li>
        # Note: No space between minutes and AM/PM
        page_source = driver.page_source
        
        # Updated pattern - more specific to avoid matching start time
        # Look for <b>Closing Time and capture the date/time that follows
        match = re.search(
            r'<b>Closing Time\s*</b>.*?(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}[AP]M)\s+([A-Z]{2,3})',
            page_source,
            re.IGNORECASE | re.DOTALL
        )
        
        if match:
            date_part = match.group(1)  # "01/16/2026"
            time_part = match.group(2)  # "06:13PM"
            tz_part = match.group(3)    # "CT"
            print(f"✓ Found closing time: {date_part} {time_part} {tz_part}")
            
            # Try parsing it
            from datetime import datetime
            try:
                # Parse the datetime (no space before AM/PM)
                dt_str = f"{date_part} {time_part}"
                dt = datetime.strptime(dt_str, '%m/%d/%Y %I:%M%p')
                print(f"✓ Successfully parsed: {dt}")
                print(f"  Timezone: {tz_part}")
            except Exception as e:
                print(f"⚠ Could not parse datetime: {e}")
        else:
            print("⚠ Could not find closing time pattern")
            # Save page source for inspection
            with open("gsa_page_source.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("  Page source saved to: gsa_page_source.html")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_6_edge_with_service():
    """Test 6: Edge with explicit Service"""
    print("\n" + "="*60)
    print("TEST 6: Edge with explicit Service")
    print("="*60)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service as EdgeService
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless=new')
        
        # Try to find msedgedriver in common locations
        import os
        possible_paths = [
            'msedgedriver.exe',
            './msedgedriver.exe',
            'C:\\Windows\\msedgedriver.exe',
            os.path.expanduser('~/.wdm/drivers/edgedriver/win64/*/msedgedriver.exe')
        ]
        
        service = None
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found driver at: {path}")
                service = EdgeService(executable_path=path)
                break
        
        if service:
            print("Initializing Edge WebDriver with explicit service...")
            driver = webdriver.Edge(service=service, options=edge_options)
        else:
            print("Using default driver location...")
            driver = webdriver.Edge(options=edge_options)
        
        print("✓ Driver initialized!")
        
        print("Navigating to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def check_edge_installation():
    """Check Edge browser and driver installation"""
    print("\n" + "="*60)
    print("CHECKING EDGE INSTALLATION")
    print("="*60)
    
    import os
    import subprocess
    
    # Check Edge browser
    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]
    
    edge_found = False
    for path in edge_paths:
        if os.path.exists(path):
            print(f"✓ Edge browser found: {path}")
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                version = result.stdout.strip()
                print(f"  Version: {version}")
            except:
                pass
            edge_found = True
            break
    
    if not edge_found:
        print("✗ Edge browser not found")
    
    # Check Edge driver
    print("\nChecking for msedgedriver.exe...")
    driver_paths = [
        'msedgedriver.exe',
        './msedgedriver.exe',
        os.path.join(os.getcwd(), 'msedgedriver.exe'),
    ]
    
    driver_found = False
    for path in driver_paths:
        if os.path.exists(path):
            print(f"✓ Edge driver found: {path}")
            driver_found = True
            break
    
    if not driver_found:
        print("✗ msedgedriver.exe not found in current directory")
        print("  Download from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
    
    # Check PATH
    print("\nChecking PATH for msedgedriver...")
    try:
        result = subprocess.run(['where', 'msedgedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ msedgedriver in PATH: {result.stdout.strip()}")
        else:
            print("✗ msedgedriver not in PATH")
    except:
        print("✗ Could not check PATH")


if __name__ == "__main__":
    print("="*60)
    print("EDGE WEBDRIVER TEST SUITE")
    print("="*60)
    
    # Check installation first
    check_edge_installation()
    
    # Run tests
    results = []
    
    tests = [
        ("Basic Edge", test_1_basic_edge),
        ("Edge Headless (new)", test_2_edge_headless_new),
        ("Edge Headless (old)", test_3_edge_headless_old),
        ("Edge Full Config", test_4_edge_full_config),
        ("Edge with Service", test_6_edge_with_service),
        ("GSA Page Load", test_5_edge_gsa_page),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\n⚠ Tests interrupted by user")
            break
        except Exception as e:
            print(f"\n✗ Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed > 0:
        print("\n✓ At least one configuration works!")
        print("  You can use Edge WebDriver for scraping")
    else:
        print("\n✗ All tests failed")
        print("  Check:")
        print("  1. Microsoft Edge is installed")
        print("  2. msedgedriver.exe is in PATH or current directory")
        print("  3. Driver version matches Edge version")
        print("  4. No antivirus/firewall blocking")
