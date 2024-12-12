# app/components/landing_page.py

import streamlit as st
from typing import Tuple
import json
from app.config.settings import settings
from app.auth.authentication import require_auth
import plotly.graph_objects as go

class LandingPage:
    def __init__(self):
        self.features = {
            "AI-Powered Interviews": "Experience realistic job interviews with our advanced AI interviewer",
            "Real-Time Feedback": "Get instant feedback on your responses and performance",
            "Custom Scenarios": "Practice interviews tailored to your industry and experience level",
            "Detailed Analytics": "Track your progress with comprehensive performance metrics",
            "Voice Interaction": "Natural voice-based conversations for a realistic experience",
            "Premium Features": "Access to recorded sessions and advanced interview techniques"
        }
        
        self.testimonials = [
            {
                "name": "Sarah Johnson",
                "role": "Software Engineer",
                "text": "This platform helped me ace my dream job interview at a top tech company!",
                "rating": 5
            },
            {
                "name": "Michael Chen",
                "role": "Product Manager",
                "text": "The AI interviews feel incredibly realistic. Great way to build confidence!",
                "rating": 5
            },
            {
                "name": "Emily Rodriguez",
                "role": "Marketing Director",
                "text": "The detailed feedback helped me identify and improve my weak points.",
                "rating": 4
            }
        ]

    def _create_hero_section(self):
        """Create the hero section of the landing page"""
        st.markdown("""
        <style>
        .hero-container {
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #f6f8fa 0%, #e9ecef 100%);
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .hero-title {
            font-size: 3rem;
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 1rem;
        }
        .hero-subtitle {
            font-size: 1.5rem;
            color: #4a4a4a;
            margin-bottom: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">Beaver Job Interview Trainer</h1>
            <p class="hero-subtitle">Master Your Interview Skills with AI-Powered Practice Sessions</p>
        </div>
        """, unsafe_allow_html=True)

    def _create_features_section(self):
        """Create the features section"""
        st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Key Features</h2>", 
                   unsafe_allow_html=True)
        
        cols = st.columns(3)
        for idx, (feature, description) in enumerate(self.features.items()):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    height: 200px;
                    margin-bottom: 1rem;
                '>
                    <h3 style='color: #2c3e50; margin-bottom: 1rem;'>{feature}</h3>
                    <p style='color: #7f8c8d;'>{description}</p>
                </div>
                """, unsafe_allow_html=True)

    def _create_pricing_section(self):
        """Create the pricing section"""
        st.markdown("<h2 style='text-align: center; margin: 3rem 0;'>Pricing Plans</h2>", 
                   unsafe_allow_html=True)

        cols = st.columns(len(settings.SUBSCRIPTION_PLANS))
        for idx, (plan_name, plan_details) in enumerate(settings.SUBSCRIPTION_PLANS.items()):
            with cols[idx]:
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                    height: 400px;
                    position: relative;
                '>
                    <h3 style='color: #2c3e50;'>{plan_details['name']}</h3>
                    <h2 style='color: #3498db; margin: 1rem 0;'>${plan_details['price']}/month</h2>
                    <ul style='list-style-type: none; padding: 0;'>
                        {"".join(f"<li style='margin: 0.5rem 0;'>âœ“ {feature}</li>" for feature in plan_details['features'])}
                    </ul>
                    <div style='position: absolute; bottom: 2rem; left: 0; right: 0;'>
                        <button style='
                            background-color: #3498db;
                            color: white;
                            border: none;
                            padding: 0.5rem 2rem;
                            border-radius: 5px;
                            cursor: pointer;
                        '>Choose Plan</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    def _create_testimonials_section(self):
        """Create the testimonials section"""
        st.markdown("<h2 style='text-align: center; margin: 3rem 0;'>What Our Users Say</h2>", 
                   unsafe_allow_html=True)

        cols = st.columns(len(self.testimonials))
        for idx, testimonial in enumerate(self.testimonials):
            with cols[idx]:
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    height: 250px;
                '>
                    <p style='color: #7f8c8d; font-style: italic;'>"{testimonial['text']}"</p>
                    <div style='margin-top: 1rem;'>
                        <p style='color: #2c3e50; font-weight: bold;'>{testimonial['name']}</p>
                        <p style='color: #7f8c8d;'>{testimonial['role']}</p>
                        <p style='color: #f1c40f;'>{'â˜…' * testimonial['rating']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    def _create_stats_section(self):
        """Create statistics section"""
        stats = {
            "Successful Interviews": "10,000+",
            "Job Offers": "5,000+",
            "User Rating": "4.8/5",
            "Active Users": "50,000+"
        }

        st.markdown("<h2 style='text-align: center; margin: 3rem 0;'>Our Impact</h2>", 
                   unsafe_allow_html=True)

        cols = st.columns(len(stats))
        for idx, (stat_name, stat_value) in enumerate(stats.items()):
            with cols[idx]:
                st.markdown(f"""
                <div style='text-align: center;'>
                    <h3 style='color: #3498db; font-size: 2rem;'>{stat_value}</h3>
                    <p style='color: #7f8c8d;'>{stat_name}</p>
                </div>
                """, unsafe_allow_html=True)

    def _create_cta_section(self):
        """Create call-to-action section"""
        st.markdown("""
        <div style='
            text-align: center;
            padding: 3rem;
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            border-radius: 10px;
            margin: 3rem 0;
        '>
            <h2 style='color: white; margin-bottom: 1rem;'>Ready to Ace Your Next Interview?</h2>
            <p style='color: white; margin-bottom: 2rem;'>Start practicing with our AI interviewer today!</p>
            <button style='
                background-color: white;
                color: #3498db;
                border: none;
                padding: 1rem 3rem;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
            '>Get Started Now</button>
        </div>
        """, unsafe_allow_html=True)

    def render(self):
        """Render the complete landing page"""
        # Custom CSS for the entire page
        st.markdown("""
        <style>
        .stApp {
            background-color: #f8f9fa;
        }
        .main {
            padding: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        # Render all sections
        self._create_hero_section()
        self._create_features_section()
        self._create_pricing_section()
        self._create_testimonials_section()
        self._create_stats_section()
        self._create_cta_section()

        # Add footer
        st.markdown("""
        <div style='text-align: center; padding: 2rem; color: #7f8c8d;'>
            © 2024 Beaver Job Interview Trainer. All rights reserved.
        </div>
        """, unsafe_allow_html=True)

# Initialize and render landing page
landing_page = LandingPage()

if __name__ == "__main__":
    landing_page.render()