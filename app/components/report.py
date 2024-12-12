# app/components/report.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
import json
import base64
from pathlib import Path
import tempfile
from app.database.operations import InterviewOperations
from app.auth.authentication import require_auth
import logging
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

class ReportComponent:
    def __init__(self):
        """Initialize report component"""
        self.interview_ops = InterviewOperations()
        self.storage_service = StorageService()
        self.color_scheme = {
            'primary': '#3498db',
            'secondary': '#2ecc71',
            'warning': '#f1c40f',
            'danger': '#e74c3c',
            'background': '#f8f9fa'
        }

    @require_auth
    def render(self, interview_id: Optional[str] = None):
        """Render the report interface"""
        st.title("Interview Report")

        # Custom CSS
        self._apply_custom_styles()

        if interview_id:
            # Show specific interview report
            self._render_single_report(interview_id)
        else:
            # Show report list
            self._render_report_list()

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .report-container {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .feedback-item {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        .highlight {
            color: #3498db;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_report_list(self):
        """Render list of interview reports"""
        # Get user's interview reports
        reports = self.interview_ops.get_user_interviews(st.session_state.user_id)
        
        if not reports:
            st.info("No interview reports found. Complete an interview to see your report.")
            return

        # Create report cards
        for report in reports:
            with st.container():
                st.markdown("<div class='report-container'>", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([2,1,1])
                
                with col1:
                    st.markdown(f"### {report['company_name']}")
                    st.markdown(f"**Date:** {report['created_at'].strftime('%Y-%m-%d %H:%M')}")
                
                with col2:
                    st.metric("Score", f"{report['total_score']}/100")
                
                with col3:
                    if st.button("View Details", key=f"view_{report['id']}"):
                        st.session_state.selected_report = report['id']
                        st.experimental_rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

    def _render_single_report(self, interview_id: str):
        """Render detailed single report view"""
        report = self.interview_ops.get_interview(interview_id)
        if not report:
            st.error("Report not found.")
            return

        # Header section
        self._render_report_header(report)

        # Scores section
        self._render_score_section(report)

        # Feedback section
        self._render_feedback_section(report)

        # Transcript section (Premium feature)
        self._render_transcript_section(report)

        # Action buttons
        self._render_action_buttons(report)

    def _render_report_header(self, report: Dict):
        """Render report header section"""
        st.markdown("<div class='report-container'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2,1])
        
        with col1:
            st.markdown(f"### Interview with {report['company_name']}")
            st.markdown(f"**Date:** {report['created_at'].strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"**Position:** {report.get('position', 'Not specified')}")
        
        with col2:
            status_color = self._get_score_color(report['total_score'])
            st.markdown(f"""
            <div style='text-align: center;'>
                <h2 style='color: {status_color}'>{report['total_score']}/100</h2>
                <p>Overall Score</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    def _render_score_section(self, report: Dict):
        """Render detailed score breakdown"""
        st.markdown("### Score Breakdown")
        
        # Radar chart for skills
        fig = go.Figure()
        
        categories = ['Technical', 'Communication', 'Behavioral', 'Problem Solving']
        values = [
            report['scores']['technical'],
            report['scores']['communication'],
            report['scores']['behavioral'],
            report['scores'].get('problem_solving', 0)
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Skills Score'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Detailed score cards
        cols = st.columns(4)
        for i, (category, score) in enumerate(zip(categories, values)):
            with cols[i]:
                st.markdown(f"""
                <div class='metric-card'>
                    <h4>{category}</h4>
                    <h2 style='color: {self._get_score_color(score)}'>{score}/100</h2>
                </div>
                """, unsafe_allow_html=True)

    def _render_feedback_section(self, report: Dict):
        """Render detailed feedback section"""
        st.markdown("### Detailed Feedback")
        
        # Strengths
        st.subheader("Strengths")
        for strength in report['feedback']['strengths']:
            st.markdown(f"""
            <div class='feedback-item'>
                <i class="fas fa-check-circle" style="color: {self.color_scheme['secondary']}"></i>
                {strength}
            </div>
            """, unsafe_allow_html=True)

        # Areas for Improvement
        st.subheader("Areas for Improvement")
        for improvement in report['feedback']['improvements']:
            st.markdown(f"""
            <div class='feedback-item'>
                <i class="fas fa-exclamation-circle" style="color: {self.color_scheme['warning']}"></i>
                {improvement}
            </div>
            """, unsafe_allow_html=True)

        # Specific Question Feedback
        if 'question_feedback' in report['feedback']:
            st.subheader("Question-by-Question Analysis")
            for q_feedback in report['feedback']['question_feedback']:
                with st.expander(q_feedback['question']):
                    st.markdown(f"""
                    **Response Quality:** {q_feedback['score']}/100  
                    **Feedback:** {q_feedback['feedback']}
                    """)

    def _render_transcript_section(self, report: Dict):
        """Render interview transcript section"""
        if 'transcript' in report and report['transcript']:
            st.markdown("### Interview Transcript")
            
            # Check if user has premium access
            if self._check_premium_access():
                with st.expander("View Full Transcript"):
                    for entry in report['transcript']:
                        st.markdown(f"""
                        **{entry['speaker']}:** {entry['text']}  
                        *{entry['timestamp']}*
                        """)
            else:
                st.warning("Upgrade to Premium to access the full interview transcript!")
                st.button("Upgrade to Premium")

    def _render_action_buttons(self, report: Dict):
        """Render action buttons"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Download Report"):
                self._download_report(report)
        
        with col2:
            if st.button("Share Report"):
                self._share_report(report)
        
        with col3:
            if st.button("Practice Again"):
                st.session_state.page = "interview"
                st.experimental_rerun()

    def _get_score_color(self, score: int) -> str:
        """Get color based on score"""
        if score >= 80:
            return self.color_scheme['secondary']
        elif score >= 60:
            return self.color_scheme['primary']
        elif score >= 40:
            return self.color_scheme['warning']
        else:
            return self.color_scheme['danger']

    def _check_premium_access(self) -> bool:
        """Check if user has premium access"""
        return st.session_state.get('subscription_plan', 'free') == 'premium'

    def _download_report(self, report: Dict):
        """Generate and download report"""
        try:
            # Prepare report data
            report_data = {
                'interview_details': {
                    'company': report['company_name'],
                    'date': report['created_at'].isoformat(),
                    'position': report.get('position', 'Not specified')
                },
                'scores': report['scores'],
                'feedback': report['feedback'],
                'summary': report.get('summary', '')
            }
            
            # Convert to JSON
            json_report = json.dumps(report_data, indent=2)
            b64 = base64.b64encode(json_report.encode()).decode()
            
            # Create download link
            href = f'<a href="data:application/json;base64,{b64}" download="interview_report.json">Download Report</a>'
            st.markdown(href, unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Error downloading report: {str(e)}")
            st.error("Failed to download report.")

    def _share_report(self, report: Dict):
        """Share report functionality"""
        st.markdown("### Share Report")
        
        # Generate shareable link
        share_link = f"{st.get_option('server.baseUrlPath')}/report/{report['id']}"
        
        # Display sharing options
        st.text_input("Shareable Link", share_link)
        
        # Social sharing buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("Share on LinkedIn")
        with col2:
            st.button("Share via Email")
        with col3:
            st.button("Copy Link")

# Initialize component
report_component = ReportComponent()

if __name__ == "__main__":
    report_component.render()