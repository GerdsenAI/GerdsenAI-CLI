#!/usr/bin/env python3
"""
Quick demo of the animation system.

This script demonstrates the different animation types available.
"""

import asyncio
from gerdsenai_cli.ui.animations import AnimationFrames, PlanCapture


def demo_animation_frames():
    """Show all available animation frame sequences."""
    print("🎨 Animation Frames Demo\n")
    print("=" * 70)
    
    animations = {
        "SPINNER": AnimationFrames.SPINNER,
        "THINKING": AnimationFrames.THINKING,
        "PLANNING": AnimationFrames.PLANNING,
        "ANALYZING": AnimationFrames.ANALYZING,
        "EXECUTING": AnimationFrames.EXECUTING,
        "DOTS": AnimationFrames.DOTS,
    }
    
    for name, frames in animations.items():
        print(f"\n{name:12} : {' '.join(frames)}")
    
    print("\n" + "=" * 70)


def demo_plan_capture():
    """Demonstrate plan extraction and formatting."""
    print("\n\n📋 Plan Capture Demo\n")
    print("=" * 70)
    
    # Sample AI response
    sample_response = """
I'll help you create a user authentication module for your application.

Here's my plan:

1. Create the main authentication module in gerdsenai_cli/auth/user_auth.py
   This will contain the core authentication logic including login, logout, and session management.

2. Add password hashing utilities using bcrypt
   We'll create secure password storage and verification functions.

3. Implement session token generation
   Using JWT tokens for stateless authentication.

4. Create unit tests in tests/test_user_auth.py
   Comprehensive test coverage for all authentication functions.

5. Update the CLI to integrate authentication
   Modify gerdsenai_cli/main.py to add login/logout commands.

6. Add configuration for auth settings
   Update gerdsenai_cli/config/settings.py with auth parameters.

The implementation will be modular, secure, and well-tested. Each component will be 
properly documented with docstrings and type hints.
"""
    
    # Extract summary
    plan = PlanCapture.extract_summary(sample_response)
    
    print("\n📊 Extracted Plan Information:\n")
    print(f"Complexity: {plan['complexity']}")
    print(f"\nFiles affected: {len(plan['files_affected'])}")
    for file in plan['files_affected']:
        print(f"  • {file}")
    
    print(f"\nActions detected: {len(plan['actions'])}")
    for action in plan['actions'][:3]:
        print(f"  • {action[:70]}...")
    
    print("\n" + "=" * 70)
    print("\n📋 Formatted Plan Preview:\n")
    print(PlanCapture.format_plan_preview(plan))
    print("\n" + "=" * 70)


async def demo_live_animation():
    """Show a live animation demo."""
    print("\n\n✨ Live Animation Demo\n")
    print("=" * 70)
    print("\nShowing 2 seconds of each animation type...\n")
    
    animations = [
        ("Thinking about your request", AnimationFrames.THINKING),
        ("Planning the implementation", AnimationFrames.PLANNING),
        ("Analyzing code structure", AnimationFrames.ANALYZING),
        ("Executing changes", AnimationFrames.EXECUTING),
        ("Processing data", AnimationFrames.SPINNER),
        ("Loading modules", AnimationFrames.DOTS),
    ]
    
    for message, frames in animations:
        print(f"\n{message}...")
        for _ in range(14):  # ~2 seconds at 150ms per frame
            for frame in frames:
                print(f"\r{frame} {message}", end="", flush=True)
                await asyncio.sleep(0.15)
        print()  # Newline after animation
    
    print("\n" + "=" * 70)
    print("\n✅ Animation demo complete!")


def main():
    """Run all demos."""
    print("\n" + "🎭" * 35)
    print("\n  GerdsenAI CLI - Animation System Demo")
    print("\n" + "🎭" * 35)
    
    # Demo 1: Show animation frames
    demo_animation_frames()
    
    # Demo 2: Show plan capture
    demo_plan_capture()
    
    # Demo 3: Show live animations
    print("\n\nPress Ctrl+C to skip live animation demo...")
    try:
        asyncio.run(demo_live_animation())
    except KeyboardInterrupt:
        print("\n\n⏭️  Skipped live animation demo")
    
    print("\n\n🎉 All demos complete!")
    print("\nTo test in the actual TUI:")
    print("  1. Run: python -m gerdsenai_cli")
    print("  2. Switch to ARCHITECT mode: /mode architect")
    print("  3. Make a request: 'Create a calculator module'")
    print("  4. Watch the animations and approval workflow!\n")


if __name__ == "__main__":
    main()
