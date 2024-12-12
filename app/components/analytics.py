# app/components/analytics.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from app.database.operations import UserOperations, InterviewOperations
from app.auth.authentication import require_auth
from app.utils.helpers import DataHelpers
import calendar
import json

logger = logging.getLogger(__name__)

class AnalyticsComponent:
    def __init__(self):
        """Initialize analytics component"""
        self.user_ops = UserOperations()
        self.interview_ops = InterviewOperations()
        self.data_helpers = DataHelpers()
        
        # Color schemes
        self.colors = {
            'primary': '#3498db',
            'secondary': '#2ecc71',
            'warning': '#f1c40f',
            'danger': '#e74c3c',
            'neutral': '#95a5a6'
        }

    @require_auth
    def render(self):
        """Render the analytics dashboard"""
        st.title("Performance Analytics")

        # Apply custom styling
        self._apply_custom_styles()

        # Time period selector
        time_period = st.selectbox(
            "Time Period",
            ["Last 7 Days", "Last 30 Days", "Last 3 Months", "Last Year", "All Time"]
        )

        # Get date range based on selection
        start_date, end_date = self._get_date_range(time_period)

        # Create dashboard layout
        col1, col2 = st.columns([2, 1])

        with col1:
            # Main metrics
            self._render_key_metrics(start_date, end_date)
            
            # Performance trends
            self._render_performance_trends(start_date, end_date)

        with col2:
            # Quick stats
            self._render_quick_stats(start_date, end_date)

        # Detailed analysis sections
        tabs = st.tabs([
            "Skills Analysis",
            "Question Categories",
            "Improvement Areas",
            "Time Analysis"
        ])

        with tabs[0]:
            self._render_skills_analysis(start_date, end_date)

        with tabs[1]:
            self._render_question_categories(start_date, end_date)

        with tabs[2]:
            self._render_improvement_areas(start_date, end_date)

        with tabs[3]:
            self._render_time_analysis(start_date, end_date)

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            margin-bottom: 1rem;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #3498db;
        }
        .trend-indicator {
            font-size: 0.9rem;
            margin-left: 0.5rem;
        }
        .trend-up {
            color: #2ecc71;
        }
        .trend-down {
            color: #e74c3c;
        }
        </style>
        """, unsafe_allow_html=True)

    def _get_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """Get date range based on selected period"""
        end_date = datetime.now()
        
        if period == "Last 7 Days":
            start_date = end_date - timedelta(days=7)
        elif period == "Last 30 Days":
            start_date = end_date - timedelta(days=30)
        elif period == "Last 3 Months":
            start_date = end_date - timedelta(days=90)
        elif period == "Last Year":
            start_date = end_date - timedelta(days=365)
        else:  # All Time
            start_date = datetime(2000, 1, 1)  # Arbitrary past date
            
        return start_date, end_date

    def _render_key_metrics(self, start_date: datetime, end_date: datetime):
        """Render key performance metrics"""
        st.subheader("Key Metrics")

        # Get metrics data
        metrics = self._calculate_key_metrics(start_date, end_date)
        
        cols = st.columns(4)
        
        with cols[0]:
            self._render_metric_card(
                "Overall Score",
                f"{metrics['average_score']:.1f}%",
                metrics['score_trend']
            )
            
        with cols[1]:
            self._render_metric_card(
                "Interviews Completed",
                metrics['total_interviews'],
                metrics['interview_trend']
            )
            
        with cols[2]:
            self._render_metric_card(
                "Success Rate",
                f"{metrics['success_rate']:.1f}%",
                metrics['success_trend']
            )
            
        with cols[3]:
            self._render_metric_card(
                "Improvement Rate",
                f"{metrics['improvement_rate']:+.1f}%",
                metrics['improvement_rate']
            )

    def _render_performance_trends(self, start_date: datetime, end_date: datetime):
        """Render performance trend charts"""
        st.subheader("Performance Trends")

        # Get performance data
        performance_data = self._get_performance_data(start_date, end_date)
        
        # Create line chart
        fig = go.Figure()
        
        # Add overall score line
        fig.add_trace(go.Scatter(
            x=performance_data['date'],
            y=performance_data['overall_score'],
            name='Overall Score',
            line=dict(color=self.colors['primary'], width=3)
        ))
        
        # Add category score lines
        for category in ['technical', 'communication', 'behavioral']:
            fig.add_trace(go.Scatter(
                x=performance_data['date'],
                y=performance_data[f'{category}_score'],
                name=category.title(),
                line=dict(width=2)
            ))
            
        fig.update_layout(
            title="Score Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Score",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_quick_stats(self, start_date: datetime, end_date: datetime):
        """Render quick statistics"""
        st.subheader("Quick Stats")

        stats = self._calculate_quick_stats(start_date, end_date)
        
        for stat_name, stat_value in stats.items():
            st.markdown(f"""
            <div class="metric-card">
                <h4>{stat_name}</h4>
                <div class="stat-value">{stat_value}</div>
            </div>
            """, unsafe_allow_html=True)

    def _render_skills_analysis(self, start_date: datetime, end_date: datetime):
        """Render skills analysis section"""
        st.subheader("Skills Analysis")

        # Get skills data
        skills_data = self._get_skills_data(start_date, end_date)
        
        # Create radar chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=list(skills_data['scores']),
            theta=list(skills_data['skills']),
            fill='toself',
            name='Current Skills'
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

        # Skills breakdown table
        st.dataframe(
            pd.DataFrame(skills_data['details']),
            use_container_width=True
        )

    def _render_question_categories(self, start_date: datetime, end_date: datetime):
        """Render question categories analysis"""
        st.subheader("Question Categories Performance")

        # Get categories data
        categories_data = self._get_categories_data(start_date, end_date)
        
        # Create bar chart
        fig = px.bar(
            categories_data,
            x='category',
            y='score',
            color='score',
            color_continuous_scale=['red', 'yellow', 'green'],
            text='score'
        )
        
        fig.update_layout(
            title="Performance by Question Category",
            xaxis_title="Category",
            yaxis_title="Average Score"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_improvement_areas(self, start_date: datetime, end_date: datetime):
        """Render improvement areas analysis"""
        st.subheader("Areas for Improvement")

        # Get improvement data
        improvement_data = self._get_improvement_data(start_date, end_date)
        
        # Create horizontal bar chart
        fig = go.Figure(go.Bar(
            x=improvement_data['scores'],
            y=improvement_data['areas'],
            orientation='h',
            marker_color=self.colors['warning']
        ))
        
        fig.update_layout(
            title="Areas Needing Most Improvement",
            xaxis_title="Current Score",
            yaxis_title="Area"
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Improvement recommendations
        st.subheader("Recommendations")
        for area, recommendations in improvement_data['recommendations'].items():
            with st.expander(area):
                for rec in recommendations:
                    st.write(f"â€¢ {rec}")

    def _render_time_analysis(self, start_date: datetime, end_date: datetime):
        """Render time-based analysis"""
        st.subheader("Time Analysis")

        # Get time analysis data
        time_data = self._get_time_analysis(start_date, end_date)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=time_data['performance_matrix'],
            x=time_data['hours'],
            y=time_data['days'],
            colorscale='RdYlGn'
        ))
        
        fig.update_layout(
            title="Performance by Time of Day",
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _calculate_key_metrics(self, 
                             start_date: datetime, 
                             end_date: datetime) -> Dict:
        """Calculate key performance metrics"""
        try:
            interviews = self.interview_ops.get_user_interviews(
                st.session_state.user_id,
                start_date,
                end_date
            )
            
            if not interviews:
                return {
                    'average_score': 0,
                    'total_interviews': 0,
                    'success_rate': 0,
                    'improvement_rate': 0,
                    'score_trend': 0,
                    'interview_trend': 0,
                    'success_trend': 0
                }
            
            scores = [interview['score'] for interview in interviews]
            
            return {
                'average_score': np.mean(scores),
                'total_interviews': len(interviews),
                'success_rate': len([s for s in scores if s >= 70]) / len(scores) * 100,
                'improvement_rate': self._calculate_improvement_rate(scores),
                'score_trend': self._calculate_trend(scores),
                'interview_trend': len(interviews) - len([i for i in interviews 
                    if i['date'] < (end_date - (end_date - start_date) / 2)]),
                'success_trend': self._calculate_success_trend(scores)
            }
            
        except Exception as e:
            logger.error(f"Error calculating key metrics: {str(e)}")
            return {}

    def _calculate_improvement_rate(self, scores: List[float]) -> float:
        """Calculate improvement rate between first and last scores"""
        if len(scores) < 2:
            return 0.0
        return ((scores[-1] - scores[0]) / scores[0]) * 100

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction and magnitude"""
        if len(values) < 2:
            return 0.0
        return np.polyfit(range(len(values)), values, 1)[0]

    def _calculate_success_trend(self, scores: List[float]) -> float:
        """Calculate trend in success rate"""
        if len(scores) < 2:
            return 0.0
        success_rates = [
            len([s for s in scores[i:i+5] if s >= 70]) / min(5, len(scores[i:i+5]))
            for i in range(0, len(scores), 5)
        ]
        return self._calculate_trend(success_rates)

    def _render_metric_card(self, title: str, value: Any, trend: float):
        """Render metric card with trend indicator"""
        trend_icon = "â†‘" if trend > 0 else "â†“" if trend < 0 else "â†’"
        trend_class = "trend-up" if trend > 0 else "trend-down" if trend < 0 else ""
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>{title}</h4>
            <div class="stat-value">
                {value}
                <span class="trend-indicator {trend_class}">
                    {trend_icon} {abs(trend):.1f}%
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Initialize component
analytics_component = AnalyticsComponent()

if __name__ == "__main__":
    analytics_component.render()