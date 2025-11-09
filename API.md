# Robot Control API Documentation

## Overview

This ESP32-S3-CAM robot provides a REST API for motor control and camera operations over WiFi.

## Base URL

After connecting to WiFi, the robot will print its IP address to the serial console. Use this IP as the base URL:

```
http://<ROBOT_IP>/api/
```

## Endpoints

### Motor Control

All motor control endpoints accept an optional `duration` parameter (in milliseconds).

#### Move Forward
```
GET /api/motor/forward?duration=<ms>
```
- **Parameters:**
  - `duration` (optional): Movement duration in milliseconds (50-5000). Default: 500ms
- **Response:** `{"status":"ok","action":"forward"}`

#### Move Backward
```
GET /api/motor/backward?duration=<ms>
```
- **Parameters:**
  - `duration` (optional): Movement duration in milliseconds (50-5000). Default: 500ms
- **Response:** `{"status":"ok","action":"backward"}`

#### Turn Left
```
GET /api/motor/left?duration=<ms>
```
- **Parameters:**
  - `duration` (optional): Turn duration in milliseconds (50-5000). Default: 500ms
- **Response:** `{"status":"ok","action":"left"}`

#### Turn Right
```
GET /api/motor/right?duration=<ms>
```
- **Parameters:**
  - `duration` (optional): Turn duration in milliseconds (50-5000). Default: 500ms
- **Response:** `{"status":"ok","action":"right"}`

#### Stop Motors
```
GET /api/motor/stop
```
- **Response:** `{"status":"ok","action":"stop"}`

### Camera

#### Capture Photo
```
GET /api/camera/photo
```
- **Response:** JPEG image (640x480)
- **Content-Type:** `image/jpeg`

### Status

#### Get System Status
```
GET /api/status
```
- **Response:** `{"camera":true|false,"wifi":"<IP_ADDRESS>"}`

## Usage Examples

### Using curl

```bash
# Move forward for default duration (500ms)
curl http://192.168.1.100/api/motor/forward

# Move forward for 2 seconds
curl http://192.168.1.100/api/motor/forward?duration=2000

# Turn left for 300ms
curl http://192.168.1.100/api/motor/left?duration=300

# Stop motors
curl http://192.168.1.100/api/motor/stop

# Capture photo and save to file
curl http://192.168.1.100/api/camera/photo -o photo.jpg

# Check system status
curl http://192.168.1.100/api/status
```

### Using JavaScript (fetch)

```javascript
const ROBOT_IP = '192.168.1.100';

// Move forward for 1 second
fetch(`http://${ROBOT_IP}/api/motor/forward?duration=1000`)
  .then(res => res.json())
  .then(data => console.log(data));

// Capture photo
fetch(`http://${ROBOT_IP}/api/camera/photo`)
  .then(res => res.blob())
  .then(blob => {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(blob);
    document.body.appendChild(img);
  });
```

### Using Python (requests)

```python
import requests

ROBOT_IP = '192.168.1.100'

# Move forward for 1.5 seconds
response = requests.get(f'http://{ROBOT_IP}/api/motor/forward?duration=1500')
print(response.json())

# Capture and save photo
response = requests.get(f'http://{ROBOT_IP}/api/camera/photo')
with open('photo.jpg', 'wb') as f:
    f.write(response.content)
```

## Notes

- Duration values are automatically constrained between 50ms and 5000ms for safety
- All endpoints support CORS, allowing requests from any origin
- The camera must be successfully initialized for photo capture to work
- Motor movements are blocking - the endpoint will not respond until the movement completes
