# Vision Debug Guide

## What You Should See When Testing Vision Mode

### 🎯 **Step 1: Switch to Vision Mode**
1. Click the "Vision Control" radio button
2. You should see: "Vision mode enabled. Start camera to use gesture controls."

### 📷 **Step 2: Start Camera**
1. Click "Start Camera" button
2. **Camera Preview Window** should show:
   - **Live video feed** with debug overlays
   - **Blue overlay areas** = what the system detects as "skin color"
   - **Yellow contours** = all detected objects/shapes
   - **Green circle + box** = main hand detection (if area > 1500px)
   - **Red circle labeled "TOP"** = topmost point for pointing
   - **White text at bottom** = detection settings and legend

### 🔍 **Step 3: Debug Panel (Top Right)**
A black debug panel should appear showing:
- **Contours Found**: Number of shapes detected
- **Areas**: Size of each detected shape in pixels  
- **HSV Sample**: Color values at detected hand center
- **Tips**: What conditions work best

### ✋ **Step 4: Test Hand Detection**
Move your hand in front of camera. You should see:

**Good Detection** (what we want):
- Blue overlay follows your hand smoothly
- Green circle tracks hand center steadily
- Area shows 1500+ pixels
- HSV values in range: H[0-25] S[30-255] V[60-255]
- Yellow contour outlines your hand

**Bad Detection** (problems to report):
- Blue overlay appears on background objects
- Multiple yellow contours on non-hand items
- Green circle jumps around erratically
- Area too small (<1500) or too large (>20000)
- HSV values outside expected ranges

### 🎮 **Step 5: Test Board Interaction**
With hand detected:
- **Hover**: Hand over board should show green highlight on squares
- **Point**: Hold hand still for 2+ seconds = select piece
- **Move**: Point at different square = move piece

### 🚨 **Common Issues to Look For:**

1. **"Flickering green box"**:
   - Debug info shows rapidly changing contour areas
   - Multiple small areas detected
   - HSV values jumping around

2. **"No detection"**:
   - Blue overlay missing or very small
   - Area always < 1500
   - Debug panel shows 0 contours

3. **"False positives"**:
   - Blue overlay on walls, objects, clothes
   - Multiple large yellow contours
   - Areas > 10000 on background items

### 💡 **Testing Tips:**
- **Good lighting**: Bright, even lighting works best
- **Contrasting background**: Hand against plain wall/surface
- **Clean background**: Remove other objects from camera view
- **Steady hand**: Move slowly for better tracking
- **Skin exposure**: Bare hand works better than gloves

## What to Report:
1. **What you see** in camera preview (colors, overlays, tracking)
2. **Debug panel values** (contours, areas, HSV)
3. **Expected vs actual behavior** 
4. **Environment conditions** (lighting, background, etc.)

This debug system will help us identify exactly what's causing the vision tracking issues!