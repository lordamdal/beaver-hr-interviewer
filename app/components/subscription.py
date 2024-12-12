# app/components/subscription.py

import streamlit as st
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
from app.database.operations import UserOperations
from app.services.payment_service import PaymentService
from app.utils.helpers import UIHelpers, ValidationHelpers
from app.config.settings import settings
from app.auth.authentication import require_auth
import logging
import plotly.graph_objects as go
import pandas as pd

logger = logging.getLogger(__name__)

class SubscriptionComponent:
    def __init__(self):
        """Initialize subscription component"""
        self.user_ops = UserOperations()
        self.payment_service = PaymentService()
        
        # Subscription features
        self.features = {
            "free": {
                "interviews_per_month": 1,
                "features": [
                    "Basic Interview Practice",
                    "Basic Performance Report",
                    "Email Support"
                ],
                "limitations": [
                    "Limited to 1 interview per month",
                    "Basic feedback only",
                    "No recording access"
                ]
            },
            "basic": {
                "interviews_per_month": 5,
                "features": [
                    "5 Monthly Interviews",
                    "Detailed Performance Reports",
                    "Email & Chat Support",
                    "Interview Recording Access",
                    "Basic Analytics"
                ],
                "limitations": [
                    "Limited to 5 interviews per month",
                    "No custom interview scenarios"
                ]
            },
            "premium": {
                "interviews_per_month": 20,
                "features": [
                    "Unlimited Interviews",
                    "Advanced Performance Analytics",
                    "Priority Support",
                    "Custom Interview Scenarios",
                    "Interview Recording Downloads",
                    "AI-Powered Recommendations",
                    "Resume Review",
                    "Career Coaching"
                ],
                "limitations": []
            }
        }

    @require_auth
    def render(self):
        """Render the subscription interface"""
        st.title("Subscription Plans")

        # Get current user's subscription
        user_data = self.user_ops.get_user(st.session_state.user_id)
        current_plan = user_data.get('subscription_plan', 'free')

        # Custom CSS
        self._apply_custom_styles()

        # Render subscription header
        self._render_subscription_header(current_plan)

        # Render plan comparison
        self._render_plan_comparison(current_plan)

        # Render subscription management
        if current_plan != 'free':
            self._render_subscription_management(user_data)

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .plan-card {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: 100%;
        }
        .plan-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .plan-price {
            font-size: 2rem;
            font-weight: bold;
            color: #3498db;
        }
        .feature-list {
            list-style-type: none;
            padding: 0;
        }
        .feature-item {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
        }
        .feature-item:before {
            content: "âœ“";
            position: absolute;
            left: 0;
            color: #2ecc71;
        }
        .limitation-item:before {
            content: "Ã—";
            color: #e74c3c;
        }
        .current-plan {
            border: 2px solid #3498db;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_subscription_header(self, current_plan: str):
        """Render subscription header with usage stats"""
        st.header("Your Subscription")
        
        # Usage metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            interviews_used = self.user_ops.get_user_interview_count(
                st.session_state.user_id,
                period="month"
            )
            total_interviews = self.features[current_plan]['interviews_per_month']
            st.metric(
                "Interviews This Month",
                f"{interviews_used}/{total_interviews}"
            )
        
        with col2:
            days_remaining = self._get_days_remaining()
            st.metric("Days Until Renewal", days_remaining)
        
        with col3:
            if current_plan != 'free':
                next_billing = self._get_next_billing_date()
                st.metric("Next Billing Date", next_billing.strftime("%Y-%m-%d"))

    def _render_plan_comparison(self, current_plan: str):
        """Render plan comparison cards"""
        st.header("Available Plans")
        
        cols = st.columns(len(self.features))
        
        for idx, (plan_name, plan_details) in enumerate(self.features.items()):
            with cols[idx]:
                self._render_plan_card(
                    plan_name,
                    plan_details,
                    is_current=plan_name == current_plan
                )

    def _render_plan_card(self, plan_name: str, plan_details: Dict, is_current: bool):
        """Render individual plan card"""
        card_class = "plan-card" + (" current-plan" if is_current else "")
        
        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        
        # Plan header
        st.markdown(f"""
        <div class="plan-header">
            <h3>{plan_name.title()} Plan</h3>
            <div class="plan-price">${settings.SUBSCRIPTION_PLANS[plan_name]['price']}/mo</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Features
        st.markdown("### Features")
        for feature in plan_details['features']:
            st.markdown(f"""
            <div class="feature-item">{feature}</div>
            """, unsafe_allow_html=True)
        
        # Limitations
        if plan_details['limitations']:
            st.markdown("### Limitations")
            for limitation in plan_details['limitations']:
                st.markdown(f"""
                <div class="feature-item limitation-item">{limitation}</div>
                """, unsafe_allow_html=True)
        
        # Action button
        if not is_current:
            if st.button(f"Upgrade to {plan_name.title()}", key=f"upgrade_{plan_name}"):
                self._handle_plan_change(plan_name)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 1rem;">
                <span style="color: #3498db;">Current Plan</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    def _render_subscription_management(self, user_data: Dict):
        """Render subscription management section"""
        st.header("Subscription Management")
        
        # Billing information
        with st.expander("Billing Information"):
            self._render_billing_info(user_data)
        
        # Payment history
        with st.expander("Payment History"):
            self._render_payment_history()
        
        # Cancel subscription
        with st.expander("Cancel Subscription"):
            self._render_cancellation_options()

    def _render_billing_info(self, user_data: Dict):
        """Render billing information form"""
        with st.form("billing_info"):
            st.text_input("Card Holder Name", value=user_data.get('card_holder', ''))
            st.text_input("Card Number (last 4 digits)", 
                         value=f"**** **** **** {user_data.get('card_last4', '')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Expiry Date", value=user_data.get('card_expiry', ''))
            with col2:
                st.text_input("CVV", type="password")
            
            if st.form_submit_button("Update Billing Information"):
                self._update_billing_info()

    def _render_payment_history(self):
        """Render payment history table"""
        payments = self.payment_service.get_payment_history(st.session_state.user_id)
        
        if payments:
            df = pd.DataFrame(payments)
            st.dataframe(df)
        else:
            st.info("No payment history available.")

    def _render_cancellation_options(self):
        """Render subscription cancellation options"""
        st.warning("Warning: Canceling your subscription will limit your access to basic features.")
        
        reason = st.selectbox(
            "Reason for cancellation",
            [
                "Too expensive",
                "Not using enough",
                "Missing features",
                "Found alternative",
                "Other"
            ]
        )
        
        if reason == "Other":
            st.text_area("Please specify")
        
        if st.button("Cancel Subscription", type="primary"):
            if self._cancel_subscription():
                st.success("Subscription cancelled successfully.")
                st.info("Your premium features will remain active until the end of the billing period.")
            else:
                st.error("Failed to cancel subscription. Please try again or contact support.")

    def _handle_plan_change(self, new_plan: str):
        """Handle plan upgrade/downgrade"""
        try:
            # Create checkout session
            success, session_url = self.payment_service.create_checkout_session(
                st.session_state.user_id,
                new_plan
            )
            
            if success:
                # Redirect to checkout
                st.markdown(f'<meta http-equiv="refresh" content="0;url={session_url}">', 
                          unsafe_allow_html=True)
            else:
                st.error("Failed to process upgrade. Please try again.")
                
        except Exception as e:
            logger.error(f"Error handling plan change: {str(e)}")
            st.error("An error occurred. Please try again later.")

    def _update_billing_info(self) -> bool:
        """Update billing information"""
        try:
            # Implementation will depend on payment provider
            return True
        except Exception as e:
            logger.error(f"Error updating billing info: {str(e)}")
            return False

    def _cancel_subscription(self) -> bool:
        """Cancel subscription"""
        try:
            return self.payment_service.cancel_subscription(st.session_state.user_id)
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return False

    def _get_days_remaining(self) -> int:
        """Get days remaining in current billing cycle"""
        user_data = self.user_ops.get_user(st.session_state.user_id)
        if user_data.get('subscription_end_date'):
            end_date = datetime.fromisoformat(user_data['subscription_end_date'])
            return (end_date - datetime.now()).days
        return 0

    def _get_next_billing_date(self) -> datetime:
        """Get next billing date"""
        user_data = self.user_ops.get_user(st.session_state.user_id)
        if user_data.get('subscription_end_date'):
            return datetime.fromisoformat(user_data['subscription_end_date'])
        return datetime.now()

# Initialize component
subscription_component = SubscriptionComponent()

if __name__ == "__main__":
    subscription_component.render()