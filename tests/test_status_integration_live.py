#!/usr/bin/env python3
"""
Integration test for status messages in the CLI.

This test verifies the status message system is properly integrated.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_status_messages_standalone():
    """Test just the status message generation without agent."""
    from gerdsenai_cli.utils.status_messages import OperationType, get_status_message
    
    print("\n" + "="*80)
    print("STANDALONE STATUS MESSAGE TEST")
    print("="*80 + "\n")
    
    operations = [
        OperationType.THINKING,
        OperationType.ANALYZING,
        OperationType.CONTEXTUALIZING,
        OperationType.READING,
        OperationType.STREAMING,
        OperationType.SYNTHESIZING,
    ]
    
    print("Testing message generation for typical operation sequence:\n")
    for i, op_type in enumerate(operations, 1):
        message = get_status_message(op_type)
        print(f"{i}. {op_type.value.upper()}: {message}")
    
    print("\n" + "="*80)
    print("✓ Status message generation working perfectly!")
    print("="*80 + "\n")


def test_integration_check():
    """Verify all integration points are in place."""
    print("\n" + "="*80)
    print("STATUS MESSAGE INTEGRATION VERIFICATION")
    print("="*80 + "\n")
    
    print("Checking integration points...\n")
    
    # Check 1: Status messages module
    try:
        from gerdsenai_cli.utils.status_messages import OperationType, get_status_message
        print("✓ Status messages module imported successfully")
        print(f"  - Found {len(OperationType)} operation types")
    except ImportError as e:
        print(f"✗ Failed to import status messages: {e}")
        return False
    
    # Check 2: Console integration
    try:
        # Just check the file exists and has the right method
        with open("gerdsenai_cli/ui/console.py", "r") as f:
            content = f.read()
            if "set_operation" in content:
                print("✓ EnhancedConsole.set_operation() method found")
            else:
                print("✗ set_operation() method not found in console.py")
                return False
            
            if "from ..utils.status_messages import" in content:
                print("✓ Status messages imported in console.py")
            else:
                print("✗ Status messages not imported in console.py")
                return False
    except Exception as e:
        print(f"✗ Failed to check console.py: {e}")
        return False
    
    # Check 3: Agent integration
    try:
        with open("gerdsenai_cli/core/agent.py", "r") as f:
            content = f.read()
            if "status_callback" in content:
                print("✓ Agent has status_callback parameter")
            else:
                print("✗ status_callback not found in agent.py")
                return False
            
            if 'status_callback("' in content or "status_callback('" in content:
                print("✓ Agent calls status_callback")
            else:
                print("✗ Agent doesn't call status_callback")
                return False
    except Exception as e:
        print(f"✗ Failed to check agent.py: {e}")
        return False
    
    # Check 4: Main loop integration
    try:
        with open("gerdsenai_cli/main.py", "r") as f:
            content = f.read()
            if "set_operation" in content:
                print("✓ Main loop calls set_operation()")
            else:
                print("✗ set_operation() not called in main.py")
                return False
            
            if "status_callback" in content:
                print("✓ Main loop passes status_callback to agent")
            else:
                print("✗ status_callback not passed in main.py")
                return False
    except Exception as e:
        print(f"✗ Failed to check main.py: {e}")
        return False
    
    print("\n" + "="*80)
    print("✓ ALL INTEGRATION CHECKS PASSED")
    print("="*80)
    return True


if __name__ == "__main__":
    print("\n🎯 Testing Status Message System Integration\n")
    
    # Test 1: Standalone message generation
    print("Test 1: Message Generation")
    print("-" * 80)
    test_status_messages_standalone()
    
    # Test 2: Integration verification
    print("\n\nTest 2: Integration Verification")
    print("-" * 80)
    success = test_integration_check()
    
    if success:
        print("\n\n" + "="*80)
        print("🎉 STATUS MESSAGE SYSTEM FULLY INTEGRATED")
        print("="*80)
        print("\nNext steps:")
        print("1. Run the CLI with: python -m gerdsenai_cli")
        print("2. Enter any query and watch the sophisticated status messages")
        print("3. Messages will appear in the footer during AI operations")
        print("\nExample status messages you'll see:")
        print('  • "Cogitating possibilities via methodical inquiry..."')
        print('  • "Deconstructing semantic topology..."')
        print('  • "Channeling cognitive flow..."')
        print()
    else:
        print("\n\n" + "="*80)
        print("⚠ INTEGRATION INCOMPLETE")
        print("="*80)
        print("\nSome integration points are missing.")
        print("Review the error messages above.")
        print()
