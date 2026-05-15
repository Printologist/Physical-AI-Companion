"""
Voice assistant using OpenAI Whisper, GPT-4o, and OpenAI TTS.
With camera vision support via Viam and NeoPixel volume display.

Requires: pip install viam-sdk openai pyserial --break-system-packages
"""

import asyncio
import os
import wave
import base64
import serial
import math
from io import BytesIO

from viam.robot.client import RobotClient
from viam.components.audio_in import AudioIn, AudioCodec
from viam.components.audio_out import AudioOut, AudioInfo
from viam.components.camera import Camera
from viam.media.video import CameraMimeType
from openai import OpenAI


SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200


def get_serial():
    """Try to open serial connection to CircuitPython board."""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to NeoPixels on {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"Could not connect to NeoPixels: {e}")
        return None


def send_volume(ser, volume: float):
    """Send volume value (0.0 to 1.0) over serial."""
    if ser:
        try:
            ser.write(f"v:{volume:.2f}\n".encode())
        except Exception:
            pass


def estimate_mp3_volume(mp3_data: bytes) -> float:
    """Estimate relative volume/energy from MP3 bytes."""
    step = max(1, len(mp3_data) // 500)
    samples = [mp3_data[i] for i in range(0, len(mp3_data), step)]
    if not samples:
        return 0.0
    mean = sum(samples) / len(samples)
    variance = sum((s - mean) ** 2 for s in samples) / len(samples)
    normalized = min(math.sqrt(variance) / 50.0, 1.0)
    return normalized


async def animate_leds(ser, volume: float, duration: float):
    """Send volume to LEDs, then fade out over duration."""
    send_volume(ser, volume)
    await asyncio.sleep(duration * 0.8)
    # Fade out
    steps = 10
    for i in range(steps):
        faded = volume * (1 - i / steps)
        send_volume(ser, faded)
        await asyncio.sleep(0.05)
    send_volume(ser, 0.0)


class OpenAIVoiceAssistant:
    """Voice assistant powered by OpenAI services with camera vision."""

    def __init__(
        self,
        robot: RobotClient,
        filter_name: str = "wake-word",
        audioout_name: str = "speaker",
        camera_name: str = "camera",
        ser=None,
    ):
        self.robot = robot
        self.filter_name = filter_name
        self.audioout_name = audioout_name
        self.camera_name = camera_name
        self.filter = None
        self.audioout = None
        self.camera = None
        self.ser = ser

        self.client = OpenAI(api_key='YOUR_OPENAI_KEY_HERE')
        self.system_prompt = (
            "You are a helpful voice assistant on a robot. "
            "Keep responses concise and conversational."
        )
        self.chat_history = []

        # Keywords that trigger a camera capture
        self.vision_keywords = [
            "see", "look", "what is", "what's", "describe",
            "in front", "around", "camera", "show", "watch"
        ]

    async def start(self):
        self.filter = AudioIn.from_robot(self.robot, self.filter_name)
        self.audioout = AudioOut.from_robot(self.robot, self.audioout_name)
        self.camera = Camera.from_robot(self.robot, self.camera_name)
        print(f"Connected to wake-word filter: {self.filter_name}")
        print(f"Connected to speaker: {self.audioout_name}")
        print(f"Connected to camera: {self.camera_name}")

    def is_vision_request(self, text: str) -> bool:
        """Check if the user is asking about what the robot sees."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.vision_keywords)

    async def get_camera_image(self) -> str | None:
        """Capture a frame from the camera and return as base64."""
        try:
            result = await self.camera.get_images()
            named_images = result[0]
            image = named_images[0]
            image_bytes = image.data
            print(f"Image captured, size: {len(image_bytes)} bytes")
            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def speech_to_text(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Convert audio to text using Whisper."""
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
        response = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_buffer,
        )
        return response.text

    async def get_response(self, user_text: str) -> str:
        """Generate response using GPT-4o, with vision if needed."""
        if not user_text:
            return "I didn't catch that."

        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.chat_history)

            if self.is_vision_request(user_text):
                print("Vision request detected, capturing image...")
                image_b64 = await self.get_camera_image()

                if image_b64:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": user_text
                            }
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": user_text})
            else:
                messages.append({"role": "user", "content": user_text})

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )

            assistant_message = response.choices[0].message.content

            self.chat_history.append({"role": "user", "content": user_text})
            self.chat_history.append({"role": "assistant", "content": assistant_message})

            return assistant_message
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return "Sorry, I had trouble processing that."

    async def speak(self, text: str):
        """Text to speech using OpenAI TTS, with LED volume animation."""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            mp3_data = response.content

            # Estimate volume and duration
            volume = estimate_mp3_volume(mp3_data)
            words = len(text.split())
            estimated_duration = words / 2.5  # ~2.5 words per second

            print(f"Estimated volume: {volume:.2f}, duration: {estimated_duration:.1f}s")

            # Play audio and animate LEDs concurrently
            audio_info = AudioInfo(codec=AudioCodec.MP3)
            await asyncio.gather(
                self.audioout.play(mp3_data, audio_info),
                animate_leds(self.ser, volume, estimated_duration)
            )
        except Exception as e:
            print(f"Error in text to speech: {e}")

    async def run(self):
        """Continuously listen and respond."""
        print("Listening for wake word 'robot'...")

        while True:
            try:
                audio_stream = await self.filter.get_audio("pcm16", 0, 0)
            except Exception as e:
                print(f"Error starting audio stream: {e}, retrying...")
                await asyncio.sleep(1)
                continue

            try:
                segment = bytearray()

                async for chunk in audio_stream:
                    audio_data = chunk.audio.audio_data

                    if len(audio_data) == 0:
                        if segment:
                            print(f"\nWake word detected! Processing {len(segment)} bytes...")
                            try:
                                user_text = self.speech_to_text(bytes(segment))
                                if user_text:
                                    print(f"You: {user_text}")
                                    response_text = await self.get_response(user_text)
                                    print(f"Bot: {response_text}")
                                    await self.speak(response_text)
                                else:
                                    print("No speech recognized")
                            except Exception as e:
                                print(f"Error processing speech: {e}")

                            segment.clear()
                            print("Listening for next wake word...\n")
                    else:
                        segment.extend(audio_data)

            except KeyboardInterrupt:
                print("\n\nStopping...")
                return
            except Exception as e:
                print(f"Stream disconnected: {e}, reconnecting...")
                await asyncio.sleep(1)
                continue


async def main():
    ser = get_serial()

    opts = RobotClient.Options.with_api_key(
        api_key='',
        api_key_id=''
    )
    robot = await RobotClient.at_address('', opts)

    try:
        assistant = OpenAIVoiceAssistant(robot, "wake-word", "speaker", "camera", ser)
        await assistant.start()
        await assistant.run()
    finally:
        await robot.close()
        if ser:
            ser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user")
