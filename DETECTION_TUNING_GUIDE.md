# Enhanced Red Marker Detection - Tuning Guide

## Overview
This guide covers parameter tuning, testing procedures, and troubleshooting for the enhanced red marker detection system designed to eliminate false positives from red clothing while reliably detecting 1-2cm round marker tips.

## Key Detection Parameters

### Color Detection Parameters (`AdaptiveColorDetector`)
```python
# HSV color ranges - tuned for markers vs clothing
marker_red_ranges = [
    ([0, 120, 120], [10, 255, 255]),    # Primary red - higher saturation
    ([160, 120, 120], [179, 255, 255])  # Wrap-around red
]
```

**Tuning Guidelines:**
- **Saturation Min (120)**: Key parameter to eliminate clothing false positives
  - Increase to 140+ for very restrictive detection (less clothing interference)  
  - Decrease to 100 if missing valid markers in poor lighting
- **Value/Brightness (120)**: Minimum brightness to ensure visible markers
  - Adjust based on lighting conditions
  - Lower values (80-100) for dim environments
  - Higher values (150+) for bright environments

### Geometric Validation Parameters (`MarkerGeometryValidator`)
```python
# Size constraints for 1-2cm markers at 30-100cm distance
min_area = 50      # Very close camera (30cm)
max_area = 800     # Far camera (100cm)
min_circularity = 0.75  # Strictness for round shape
min_convexity = 0.9     # Eliminate clothing folds
aspect_ratio_range = (0.8, 1.2)  # Nearly circular
min_compactness = 0.7   # Area vs bounding box ratio
```

**Tuning Guidelines:**
- **Area Range (50-800)**: Critical for size filtering
  - Measure actual marker areas at your typical distances
  - Use calibration system for automatic adjustment
- **Circularity (0.75)**: Balance between strict circles and real-world markers
  - Increase to 0.8+ to be more selective
  - Decrease to 0.6+ if missing valid round markers
- **Convexity (0.9)**: Eliminates most clothing folds
  - Very effective against fabric wrinkles and shadows
  - Rarely needs adjustment

### Color Uniformity Parameters (`ColorUniformityAnalyzer`)
```python
max_color_variance = 400    # Texture detection threshold
max_brightness_range = 40   # Shadow/highlight tolerance
min_saturation_consistency = 0.85  # Color purity requirement
```

**Tuning Guidelines:**
- **Color Variance (400)**: Key parameter for texture detection
  - Lower values (200-300) for stricter uniformity (less clothing)
  - Higher values (500-600) if missing markers with slight color variation
- **Brightness Range (40)**: Tolerance for lighting variations
  - Increase for uneven lighting conditions
  - Decrease for more uniform detection environment

### Temporal Validation Parameters (`TemporalConsistencyValidator`)
```python
max_position_jump = 30  # pixels - reasonable hand movement
max_size_change = 0.3   # 30% size change allowed
stability_threshold = 15  # pixels for stable position
```

### Confidence Scoring Weights (`MarkerConfidenceScorer`)
```python
weights = {
    'geometric': 0.30,    # Shape, size, circularity
    'color': 0.25,        # Hue accuracy, saturation
    'uniformity': 0.25,   # Color consistency, no texture  
    'temporal': 0.20      # Position stability, consistency
}
min_component_threshold = 0.6  # All components must be reasonable
```

## Testing Procedures

### 1. False Positive Elimination Test
**Purpose:** Ensure red clothing doesn't trigger detection

**Test Cases:**
- Red t-shirts with various textures (solid, patterns, worn fabric)
- Red backgrounds (walls, posters, books)
- Red objects (cups, toys, furniture)
- Mixed red items in scene

**Success Criteria:**
- No detections with confidence > 0.3 for non-marker red objects
- Detection pipeline shows candidates rejected at uniformity stage
- Debug info shows high color variance for textured objects

**Tuning if Test Fails:**
1. Increase `max_color_variance` threshold (lower value = stricter)
2. Increase `min_saturation_consistency` (higher = more selective)
3. Adjust `marker_red_ranges` saturation minimums upward

### 2. Marker Detection Reliability Test
**Purpose:** Ensure consistent detection of actual markers

**Test Setup:**
- Use actual 1-2cm round red marker tip
- Test at distances: 30cm, 50cm, 70cm, 100cm
- Various lighting conditions: bright, dim, mixed
- Different angles: straight-on, 30°, 45°

**Success Criteria:**
- Detection confidence > 0.75 in all reasonable conditions
- Stable tracking with minimal jitter
- Detection state reaches "CONFIRMED" consistently

**Tuning if Test Fails:**
1. Run calibration system to adjust size ranges
2. Lower confidence thresholds temporarily to debug
3. Check individual component scores in quality metrics
4. Adjust geometric parameters (circularity, convexity)

### 3. Gesture Recognition Test
**Purpose:** Verify interaction gestures work reliably

**Test Sequence:**
1. Approach marker to board (IDLE → HOVERING)
2. Hold steady over piece for 1 second (HOVERING → SELECTING)  
3. Move marker to drag piece (SELECTING → DRAGGING)
4. Hold steady at destination (DRAGGING → RELEASING)

**Success Criteria:**
- State transitions occur predictably
- Dwell time threshold works consistently (1 second)
- No false selections from quick movements
- Stable drag tracking

### 4. Lighting Adaptation Test
**Purpose:** Ensure detection works across lighting conditions

**Test Conditions:**
- Bright indoor lighting (office/daylight)
- Dim indoor lighting (evening/ambient)
- Mixed lighting (window + artificial)
- Directional lighting (desk lamp)

**Adaptive Parameters:**
- Color detection ranges may need adjustment
- Brightness thresholds in uniformity analysis
- Consider auto-exposure impact on HSV values

## Troubleshooting Common Issues

### Issue: Red Clothing Causing False Positives
**Symptoms:** Detections on shirts, backgrounds, textured objects
**Solution Steps:**
1. Check `debug_info.passed_uniformity` - should be 0 for clothing
2. Increase saturation minimum in color ranges: 120 → 140
3. Decrease `max_color_variance`: 400 → 300
4. Verify `min_saturation_consistency`: keep ≥ 0.85

### Issue: Missing Valid Marker Detections  
**Symptoms:** No detection despite visible red marker
**Debugging Steps:**
1. Check `debug_info.candidates_found` - should be > 0
2. Check `debug_info.passed_geometry` - geometric validation
3. Check quality component scores in debug output
4. Verify marker is actually round and uniform

**Solution Approaches:**
- If candidates_found = 0: Adjust color HSV ranges
- If passed_geometry = 0: Check size ranges, run calibration
- If passed_uniformity = 0: Increase color variance tolerance
- If low confidence: Check individual component thresholds

### Issue: Unstable Tracking/Jittery Detection
**Symptoms:** Detection confidence fluctuates, position jumps
**Solutions:**
1. Increase Kalman filter process noise for more smoothing
2. Adjust `stability_threshold` in temporal validator
3. Check for reflections or lighting variations on marker
4. Ensure marker surface is matte/non-reflective

### Issue: Gesture Recognition Not Triggering
**Symptoms:** Hovering but no selection, dragging not detected
**Check:**
1. Detection confidence consistently > 0.75
2. Marker stability (stable=true in output)
3. Dwell time threshold (1 second default)
4. Quality validation thresholds in interaction manager

## Performance Optimization

### Real-time Performance Tips
- Target frame rate: 30+ FPS for responsive interaction
- Monitor `debug_info` candidate counts - high numbers indicate processing load
- Consider reducing max contour processing if too many candidates
- Use camera resolution appropriate for detection distance (640x480 often sufficient)

### Memory Usage
- Position history buffers are limited (10-15 frames)
- Kalman filter state is minimal
- No significant memory leaks in detection pipeline

### CPU Usage Optimization
- Most expensive operations are in color uniformity analysis
- Morphological operations can be tuned (kernel size, iterations)
- Consider down-sampling frame for detection if performance issues

## Calibration Procedures

### Automatic Size Calibration
```bash
# Run interactive calibration
python backend/calibration_system.py

# Steps:
1. Hold marker at 30cm from camera, press 'c'
2. Hold marker at 50cm from camera, press 'c'  
3. Hold marker at 70cm from camera, press 'c'
4. Hold marker at 100cm from camera, press 'c'
5. Press 'f' to finalize calibration
```

### Manual Parameter Adjustment
For specific environments, manually tune these key parameters:

```python
# In detection.py - AdaptiveColorDetector
marker_red_ranges = [
    ([0, YOUR_MIN_SAT, YOUR_MIN_VAL], [10, 255, 255]),
    ([160, YOUR_MIN_SAT, YOUR_MIN_VAL], [179, 255, 255])
]

# In detection.py - MarkerGeometryValidator  
min_area = YOUR_CLOSE_DISTANCE_AREA    # Measured at 30cm
max_area = YOUR_FAR_DISTANCE_AREA      # Measured at 100cm

# In detection.py - ColorUniformityAnalyzer
max_color_variance = YOUR_TEXTURE_THRESHOLD  # Start with 400, adjust down for stricter
```

## Debug Output Interpretation

### Quality Metrics Scores
- **Geometric (0-1)**: Shape quality (circularity, size, convexity)
- **Color (0-1)**: Hue accuracy and saturation levels  
- **Uniformity (0-1)**: Color consistency across marker region
- **Temporal (0-1)**: Position stability and property consistency

### Debug Pipeline Info
```json
{
  "candidates_found": 5,        // Red regions found
  "passed_geometry": 2,         // Passed shape validation
  "passed_uniformity": 1        // Passed texture validation  
}
```

**Interpretation:**
- High candidates, low geometry pass: Size/shape issues
- High geometry pass, low uniformity pass: Texture/clothing detection
- All stages pass but low confidence: Component score thresholds

## Best Practices

1. **Use Physical Marker Consistently**: Same marker for calibration and use
2. **Calibrate for Your Environment**: Lighting and distance matter significantly  
3. **Monitor Quality Metrics**: Use debug mode to understand detection quality
4. **Test Edge Cases**: Clothing, backgrounds, mixed lighting scenarios
5. **Iterate Parameters**: Small adjustments can have big impact on reliability

This enhanced detection system provides robust marker tracking while eliminating false positives, but proper tuning for your specific setup is essential for optimal performance.