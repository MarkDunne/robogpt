# ESP32-S3-CAM Setup Guide

## Board Information
- **Board**: Goouuu SEP32 S3 CAM
- **Chip**: ESP32-S3 (QFN56) revision v0.2
- **Features**: WiFi, BT 5 (LE), Dual Core + LP Core, 240MHz
- **Memory**: 8MB Embedded PSRAM (AP_3v3)
- **USB-Serial Chip**: CH340C
- **Ports**: 2x USB-C (UART/Serial + USB-OTG)

## Working Arduino IDE Settings

### Critical Settings for Mac + CH340C
- **Board**: ESP32S3 Dev Module
- **Upload Speed**: 115200 *(CRITICAL - 921600 fails with CH340C on Mac)*
- **PSRAM**: OPI PSRAM *(MUST enable or camera fails)*
- **Partition Scheme**: Default 4MB with SPIFFS
- **Port**: /dev/cu.usbserial-XXX (UART port)

## Key Troubleshooting Discoveries

### 1. Upload Speed Issue
- **Problem**: "The chip stopped responding" error during flash
- **Cause**: CH340C USB-serial chip can't handle 921600 baud on Mac
- **Solution**: Set Upload Speed to 115200 in Arduino IDE

### 2. Camera Memory Allocation
- **Problem**: "frame buffer malloc failed" error
- **Cause**: PSRAM not enabled, camera needs more memory than internal RAM provides
- **Solution**:
  - Select ESP32S3 Dev Module (not ESP32 Dev Module)
  - Enable PSRAM in Tools menu
  - Verify with `psramFound()` function

### 3. Image Transfer Timeout
- **Problem**: Browser connection times out when loading image
- **Solutions Applied**:
  - Frame size: FRAMESIZE_VGA (640x480)
  - JPEG quality: 10 (lower = better quality, range 0-63)
  - Using 2 frame buffers for smoother capture
  - Frame buffers stored in PSRAM when available

## Camera Pin Configuration
```cpp
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5
#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM       8
#define Y3_GPIO_NUM       9
#define Y2_GPIO_NUM       11
#define VSYNC_GPIO_NUM    6
#define HREF_GPIO_NUM     7
#define PCLK_GPIO_NUM     13
```

## Memory Architecture
- **Internal RAM**: ~320KB (fast, always available)
- **PSRAM**: 8MB (medium speed, must be enabled in Arduino IDE)
- **Flash/SPIFFS**: Storage, not for active memory

## WiFi Configuration
- **Mode**: Station (connects to existing WiFi network)
- **Credentials**: Configured in code (`ssid` and `password` constants)
- **Connection**: Uses `WiFi.begin()` to connect as a client
- **IP Address**: Assigned by DHCP from the router, printed to serial on boot

## Lessons Learned
1. Always check upload speed when using CH340 chips on Mac
2. ESP32-S3 boards need explicit PSRAM enablement for camera operations
3. Boot messages that look like errors are often just normal status info
4. Use RST button to restart board after upload to see serial output
5. Image size/quality directly impacts WiFi transfer reliability

## Command Line Usage (Arduino CLI + Just)

### Quick Start
```bash
# First time setup
just setup

# Compile, upload, and monitor
just run

# Just upload code
just upload

# Just monitor serial output
just monitor
```

### Available Commands
- `just` - Show all available commands
- `just compile` - Compile without uploading
- `just list-boards` - Find your board's port
- `just board-info` - Show ESP32-S3 board details

The `justfile` includes all working settings (115200 baud, OPI PSRAM) discovered during setup.

## Next Steps
- Could implement SD card storage
- Could add continuous capture mode
- Could create better web interface with controls
- Could implement different image formats/resolutions