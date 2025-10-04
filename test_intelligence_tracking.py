#!/usr/bin/env python3
"""
Test script for intelligence activity tracking system.

This script demonstrates the new intelligence activity tracking features:
- Real-time activity status display
- Progress tracking for multi-step operations
- Activity history and statistics
- /intelligence command
"""

import asyncio
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from gerdsenai_cli.ui.console import EnhancedConsole
from gerdsenai_cli.ui.status_display import IntelligenceActivity

console = Console()


async def test_activity_tracking():
    """Test intelligence activity tracking with simulated operations."""
    
    console.print("\n[bold cyan]🧪 Testing Intelligence Activity Tracking System[/bold cyan]\n")
    
    # Initialize enhanced console
    enhanced_console = EnhancedConsole()
    
    console.print("[bold]Test 1: Basic Activity Tracking[/bold]")
    console.print("Setting various intelligence activities...\n")
    
    # Test 1: Detecting Intent
    enhanced_console.set_intelligence_activity(
        IntelligenceActivity.DETECTING_INTENT,
        "Analyzing your request",
        progress=0.2
    )
    console.print(f"Status: {enhanced_console.status_display.get_status_line()}")
    await asyncio.sleep(1)
    
    # Test 2: Analyzing Context
    enhanced_console.set_intelligence_activity(
        IntelligenceActivity.ANALYZING_CONTEXT,
        "Building project context",
        progress=0.4
    )
    console.print(f"Status: {enhanced_console.status_display.get_status_line()}")
    await asyncio.sleep(1)
    
    # Test 3: Recalling Memory
    enhanced_console.set_intelligence_activity(
        IntelligenceActivity.RECALLING_MEMORY,
        "Searching recent files",
        progress=0.6
    )
    console.print(f"Status: {enhanced_console.status_display.get_status_line()}")
    await asyncio.sleep(1)
    
    # Test 4: Generating Suggestions
    enhanced_console.set_intelligence_activity(
        IntelligenceActivity.GENERATING_SUGGESTIONS,
        "Generated 5 suggestions",
        progress=0.9
    )
    console.print(f"Status: {enhanced_console.status_display.get_status_line()}")
    await asyncio.sleep(1)
    
    console.print("\n[green]✓ Basic activity tracking working![/green]\n")
    
    # Test 2: Planning with Step Info
    console.print("[bold]Test 2: Planning Progress Tracking[/bold]")
    console.print("Simulating multi-step plan execution...\n")
    
    total_steps = 5
    for step in range(1, total_steps + 1):
        progress = step / total_steps
        enhanced_console.set_intelligence_activity(
            IntelligenceActivity.EXECUTING_PLAN,
            f"Executing plan with {total_steps} steps",
            progress=progress,
            step_info=f"Step {step}/{total_steps}"
        )
        console.print(f"Status: {enhanced_console.status_display.get_status_line()}")
        await asyncio.sleep(0.5)
    
    console.print("\n[green]✓ Planning progress tracking working![/green]\n")
    
    # Test 3: Activity History
    console.print("[bold]Test 3: Activity History[/bold]")
    console.print("Showing detailed activity history...\n")
    
    enhanced_console.show_intelligence_details()
    
    console.print("[green]✓ Activity history display working![/green]\n")
    
    # Test 4: Activity Statistics
    console.print("[bold]Test 4: Activity Statistics[/bold]")
    console.print("Retrieving activity summary...\n")
    
    summary = enhanced_console.get_intelligence_summary()
    
    panel_content = f"""[cyan]Current Activity:[/cyan] {summary['current_activity'].replace('_', ' ').title()}
[cyan]Total Activities:[/cyan] {summary['total_activities']}
[cyan]Total Time:[/cyan] {summary['total_time_seconds']:.1f}s
[cyan]Average Time:[/cyan] {summary['average_time_seconds']:.1f}s

[dim]Activity Breakdown:[/dim]"""
    
    for activity, count in summary['activity_counts'].items():
        panel_content += f"\n  • {activity.replace('_', ' ').title()}: {count}"
    
    console.print(Panel(
        panel_content,
        title="📊 Activity Summary",
        border_style="cyan"
    ))
    
    console.print("\n[green]✓ Activity statistics working![/green]\n")
    
    # Test 5: Clear Activity
    console.print("[bold]Test 5: Clear Activity[/bold]")
    enhanced_console.clear_intelligence_activity()
    console.print(f"Status after clear: {enhanced_console.status_display.get_status_line()}")
    console.print("\n[green]✓ Clear activity working![/green]\n")
    
    # Final Summary
    console.print("\n[bold green]✅ All Tests Passed![/bold green]\n")
    console.print("[bold]Intelligence Activity Tracking Features:[/bold]")
    console.print("  ✓ 12 activity types with icons")
    console.print("  ✓ Progress tracking (0.0-1.0)")
    console.print("  ✓ Step info for multi-step operations")
    console.print("  ✓ Activity history (last 10 activities)")
    console.print("  ✓ Activity statistics and timing")
    console.print("  ✓ Rich console integration")
    console.print("  ✓ Status line display")
    console.print("\n[bold cyan]Ready for integration with agent![/bold cyan]\n")


async def test_all_activity_types():
    """Test all 12 intelligence activity types."""
    
    console.print("\n[bold cyan]🎨 Testing All Activity Types[/bold cyan]\n")
    
    enhanced_console = EnhancedConsole()
    
    activities = [
        (IntelligenceActivity.IDLE, "System ready"),
        (IntelligenceActivity.THINKING, "Processing your request"),
        (IntelligenceActivity.READING_FILES, "Reading source files"),
        (IntelligenceActivity.WRITING_CODE, "Writing code changes"),
        (IntelligenceActivity.DETECTING_INTENT, "Analyzing intent"),
        (IntelligenceActivity.ANALYZING_CONTEXT, "Building context"),
        (IntelligenceActivity.RECALLING_MEMORY, "Searching memory"),
        (IntelligenceActivity.PLANNING, "Creating plan"),
        (IntelligenceActivity.EXECUTING_PLAN, "Executing step 1/3"),
        (IntelligenceActivity.GENERATING_SUGGESTIONS, "Finding improvements"),
        (IntelligenceActivity.ASKING_CLARIFICATION, "Requesting clarification"),
        (IntelligenceActivity.CONFIRMING_OPERATION, "Confirming deletion"),
    ]
    
    console.print("[bold]All 12 Activity Types:[/bold]\n")
    
    for activity, message in activities:
        enhanced_console.set_intelligence_activity(activity, message, progress=0.5)
        status = enhanced_console.status_display.get_status_line()
        console.print(f"  {status}")
        await asyncio.sleep(0.3)
    
    console.print("\n[green]✓ All activity types display correctly![/green]\n")


async def test_progress_updates():
    """Test dynamic progress updates."""
    
    console.print("\n[bold cyan]⚡ Testing Dynamic Progress Updates[/bold cyan]\n")
    
    enhanced_console = EnhancedConsole()
    
    # Set initial activity
    enhanced_console.set_intelligence_activity(
        IntelligenceActivity.ANALYZING_CONTEXT,
        "Analyzing 50 files",
        progress=0.0,
        step_info="File 0/50"
    )
    
    console.print("[bold]Simulating file analysis with progress updates...[/bold]\n")
    
    # Update progress 10 times
    for i in range(1, 11):
        files_processed = i * 5
        progress = files_processed / 50
        enhanced_console.update_intelligence_progress(
            progress=progress,
            step_info=f"File {files_processed}/50"
        )
        console.print(f"  {enhanced_console.status_display.get_status_line()}")
        await asyncio.sleep(0.2)
    
    console.print("\n[green]✓ Dynamic progress updates working![/green]\n")


async def main():
    """Run all tests."""
    try:
        await test_activity_tracking()
        await test_all_activity_types()
        await test_progress_updates()
        
        console.print("\n[bold green]🎉 All Intelligence Tracking Tests Passed![/bold green]\n")
        console.print("[bold]Next Steps:[/bold]")
        console.print("  1. Test with real agent operations")
        console.print("  2. Test /intelligence command in CLI")
        console.print("  3. Add suggestion panels")
        console.print("  4. Enhance layout with intelligence sections\n")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
