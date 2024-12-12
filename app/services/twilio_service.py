# app/services/twilio_service.py

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import VoiceResponse, Gather
import logging
from typing import Dict, Optional, List, Tuple
import asyncio
from datetime import datetime
import json
from pathlib import Path
import tempfile
from app.config.settings import settings
from urllib.parse import urljoin
import base64

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        """Initialize Twilio service"""
        try:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID.get_secret_value(),
                settings.TWILIO_AUTH_TOKEN.get_secret_value()
            )
            self.phone_number = settings.TWILIO_PHONE_NUMBER
            self.temp_dir = Path(tempfile.gettempdir()) / "beaver_calls"
            self.temp_dir.mkdir(exist_ok=True)
            
            # Call status mapping
            self.call_status = {
                "queued": "Waiting to start",
                "ringing": "Calling candidate",
                "in-progress": "Interview in progress",
                "completed": "Interview completed",
                "failed": "Call failed",
                "busy": "Candidate busy",
                "no-answer": "No answer",
                "canceled": "Interview canceled"
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize Twilio service: {str(e)}")
            raise

    async def start_interview_call(self,
                                 to_number: str,
                                 callback_url: str,
                                 user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Start an interview call
        
        Args:
            to_number: Candidate's phone number
            callback_url: Webhook URL for call events
            user_id: User ID for tracking
            
        Returns:
            Tuple of (success_status, call_sid)
        """
        try:
            # Validate phone number
            if not self._validate_phone_number(to_number):
                raise ValueError("Invalid phone number format")

            # Start call
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=callback_url,
                status_callback=urljoin(callback_url, "status"),
                status_callback_event=[
                    "initiated", "ringing", "answered", "completed"
                ],
                record=True,
                recording_status_callback=urljoin(callback_url, "recording"),
                timeout=30
            )
            
            logger.info(f"Started interview call: {call.sid}")
            return True, call.sid

        except TwilioRestException as e:
            logger.error(f"Twilio error starting call: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Error starting call: {str(e)}")
            return False, None

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        import re
        pattern = r'^\+?1?\d{10,15}$'
        return bool(re.match(pattern, phone_number))

    def generate_interview_twiml(self,
                               message: str,
                               gather_input: bool = True,
                               timeout: int = 5) -> str:
        """Generate TwiML for interview interaction"""
        response = VoiceResponse()
        
        # Add initial message
        response.say(message, voice='alice')
        
        if gather_input:
            # Gather spoken input
            gather = Gather(
                input='speech',
                timeout=timeout,
                language='en-US',
                enhanced=True,
                speech_timeout='auto'
            )
            response.append(gather)
        
        return str(response)

    async def end_call(self, call_sid: str) -> bool:
        """End an active call"""
        try:
            call = self.client.calls(call_sid).update(status='completed')
            logger.info(f"Ended call: {call_sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to end call: {str(e)}")
            return False

    async def get_call_status(self, call_sid: str) -> Optional[Dict]:
        """Get current call status and details"""
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'status': self.call_status.get(call.status, call.status),
                'duration': call.duration,
                'start_time': call.start_time,
                'end_time': call.end_time,
                'price': call.price,
                'direction': call.direction
            }
        except Exception as e:
            logger.error(f"Failed to get call status: {str(e)}")
            return None

    async def get_recording_url(self, call_sid: str) -> Optional[str]:
        """Get recording URL for a completed call"""
        try:
            recordings = self.client.recordings.list(call_sid=call_sid)
            if recordings:
                recording = recordings[0]
                return f"https://api.twilio.com{recording.uri}.mp3"
            return None
        except Exception as e:
            logger.error(f"Failed to get recording URL: {str(e)}")
            return None

    async def download_recording(self,
                               recording_url: str,
                               output_path: str) -> bool:
        """Download call recording"""
        try:
            import requests
            
            # Add authentication to URL
            auth = base64.b64encode(
                f"{settings.TWILIO_ACCOUNT_SID.get_secret_value()}:"
                f"{settings.TWILIO_AUTH_TOKEN.get_secret_value()}".encode()
            ).decode()
            
            headers = {'Authorization': f'Basic {auth}'}
            
            # Download recording
            response = requests.get(recording_url, headers=headers)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            return True
        except Exception as e:
            logger.error(f"Failed to download recording: {str(e)}")
            return False

    async def handle_webhook(self, data: Dict) -> Dict:
        """Handle Twilio webhook events"""
        try:
            event_type = data.get('EventType')
            call_sid = data.get('CallSid')
            
            response = {
                'success': True,
                'call_sid': call_sid,
                'event': event_type
            }
            
            if event_type == 'completed':
                # Handle call completion
                recording_url = await self.get_recording_url(call_sid)
                if recording_url:
                    response['recording_url'] = recording_url
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def monitor_call_quality(self, call_sid: str) -> Dict:
        """Monitor call quality metrics"""
        try:
            # Get call quality metrics
            metrics = self.client.calls(call_sid).feedback.create(
                quality_score=None,
                issue=['audio-latency', 'choppy-audio', 'dropped-call']
            )
            
            return {
                'quality_score': metrics.quality_score,
                'issues': metrics.issues
            }
        except Exception as e:
            logger.error(f"Failed to monitor call quality: {str(e)}")
            return {}

    def create_conference_call(self,
                             participants: List[str],
                             moderator_number: str) -> Tuple[bool, Optional[str]]:
        """Create a conference call for multiple participants"""
        try:
            # Create conference room
            room_name = f"interview_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Add moderator
            moderator_call = self.client.calls.create(
                to=moderator_number,
                from_=self.phone_number,
                twiml=self._generate_conference_twiml(room_name, is_moderator=True)
            )
            
            # Add participants
            for participant in participants:
                self.client.calls.create(
                    to=participant,
                    from_=self.phone_number,
                    twiml=self._generate_conference_twiml(room_name)
                )
            
            return True, moderator_call.sid
            
        except Exception as e:
            logger.error(f"Failed to create conference call: {str(e)}")
            return False, None

    def _generate_conference_twiml(self,
                                 room_name: str,
                                 is_moderator: bool = False) -> str:
        """Generate TwiML for conference calls"""
        response = VoiceResponse()
        dial = response.dial()
        
        conference = dial.conference(
            room_name,
            start_conference_on_enter=is_moderator,
            end_conference_on_exit=is_moderator,
            record='record-from-start',
            recording_status_callback='/recording/callback'
        )
        
        return str(response)

# Usage example
if __name__ == "__main__":
    async def test_twilio():
        twilio_service = TwilioService()
        
        # Test starting a call
        success, call_sid = await twilio_service.start_interview_call(
            "+1234567890",
            "https://your-webhook-url.com/callback",
            "test_user_id"
        )
        
        if success:
            print(f"Started call: {call_sid}")
            
            # Monitor call status
            status = await twilio_service.get_call_status(call_sid)
            print(f"Call status: {status}")
            
            # Generate TwiML
            twiml = twilio_service.generate_interview_twiml(
                "Welcome to your interview. Please introduce yourself.",
                gather_input=True
            )
            print(f"Generated TwiML: {twiml}")
            
            # End call after delay
            await asyncio.sleep(60)
            await twilio_service.end_call(call_sid)
            
            # Get recording URL
            recording_url = await twilio_service.get_recording_url(call_sid)
            if recording_url:
                print(f"Recording URL: {recording_url}")
                
                # Download recording
                await twilio_service.download_recording(
                    recording_url,
                    "interview_recording.mp3"
                )

    asyncio.run(test_twilio())