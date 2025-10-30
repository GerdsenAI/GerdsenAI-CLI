#!/usr/bin/env python3
"""
Simple Phase 8c validation test (no pytest required)
"""

import asyncio
from pathlib import Path

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.context_manager import ProjectContext
from gerdsenai_cli.core.llm_client import LLMClient


def test_context_window_detection():
    """Test context window auto-detection for various models."""
    print("\n🧪 Testing context window detection...")
    
    settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
    client = LLMClient(settings=settings)
    
    tests = [
        ("gpt-4-turbo", 128000),
        ("gemini-pro", 1000000),
        ("claude-3-opus", 200000),
        ("llama3", 8192),
        ("unknown-model", 4096),
    ]
    
    for model_id, expected in tests:
        result = client.get_model_context_window(model_id)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {model_id}: {result} tokens (expected {expected})")
        assert result == expected, f"Failed: {model_id}"
    
    print("✅ Context window detection tests passed!")


def test_settings_validation():
    """Test Phase 8c settings validation."""
    print("\n🧪 Testing settings validation...")
    
    settings = Settings(
        llm_server_url="http://localhost:11434",
        current_model="test-model",
        context_window_usage=0.8,
        auto_read_strategy="smart",
        enable_file_summarization=True
    )
    
    assert settings.context_window_usage == 0.8
    assert settings.auto_read_strategy == "smart"
    assert settings.enable_file_summarization is True
    
    print("  ✅ context_window_usage: 0.8")
    print("  ✅ auto_read_strategy: smart")
    print("  ✅ enable_file_summarization: True")
    print("✅ Settings validation tests passed!")


def test_token_estimation():
    """Test token estimation."""
    print("\n🧪 Testing token estimation...")
    
    text = "a" * 400  # 400 chars = ~100 tokens
    estimated = ProjectContext._estimate_tokens(text)
    
    assert estimated == 100, f"Expected 100, got {estimated}"
    print(f"  ✅ 400 chars → {estimated} tokens (expected 100)")
    
    empty = ProjectContext._estimate_tokens("")
    assert empty == 0
    print(f"  ✅ Empty string → {empty} tokens (expected 0)")
    
    print("✅ Token estimation tests passed!")


async def test_dynamic_context():
    """Test dynamic context building."""
    print("\n🧪 Testing dynamic context building...")
    
    context_manager = ProjectContext(project_root=Path.cwd())
    await context_manager.scan_directory(max_depth=2)
    
    # Test smart strategy
    context = await context_manager.build_dynamic_context(
        query="test",
        max_tokens=1000,
        strategy="smart"
    )
    
    assert context is not None
    assert isinstance(context, str)
    assert len(context) > 0
    print(f"  ✅ Smart strategy: Generated {len(context)} chars")
    
    # Test off strategy
    empty_context = await context_manager.build_dynamic_context(
        query="test",
        max_tokens=1000,
        strategy="off"
    )
    
    assert empty_context == ""
    print("  ✅ Off strategy: Returns empty string")
    
    # Test file prioritization
    mentioned_files = [Path("README.md")]
    prioritized = context_manager._prioritize_files(
        query="readme",
        mentioned_files=mentioned_files
    )
    
    assert len(prioritized) > 0
    print(f"  ✅ File prioritization: {len(prioritized)} files sorted")
    
    # Test summarization
    long_content = "line\n" * 1000
    summarized = await context_manager._summarize_file(long_content, max_tokens=200)
    
    assert len(summarized) < len(long_content)
    assert "lines omitted" in summarized or "truncated" in summarized
    print(f"  ✅ Summarization: {len(long_content)} → {len(summarized)} chars")
    
    print("✅ Dynamic context tests passed!")


def test_component_presence():
    """Verify all Phase 8c components are present."""
    print("\n🧪 Testing component presence...")
    
    # LLMClient methods
    assert hasattr(LLMClient, "get_model_context_window")
    print("  ✅ LLMClient.get_model_context_window()")
    
    # Settings fields
    settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
    assert hasattr(settings, "model_context_window")
    assert hasattr(settings, "context_window_usage")
    assert hasattr(settings, "auto_read_strategy")
    assert hasattr(settings, "enable_file_summarization")
    assert hasattr(settings, "max_iterative_reads")
    print("  ✅ Settings: All Phase 8c fields present")
    
    # ProjectContext methods
    assert hasattr(ProjectContext, "build_dynamic_context")
    assert hasattr(ProjectContext, "_smart_context_building")
    assert hasattr(ProjectContext, "_prioritize_files")
    assert hasattr(ProjectContext, "_estimate_tokens")
    assert hasattr(ProjectContext, "_summarize_file")
    print("  ✅ ProjectContext: All Phase 8c methods present")
    
    print("✅ Component presence tests passed!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 8c Implementation Validation")
    print("=" * 60)
    
    try:
        # Sync tests
        test_component_presence()
        test_context_window_detection()
        test_settings_validation()
        test_token_estimation()
        
        # Async tests
        await test_dynamic_context()
        
        print("\n" + "=" * 60)
        print("🎉 All Phase 8c tests passed!")
        print("=" * 60)
        print("\n✅ Phase 8c core implementation verified")
        print("📊 Summary:")
        print("  - Context window auto-detection: ✅")
        print("  - Dynamic settings: ✅")
        print("  - Token estimation: ✅")
        print("  - Dynamic context building: ✅")
        print("  - File prioritization: ✅")
        print("  - Summarization: ✅")
        print("\n🚀 Ready for integration testing!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
