"""
Test script to verify Selenium and Edge WebDriver setup
"""

def test_imports():
    """Test if selenium and webdriver_manager are installed"""
    print("Testing imports...")
    try:
        import selenium
        print(f"✓ selenium installed (version {selenium.__version__})")
    except ImportError as e:
        print(f"✗ selenium not installed: {e}")
        return False
    
    try:
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        print("✓ webdriver_manager installed")
    except ImportError as e:
        print(f"✗ webdriver_manager not installed: {e}")
        return False
    
    return True


def test_edge_driver():
    """Test if Edge WebDriver can be initialized"""
    print("\nTesting Edge WebDriver initialization...")
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service as EdgeService
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        
        edge_options = EdgeOptions()
        edge_options.add_argument('--headless=new')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        print("Initializing Edge WebDriver...")
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=edge_options)
        
        print("✓ Edge WebDriver initialized successfully")
        
        # Test a simple navigation
        print("Testing navigation to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Page loaded: {driver.title}")
        
        driver.quit()
        print("✓ Driver closed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Edge WebDriver failed: {e}")
        return False


def test_chrome_driver():
    """Test if Chrome WebDriver can be initialized (fallback)"""
    print("\nTesting Chrome WebDriver initialization (fallback)...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        print("Initializing Chrome WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ Chrome WebDriver initialized successfully")
        
        driver.quit()
        print("✓ Driver closed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Chrome WebDriver failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Selenium Setup Verification")
    print("=" * 60)
    
    if not test_imports():
        print("\n❌ Please install required packages:")
        print("   pip install selenium==4.27.1 webdriver-manager==4.0.2")
        exit(1)
    
    edge_ok = test_edge_driver()
    
    if not edge_ok:
        print("\nEdge failed, trying Chrome as fallback...")
        chrome_ok = test_chrome_driver()
        
        if not chrome_ok:
            print("\n❌ Both Edge and Chrome WebDriver failed")
            print("   Make sure Microsoft Edge or Google Chrome is installed")
            exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Selenium setup is working correctly")
    print("=" * 60)
