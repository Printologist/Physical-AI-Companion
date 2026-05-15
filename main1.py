"""
Voice assistant using OpenAI Whisper, GPT-4o, and OpenAI TTS.
With camera vision support via Viam.

Requires: pip install viam-sdk openai
"""

import asyncio
import os
import wave
import base64
from io import BytesIO

from viam.robot.client import RobotClient
from viam.components.audio_in import AudioIn, AudioCodec
from viam.components.audio_out import AudioOut, AudioInfo
from viam.components.camera import Camera
from viam.media.video import CameraMimeType
from openai import OpenAI


class OpenAIVoiceAssistant:
    """Voice assistant powered by OpenAI services with camera vision."""

    def __init__(
        self,
        robot: RobotClient,
        filter_name: str = "wake-word",
        audioout_name: str = "speaker",
        camera_name: str = "camera",
    ):
        self.robot = robot
        self.filter_name = filter_name
        self.audioout_name = audioout_name
        self.camera_name = camera_name
        self.filter = None
        self.audioout = None
        self.camera = None

        self.client = OpenAI(api_key='Paste a key here')
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
        try:
            result = await self.camera.get_images()
            named_images = result[0]
            image = named_images[0]
            print(f"image type: {type(image)}")
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

            # If vision request, capture image and send to GPT-4o
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

            # Update chat history (text only)
            self.chat_history.append({"role": "user", "content": user_text})
            self.chat_history.append({"role": "assistant", "content": assistant_message})

            return assistant_message
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return "Sorry, I had trouble processing that."

    async def speak(self, text: str):
        """Text to speech using OpenAI TTS."""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            mp3_data = response.content
            audio_info = AudioInfo(codec=AudioCodec.MP3)
            await self.audioout.play(mp3_data, audio_info)
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
    opts = RobotClient.Options.with_api_key(
        api_key='api key here',
        api_key_id='key id here'
    )
    robot = await RobotClient.at_address('scumain.whatever here', opts)

    try:
        assistant = OpenAIVoiceAssistant(robot, "wake-word", "speaker", "camera")
        await assistant.start()
        await assistant.run()
    finally:
        await robot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user")