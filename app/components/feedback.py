# app/components/feedback.py

import streamlit as st
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from app.database.operations import FeedbackOperations, UserOperations
from app.auth.authentication import require_auth
from app.services.notification_service import notification_service, NotificationType
from app.utils.helpers import ValidationHelpers
import json
import numpy as np

logger = logging.getLogger(__name__)

class FeedbackComponent:
    def __init__(self):
        """Initialize feedback component"""
        self.feedback_ops = FeedbackOperations()
        self.user_ops = UserOperations()
        self.validators = ValidationHelpers()
        
        # Feedback categories
        self.categories = {
            'interview_experience': [
                'Question Quality',
                'AI Interviewer Interaction',
                'Voice Recognition',
                'Response Analysis',
                'Overall Experience'
            ],
            'platform_features': [
                'Ease of Use',
                'Technical Performance',
                'Report Quality',
                'User Interface',
                'Feature Completeness'
            ],
            'support_quality': [
                'Response Time',
                'Solution Quality',
                'Communication',
                'Documentation',
                'Overall Support'
            ]
        }
        
        # Rating scales
        self.rating_scales = {
            'satisfaction': {
                1: 'Very Dissatisfied',
                2: 'Dissatisfied',
                3: 'Neutral',
                4: 'Satisfied',
                5: 'Very Satisfied'
            },
            'effectiveness': {
                1: 'Not Effective',
                2: 'Slightly Effective',
                3: 'Moderately Effective',
                4: 'Effective',
                5: 'Very Effective'
            }
        }

    @require_auth
    def render(self):
        """Render the feedback interface"""
        st.title("Feedback & Ratings")

        # Apply custom styling
        self._apply_custom_styles()

        # Create tabs for different feedback sections
        tabs = st.tabs([
            "Provide Feedback",
            "Your Feedback History",
            "Community Insights"
        ])

        with tabs[0]:
            self._render_feedback_form()

        with tabs[1]:
            self._render_feedback_history()

        with tabs[2]:
            self._render_community_insights()

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .feedback-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .rating-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 1rem 0;
        }
        .rating-label {
            font-weight: bold;
            margin-right: 1rem;
        }
        .feedback-meta {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        .highlight {
            color: #3498db;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_feedback_form(self):
        """Render feedback submission form"""
        st.header("Share Your Feedback")

        # Feedback type selection
        feedback_type = st.selectbox(
            "What would you like to provide feedback about?",
            [
                "Recent Interview",
                "Platform Features",
                "Support Experience",
                "General Feedback"
            ]
        )

        with st.form("feedback_form"):
            if feedback_type == "Recent Interview":
                feedback_data = self._render_interview_feedback_form()
            elif feedback_type == "Platform Features":
                feedback_data = self._render_platform_feedback_form()
            elif feedback_type == "Support Experience":
                feedback_data = self._render_support_feedback_form()
            else:
                feedback_data = self._render_general_feedback_form()

            submit = st.form_submit_button("Submit Feedback")
            
            if submit:
                self._handle_feedback_submission(feedback_type, feedback_data)

    def _render_interview_feedback_form(self) -> Dict:
        """Render interview-specific feedback form"""
        feedback_data = {}
        
        # Get recent interviews
        recent_interviews = self.feedback_ops.get_recent_interviews(
            st.session_state.user_id
        )
        
        if not recent_interviews:
            st.warning("No recent interviews found.")
            return {}

        # Interview selection
        selected_interview = st.selectbox(
            "Select Interview",
            recent_interviews,
            format_func=lambda x: f"{x['company_name']} - {x['date'].strftime('%Y-%m-%d')}"
        )

        # Rating categories
        st.subheader("Rate Your Experience")
        for category in self.categories['interview_experience']:
            feedback_data[category] = st.slider(
                category,
                1, 5,
                help=f"Rate your experience with {category.lower()}"
            )

        # Specific questions
        feedback_data['most_helpful'] = st.text_area(
            "What was most helpful about this interview?"
        )
        feedback_data['improvement_suggestions'] = st.text_area(
            "What could be improved?"
        )
        feedback_data['interview_id'] = selected_interview['id']

        return feedback_data

    def _render_platform_feedback_form(self) -> Dict:
        """Render platform-specific feedback form"""
        feedback_data = {}
        
        # Feature ratings
        st.subheader("Rate Platform Features")
        for category in self.categories['platform_features']:
            feedback_data[category] = st.slider(
                category,
                1, 5,
                help=f"Rate your experience with {category.lower()}"
            )

        # Feature requests
        feedback_data['missing_features'] = st.text_area(
            "Are there any features you'd like to see added?"
        )
        feedback_data['usability_feedback'] = st.text_area(
            "How can we make the platform more user-friendly?"
        )

        return feedback_data

    def _render_support_feedback_form(self) -> Dict:
        """Render support experience feedback form"""
        feedback_data = {}
        
        # Support ticket selection
        recent_tickets = self.feedback_ops.get_recent_support_tickets(
            st.session_state.user_id
        )
        
        if recent_tickets:
            selected_ticket = st.selectbox(
                "Select Support Ticket",
                recent_tickets,
                format_func=lambda x: f"Ticket #{x['id']} - {x['subject']}"
            )
            feedback_data['ticket_id'] = selected_ticket['id']

        # Support ratings
        st.subheader("Rate Support Quality")
        for category in self.categories['support_quality']:
            feedback_data[category] = st.slider(
                category,
                1, 5,
                help=f"Rate your experience with {category.lower()}"
            )

        feedback_data['support_comments'] = st.text_area(
            "Additional comments about your support experience"
        )

        return feedback_data

    def _render_general_feedback_form(self) -> Dict:
        """Render general feedback form"""
        feedback_data = {}
        
        feedback_data['overall_satisfaction'] = st.slider(
            "Overall Satisfaction",
            1, 5,
            help="Rate your overall satisfaction with the platform"
        )

        feedback_data['feedback_text'] = st.text_area(
            "Share your thoughts, suggestions, or concerns"
        )

        feedback_data['would_recommend'] = st.radio(
            "Would you recommend our platform to others?",
            ["Yes", "No", "Maybe"]
        )

        return feedback_data

    def _handle_feedback_submission(self, feedback_type: str, feedback_data: Dict):
        """Handle feedback submission"""
        try:
            if not feedback_data:
                st.error("Please provide feedback before submitting.")
                return

            # Validate feedback data
            if not self._validate_feedback(feedback_data):
                return

            # Add metadata
            feedback_data.update({
                'user_id': st.session_state.user_id,
                'feedback_type': feedback_type,
                'submitted_at': datetime.utcnow()
            })

            # Save feedback
            feedback_id = self.feedback_ops.create_feedback(feedback_data)

            if feedback_id:
                st.success("Thank you for your feedback!")
                
                # Send notification to admins for low ratings
                if self._has_low_ratings(feedback_data):
                    self._notify_admins_low_rating(feedback_data)
                
                # Update user feedback stats
                self._update_user_feedback_stats(feedback_data)
                
            else:
                st.error("Failed to submit feedback. Please try again.")

        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            st.error("An error occurred while submitting feedback.")

    def _render_feedback_history(self):
        """Render user's feedback history"""
        st.header("Your Feedback History")

        # Get user's feedback history
        feedback_history = self.feedback_ops.get_user_feedback(
            st.session_state.user_id
        )

        if not feedback_history:
            st.info("You haven't provided any feedback yet.")
            return

        # Create feedback timeline
        fig = self._create_feedback_timeline(feedback_history)
        st.plotly_chart(fig, use_container_width=True)

        # Show detailed feedback history
        for feedback in feedback_history:
            with st.expander(
                f"{feedback['feedback_type']} - {feedback['submitted_at'].strftime('%Y-%m-%d')}"
            ):
                self._render_feedback_details(feedback)

    def _render_community_insights(self):
        """Render community feedback insights"""
        st.header("Community Insights")

        # Get aggregated feedback data
        feedback_stats = self.feedback_ops.get_aggregated_feedback_stats()

        # Create visualization tabs
        viz_tabs = st.tabs([
            "Overall Ratings",
            "Feature Satisfaction",
            "Trending Topics",
            "Improvement Areas"
        ])

        with viz_tabs[0]:
            self._render_overall_ratings(feedback_stats)

        with viz_tabs[1]:
            self._render_feature_satisfaction(feedback_stats)

        with viz_tabs[2]:
            self._render_trending_topics(feedback_stats)

        with viz_tabs[3]:
            self._render_improvement_areas(feedback_stats)

    def _validate_feedback(self, feedback_data: Dict) -> bool:
        """Validate feedback data"""
        try:
            # Check required fields
            required_fields = ['user_id']
            for field in required_fields:
                if field not in feedback_data:
                    st.error(f"Missing required field: {field}")
                    return False

            # Validate ratings
            for key, value in feedback_data.items():
                if key.endswith('_rating') and not (1 <= value <= 5):
                    st.error(f"Invalid rating value for {key}")
                    return False

            # Validate text fields
            text_fields = ['feedback_text', 'improvement_suggestions', 'comments']
            for field in text_fields:
                if field in feedback_data:
                    cleaned_text = self.validators.sanitize_input(
                        feedback_data[field]
                    )
                    feedback_data[field] = cleaned_text

            return True

        except Exception as e:
            logger.error(f"Error validating feedback: {str(e)}")
            return False

    def _create_feedback_timeline(self, feedback_history: List[Dict]) -> go.Figure:
        """Create feedback timeline visualization"""
        df = pd.DataFrame(feedback_history)
        
        fig = px.line(
            df,
            x='submitted_at',
            y='overall_satisfaction',
            title='Your Feedback Over Time'
        )
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Overall Satisfaction",
            showlegend=True
        )
        
        return fig

    def _render_feedback_details(self, feedback: Dict):
        """Render detailed feedback information"""
        st.markdown(f"""
        <div class="feedback-card">
            <h4>{feedback['feedback_type']}</h4>
            <p>{feedback.get('feedback_text', '')}</p>
            <div class="feedback-meta">
                Submitted: {feedback['submitted_at'].strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _has_low_ratings(self, feedback_data: Dict) -> bool:
        """Check if feedback contains low ratings"""
        rating_fields = [k for k, v in feedback_data.items() if isinstance(v, (int, float))]
        return any(feedback_data[field] <= 2 for field in rating_fields)

    def _notify_admins_low_rating(self, feedback_data: Dict):
        """Notify administrators about low ratings"""
        notification_service.send_notification(
            user_id="admin",
            type=NotificationType.WARNING,
            title="Low Rating Alert",
            message=f"User {feedback_data['user_id']} submitted low ratings",
            data=feedback_data
        )

    def _update_user_feedback_stats(self, feedback_data: Dict):
        """Update user's feedback statistics"""
        self.user_ops.update_user_feedback_stats(
            st.session_state.user_id,
            feedback_data
        )

# Initialize component
feedback_component = FeedbackComponent()

if __name__ == "__main__":
    feedback_component.render()