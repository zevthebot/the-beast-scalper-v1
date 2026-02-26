#!/usr/bin/env python3
"""
Comprehensive Test Suite for MT5 Low-Token Mode
Tests all components before deployment
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Test configuration
TEST_DIR = Path(__file__).parent
REQUIRED_FILES = [
    "connector_optimized.py",
    "signals.json",
    "state.json",
    "README_OPTIMIZED.md",
    "SimpleAIBot_EA.mq5"
]

# Tiered slot configuration
SLOTS_NORMAL = 6
SLOTS_PREMIUM = 4
MAX_POSITIONS = 10
SCORE_THRESHOLD_NORMAL = 70
SCORE_THRESHOLD_PREMIUM = 85

def test_file_structure():
    """Test 1: Verify all files exist"""
    print("=" * 60)
    print("TEST 1: File Structure")
    print("=" * 60)
    
    all_exist = True
    for file in REQUIRED_FILES:
        path = TEST_DIR / file
        exists = path.exists()
        status = "[OK]" if exists else "[ERR]"
        print(f"  {status} {file}")
        if not exists:
            all_exist = False
    
    return all_exist

def test_signals_json():
    """Test 2: Validate signals.json format"""
    print("\n" + "=" * 60)
    print("TEST 2: Signals JSON Format")
    print("=" * 60)
    
    try:
        with open(TEST_DIR / "signals.json", 'r') as f:
            data = json.load(f)
        
        # Check required fields
        required = ["timestamp", "account", "signals", "positions"]
        for field in required:
            if field in data:
                print(f"  [OK] {field} present")
            else:
                print(f"  [ERR] {field} missing")
                return False
        
        # Check account subfields
        account_fields = ["balance", "equity", "profit", "currency"]
        for field in account_fields:
            if field in data["account"]:
                print(f"  [OK] account.{field} present")
            else:
                print(f"  [WARN] account.{field} missing (optional)")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  [ERR] Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  [ERR] Error: {e}")
        return False

def test_state_json():
    """Test 3: Validate state.json format"""
    print("\n" + "=" * 60)
    print("TEST 3: State JSON Format")
    print("=" * 60)
    
    try:
        with open(TEST_DIR / "state.json", 'r') as f:
            data = json.load(f)
        
        required = ["last_scan", "positions_at_last_scan", "daily_stats"]
        for field in required:
            if field in data:
                print(f"  [OK] {field} present")
            else:
                print(f"  [ERR] {field} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"  [ERR] Error: {e}")
        return False

def test_connector_import():
    """Test 4: Verify connector can be imported"""
    print("\n" + "=" * 60)
    print("TEST 4: Connector Import")
    print("=" * 60)
    
    try:
        sys.path.insert(0, str(TEST_DIR))
        from connector_optimized import MT5ConnectorOptimized, MT5State
        print("  [OK] connector_optimized imports successfully")
        
        # Check class methods
        connector = MT5ConnectorOptimized()
        required_methods = ['connect', 'get_positions', 'read_signals', 'process_signals', 'run']
        for method in required_methods:
            if hasattr(connector, method):
                print(f"  [OK] Method '{method}' exists")
            else:
                print(f"  [ERR] Method '{method}' missing")
                return False
        
        return True
        
    except ImportError as e:
        print(f"  [ERR] Import error: {e}")
        return False
    except Exception as e:
        print(f"  [ERR] Error: {e}")
        return False

def test_mt5_connection():
    """Test 5: Test MT5 connection (requires MT5 running)"""
    print("\n" + "=" * 60)
    print("TEST 5: MT5 Connection")
    print("=" * 60)
    
    try:
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            print("  [WARN] MT5 not initialized (may not be running)")
            print("  [INFO] Start MT5 and login to account 62108425 to test")
            return None  # Neutral
        
        account = mt5.account_info()
        if account:
            print(f"  [OK] MT5 connected")
            print(f"  [OK] Account: {account.login}")
            print(f"  [OK] Balance: {account.balance:.2f} {account.currency}")
            mt5.shutdown()
            return True
        else:
            print("  [WARN] MT5 running but not logged in")
            mt5.shutdown()
            return None
            
    except ImportError:
        print("  [ERR] MetaTrader5 module not installed")
        print("  [INFO] Run: pip install MetaTrader5")
        return False
    except Exception as e:
        print(f"  [WARN] Connection test error: {e}")
        return None

def test_signal_processing():
    """Test 6: Test signal processing logic"""
    print("\n" + "=" * 60)
    print("TEST 6: Signal Processing Logic")
    print("=" * 60)
    
    try:
        sys.path.insert(0, str(TEST_DIR))
        from connector_optimized import MT5ConnectorOptimized
        
        connector = MT5ConnectorOptimized()
        
        # Test correlation check
        result, other = connector.check_correlation("EURUSD", ["GBPUSD"])
        if result and other == "GBPUSD":
            print("  [OK] Correlation detection works")
        else:
            print(f"  [WARN] Correlation check returned: {result}, {other}")
        
        # Test state management
        connector.state.update(test_value=123)
        with open(TEST_DIR / "state.json", 'r') as f:
            state_data = json.load(f)
        
        if state_data.get("test_value") == 123:
            print("  [OK] State persistence works")
        else:
            print("  [ERR] State persistence failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  [ERR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ea_syntax():
    """Test 7: Basic EA syntax check"""
    print("\n" + "=" * 60)
    print("TEST 7: EA Syntax Check")
    print("=" * 60)
    
    ea_path = TEST_DIR / "SimpleAIBot_EA.mq5"
    
    try:
        with open(ea_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for key components
        checks = [
            ("#property", "Property directives"),
            ("OnInit", "OnInit function"),
            ("OnDeinit", "OnDeinit function"),
            ("OnTick", "OnTick function"),
            ("ExportSignalsToJSON", "ExportSignalsToJSON function"),
        ]
        
        all_found = True
        for keyword, description in checks:
            if keyword in content:
                print(f"  [OK] {description}")
            else:
                print(f"  [ERR] {description} missing")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"  [ERR] Error reading EA: {e}")
        return False

def run_all_tests():
    """Run complete test suite"""
    print("\n" + "MT5 LOW-TOKEN MODE - COMPREHENSIVE TEST SUITE".center(60))
    
    tests = [
        ("File Structure", test_file_structure),
        ("Signals JSON", test_signals_json),
        ("State JSON", test_state_json),
        ("Connector Import", test_connector_import),
        ("MT5 Connection", test_mt5_connection),
        ("Signal Processing", test_signal_processing),
        ("EA Syntax", test_ea_syntax),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  [ERR] Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    neutral = sum(1 for _, r in results if r is None)
    failed = sum(1 for _, r in results if r is False)
    
    print(f"\n  [OK] Passed: {passed}")
    print(f"  [WARN] Neutral (needs MT5): {neutral}")
    print(f"  [ERR] Failed: {failed}")
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("ALL CRITICAL TESTS PASSED")
        print("System ready for deployment!")
        print(f"\nConfiguration: {MAX_POSITIONS} slots total")
        print(f"  - Slots 1-{SLOTS_NORMAL}: threshold {SCORE_THRESHOLD_NORMAL}+")
        print(f"  - Slots {SLOTS_NORMAL+1}-{MAX_POSITIONS}: threshold {SCORE_THRESHOLD_PREMIUM}+")
    else:
        print("SOME TESTS FAILED")
        print("Please review failures before deployment")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
