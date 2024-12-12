# app/services/tts_service.py

import asyncio
import edge_tts
import logging
import tempfile
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import json
import aiofiles
from pathlib import Path
import soundfile as sf
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        """Initialize the TTS service"""
        self.default_voice = "en-US-ChristopherNeural"
        self.voices_cache = {}
        self.temp_dir = Path(tempfile.gettempdir()) / "beaver_tts"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Voice configurations
        self.voice_configs = {
            "default": {
                "male": "en-US-ChristopherNeural",
                "female": "en-US-JennyNeural"
            },
            "british": {
                "male": "en-GB-RyanNeural",
                "female": "en-GB-SoniaNeural"
            },
            "australian": {
                "male": "en-AU-WilliamNeural",
                "female": "en-AU-NatashaNeural"
            }
        }
        
        # Voice styles
        self.voice_styles = {
            "professional": {
                "rate": "+0%",
                "volume": "+0%",
                "pitch": "+0Hz"
            },
            "friendly": {
                "rate": "-5%",
                "volume": "+10%",
                "pitch": "+10Hz"
            },
            "formal": {
                "rate": "+5%",
                "volume": "-5%",
                "pitch": "-10Hz"
            }
        }

    async def load_available_voices(self) -> List[Dict]:
        """Load and cache available voices"""
        try:
            if not self.voices_cache:
                voices = await edge_tts.list_voices()
                self.voices_cache = {
                    voice["ShortName"]: voice
                    for voice in voices
                }
            return list(self.voices_cache.values())
        except Exception as e:
            logger.error(f"Failed to load voices: {str(e)}")
            return []

    def _get_voice_by_preference(self, 
                               accent: str = "default", 
                               gender: str = "male") -> str:
        """Get voice based on preferences"""
        try:
            return self.voice_configs.get(accent, self.voice_configs["default"]).get(
                gender, self.voice_configs["default"]["male"]
            )
        except Exception as e:
            logger.error(f"Error getting voice preference: {str(e)}")
            return self.default_voice

    async def text_to_speech(self,
                           text: str,
                           voice_name: Optional[str] = None,
                           style: str = "professional",
                           output_format: str = "wav") -> Tuple[bool, Optional[str]]:
        """
        Convert text to speech and return the path to the audio file
        
        Args:
            text: Text to convert to speech
            voice_name: Name of the voice to use
            style: Style of speech (professional, friendly, formal)
            output_format: Output audio format (wav, mp3)
            
        Returns:
            Tuple of (success_status, file_path)
        """
        try:
            # Use default voice if none specified
            voice_name = voice_name or self.default_voice
            
            # Get style configuration
            style_config = self.voice_styles.get(style, self.voice_styles["professional"])
            
            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_{timestamp}_{voice_name}.{output_format}"
            output_path = self.temp_dir / filename

            # Create communicate instance
            communicate = edge_tts.Communicate(
                text,
                voice_name,
                rate=style_config["rate"],
                volume=style_config["volume"],
                pitch=style_config["pitch"]
            )

            # Generate speech
            await communicate.save(str(output_path))

            if output_format != "wav":
                # Convert to desired format if needed
                wav_path = output_path.with_suffix(".wav")
                await self._convert_format(str(wav_path), str(output_path))
                os.remove(wav_path)

            logger.info(f"Successfully generated speech: {output_path}")
            return True, str(output_path)

        except Exception as e:
            logger.error(f"Failed to generate speech: {str(e)}")
            return False, None

    async def _convert_format(self, input_path: str, output_path: str):
        """Convert audio format using soundfile"""
        try:
            data, samplerate = sf.read(input_path)
            sf.write(output_path, data, samplerate)
        except Exception as e:
            logger.error(f"Failed to convert audio format: {str(e)}")
            raise

    async def generate_interview_voice(self,
                                     text: str,
                                     context: Dict) -> Tuple[bool, Optional[str]]:
        """
        Generate interview voice based on context
        
        Args:
            text: Text to convert to speech
            context: Interview context containing voice preferences
            
        Returns:
            Tuple of (success_status, file_path)
        """
        try:
            # Get voice preferences from context
            accent = context.get("accent", "default")
            gender = context.get("gender", "male")
            style = context.get("style", "professional")
            
            # Get appropriate voice
            voice_name = self._get_voice_by_preference(accent, gender)
            
            # Generate speech
            success, file_path = await self.text_to_speech(
                text,
                voice_name=voice_name,
                style=style
            )
            
            return success, file_path

        except Exception as e:
            logger.error(f"Failed to generate interview voice: {str(e)}")
            return False, None

    async def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old temporary files"""
        try:
            current_time = datetime.now()
            for file_path in self.temp_dir.glob("tts_*"):
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() > (max_age_hours * 3600):
                    os.remove(file_path)
                    logger.info(f"Cleaned up old file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {str(e)}")

    async def concatenate_audio_files(self, 
                                    file_paths: List[str], 
                                    output_path: str) -> bool:
        """Concatenate multiple audio files"""
        try:
            # Read all audio files
            audio_data = []
            sample_rate = None
            
            for file_path in file_paths:
                data, rate = sf.read(file_path)
                if sample_rate is None:
                    sample_rate = rate
                elif rate != sample_rate:
                    # Resample if needed
                    data = self._resample_audio(data, rate, sample_rate)
                audio_data.append(data)

            # Concatenate audio data
            concatenated = np.concatenate(audio_data)
            
            # Write concatenated audio
            sf.write(output_path, concatenated, sample_rate)
            
            return True
        except Exception as e:
            logger.error(f"Failed to concatenate audio files: {str(e)}")
            return False

    def _resample_audio(self, data: np.ndarray, 
                       src_rate: int, 
                       dst_rate: int) -> np.ndarray:
        """Resample audio data to match target sample rate"""
        try:
            from scipy import signal
            return signal.resample(data, 
                                 int(len(data) * dst_rate / src_rate))
        except Exception as e:
            logger.error(f"Failed to resample audio: {str(e)}")
            raise

# Usage example
if __name__ == "__main__":
    async def test_tts():
        tts_service = TTSService()
        
        # Test basic TTS
        success, file_path = await tts_service.text_to_speech(
            "Hello, this is a test of the text-to-speech service.",
            style="friendly"
        )
        print(f"Generated audio file: {file_path}")
        
        # Test interview voice generation
        context = {
            "accent": "british",
            "gender": "female",
            "style": "professional"
        }
        
        success, file_path = await tts_service.generate_interview_voice(
            "Tell me about your experience with Python programming.",
            context
        )
        print(f"Generated interview voice: {file_path}")
        
        # Clean up old files
        await tts_service.cleanup_old_files(max_age_hours=1)

    asyncio.run(test_tts())