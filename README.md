# Scuttle AI Voice Assistant Robot

Build kit:
👉 https://ScuttleRobot.org (Checkout Code: AVIVMAKES for 10% off!)



---

## 🛠️ Hardware you need, not in the official build kit

| Component | Link |
|---|---|
(As an Amazon Associate, I earn from qualifying purchases #ad)
| Raspberry Pi HQ Camera (M12 / CSI) | https://amzn.to/44OXX8I |
| AirHug USB Speaker & Microphone | https://amzn.to/4f1tLMm |
| MPU-6050 6-DoF Accelerometer/Gyro IMU | https://amzn.to/4gvAznX |
| Anker 87W 20,000mAh Power Bank | https://amzn.to/4eILc5D |
| Adafruit Qualia ESP32-S3 (round display) | (see Adafruit) |
| 16x NeoPixel strip | (see Adafruit) |
| RPLidar (any model) | |
3030 Vertical Extrusion |https://amzn.to/44utr41|
HDMI to CSI Camera Adapter Board |https://amzn.to/44Mue09|
SO-101 Robotic Arm Kit |https://amzn.to/3QWlG3v|
Upgraded Servos (optional) |https://amzn.to/4eG8hpt|

---

## 📁 Files

| File | Location | Description |
|---|---|---|
| `main.py` | `/home/username/AI-ASSIST/main.py` | Main voice assistant code (runs on Pi) |
| `code.py` | Qualia CIRCUITPY drive | CircuitPython code for the round display and NeoPixels |
| `smooth_base/` | `/home/username/smooth_base/` | Custom Viam module for smooth motor ramping |
| `eyes_viam.py` | `/home/username/AI-ASSIST/eyes_viam.py` | Local Viam module — sends face tracking gaze coordinates over serial to the Qualia display |

---

## ⚙️ Raspberry Pi Setup

### 1. Install Viam Agent
Go to [app.viam.com](https://app.viam.com), create a free account, add a new machine, and follow the on-screen install instructions. It will give you a one-line install command to run on the Pi.

### 2. Enable I2C (for encoders and IMU)
```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

### 3. Install Python dependencies
```bash
pip install viam-sdk openai pyserial pydub numpy --break-system-packages
sudo apt install ffmpeg -y
```

### 4. Fix LIDAR permissions (run on every boot, or add to /etc/rc.local)
```bash
sudo chmod 666 /dev/ttyUSB0
```

### 5. Fill in credentials in main.py
Open `/home/username/AI-ASSIST/main.py` and fill in:
- **Line ~100**: Your OpenAI API key — get one at https://platform.openai.com/api-keys
- **Bottom of file**: Your Viam API key, API key ID, and robot address — found in the Connect tab on app.viam.com

---

## 🤖 Viam Configuration

Log into [app.viam.com](https://app.viam.com) and configure the following components on your machine:

### Components

| Name | Type | Model |
|---|---|---|
| `filter` | audio_in | `viam:system-audio:microphone` |
| `wake-word` | audio_in | `viam:filtered-audio:wake-word-filter` |
| `speaker` | audio_out | `viam:system-audio:speaker` |
| `camera` | camera | `viam:camera:csi-pi` |
| `Lidar` | camera | `viam:lidar:rplidar` |
| `base` | base | `rdk:builtin:wheeled` |
| `board-1` | board | `viam:raspberry-pi:rpi5` |
| `Left` | encoder | `viam:ams:as5048` |
| `Right` | encoder | `viam:ams:as5048` |
| `Left-Motor` | motor | `rdk:builtin:gpio` |
| `Right-Motor` | motor | `rdk:builtin:gpio` |
| `imu` | movement_sensor | `viam:tdk-invensense:mpu6050` |

### Services

| Name | Type | Model |
|---|---|---|
| `vision-1` | vision | `rdk:builtin:mlmodel` |
| `mlmodel-1` | mlmodel | `viam:mlmodel-tflite:tflite_cpu` |
| `slam-1` | slam | `viam:slam:cartographer` |
| `data_manager-1` | data_manager | `rdk:builtin:builtin` |

### Key attribute settings
- `wake-word` attributes: `{ "source_microphone": "filter", "wake_words": ["robot"] }`
- `filter` attributes: `{ "num_channels": 1, "sample_rate": 16000 }`
- `Lidar` attributes: `{ "serial_path": "/dev/ttyUSB0" }`
- `imu` attributes: `{ "i2c_bus": "1" }`

---

## 🎭 CircuitPython Setup (Qualia ESP32-S3)

1. Flash **CircuitPython 10.2.0** for the Qualia ESP32-S3 from [circuitpython.org](https://circuitpython.org)
2. Install required Adafruit libraries onto the CIRCUITPY drive:
   - `adafruit_qualia`
   - `neopixel`
   - `vectorio`
   - `displayio`
3. Copy `code.py` to the root of the CIRCUITPY drive
4. The NeoPixel strip connects to pin **A0** on the Qualia board (16 LEDs)
5. The Qualia connects to the Pi via USB and appears as `/dev/ttyACM0`

---

## 🚀 Running the Assistant

```bash
python3 /home/username/AI-ASSIST/main.py
```

Make sure Thonny is **closed** before running, otherwise it will block the serial connection to the Qualia board.

---

## 🗣️ Voice Commands

Say **"robot"** to wake the assistant, then speak your command:

| Command | Action |
|---|---|
| "move forward" | Moves forward 500mm |
| "move backward" | Moves backward 500mm |
| "turn left" | Turns left 45 degrees |
| "turn right" | Turns right 45 degrees |
| "stop" | Stops all movement |
| "dance" | Performs a square dance routine |
| "follow me" | Starts person-following mode using camera |
| "stop following" | Stops person-following mode |
| "get out of the way" | Moves aside |
| "what do you see?" | Captures camera image and describes it |
| "how far is the wall?" | Reads LIDAR distance |
| Anything else | General conversation via GPT-4o |

---

## 🔑 Credentials Needed

- **OpenAI API key** — https://platform.openai.com/api-keys
- **Viam API key** — app.viam.com → your machine → Connect tab
- **Viam API key ID** — same location
- **Viam robot address** — same location

---

## 🧩 Smooth Base Module

The `smooth_base` custom Viam module adds acceleration ramping to movement commands so the robot doesn't jerk when starting or stopping. It wraps the standard `base` component.

To install it, copy the `smooth_base/` folder to `/home/username/smooth_base/` and make sure `run.sh` is executable:

```bash
chmod +x /home/username/smooth_base/run.sh
```

Then add it as a local module in your Viam config pointing to `/home/username/smooth_base/run.sh`.

---

## 🛟 Recovery (if SD card fails)

If your Pi SD card dies, you need to restore:
1. Re-flash Pi OS and reinstall viam-agent (your Viam config is safe in the cloud)
2. Reinstall Python dependencies (see step 3 above)
3. Restore these files from backup:
   - `main.py`
   - `smooth_base/` folder
   - `eyes_viam.py`
4. Re-enter your credentials in `main.py`
5. `code.py` is safe — it lives on the Qualia's own flash memory

---

## 📺 YouTube

Follow the build process on YouTube: [youtube.com/c/avivmakesrobots]
