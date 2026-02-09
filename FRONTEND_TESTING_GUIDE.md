# Frontend Testing Guide

## 🧪 Manual Testing Instructions

**Prerequisites:**

- ✅ Backend running on http://localhost:8000
- ✅ Frontend running on http://localhost:5173
- ✅ Modern browser (Chrome, Firefox, Edge)

---

## Test 1: Welcome Page

### Steps:

1. Open browser and navigate to: **http://localhost:5173**
2. Verify page loads without errors

### Expected Results:

✅ Page title: "ML Variation Evaluation System"  
✅ Hero section with "Professional FIDIC-Compliant Variation Assessment"  
✅ "Start New Evaluation" button (blue)  
✅ "My Sessions" button in header  
✅ 4 feature cards visible:

- Multi-File Upload (blue icon)
- FIDIC Workflow (green icon)
- CPM Analysis (amber icon)
- QS Validation (green icon)  
  ✅ FIDIC types section showing 6 variation types  
  ✅ Footer with version info

### Actions to Test:

- [ ] Click "Start New Evaluation" → Should navigate to `/upload`
- [ ] Click "My Sessions" → Should navigate to `/sessions`

---

## Test 2: Upload Page

### Steps:

1. From Welcome page, click "Start New Evaluation"
2. Should navigate to: **http://localhost:5173/upload**

### Expected Results:

✅ Page title: "File Upload"  
✅ Progress bar showing "Step 1 of 4"  
✅ Step 1: Upload BOQ section visible  
✅ Drag-and-drop zone for BOQ file  
✅ "Previous" and "Next Step" buttons

### Test Sequence:

#### Step 1: BOQ Upload

1. Click "Next Step" without uploading → Should move to Step 2
2. Go back to Step 1
3. **Drag and drop** a CSV file OR click to browse
4. File: Use `test_data/sample_boq.csv`
5. Verify file appears with green checkmark
6. Verify file name and size displayed
7. Click "Remove" → File should be removed
8. Re-upload the file
9. Click "Next Step"

#### Step 2: Rate Breakdown Upload

1. Progress bar should show "Step 2 of 4"
2. Upload `test_data/sample_rate_breakdown.csv`
3. Verify file appears with green checkmark
4. Click "Next Step"

#### Step 3: Schedule Upload

1. Progress bar should show "Step 3 of 4"
2. Upload `test_data/sample_schedule.csv`
3. Verify file appears with green checkmark
4. Click "Upload Files" button

#### Step 4: Upload Results

1. Progress bar should show "Step 4 of 4"
2. Watch for upload progress indicator (0-100%)
3. Verify success message appears
4. Check results display:
   - ✅ BOQ Items: 18
   - ✅ Schedule Tasks: 22
   - ✅ Critical Activities: 12
5. Verify processing notes appear
6. Click "Start Variation Evaluation" button

### Expected Navigation:

Should navigate to `/chat/:sessionId` (e.g., `/chat/1`)

---

## Test 3: Chat Page

### Steps:

1. Should auto-navigate from upload page
2. URL: **http://localhost:5173/chat/1** (or session ID from upload)

### Expected Results:

✅ Page title: "Variation Evaluation Chat"  
✅ Header shows project info (18 BOQ items, 22 activities)  
✅ "Active" status badge (green)  
✅ Empty state message: "Start Your Variation Evaluation"  
✅ Helper text about FIDIC workflow  
✅ Message input area at bottom  
✅ "Send" button

### Test Conversation:

#### Message 1: Initial Request

1. Type: `I need to evaluate a variation for Guard Stones`
2. Press Enter OR click "Send"
3. Verify:
   - ✅ Your message appears (blue, right-aligned)
   - ✅ "AI is typing..." indicator appears
   - ✅ AI response appears (white, left-aligned)
   - ✅ Messages auto-scroll to bottom

#### Message 2: Provide Details

1. Type: `Increase quantity from 150 to 200 units`
2. Send message
3. Verify AI responds

#### Message 3: Cost Query

1. Type: `What is the cost impact?`
2. Send message
3. Verify AI responds with cost information

### Expected Behavior:

- ✅ Messages appear in conversation order
- ✅ Timestamps show on each message
- ✅ Auto-scroll to latest message
- ✅ Enter key sends message
- ✅ Shift+Enter creates new line

---

## Test 4: Proposal Page

### Steps:

1. Navigate to: **http://localhost:5173/proposal/1**
2. (In real flow, would navigate from chat after proposal generation)

### Expected Results:

✅ Page title: "Variation Proposal"  
✅ "Download PDF" button in header  
✅ Executive Summary section with 3 cards:

- Cost Impact (blue)
- Time Impact (green)
- Variation Type (amber)  
  ✅ Cost Breakdown table  
  ✅ Time Impact Analysis section (if time impact > 0)  
  ✅ Action buttons:
- "Back to Chat"
- "Edit Variation"
- "Approve Proposal"

### Actions to Test:

- [ ] Click "Back to Chat" → Should navigate back
- [ ] Click "Download PDF" → Should trigger PDF download
- [ ] Click "Approve Proposal" → Should show approval confirmation

---

## Test 5: Sessions Page

### Steps:

1. Navigate to: **http://localhost:5173/sessions**
2. OR click "My Sessions" from header

### Expected Results:

✅ Page title: "My Sessions"  
✅ "New Evaluation" button in header  
✅ Filter tabs: All, Active, Archived  
✅ Sessions list OR empty state

### If Sessions Exist:

✅ Each session card shows:

- Session name
- Status badge (Active/Archived/Closed)
- Created date
- Message count
- Action buttons

### Actions to Test:

- [ ] Click filter tabs → Should filter sessions
- [ ] Click "Continue" on active session → Navigate to chat
- [ ] Click "New Evaluation" → Navigate to upload

### If No Sessions:

✅ Empty state message: "No Sessions Yet"  
✅ "Start New Evaluation" button

---

## Test 6: Navigation & Routing

### Test All Routes:

1. **/** → Welcome page ✅
2. **/upload** → Upload page ✅
3. **/chat/1** → Chat page ✅
4. **/proposal/1** → Proposal page ✅
5. **/sessions** → Sessions page ✅
6. **/invalid-route** → Should redirect to Welcome page ✅

### Test Back Button:

- [ ] Navigate through pages
- [ ] Use browser back button
- [ ] Verify correct page loads

---

## Test 7: Responsive Design

### Desktop (> 1024px):

- [ ] All pages display correctly
- [ ] Multi-column layouts work
- [ ] Cards display in grid

### Tablet (640px - 1024px):

- [ ] Resize browser window
- [ ] Verify responsive breakpoints
- [ ] Check grid layouts adjust

### Mobile (< 640px):

- [ ] Open browser dev tools
- [ ] Toggle device toolbar
- [ ] Select mobile device
- [ ] Verify:
  - Single column layouts
  - Touch-friendly buttons
  - Readable text
  - No horizontal scroll

---

## Test 8: Error Handling

### Test Upload Errors:

1. Go to upload page
2. Try uploading invalid file type (e.g., .txt)
3. Verify error message appears

### Test API Errors:

1. Stop backend server
2. Try to upload files
3. Verify error message appears
4. Restart backend
5. Retry upload → Should work

---

## Test 9: Loading States

### During File Upload:

- [ ] Progress bar shows (0-100%)
- [ ] Upload button disabled during upload
- [ ] Loading indicator visible

### During Chat:

- [ ] "AI is typing..." appears
- [ ] Send button disabled while waiting
- [ ] Messages appear after response

---

## Test 10: Integration Test (End-to-End)

### Complete Flow:

1. **Start** → Welcome page
2. **Click** "Start New Evaluation"
3. **Upload** BOQ file
4. **Upload** Rate breakdown file
5. **Upload** Schedule file
6. **Verify** upload results
7. **Navigate** to chat
8. **Send** variation request message
9. **Send** variation details
10. **Verify** AI responses
11. **Check** proposal generated (if applicable)
12. **Navigate** to sessions page
13. **Verify** session appears in list
14. **Continue** session from sessions page
15. **Verify** returns to chat with history

---

## ✅ Testing Checklist Summary

### Pages (5/5)

- [ ] Welcome Page
- [ ] Upload Page
- [ ] Chat Page
- [ ] Proposal Page
- [ ] Sessions Page

### Features

- [ ] File upload (drag-and-drop)
- [ ] Multi-step wizard
- [ ] Progress tracking
- [ ] Chat messaging
- [ ] AI responses
- [ ] Session management
- [ ] Navigation
- [ ] Responsive design
- [ ] Error handling
- [ ] Loading states

### API Integration

- [ ] File upload endpoint
- [ ] Chat endpoint
- [ ] Session endpoints
- [ ] Error responses

---

## 🐛 Known Issues to Watch For

1. **CORS Errors**: If you see CORS errors in console, backend may need CORS configuration
2. **File Upload Fails**: Check backend is running on port 8000
3. **Chat Not Responding**: Verify Groq API key is set in backend .env
4. **Session Not Found**: May need to create session first via upload

---

## 📊 Success Criteria

**All tests pass if:**

- ✅ All 5 pages load without errors
- ✅ File upload completes successfully
- ✅ Chat messages send and receive
- ✅ Navigation works correctly
- ✅ No console errors
- ✅ Responsive on all screen sizes
- ✅ Error messages display appropriately
- ✅ Loading states show correctly

---

## 🎯 Quick Test (5 Minutes)

**Minimal test to verify everything works:**

1. Open http://localhost:5173
2. Click "Start New Evaluation"
3. Upload sample_boq.csv
4. Click through to upload results
5. Verify 18 BOQ items processed
6. Click "Start Variation Evaluation"
7. Send a test message in chat
8. Verify AI responds
9. Navigate to sessions page
10. Verify session appears

**If all 10 steps work → Frontend is operational! ✅**

---

_Testing Guide Created: February 9, 2026_  
_Frontend Version: 1.0.0_
