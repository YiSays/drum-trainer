# Drum Trainer Web UI - UI Control Fixes

## 🎯 Goal

Fix three UI control issues in the JavaScript-based drum trainer web app (`web_ui/`):

1. **Time Display Issue**: Total duration should show when tracks are selected, not just during playback
2. **Play Button Logic**: Should be disabled during playback, enabled when stopped/paused
3. **Button State Styling**: Stop and pause buttons should be highlighted when playing (opposite of play button)

---

## 📋 Issues Analysis

### Issue 1: Time Display (`totalTime`)
**Current Behavior**: `totalTime` only shows when audio is playing (via `updateDuration()` triggered by `loadedmetadata` event during playback)

**Expected Behavior**: When tracks are selected, show the total duration even before clicking play

**Root Cause**: The `loadedmetadata` event is only attached when `play()` is called and audio elements are created. Before play, no audio elements exist, so duration cannot be retrieved.

**Solution**: When tracks are selected, fetch the first track's duration via `/tracks/info/{name}` endpoint to display total time.

### Issue 2: Play Button Logic
**Current Behavior**: Play button can be clicked at any time

**Expected Behavior**:
- Play button should be **disabled** when playing
- Play button should be **enabled** when stopped/paused

**Solution**: Update `updatePlayState()` to manage play button's `disabled` property, and call it when playback state changes.

### Issue 3: Button State Styling (Stop/Pause)
**Current Behavior**: Only play button changes opacity (0.5 when playing)

**Expected Behavior**:
- Play button: dimmed when playing (current behavior)
- Stop button: highlighted when playing (opposite of play)
- Pause button: highlighted when playing (opposite of play)

**Solution**: Add visual highlight styles to stop and pause buttons when playing.

---

## 🔧 Implementation Plan

### File 1: `web_ui/js/app.js`

#### Change 1: Update `updatePlayState()` function (lines 1450-1457)

**Current Code**:
```javascript
function updatePlayState() {
    if (!elements.playBtn) return;
    if (state.isPlaying) {
        elements.playBtn.style.opacity = '0.5';
    } else {
        elements.playBtn.style.opacity = '1';
    }
}
```

**New Code**:
```javascript
function updatePlayState() {
    if (!elements.playBtn) return;

    // Play button: disabled when playing, enabled when stopped/paused
    if (state.isPlaying) {
        elements.playBtn.style.opacity = '0.5';
        elements.playBtn.disabled = true;
    } else {
        elements.playBtn.style.opacity = '1';
        elements.playBtn.disabled = false;
    }

    // Stop button: highlight when playing
    if (elements.stopBtn) {
        elements.stopBtn.style.opacity = state.isPlaying ? '1' : '0.6';
        elements.stopBtn.style.background = state.isPlaying
            ? 'rgba(239, 68, 68, 0.2)'
            : '';
        elements.stopBtn.style.borderColor = state.isPlaying
            ? 'rgba(239, 68, 68, 0.3)'
            : '';
    }

    // Pause button: highlight when playing
    if (elements.pauseBtn) {
        elements.pauseBtn.style.opacity = state.isPlaying ? '1' : '0.6';
        elements.pauseBtn.style.background = state.isPlaying
            ? 'rgba(251, 191, 36, 0.2)'
            : '';
        elements.pauseBtn.style.borderColor = state.isPlaying
            ? 'rgba(251, 191, 36, 0.3)'
            : '';
    }
}
```

#### Change 2: Add `updateTotalTimeForSelectedTracks()` function

Add new function after `updateDuration()` (around line 1381):

```javascript
/**
 * Update total time display when tracks are selected (before playing)
 */
function updateTotalTimeForSelectedTracks() {
    if (!elements.totalTime || state.selectedTracks.length === 0) {
        return;
    }

    // Get the first selected track's duration
    const firstTrack = state.selectedTracks[0].track;
    if (firstTrack && firstTrack.duration) {
        elements.totalTime.textContent = formatTime(firstTrack.duration);
    }
}
```

#### Change 3: Call `updateTotalTimeForSelectedTracks()` when tracks change

In `addToSelectedTracks()` function (around line 743), add:
```javascript
function addToSelectedTracks(track, index) {
    // ... existing code ...

    // Update total time display
    updateTotalTimeForSelectedTracks();

    showToast(`已添加: ${track.name}`, 'success');
}
```

In `removeFromSelectedTracks()` function (around line 770), add:
```javascript
function removeFromSelectedTracks(index) {
    // ... existing code ...

    // Update total time display (or clear if no tracks left)
    if (state.selectedTracks.length === 0) {
        if (elements.totalTime) elements.totalTime.textContent = '0:00';
    } else {
        updateTotalTimeForSelectedTracks();
    }

    showToast(`已移除: ${trackToRemove.track.name}`, 'info');
}
```

#### Change 4: Update `stop()` function to reset play button state

In `stop()` function (around line 1190), ensure `updatePlayState()` is called:

```javascript
function stop() {
    stopAllAudio();
    state.isPlaying = false;
    updatePlayState();  // This already exists, but verify it's called
    stopRealtimeVisualization();
}
```

#### Change 5: Update keyboard shortcuts for Space key

In `setupKeyboardShortcuts()` (around line 418), update the Space key handler:
```javascript
case 'Space':
    e.preventDefault();
    if (state.isPlaying) {
        pause();
    } else if (state.selectedTracks.length > 0) {
        play();
    }
    break;
```

This should already work, but verify the play button is properly disabled during playback.

---

### File 2: `web_ui/css/style.css`

#### Change 1: Add styles for button states (optional - if JS styles don't work well)

Add after existing button styles (around line 1194):

```css
/* Play button disabled state */
.btn-control.play:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

/* Stop button highlight when active/playing */
.btn-control.stop.active {
    opacity: 1;
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.3);
}

/* Pause button highlight when active/playing */
.btn-control.pause.active {
    opacity: 1;
    background: rgba(251, 191, 36, 0.2);
    border-color: rgba(251, 191, 36, 0.3);
}
```

---

## 🧪 Testing Plan

### Test 1: Time Display Shows When Tracks Selected

**Steps**:
1. Load app, wait for tracks to appear
2. Click on a track to select it (green border)
3. **Expected**: `totalTime` element shows the track's duration (e.g., "2:34")
4. Click another track
5. **Expected**: `totalTime` still shows duration
6. Unselect all tracks
7. **Expected**: `totalTime` resets to "0:00"

**Console check**:
```javascript
// After selecting track
console.log('Total time:', elements.totalTime.textContent);
// Should show something like "2:34", not "0:00"
```

### Test 2: Play Button Disabled During Playback

**Steps**:
1. Select one or more tracks
2. **Before clicking play**: Check play button
   - Should be **enabled** (clickable)
   - `elements.playBtn.disabled` should be `false`
3. Click play button
4. **During playback**: Check play button
   - Should be **disabled** (not clickable)
   - `elements.playBtn.disabled` should be `true`
   - Should be visually dimmed (opacity 0.5)
5. Click pause button
6. **After pause**: Check play button
   - Should be **enabled** again
   - `elements.playBtn.disabled` should be `false`

**Console check**:
```javascript
// Before play
console.log('Play button disabled:', elements.playBtn.disabled); // Should be false

// During playback
console.log('Play button disabled:', elements.playBtn.disabled); // Should be true

// After pause
console.log('Play button disabled:', elements.playBtn.disabled); // Should be false
```

### Test 3: Stop/Pause Button Highlight When Playing

**Steps**:
1. Select tracks, click play
2. **During playback**:
   - Play button: dimmed (opacity 0.5)
   - Stop button: **highlighted** (opacity 1, red border)
   - Pause button: **highlighted** (opacity 1, yellow border)
3. Click pause
4. **After pause**:
   - Play button: normal (opacity 1)
   - Stop button: less prominent (opacity 0.6)
   - Pause button: less prominent (opacity 0.6)
5. Click play again
6. **During playback**:
   - Buttons return to highlighted state

**Visual check**:
- Stop button should show red background/border when playing
- Pause button should show yellow background/border when playing

### Test 4: Space Key Behavior

**Steps**:
1. Select tracks
2. Press Space
3. **Expected**: Playback starts, play button becomes disabled
4. Press Space again
5. **Expected**: Playback pauses, play button becomes enabled
6. Press Space again
7. **Expected**: Playback resumes, play button becomes disabled

### Test 5: Combined Flow

**Steps**:
1. Load app
2. Select 2 tracks
3. **Verify**: Total time shows correct duration
4. **Verify**: Play button is enabled
5. **Verify**: Stop and pause buttons are less prominent (not highlighted)
6. Click play
7. **Verify**: Total time continues to show duration (doesn't reset)
8. **Verify**: Play button is disabled
9. **Verify**: Stop and pause buttons are highlighted
10. Click stop
11. **Verify**: Total time shows "0:00"
12. **Verify**: Play button is enabled
13. **Verify**: Stop and pause buttons are less prominent

---

## 📊 Expected Results

| Scenario | Play Button | Stop Button | Pause Button | Total Time |
|----------|-------------|-------------|--------------|------------|
| No tracks selected | Disabled | Normal | Normal | 0:00 |
| Tracks selected, not playing | Enabled | Normal | Normal | Shows duration |
| Tracks selected, playing | **Disabled** | **Highlighted** | **Highlighted** | Shows duration |
| Tracks selected, paused | Enabled | Normal | Normal | Shows duration |
| All tracks unselected | Disabled | Normal | Normal | 0:00 |

---

## 🎯 Files to Modify

### Primary Files
1. **`web_ui/js/app.js`**:
   - `updatePlayState()` - Enhanced to manage all button states
   - `addToSelectedTracks()` - Call `updateTotalTimeForSelectedTracks()`
   - `removeFromSelectedTracks()` - Call `updateTotalTimeForSelectedTracks()` or clear time
   - New function: `updateTotalTimeForSelectedTracks()`

### Optional Files
2. **`web_ui/css/style.css`**:
   - Add button state styles (for visual consistency)

---

## ⚠️ Important Notes

1. **Total Time Display**: The `totalTime` element currently only updates when `loadedmetadata` fires during playback. We need a way to show duration before playback. The solution is to:
   - Either fetch track info from API when selecting tracks
   - Or use the track.duration data already available from the tracks list

   **Recommended**: Use `track.duration` from the existing data (already fetched in `state.tracks`).

2. **Play Button Disabled State**: The `enablePlayerControls()` function (line 887-891) controls initial enabled/disabled state based on API connection. This should remain unchanged - we only need to update `updatePlayState()` to toggle play button during playback.

3. **Button Styling**: Currently buttons use inline styles (`style.opacity`). We should continue using inline styles for consistency, or switch to adding/removing CSS classes.

4. **Stop/Pause Button States**: Currently these buttons have no visual change. We need to add styling that matches the design system (using the existing CSS variables for colors).

---

## 🔍 Code Locations for Reference

### Current Code Locations

**updatePlayState()** (lines 1450-1457):
```javascript
function updatePlayState() {
    if (!elements.playBtn) return;
    if (state.isPlaying) {
        elements.playBtn.style.opacity = '0.5';
    } else {
        elements.playBtn.style.opacity = '1';
    }
}
```

**addToSelectedTracks()** (lines 718-744):
```javascript
function addToSelectedTracks(track, index) {
    // ... adds to selectedTracks array
    // ... updates UI (adds 'active' class to card)
    // ... starts playback if already playing
    showToast(`已添加: ${track.name}`, 'success');
}
```

**removeFromSelectedTracks()** (lines 746-771):
```javascript
function removeFromSelectedTracks(index) {
    // ... removes from selectedTracks array
    // ... updates UI (removes 'active' class from card)
    // ... stops this audio element if playing
    showToast(`已移除: ${trackToRemove.track.name}`, 'info');
}
```

**stop()** (lines 1187-1195):
```javascript
function stop() {
    stopAllAudio();
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
}
```

**pause()** (lines 1177-1185):
```javascript
function pause() {
    pauseAllAudio();
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
}
```

**elements.totalTime** is defined at line 62:
```javascript
totalTime: document.getElementById('totalTime'),
```

---

## 📝 Summary of Changes

### app.js Changes Summary

| Function | Change | Lines |
|----------|--------|-------|
| `updatePlayState()` | Add play button disabled logic, add stop/pause highlight | ~1450-1475 |
| `addToSelectedTracks()` | Add call to `updateTotalTimeForSelectedTracks()` | ~743 |
| `removeFromSelectedTracks()` | Add call to `updateTotalTimeForSelectedTracks()` or clear time | ~770 |
| New: `updateTotalTimeForSelectedTracks()` | Display total time when tracks selected | New function |

### CSS Changes Summary

| Selector | Change |
|----------|--------|
| `.btn-control.play:disabled` | Disabled play button styling |
| `.btn-control.stop.active` | Highlighted stop button (when playing) |
| `.btn-control.pause.active` | Highlighted pause button (when playing) |

---

## ✅ Verification Checklist

- [ ] Time display shows duration when tracks are selected
- [ ] Time display shows "0:00" when no tracks selected
- [ ] Play button is disabled during playback
- [ ] Play button is enabled when stopped/paused
- [ ] Stop button is highlighted when playing
- [ ] Pause button is highlighted when playing
- [ ] Button states work correctly with keyboard shortcuts
- [ ] No regression in existing functionality (play/pause/stop/seek work as before)

---

**Last Updated**: 2026-01-15
**Priority**: High - UI/UX improvements
