# app/services/stt_service.py

# app/services/stt_service.py

from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator
import logging
from datetime import datetime
import wave
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import soundfile as sf
import numpy as np
from pydub import AudioSegment
import json
from google.cloud import speech_v1
from google.cloud.speech_v1 import SpeechClient
from google.cloud import storage


logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        """Initialize the Speech-to-Text service"""
        try:
            self.client = SpeechClient()
            self.temp_dir = Path(tempfile.gettempdir()) / "beaver_stt"
            self.temp_dir.mkdir(exist_ok=True)
            
            # Supported languages
            self.supported_languages = {
                "en-US": "English (United States)",
                "en-GB": "English (United Kingdom)",
                "en-AU": "English (Australia)",
                "en-CA": "English (Canada)"
            }
            
            # Speech recognition configs
            self.recognition_configs = {
                "default": speech_v1.RecognitionConfig(
                    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code="en-US",
                    enable_automatic_punctuation=True,
                    model="latest_long",
                ),
                "enhanced": speech_v1.RecognitionConfig(
                    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code="en-US",
                    enable_automatic_punctuation=True,
                    model="latest_long",
                    use_enhanced=True,
                    enable_speaker_diarization=True,
                    diarization_speaker_count=2,
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize STT service: {str(e)}")
            raise

    async def transcribe_audio(self,
                             audio_file_path: str,
                             language_code: str = "en-US",
                             enhanced: bool = False) -> Tuple[bool, Optional[Dict]]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to the audio file
            language_code: Language code for transcription
            enhanced: Whether to use enhanced recognition
            
        Returns:
            Tuple of (success_status, transcription_result)
        """
        try:
            # Prepare audio file
            audio_file = Path(audio_file_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            # Convert audio to proper format if needed
            processed_audio_path = await self._prepare_audio_file(audio_file_path)
            
            # Read the audio file
            with io.open(processed_audio_path, "rb") as audio_file:
                content = audio_file.read()
            
            # Create audio object
            audio = speech_v1.RecognitionAudio(content=content)
            
            # Get recognition config
            config = self.recognition_configs["enhanced" if enhanced else "default"]
            config.language_code = language_code
            
            # Perform transcription
            operation = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.long_running_recognize,
                config,
                audio
            )
            
            response = operation.result()
            
            # Process results
            transcription = {
                "text": "",
                "confidence": 0.0,
                "words": [],
                "speakers": [] if enhanced else None
            }
            
            for result in response.results:
                transcription["text"] += result.alternatives[0].transcript + " "
                transcription["confidence"] = max(
                    transcription["confidence"],
                    result.alternatives[0].confidence
                )
                
                # Add word-level information
                for word_info in result.alternatives[0].words:
                    transcription["words"].append({
                        "word": word_info.word,
                        "start_time": word_info.start_time.total_seconds(),
                        "end_time": word_info.end_time.total_seconds(),
                        "confidence": result.alternatives[0].confidence
                    })
                
                # Add speaker diarization if enabled
                if enhanced and result.speaker_tags:
                    current_speaker = None
                    current_text = ""
                    
                    for word_info in result.alternatives[0].words:
                        if word_info.speaker_tag != current_speaker:
                            if current_speaker is not None:
                                transcription["speakers"].append({
                                    "speaker": f"Speaker {current_speaker}",
                                    "text": current_text.strip()
                                })
                            current_speaker = word_info.speaker_tag
                            current_text = word_info.word + " "
                        else:
                            current_text += word_info.word + " "
                    
                    if current_speaker is not None:
                        transcription["speakers"].append({
                            "speaker": f"Speaker {current_speaker}",
                            "text": current_text.strip()
                        })
            
            # Cleanup temporary files
            if processed_audio_path != audio_file_path:
                os.remove(processed_audio_path)
            
            return True, transcription

        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}")
            return False, None

    async def _prepare_audio_file(self, file_path: str) -> str:
        """Prepare audio file for transcription"""
        try:
            # Check file format
            audio = AudioSegment.from_file(file_path)
            
            # Convert to proper format if needed
            if audio.frame_rate != 16000 or audio.channels != 1:
                # Convert to 16kHz mono
                audio = audio.set_frame_rate(16000).set_channels(1)
                
                # Save to temporary file
                output_path = str(self.temp_dir / f"processed_{Path(file_path).name}")
                audio.export(output_path, format="wav")
                return output_path
            
            return file_path

        except Exception as e:
            logger.error(f"Failed to prepare audio file: {str(e)}")
            raise

    async def transcribe_stream(self,
                              audio_stream,
                              language_code: str = "en-US") -> AsyncGenerator[str, None]:
        """
        Transcribe audio stream in real-time
        
        Args:
            audio_stream: Audio stream to transcribe
            language_code: Language code for transcription
            
        Yields:
            Transcribed text segments
        """
        try:
            # Create streaming config
            streaming_config = speech_v1.StreamingRecognitionConfig(
                config=speech_v1.RecognitionConfig(
                    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code=language_code,
                    enable_automatic_punctuation=True,
                ),
                interim_results=True
            )
            
            # Create streaming request generator
            def request_generator():
                yield speech_v1.StreamingRecognizeRequest(
                    streaming_config=streaming_config
                )
                
                for content in audio_stream:
                    yield speech_v1.StreamingRecognizeRequest(audio_content=content)
            
            # Process streaming responses
            responses = self.client.streaming_recognize(request_generator())
            
            for response in responses:
                if not response.results:
                    continue
                
                result = response.results[0]
                if not result.alternatives:
                    continue
                
                transcript = result.alternatives[0].transcript
                
                if result.is_final:
                    yield {
                        "text": transcript,
                        "is_final": True,
                        "confidence": result.alternatives[0].confidence
                    }
                else:
                    yield {
                        "text": transcript,
                        "is_final": False,
                        "confidence": None
                    }

        except Exception as e:
            logger.error(f"Failed to transcribe stream: {str(e)}")
            yield {
                "text": "",
                "is_final": True,
                "confidence": 0.0,
                "error": str(e)
            }

    async def save_transcription(self,
                               transcription: Dict,
                               output_path: str) -> bool:
        """Save transcription to file"""
        try:
            with open(output_path, 'w') as f:
                json.dump(transcription, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save transcription: {str(e)}")
            return False

# Usage example
if __name__ == "__main__":
    async def test_stt():
        stt_service = STTService()
        
        # Test file transcription
        test_file = "path/to/test/audio.wav"
        if os.path.exists(test_file):
            success, transcription = await stt_service.transcribe_audio(
                test_file,
                enhanced=True
            )
            if success:
                print("Transcription:", json.dumps(transcription, indent=2))
                
                # Save transcription
                await stt_service.save_transcription(
                    transcription,
                    "transcription_result.json"
                )
        
        # Test streaming (requires audio stream implementation)
        async def audio_stream():
            # Simulate audio stream
            chunk_size = 1024
            with wave.open("path/to/test/audio.wav", 'rb') as wav_file:
                while True:
                    data = wav_file.readframes(chunk_size)
                    if not data:
                        break
                    yield data
        
        async for result in stt_service.transcribe_stream(audio_stream()):
            print("Streaming result:", result)

    asyncio.run(test_stt())