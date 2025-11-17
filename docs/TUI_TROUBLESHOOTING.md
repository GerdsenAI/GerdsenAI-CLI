# TUI Troubleshooting Guide

Quick reference for diagnosing and fixing common TUI issues.

## 🚨 Quick Diagnostics

If the TUI isn't working correctly, run these checks:

```bash
# 1. Check Python version (need 3.10+)
python --version

# 2. Check if dependencies are installed
python -c "import rich; print('✅ Rich installed')"
python -c "import prompt_toolkit; print('✅ Prompt Toolkit installed')"

# 3. Check LLM provider is running
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:1234/v1/models  # LM Studio

# 4. Check logs for errors
tail -f ~/.gerdsenai/logs/tui.log
```

---

## Common Issues

### Issue: TUI won't start

**Symptoms**: Import errors, crashes on startup

**Solutions**:
1. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Check Python version:
   ```bash
   python --version  # Must be 3.10+
   ```

3. Try direct import test:
   ```bash
   python -c "from gerdsenai_cli.ui.prompt_toolkit_tui import PromptToolkitTUI"
   ```

4. Check for conflicting installations:
   ```bash
   pip list | grep gerdsenai
   ```

---

### Issue: No response from AI

**Symptoms**: Messages sent but no response appears

**Solutions**:
1. Check provider is running:
   ```bash
   # Ollama
   ollama list

   # LM Studio
   curl http://localhost:1234/v1/models
   ```

2. Check model is loaded:
   ```bash
   # In TUI
   /model

   # Or check directly
   curl http://localhost:11434/api/tags | jq
   ```

3. Verify network connectivity:
   ```bash
   ping localhost
   telnet localhost 11434
   ```

4. Check logs for errors:
   ```bash
   tail -f ~/.gerdsenai/logs/tui.log
   ```

5. Enable debug mode:
   ```bash
   # In TUI
   /debug
   ```

---

### Issue: Streaming is slow or choppy

**Symptoms**: Text appears slowly, laggy display

**Solutions**:
1. Adjust streaming speed:
   ```bash
   # In TUI
   /speed fast
   # Or
   /speed instant
   ```

2. Check CPU/GPU usage:
   ```bash
   top  # Check if provider is maxing CPU
   nvidia-smi  # Check GPU usage if applicable
   ```

3. Reduce model size if running locally:
   - Switch to smaller quantization (Q4 vs Q8)
   - Use smaller model variant

4. Check network latency (if remote provider):
   ```bash
   ping <provider-host>
   ```

---

### Issue: Display looks corrupted

**Symptoms**: Strange characters, broken borders, wrong colors

**Solutions**:
1. Check terminal supports 256 colors:
   ```bash
   echo $TERM
   # Should be: xterm-256color or similar
   ```

2. Set TERM variable:
   ```bash
   export TERM=xterm-256color
   python -m gerdsenai_cli tui
   ```

3. Try different terminal emulator:
   - macOS: iTerm2, Terminal.app
   - Linux: gnome-terminal, konsole, alacritty
   - Windows: Windows Terminal, ConEmu

4. Disable Rich formatting (fallback mode):
   ```bash
   # Edit code to set RICH_AVAILABLE = False
   # Or uninstall rich temporarily
   pip uninstall rich
   ```

---

### Issue: Cannot scroll conversation

**Symptoms**: Page Up/Down don't work, stuck at position

**Solutions**:
1. Check terminal supports key bindings:
   - Try clicking in conversation area first
   - Use mouse wheel as alternative

2. Verify no key conflict:
   - Try in different terminal
   - Check terminal key binding settings

3. Use alternative navigation:
   - Mouse wheel scrolling
   - Click and drag scrollbar

4. Restart TUI if state is corrupted:
   ```bash
   # Press Ctrl+C and restart
   ```

---

### Issue: Messages rejected with "dangerous pattern"

**Symptoms**: Security error when sending certain messages

**Solutions**:
1. This is intentional security validation
2. Remove shell commands from message:
   - Remove: `; rm -rf`, `&& rm`, `| sh`
   - Remove: command substitution `$(...)`, backticks

3. If you need to discuss these patterns:
   - Add spaces: `r m -rf` instead of `rm -rf`
   - Use code blocks to escape them
   - Disable validation (advanced):
     ```python
     # In validation.py - not recommended
     DANGEROUS_PATTERNS = []
     ```

---

### Issue: "Circuit breaker is OPEN" error

**Symptoms**: Provider refuses connections after failures

**Solutions**:
1. This protects against repeatedly hitting dead provider
2. Wait 60 seconds for circuit to reset
3. Fix underlying issue:
   - Restart provider
   - Check provider logs
   - Verify network connectivity

4. Force reset by restarting TUI

---

### Issue: Memory usage grows over time

**Symptoms**: TUI becomes slow after many messages

**Solutions**:
1. This should auto-archive at 800+ messages
2. Manually clear if needed:
   ```bash
   # In TUI
   /clear
   ```

3. Export and restart:
   ```bash
   /export my-conversation
   /exit
   # Then restart TUI
   ```

4. Check archive is working:
   - Should see "📦 X messages archived" notice
   - Check logs for archive events

---

### Issue: Cannot copy conversation to clipboard

**Symptoms**: /copy or Ctrl+Y fails

**Solutions**:
1. **macOS**: Install pbcopy (usually pre-installed)
   ```bash
   which pbcopy
   ```

2. **Linux**: Install xclip or xsel
   ```bash
   sudo apt-get install xclip
   # Or
   sudo apt-get install xsel
   ```

3. **Windows/All platforms**: Install pyperclip
   ```bash
   pip install pyperclip
   ```

4. Alternative: Manual export
   ```bash
   # In TUI
   /export my-conversation
   # Then open file manually
   ```

---

### Issue: Auto-scroll not working

**Symptoms**: New messages appear off-screen

**Solutions**:
1. Check if you manually scrolled up:
   - Look for "[SCROLLED UP ↑]" indicator
   - Scroll to bottom with Page Down

2. Re-enable auto-scroll:
   - Send a new message
   - Or scroll to very bottom

3. Restart TUI if stuck:
   ```bash
   # Ctrl+C and restart
   ```

---

### Issue: Mode colors not changing

**Symptoms**: All modes look the same

**Solutions**:
1. Verify terminal supports colors:
   ```bash
   tput colors  # Should show 256
   ```

2. Check TERM variable:
   ```bash
   echo $TERM
   export TERM=xterm-256color
   ```

3. Try in different terminal emulator

4. Check logs for style errors:
   ```bash
   grep -i "style\|color" ~/.gerdsenai/logs/tui.log
   ```

---

### Issue: Keyboard shortcuts not working

**Symptoms**: Shift+Tab, Ctrl+Y, etc. don't work

**Solutions**:
1. Check terminal captures key combo:
   - Some terminals intercept certain keys
   - Check terminal preferences/settings

2. Try alternative methods:
   - Use `/mode <mode>` instead of Shift+Tab
   - Use `/copy` instead of Ctrl+Y

3. Verify no conflicting bindings:
   - Check terminal key binding settings
   - Try in different terminal

4. Use mouse alternatives where possible

---

### Issue: Thinking mode shows no reasoning

**Symptoms**: /thinking enabled but no thought process shown

**Solutions**:
1. Check model supports structured thinking:
   - Claude models: ✅ Support
   - GPT models: ✅ Support
   - Most local models: ❌ Don't support

2. Look for warning message:
   - "This model does not support structured thinking"

3. This is expected for most local models:
   - Feature requires specific model architecture
   - Local models typically output direct responses

---

### Issue: SmartRouter not detecting intents

**Symptoms**: Natural language commands not recognized

**Solutions**:
1. Check if enabled in settings:
   ```python
   # config/settings.py
   enable_smart_routing = True
   ```

2. Check LLM has capacity for intent detection:
   - Requires working chat completions
   - May fail if model is overloaded

3. Use explicit slash commands as fallback:
   - `/model` instead of "show me models"
   - `/mode architect` instead of "switch to architect"

4. Check logs for routing errors:
   ```bash
   grep -i "smartrouter\|routing" ~/.gerdsenai/logs/tui.log
   ```

---

### Issue: Proactive context not reading files

**Symptoms**: Files mentioned in chat not automatically loaded

**Solutions**:
1. Check if enabled:
   ```python
   # config/settings.py
   enable_proactive_context = True
   ```

2. Verify file paths are clear:
   - ✅ "What's in utils/validation.py?"
   - ❌ "Check the validation file"

3. Check token budget:
   - May skip files if context full
   - Clear conversation and retry

4. Check file exists and readable:
   ```bash
   ls -la utils/validation.py
   cat utils/validation.py  # Test readability
   ```

---

## Performance Issues

### TUI feels sluggish

**Checklist**:
- [ ] Check CPU usage: `top`
- [ ] Check memory: `free -h`
- [ ] Clear conversation: `/clear`
- [ ] Reduce streaming speed: `/speed instant`
- [ ] Close other applications
- [ ] Restart provider and TUI
- [ ] Check for background processes

### Provider is slow

**Checklist**:
- [ ] Check provider logs for errors
- [ ] Verify GPU is being used (if applicable)
- [ ] Try smaller model
- [ ] Try lower quantization (Q4 vs Q8)
- [ ] Check system resources aren't maxed
- [ ] Restart provider service

---

## Advanced Debugging

### Enable verbose logging

```bash
# In TUI
/debug

# Check logs in real-time
tail -f ~/.gerdsenai/logs/tui.log

# Search for specific errors
grep -i "error\|exception" ~/.gerdsenai/logs/tui.log
```

### Test provider directly

```bash
# Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Hello, world!"
}'

# LM Studio / OpenAI-compatible
curl http://localhost:1234/v1/chat/completions -d '{
  "model": "local-model",
  "messages": [{"role": "user", "content": "Hello"}]
}'
```

### Check network connectivity

```bash
# Test local ports
netstat -an | grep LISTEN | grep 11434  # Ollama
netstat -an | grep LISTEN | grep 1234   # LM Studio

# Test HTTP connectivity
curl -v http://localhost:11434/api/tags
curl -v http://localhost:1234/v1/models
```

### Validate configuration

```python
# Test imports
python -c "from gerdsenai_cli.core.providers.detector import ProviderDetector; print('✅')"

# Test provider detection
python -c "
import asyncio
from gerdsenai_cli.core.providers.detector import ProviderDetector

async def test():
    detector = ProviderDetector()
    providers = await detector.scan_common_ports()
    print(f'Found {len(providers)} providers')
    for url, provider in providers:
        print(f'  - {provider.provider_type.value} at {url}')

asyncio.run(test())
"
```

---

## Getting Help

If none of these solutions work:

1. **Check logs** for detailed error information:
   ```bash
   cat ~/.gerdsenai/logs/tui.log
   ```

2. **Create minimal reproduction**:
   - Start fresh TUI
   - Document exact steps
   - Note all error messages

3. **Gather system info**:
   ```bash
   python --version
   pip list | grep gerdsenai
   echo $TERM
   uname -a
   ```

4. **Report issue** with:
   - Operating system and terminal
   - Python version
   - Provider type and version
   - Steps to reproduce
   - Error messages and logs
   - Screenshots if visual issue

5. **GitHub Issues**:
   - https://github.com/GerdsenAI/GerdsenAI-CLI/issues
   - Include all info from step 3 and 4

---

## Emergency Recovery

### TUI completely broken

```bash
# 1. Kill any running instances
pkill -f "gerdsenai_cli tui"

# 2. Clear cache (if exists)
rm -rf ~/.gerdsenai/cache/*

# 3. Reset configuration (backup first!)
cp ~/.gerdsenai/config.yaml ~/.gerdsenai/config.yaml.backup
# Then edit or delete config.yaml

# 4. Reinstall package
pip uninstall gerdsenai-cli
pip install -e .

# 5. Test basic functionality
python -c "from gerdsenai_cli import __version__; print(__version__)"

# 6. Try minimal launch
python -m gerdsenai_cli --help
```

### Provider unresponsive

```bash
# Ollama
ollama ps  # Check running
ollama stop --all  # Stop all
ollama serve  # Restart server
ollama run llama2  # Load model

# LM Studio
# Restart application from GUI
# Reload model from model list

# vLLM
# Kill process and restart with proper config
pkill -f vllm
python -m vllm.entrypoints.openai.api_server \
  --model <model-path> \
  --port 8000
```

---

## Prevention Tips

### Best Practices:
1. ✅ Keep provider running before starting TUI
2. ✅ Use `/save` or `/export` regularly
3. ✅ Enable debug mode when troubleshooting
4. ✅ Update dependencies regularly
5. ✅ Monitor system resources
6. ✅ Use version control for configuration
7. ✅ Read logs when issues occur
8. ✅ Test in clean environment first

### Avoid:
1. ❌ Sending huge messages (>100KB)
2. ❌ Rapid-fire message spam
3. ❌ Running on underpowered systems
4. ❌ Using unsupported terminals
5. ❌ Modifying core files without backups
6. ❌ Ignoring warning messages
7. ❌ Running multiple TUI instances
8. ❌ Killing processes abruptly (use Ctrl+C)
