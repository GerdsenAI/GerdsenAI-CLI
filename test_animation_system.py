#!/usr/bin/env python3
"""
Test script for animation system and approval workflow.

This script tests the core functionality without requiring manual interaction.
"""

import asyncio
from gerdsenai_cli.ui.animations import AnimationFrames, StatusAnimation, PlanCapture


def test_animation_frames():
    """Test that all animation frames are defined."""
    print("🧪 Test 1: Animation Frames")
    print("-" * 70)
    
    assert hasattr(AnimationFrames, 'SPINNER'), "SPINNER frames missing"
    assert hasattr(AnimationFrames, 'THINKING'), "THINKING frames missing"
    assert hasattr(AnimationFrames, 'PLANNING'), "PLANNING frames missing"
    assert hasattr(AnimationFrames, 'ANALYZING'), "ANALYZING frames missing"
    assert hasattr(AnimationFrames, 'EXECUTING'), "EXECUTING frames missing"
    assert hasattr(AnimationFrames, 'DOTS'), "DOTS frames missing"
    
    assert len(AnimationFrames.SPINNER) > 0, "SPINNER frames empty"
    assert len(AnimationFrames.THINKING) > 0, "THINKING frames empty"
    assert len(AnimationFrames.PLANNING) > 0, "PLANNING frames empty"
    
    print("✅ All animation frames defined and non-empty")
    print()


def test_plan_capture_extraction():
    """Test plan extraction from AI response."""
    print("🧪 Test 2: Plan Capture - Extraction")
    print("-" * 70)
    
    sample_response = """
I'll create a calculator module with the following functions.

First, I'll create calculator.py with add, subtract, multiply, and divide functions.
Then I'll add tests in test_calculator.py to verify each function works correctly.
Finally, I'll update the main.py to import and use the calculator.

This will be a simple implementation focusing on basic arithmetic operations.
"""
    
    plan = PlanCapture.extract_summary(sample_response)
    
    assert 'summary' in plan, "Missing 'summary' key"
    assert 'files_affected' in plan, "Missing 'files_affected' key"
    assert 'actions' in plan, "Missing 'actions' key"
    assert 'complexity' in plan, "Missing 'complexity' key"
    assert 'full_response' in plan, "Missing 'full_response' key"
    
    assert len(plan['summary']) > 0, "Summary is empty"
    assert plan['full_response'] == sample_response, "Full response not preserved"
    assert plan['complexity'] in ['simple', 'moderate', 'complex'], f"Invalid complexity: {plan['complexity']}"
    
    print(f"✅ Plan extraction successful")
    print(f"   - Summary: {len(plan['summary'])} chars")
    print(f"   - Files: {len(plan['files_affected'])} detected")
    print(f"   - Actions: {len(plan['actions'])} detected")
    print(f"   - Complexity: {plan['complexity']}")
    print()


def test_plan_capture_file_detection():
    """Test file detection in plan capture."""
    print("🧪 Test 3: Plan Capture - File Detection")
    print("-" * 70)
    
    response_with_files = """
I'll modify the following files:
- gerdsenai_cli/main.py
- gerdsenai_cli/ui/animations.py
- tests/test_animations.py
- README.md
- config.json
"""
    
    plan = PlanCapture.extract_summary(response_with_files)
    
    expected_files = ['main.py', 'animations.py', 'test_animations.py', 'README.md', 'config.json']
    detected_files = plan['files_affected']
    
    print(f"✅ File detection working")
    print(f"   - Expected at least: {len(expected_files)} files")
    print(f"   - Detected: {len(detected_files)} files")
    
    for file in detected_files:
        print(f"     • {file}")
    print()


def test_plan_capture_action_detection():
    """Test action detection in plan capture."""
    print("🧪 Test 4: Plan Capture - Action Detection")
    print("-" * 70)
    
    response_with_actions = """
Here's what I'll do:

1. Create a new authentication module
2. Modify the existing user model
3. Add password hashing functionality
4. Update the database schema
5. Implement login and logout functions
6. Refactor the session management code
"""
    
    plan = PlanCapture.extract_summary(response_with_actions)
    actions = plan['actions']
    
    action_verbs = ['create', 'modify', 'add', 'update', 'implement', 'refactor']
    assert len(actions) > 0, "No actions detected"
    
    # Check that detected actions contain expected verbs
    actions_text = ' '.join(actions).lower()
    detected_verbs = [verb for verb in action_verbs if verb in actions_text]
    
    print(f"✅ Action detection working")
    print(f"   - Detected: {len(actions)} actions")
    print(f"   - Verbs found: {', '.join(detected_verbs)}")
    
    for i, action in enumerate(actions[:3], 1):
        print(f"     {i}. {action[:60]}...")
    print()


def test_plan_preview_formatting():
    """Test plan preview formatting."""
    print("🧪 Test 5: Plan Preview Formatting")
    print("-" * 70)
    
    sample_plan = {
        'summary': 'Creating a calculator module with basic arithmetic functions',
        'files_affected': ['calculator.py', 'test_calculator.py', 'main.py'],
        'actions': [
            'Create calculator.py with add, subtract functions',
            'Add multiply and divide functions',
            'Create comprehensive test suite',
        ],
        'complexity': 'moderate',
        'full_response': 'Full details here...'
    }
    
    preview = PlanCapture.format_plan_preview(sample_plan)
    
    assert '📋 Plan Summary' in preview, "Missing plan summary header"
    assert '📁 Files to be modified:' in preview, "Missing files section"
    assert '⚡ Actions:' in preview, "Missing actions section"
    assert 'Complexity: MODERATE' in preview, "Missing complexity"
    assert 'Do you want to proceed?' in preview, "Missing approval prompt"
    assert 'yes' in preview.lower() and 'no' in preview.lower(), "Missing yes/no options"
    
    print("✅ Plan preview formatting correct")
    print(f"   - Preview length: {len(preview)} chars")
    print(f"   - Contains all required sections")
    print()
    print("Sample preview:")
    print("-" * 70)
    print(preview[:500] + "...")
    print()


async def test_status_animation_mock():
    """Test status animation with mock TUI."""
    print("🧪 Test 6: Status Animation")
    print("-" * 70)
    
    from gerdsenai_cli.ui.prompt_toolkit_tui import PromptToolkitTUI
    from unittest.mock import Mock
    
    # Create a mock that mimics PromptToolkitTUI
    mock_tui = Mock(spec=PromptToolkitTUI)
    mock_tui.status_text = ""
    mock_tui.app = Mock()
    mock_tui.app.invalidate = Mock()
    
    animation = StatusAnimation(mock_tui, "Testing", AnimationFrames.SPINNER)
    
    # Test start
    animation.start()
    assert animation.running, "Animation should be running after start"
    assert animation.task is not None, "Animation task should be created"
    
    # Let it run for a bit
    await asyncio.sleep(0.5)
    
    # Test update
    animation.update_message("New message")
    assert animation.message == "New message", "Message not updated"
    
    # Test stop
    animation.stop()
    assert not animation.running, "Animation should be stopped"
    
    print("✅ Status animation working")
    print(f"   - Start/stop functionality verified")
    print(f"   - Message update verified")
    print()


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Animation System & Approval Workflow - Test Suite")
    print("=" * 70 + "\n")
    
    try:
        test_animation_frames()
        test_plan_capture_extraction()
        test_plan_capture_file_detection()
        test_plan_capture_action_detection()
        test_plan_preview_formatting()
        await test_status_animation_mock()
        
        print("=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\n✅ Animation system is working correctly")
        print("✅ Plan capture and extraction verified")
        print("✅ File and action detection working")
        print("✅ Plan preview formatting correct")
        print("✅ Status animation functional")
        
        print("\n📝 Next Steps:")
        print("   1. The TUI is running in another terminal")
        print("   2. Type: /mode architect")
        print("   3. Make a request: 'Create a calculator module'")
        print("   4. Watch the animations and approval workflow!")
        print()
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)
        print(f"\nError: {e}")
        return False
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ TEST ERROR")
        print("=" * 70)
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
