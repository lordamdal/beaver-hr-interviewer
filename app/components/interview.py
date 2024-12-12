# app/components/interview.py

import streamlit as st
import asyncio
import time
from typing import Dict, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path
import tempfile
import base64
from app.services.llm_service import LLMService, InterviewContext
from app.services.tts_service import TTSService
from app.services.stt_service import STTService
from app.services.twilio_service import TwilioService
from app.database.operations import InterviewOperations, UserOperations
from app.auth.authentication import require_auth
from app.utils.resume_parser import ResumeParser
import logging

logger = logging.getLogger(__name__)

class InterviewComponent:
    def __init__(self):
        """Initialize interview component"""
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.stt_service = STTService()
        self.twilio_service = TwilioService()
        self.interview_ops = InterviewOperations()
        self.user_ops = UserOperations()
        self.resume_parser = ResumeParser()

    @require_auth
    def render(self):
        """Render the interview interface"""
        st.title("Job Interview Session")

        # Initialize session state
        if 'interview_state' not in st.session_state:
            st.session_state.interview_state = {
                'started': False,
                'completed': False,
                'current_phase': 'introduction',
                'context': None,
                'call_sid': None,
                'recording_url': None
            }

        # Show interview setup if not started
        if not st.session_state.interview_state['started']:
            self._render_setup()
        elif not st.session_state.interview_state['completed']:
            self._render_interview()
        else:
            self._render_completion()

    def _render_setup(self):
        """Render interview setup interface"""
        st.markdown("""
        <style>
        .setup-container {
            background-color: #f8f9fa;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='setup-container'>", unsafe_allow_html=True)
            
            # Resume upload
            uploaded_file = st.file_uploader(
                "Upload your resume (PDF format)",
                type=['pdf'],
                key="resume_upload"
            )

            if uploaded_file:
                with st.spinner("Analyzing resume..."):
                    resume_data = self.resume_parser.parse(uploaded_file)
                    if resume_data:
                        st.success("Resume analyzed successfully!")
                        st.session_state.resume_data = resume_data

            # Job description
            job_description = st.text_area(
                "Job Description (Optional)",
                height=150,
                key="job_description"
            )

            # Company information
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input(
                    "Company Name (Optional)",
                    key="company_name"
                )
            with col2:
                company_website = st.text_input(
                    "Company Website (Optional)",
                    key="company_website"
                )

            # Interview preferences
            st.subheader("Interview Preferences")
            col1, col2 = st.columns(2)
            with col1:
                interview_mode = st.selectbox(
                    "Interview Mode",
                    ["Phone Call", "Video Call (Premium)"],
                    key="interview_mode"
                )
            with col2:
                interviewer_voice = st.selectbox(
                    "Interviewer Voice",
                    ["Male (US)", "Female (US)", "Male (UK)", "Female (UK)"],
                    key="interviewer_voice"
                )

            # Start interview button
            if st.button("Start Interview", type="primary"):
                if not uploaded_file:
                    st.error("Please upload your resume first.")
                    return

                # Initialize interview context
                context = InterviewContext(
                    resume_data=st.session_state.resume_data,
                    job_description=job_description,
                    company_info={
                        'name': company_name or "our company",
                        'website': company_website
                    }
                )

                # Start interview
                if interview_mode == "Phone Call":
                    self._start_phone_interview(context)
                else:
                    self._start_video_interview(context)

            st.markdown("</div>", unsafe_allow_html=True)

    async def _start_phone_interview(self, context: InterviewContext):
        """Start phone interview"""
        try:
            # Verify user has remaining interviews
            user = self.user_ops.get_user(st.session_state.user_id)
            if user['interviews_remaining'] <= 0:
                st.error("You have no remaining interviews. Please upgrade your plan.")
                return

            # Start Twilio call
            success, call_sid = await self.twilio_service.start_interview_call(
                user['phone'],
                f"{st.get_option('server.baseUrlPath')}/interview/webhook",
                user['id']
            )

            if success:
                st.session_state.interview_state.update({
                    'started': True,
                    'context': context,
                    'call_sid': call_sid
                })
                
                # Decrement remaining interviews
                self.user_ops.decrement_interviews(user['id'])
                
                st.success("Interview call initiated! Please answer your phone.")
            else:
                st.error("Failed to initiate interview call. Please try again.")

        except Exception as e:
            logger.error(f"Error starting phone interview: {str(e)}")
            st.error("An error occurred while starting the interview.")

    async def _start_video_interview(self, context: InterviewContext):
        """Start video interview"""
        st.warning("Video interviews are only available with a premium subscription.")
        # Video interview implementation will be added later

    def _render_interview(self):
        """Render ongoing interview interface"""
        context = st.session_state.interview_state['context']
        
        # Display interview progress
        progress = st.progress(0)
        status = st.empty()
        
        # Display current phase
        st.subheader(f"Current Phase: {context.current_phase.title()}")
        
        # Display conversation
        st.markdown("### Interview Conversation")
        conversation = st.container()
        
        # Update interview status
        async def update_status():
            while not st.session_state.interview_state['completed']:
                call_status = await self.twilio_service.get_call_status(
                    st.session_state.interview_state['call_sid']
                )
                
                if call_status:
                    status.text(f"Status: {call_status['status']}")
                    
                    if call_status['status'] == "completed":
                        st.session_state.interview_state['completed'] = True
                        break
                
                await asyncio.sleep(2)

        # Display conversation updates
        if context.history:
            with conversation:
                for i, message in enumerate(context.history):
                    if i % 2 == 0:
                        st.markdown(f"ðŸ¤– **Interviewer:** {message}")
                    else:
                        st.markdown(f"ðŸ‘¤ **You:** {message}")

    def _render_completion(self):
        """Render interview completion interface"""
        st.success("Interview Completed!")
        
        # Generate and display report
        if 'report' not in st.session_state:
            with st.spinner("Generating interview report..."):
                report = self.llm_service.generate_final_report(
                    st.session_state.interview_state['context']
                )
                st.session_state.report = report

        # Display report
        st.markdown("### Interview Report")
        
        # Overall score
        score = st.session_state.report['scores']['overall']
        st.metric("Overall Score", f"{score}/100")
        
        # Category scores
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Communication", 
                     f"{st.session_state.report['scores']['communication']}/100")
        with col2:
            st.metric("Technical", 
                     f"{st.session_state.report['scores']['technical']}/100")
        with col3:
            st.metric("Behavioral", 
                     f"{st.session_state.report['scores']['behavioral']}/100")

        # Detailed feedback
        st.markdown("### Detailed Feedback")
        st.markdown(st.session_state.report['feedback'])
        
        # Recording (Premium feature)
        if st.session_state.interview_state['recording_url']:
            st.markdown("### Interview Recording")
            st.audio(st.session_state.interview_state['recording_url'])
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download Report"):
                self._download_report()
        with col2:
            if st.button("Start New Interview"):
                self._reset_interview()

    def _download_report(self):
        """Generate and download interview report"""
        try:
            report_data = {
                "interview_data": st.session_state.interview_state['context'].__dict__,
                "report": st.session_state.report,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Convert to JSON
            report_json = json.dumps(report_data, indent=2)
            
            # Create download link
            b64 = base64.b64encode(report_json.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="interview_report.json">Download Report</a>'
            st.markdown(href, unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Error downloading report: {str(e)}")
            st.error("Failed to download report.")

    def _reset_interview(self):
        """Reset interview state for a new session"""
        st.session_state.interview_state = {
            'started': False,
            'completed': False,
            'current_phase': 'introduction',
            'context': None,
            'call_sid': None,
            'recording_url': None
        }
        if 'report' in st.session_state:
            del st.session_state.report
        st.experimental_rerun()

# Initialize component
interview_component = InterviewComponent()

if __name__ == "__main__":
    interview_component.render()