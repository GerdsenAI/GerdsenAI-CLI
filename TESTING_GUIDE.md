# 🧪 Manual Testing Guide - Animation System & Approval Workflow

## ✅ Current Status
The TUI is **running and ready** for testing! All code has been implemented:
- ✅ Animation system created
- ✅ Plan capture implemented
- ✅ Approval workflow integrated
- ✅ Mode-aware message handling complete

## 🎯 Test Scenarios

### Test 1: ARCHITECT Mode - Plan with Approval

**Steps:**
1. In the TUI, type: `/mode architect`
2. Press Enter
3. Type a request: `Create a simple calculator module with add, subtract, multiply, and divide functions`
4. Press Enter

**Expected Behavior:**
- 🤔 Animation: "Analyzing your request" (thinking emoji animation)
- 📋 Animation: "Creating execution plan" (planning emoji animation)
- 📋 **Plan Summary** appears with:
  - Summary of what will be done
  - Files to be modified
  - Actions to take
  - Complexity estimate
  - Approval prompt: "Do you want to proceed?"

**Test Approval - YES:**
5. Type: `yes`
6. Press Enter

**Expected Behavior:**
- ✅ Message: "Plan approved! Switching to EXECUTE mode..."
- ⚡ Animation: "Executing plan" (execution emoji animation)
- Response streams with typewriter effect
- ✅ Message: "Execution complete!"
- Returns to ARCHITECT mode

### Test 2: Approval - Show Full Details

**Steps:**
1. In ARCHITECT mode, make another request
2. When the approval prompt appears, type: `show full`
3. Press Enter

**Expected Behavior:**
- Full AI response displays (the verbose plan you originally didn't see)
- Approval prompt reappears: "Approve? (yes/no)"

### Test 3: Approval - Cancel

**Steps:**
1. In ARCHITECT mode, make another request
2. When the approval prompt appears, type: `no`
3. Press Enter

**Expected Behavior:**
- ❌ Message: "Plan cancelled."
- Returns to ARCHITECT mode ready for next input
- No execution happens

### Test 4: EXECUTE Mode - Direct Execution

**Steps:**
1. Type: `/mode execute`
2. Press Enter
3. Type: `Add a comment to the animations.py file explaining its purpose`
4. Press Enter

**Expected Behavior:**
- ⚡ Brief animation: "Executing" (0.3 seconds)
- Response streams immediately with typewriter effect
- **NO approval prompt** (executes directly)

### Test 5: CHAT Mode - Action Detection

**Steps:**
1. Type: `/mode chat`
2. Press Enter
3. Type: `Create a new file called test.py`
4. Press Enter

**Expected Behavior:**
- 💡 System message suggests switching to ARCHITECT or EXECUTE mode
- Explains that CHAT mode is read-only
- No file creation occurs

### Test 6: Mode Cycling with Shift+Tab

**Steps:**
1. Press `Shift+Tab` (hold Shift, press Tab)
2. Observe status bar change
3. Press `Shift+Tab` again
4. Repeat to cycle through: CHAT → ARCHITECT → EXECUTE → LLVL → CHAT

**Expected Behavior:**
- Status bar updates: `[CHAT]`, `[ARCHITECT]`, `[EXECUTE]`, `[LLVL]`
- Each press cycles to next mode

### Test 7: Streaming Speed Control

**Steps:**
1. In EXECUTE mode, type: `/speed slow`
2. Press Enter
3. Make a request
4. Observe slow typewriter effect

**Try other speeds:**
- `/speed medium` - default smooth (10ms)
- `/speed fast` - quick (5ms)
- `/speed instant` - immediate (0ms)

**Expected Behavior:**
- Each speed changes the streaming animation rate
- Status bar shows current speed setting

## 📊 Verification Checklist

After testing, verify:
- [ ] Animations display during AI thinking/planning
- [ ] Plan summaries show instead of verbose output in ARCHITECT mode
- [ ] Files and actions are extracted correctly in summaries
- [ ] Approval workflow responds to yes/no/show full
- [ ] Auto-switch to EXECUTE mode works on approval
- [ ] Execution displays with streaming after approval
- [ ] Mode restoration happens after execution
- [ ] CHAT mode blocks action requests
- [ ] No crashes or errors during any scenario
- [ ] Status bar updates correctly

## 🐛 Troubleshooting

### If animations don't appear:
- Check that you're in ARCHITECT mode
- Verify the status bar shows `[ARCHITECT]`

### If plan summary doesn't show:
- The AI response might not contain file/action patterns
- Try a more specific request like "Create a new module file"

### If approval prompt doesn't appear:
- Make sure you're in ARCHITECT mode, not EXECUTE
- EXECUTE mode bypasses approval intentionally

### If mode doesn't switch:
- Use `/mode` to check current mode
- Use `/mode <modename>` to force switch
- Try `Shift+Tab` to cycle modes

## 📝 What to Look For

### Good Signs ✅
- Smooth animations during thinking/planning
- Clean, readable plan summaries
- Clear approval prompts
- Seamless mode transitions
- Typewriter streaming effect

### Issues to Report 🐛
- Animations freeze or don't start
- Full verbose output appears instead of summary
- Approval prompt doesn't accept yes/no
- Mode doesn't switch after approval
- Errors or crashes

## 🎉 Success Criteria

The implementation is successful if:
1. **ARCHITECT mode** shows animations → summary → approval
2. **Approval** works for yes/no/show full responses
3. **Execution** happens after approval with auto-mode-switch
4. **EXECUTE mode** runs directly without approval
5. **CHAT mode** blocks actions appropriately
6. **No verbose dumps** in ARCHITECT mode

## 💡 Tips

- Use **ARCHITECT mode** when you want to review before executing
- Use **EXECUTE mode** when you trust the AI and want speed
- Use **CHAT mode** for questions and information only
- Use `/speed slow` to see the typewriter effect more clearly
- Press `Ctrl+C` to exit the TUI when done testing

---

## 🚀 Ready to Test!

The TUI is currently running in your terminal. Follow the test scenarios above and observe the behavior. All the code is implemented and ready!
