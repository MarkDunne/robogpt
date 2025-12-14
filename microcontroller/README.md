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
  - Reduced frame size to FRAMESIZE_QQVGA (160x120)
  - Increased JPEG compression (quality 20)
  - Implemented chunked transfer (1KB chunks)
  - Added keep-alive HTTP header

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

## Working WiFi AP Configuration
- **Network Name**: ESP32-CAM
- **Password**: 12345678
- **Access URL**: http://192.168.4.1
- **Mode**: Access Point (no internet needed)

### Why 192.168.4.1?
- ESP32 automatically assigns itself this IP when in AP mode (hardcoded default)
- Part of ESP-IDF WiFi stack defaults
- Uses 192.168.4.x subnet to avoid conflicts with common home routers (192.168.1.x/192.168.0.x)
- DHCP server assigns clients: 192.168.4.2, 192.168.4.3, etc.
- Can be changed with `WiFi.softAPConfig()` if needed

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