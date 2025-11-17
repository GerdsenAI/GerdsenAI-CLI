# TUI Integration Testing Scenarios

Comprehensive manual testing scenarios for the GerdsenAI TUI.

## Test Environment Setup

Before testing, ensure:
1. Local LLM provider is running (Ollama, LM Studio, vLLM, or HuggingFace TGI)
2. At least one model is loaded
3. Network connectivity is stable
4. Terminal supports ANSI colors and full-screen mode

---

## Scenario 1: Normal Operation Flow

**Objective**: Verify standard user workflow

### Steps:
1. Launch TUI: `python -m gerdsenai_cli tui`
2. Verify ASCII art displays correctly
3. Check mode indicator shows "CHAT" mode
4. Type a simple message: "Hello, how are you?"
5. Verify message appears in conversation
6. Verify AI response streams smoothly
7. Check auto-scroll keeps latest message visible
8. Send follow-up message: "Tell me about local LLMs"
9. Verify conversation history is maintained

### Expected Results:
- ✅ Clean startup with ASCII art
- ✅ Messages display with timestamps
- ✅ Streaming is smooth (no jitter)
- ✅ Auto-scroll works correctly
- ✅ Conversation context is maintained

---

## Scenario 2: Mode Switching

**Objective**: Test all execution modes

### Steps:
1. Launch TUI in CHAT mode
2. Type `/mode` to see current mode
3. Press `Shift+Tab` to cycle to ARCHITECT mode
   - Verify header/border colors change to yellow/orange
   - Verify status bar shows "ARCHITECT"
4. Press `Shift+Tab` to cycle to EXECUTE mode
   - Verify colors change to green
   - Verify status bar shows "EXECUTE"
5. Press `Shift+Tab` to cycle to LLVL mode
   - Verify colors change to magenta
   - Verify warning message appears
6. Press `Shift+Tab` to cycle back to CHAT
7. Use `/mode architect` command
8. Use `/mode llvl` command

### Expected Results:
- ✅ All 4 modes accessible
- ✅ Visual feedback for each mode (colors)
- ✅ Status bar updates correctly
- ✅ LLVL mode shows appropriate warning
- ✅ Command-based mode switching works

---

## Scenario 3: Edge Case - Large Messages

**Objective**: Test handling of very large user inputs

### Steps:
1. Launch TUI
2. Paste a 5KB message (copy from a text file)
   - Should process normally
3. Paste a 60KB message
   - Should show warning about large message
   - Should still process
4. Try to paste a 150KB message
   - Should reject with error (exceeds MAX_MESSAGE_LENGTH)

### Expected Results:
- ✅ Small to medium messages handled
- ✅ Large message warning appears (>50KB)
- ✅ Excessive messages rejected gracefully
- ✅ Error message is clear and helpful

---

## Scenario 4: Edge Case - Rapid-Fire Messages

**Objective**: Test protection against message spam

### Steps:
1. Launch TUI
2. Type and send: "Test 1"
3. Immediately type and send: "Test 2"
4. Immediately type and send: "Test 3"
5. Verify only the first message is processed
6. Check for warning about waiting

### Expected Results:
- ✅ Only first message processed
- ✅ Warning appears for rapid messages
- ✅ No crashes or errors
- ✅ Can send after brief delay

---

## Scenario 5: Edge Case - Invalid Input

**Objective**: Test input validation

### Steps:
1. Launch TUI
2. Try to send empty message (just press Enter)
   - Should clear input, no error
3. Try to send whitespace only: "   \n\t   "
   - Should show error about empty message
4. Try to send message with dangerous pattern: `test; rm -rf /`
   - Should reject with security warning
5. Try to send message with null bytes (if possible)
   - Should reject with invalid characters error

### Expected Results:
- ✅ Empty messages ignored gracefully
- ✅ Dangerous patterns rejected
- ✅ Security errors are clear
- ✅ User can continue after rejection

---

## Scenario 6: Edge Case - Network Interruption

**Objective**: Test recovery from network issues

### Steps:
1. Launch TUI with provider running
2. Send a message and wait for streaming to start
3. Stop the LLM provider (kill process or disconnect network)
4. Observe error handling
5. Restart provider
6. Send new message
7. Verify recovery

### Expected Results:
- ✅ Stream interruption detected
- ✅ Partial response displayed
- ✅ Clear error message with recovery steps
- ✅ Can resume after provider restart
- ✅ No TUI crash or hang

---

## Scenario 7: Edge Case - Provider Failure

**Objective**: Test handling of provider errors

### Steps:
1. Launch TUI with provider stopped
2. Send a message
3. Observe error handling
4. Send 2 more messages (3 consecutive failures)
5. Check for enhanced recovery help
6. Start provider
7. Send message to verify recovery

### Expected Results:
- ✅ Initial failure shows error
- ✅ After 3 failures, shows detailed recovery help
- ✅ Suggests troubleshooting steps
- ✅ Successfully recovers when provider available

---

## Scenario 8: Edge Case - Stream Timeout

**Objective**: Test handling of very slow responses

### Steps:
1. Launch TUI
2. Send a message that triggers a very long response
3. If provider supports it, configure extra slow inference
4. Observe streaming behavior
5. Verify timeout handling (if response takes >120s)

### Expected Results:
- ✅ Slow streaming handled gracefully
- ✅ Timeout occurs if exceeds limit
- ✅ Partial response displayed
- ✅ Clear timeout message
- ✅ User can retry

---

## Scenario 9: Command Execution

**Objective**: Test all slash commands

### Steps:
1. `/help` - Verify help displays
2. `/shortcuts` - Verify keyboard shortcuts display
3. `/mode` - Verify mode info displays
4. `/mode architect` - Verify mode switches
5. `/thinking` - Toggle thinking mode on
6. `/thinking` - Toggle thinking mode off
7. `/speed` - Show current speed
8. `/speed slow` - Set slow streaming
9. `/speed instant` - Set instant streaming
10. `/debug` - Toggle debug mode
11. `/clear` - Clear conversation
12. `/copy` - Copy conversation (if pbcopy/pyperclip available)
13. `/exit` - Exit TUI

### Expected Results:
- ✅ All commands execute without errors
- ✅ Command responses are formatted well
- ✅ State changes persist (mode, thinking, speed)
- ✅ /clear works without issues
- ✅ /exit cleanly terminates

---

## Scenario 10: Keyboard Shortcuts

**Objective**: Test all keyboard bindings

### Steps:
1. Launch TUI with some conversation
2. Press `Page Up` - Scroll up
   - Verify auto-scroll disabled
   - Verify "[SCROLLED UP ↑]" indicator appears
3. Press `Page Down` - Scroll down
   - Verify scroll works
   - Verify auto-scroll re-enables at bottom
4. Press `Shift+Tab` multiple times - Cycle modes
5. Press `Ctrl+Y` - Copy conversation
   - Verify success message
6. Type a message, press `Escape` - Clear input
   - Verify input cleared
7. Type multi-line with `Shift+Enter`
   - Verify newlines work
   - Press `Enter` to send
8. Press `Ctrl+C` - Exit
   - Verify clean exit

### Expected Results:
- ✅ All keyboard shortcuts functional
- ✅ Scrolling works smoothly
- ✅ Scroll indicator accurate
- ✅ Multi-line input works
- ✅ Clean exit with Ctrl+C

---

## Scenario 11: Memory Management

**Objective**: Test conversation archiving

### Steps:
1. Launch TUI
2. Send 85+ messages to trigger archive threshold
   - Can use a script to automate this
3. Verify archive notice appears
4. Verify only recent 100 messages kept
5. Continue sending messages
6. Verify TUI remains responsive

### Expected Results:
- ✅ Archive triggers at threshold
- ✅ Archive notice clear and informative
- ✅ Recent messages preserved
- ✅ No memory issues or slowdown
- ✅ TUI remains responsive

---

## Scenario 12: SmartRouter Integration

**Objective**: Test natural language intent detection

### Steps:
1. Ensure `enable_smart_routing: true` in settings
2. Launch TUI
3. Type natural command: "show me all available models"
   - Should detect list_models intent
   - Should show intent detection message
4. Type: "create a new python file called test.py"
   - Should detect create_file intent
5. Type ambiguous input: "maybe do something"
   - Should request clarification
6. Type normal chat: "how are you today?"
   - Should pass through to chat

### Expected Results:
- ✅ Intent detection works
- ✅ Visual feedback for detected intents
- ✅ Clarification requests when uncertain
- ✅ Normal chat still works
- ✅ Falls back gracefully if SmartRouter fails

---

## Scenario 13: Proactive Context Building

**Objective**: Test automatic file reading

### Steps:
1. Ensure `enable_proactive_context: true` in settings
2. Launch TUI in project directory
3. Type: "What's in main.py?"
   - Should automatically read main.py
   - Should include file contents in context
4. Type: "Compare utils/validation.py and utils/retry.py"
   - Should read both files proactively
5. Type: "Fix the import error in config.py"
   - Should read config.py and related imports

### Expected Results:
- ✅ Files automatically read when mentioned
- ✅ No need to manually specify files
- ✅ Multiple files handled
- ✅ Related files (imports) detected
- ✅ Context stays within token budget

---

## Scenario 14: Provider Auto-Detection

**Objective**: Test automatic provider discovery

### Steps:
1. Stop all LLM providers
2. Launch TUI
3. Observe auto-detection attempting to find providers
4. Start Ollama on port 11434
5. Send message - should detect and use Ollama
6. Stop Ollama, start LM Studio on 1234
7. Send message - should detect and switch to LM Studio

### Expected Results:
- ✅ Auto-detection scans common ports
- ✅ Detects Ollama when available
- ✅ Detects LM Studio when available
- ✅ Clear messages about detection
- ✅ Graceful fallback if none found

---

## Scenario 15: Error Display Enhancement

**Objective**: Test enhanced error formatting

### Steps:
1. Trigger various error types:
   - Network error (disconnect network)
   - Timeout error (very slow response)
   - Model not found (request non-existent model)
   - Context length error (send huge message)
   - Auth error (if applicable)
2. Observe error displays for each

### Expected Results:
- ✅ Each error has appropriate icon
- ✅ Error category clearly indicated
- ✅ Helpful suggestions provided
- ✅ Recovery actions listed
- ✅ Formatting is readable and clear

---

## Scenario 16: Thinking Mode

**Objective**: Test AI thinking display

### Steps:
1. Launch TUI
2. Enable thinking mode: `/thinking`
3. Send complex request: "Explain how quantum computing works"
4. Observe thinking display (if model supports it)
5. Disable thinking mode: `/thinking`
6. Send same request
7. Compare displays

### Expected Results:
- ✅ Thinking mode toggles correctly
- ✅ Reasoning process displayed when enabled
- ✅ Only final response when disabled
- ✅ Warning shown if model doesn't support thinking
- ✅ Toggle persists across messages

---

## Scenario 17: Streaming Speed Adjustment

**Objective**: Test streaming speed settings

### Steps:
1. Launch TUI
2. Set slow speed: `/speed slow`
3. Send message - observe typewriter effect
4. Set medium speed: `/speed medium`
5. Send message - observe smooth streaming
6. Set fast speed: `/speed fast`
7. Send message - observe quick streaming
8. Set instant speed: `/speed instant`
9. Send message - observe immediate display

### Expected Results:
- ✅ All speeds work as expected
- ✅ Slow shows visible typewriter effect
- ✅ Instant shows complete response immediately
- ✅ No dropped characters at any speed
- ✅ Speed persists across messages

---

## Scenario 18: Conversation Export

**Objective**: Test conversation export functionality

### Steps:
1. Launch TUI and have a conversation (5+ messages)
2. Export: `/export`
   - Should auto-generate filename
3. Verify file created with markdown content
4. Export with custom name: `/export my-conversation`
5. Verify custom filename used
6. Check exported markdown format

### Expected Results:
- ✅ Export creates markdown file
- ✅ All messages included
- ✅ Timestamps preserved
- ✅ Formatting is clean
- ✅ Custom filenames work

---

## Scenario 19: Concurrent Protection

**Objective**: Test protection against concurrent operations

### Steps:
1. Launch TUI
2. Send long message that will stream for 10+ seconds
3. While streaming, try to send another message
4. Verify second message is blocked
5. Wait for stream to complete
6. Send new message - should work

### Expected Results:
- ✅ Cannot send while streaming
- ✅ Clear message explaining why blocked
- ✅ No crashes or errors
- ✅ Can send after stream completes
- ✅ Input buffer preserved

---

## Scenario 20: Visual Regression Check

**Objective**: Verify all visual elements display correctly

### Checklist:
- [ ] ASCII art displays correctly at startup
- [ ] Header shows correct text and colors
- [ ] Mode colors change correctly (blue, yellow, green, magenta)
- [ ] Message borders display with proper characters
- [ ] Timestamps show in correct format
- [ ] Scrollbar appears when content exceeds window
- [ ] Cursor visible in input field
- [ ] Streaming cursor animates during response
- [ ] Info bar shows token count and context usage
- [ ] Status bar shows mode, thinking status, message count
- [ ] Markdown rendering works (bold, italic, code blocks)
- [ ] Code syntax highlighting works (if supported)
- [ ] No text overflow or wrapping issues
- [ ] No flickering or visual artifacts

---

## Performance Benchmarks

### Response Time Targets:
- Command execution: < 100ms
- Mode switch: < 50ms
- Scroll operation: < 30ms (60fps)
- Message send: < 200ms (to first chunk)
- Clear conversation: < 50ms

### Resource Usage Targets:
- Memory: < 500MB for 1000 messages
- CPU: < 5% when idle
- CPU: < 30% during streaming

### Stress Tests:
1. **1000 Message Conversation**: Send 1000 messages, verify no slowdown
2. **100KB Message**: Send very large message, verify handling
3. **Rapid Mode Switching**: Switch modes 100 times, verify no issues
4. **Extended Session**: Run for 8+ hours, verify stability

---

## Known Issues / Expected Behaviors

### Not Bugs:
- Rich markdown may not render on all terminals → Falls back to plain text
- Clipboard copy requires pbcopy (macOS) or pyperclip → Shows helpful error
- Some models don't support thinking mode → Warning displayed
- Provider detection may take 5-10s on first launch → Normal

### Platform-Specific:
- **macOS**: All features should work
- **Linux**: Clipboard may require xclip/xsel installation
- **Windows**: Clipboard may require pyperclip
- **tmux/screen**: May need TERM=xterm-256color

---

## Reporting Issues

When reporting TUI issues, include:
1. Operating system and terminal emulator
2. Python version
3. LLM provider and version
4. Steps to reproduce
5. Expected vs actual behavior
6. Screenshots if visual issue
7. Relevant logs from ~/.gerdsenai/logs/tui.log

---

## Success Criteria

TUI is considered **production-ready** when:
- ✅ All 20 scenarios pass
- ✅ No crashes or hangs in any scenario
- ✅ All edge cases handled gracefully
- ✅ Error messages are clear and helpful
- ✅ Performance meets benchmarks
- ✅ Visual regression check passes
- ✅ Stress tests complete successfully
- ✅ User can recover from all error states
