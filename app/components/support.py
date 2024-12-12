# app/components/support.py

import streamlit as st
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime, timedelta
from app.database.operations import SupportOperations, UserOperations
from app.services.notification_service import notification_service, NotificationType
from app.services.email_service import email_service
from app.auth.authentication import require_auth
from app.utils.helpers import ValidationHelpers, UIHelpers
import json
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class SupportComponent:
    def __init__(self):
        """Initialize support component"""
        self.support_ops = SupportOperations()
        self.user_ops = UserOperations()
        self.validators = ValidationHelpers()
        self.ui_helpers = UIHelpers()
        
        # Load support categories and priorities
        self.categories = {
            'technical': 'Technical Support',
            'account': 'Account Management',
            'billing': 'Billing & Subscription',
            'feature': 'Feature Request',
            'bug': 'Bug Report',
            'other': 'Other'
        }
        
        self.priorities = {
            'low': {'label': 'Low', 'color': '#95a5a6'},
            'medium': {'label': 'Medium', 'color': '#f1c40f'},
            'high': {'label': 'High', 'color': '#e67e22'},
            'urgent': {'label': 'Urgent', 'color': '#e74c3c'}
        }
        
        # Support hours
        self.support_hours = {
            'weekday': {'start': 9, 'end': 17},  # 9 AM - 5 PM
            'weekend': {'start': 10, 'end': 16}  # 10 AM - 4 PM
        }

    @require_auth
    def render(self):
        """Render the support interface"""
        st.title("Customer Support")

        # Apply custom styling
        self._apply_custom_styles()

        # Create tabs for different support sections
        tabs = st.tabs([
            "Support Home",
            "Submit Ticket",
            "My Tickets",
            "Live Chat",
            "Knowledge Base"
        ])

        with tabs[0]:
            self._render_support_home()

        with tabs[1]:
            self._render_submit_ticket()

        with tabs[2]:
            self._render_my_tickets()

        with tabs[3]:
            self._render_live_chat()

        with tabs[4]:
            self._render_knowledge_base()

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .support-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .ticket-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .priority-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .chat-message {
            padding: 0.5rem 1rem;
            border-radius: 1rem;
            margin-bottom: 0.5rem;
            max-width: 80%;
        }
        .chat-message.user {
            background-color: #e3f2fd;
            margin-left: auto;
        }
        .chat-message.support {
            background-color: #f5f5f5;
            margin-right: auto;
        }
        .support-hours {
            background-color: #e8f5e9;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_support_home(self):
        """Render support home page"""
        # Support hours and availability
        self._render_support_hours()

        # Quick actions
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("New Support Ticket"):
                st.session_state.active_tab = "Submit Ticket"
                st.experimental_rerun()
                
        with col2:
            if st.button("View My Tickets"):
                st.session_state.active_tab = "My Tickets"
                st.experimental_rerun()
                
        with col3:
            if st.button("Start Live Chat"):
                st.session_state.active_tab = "Live Chat"
                st.experimental_rerun()

        # Recent announcements
        st.subheader("Recent Announcements")
        announcements = self.support_ops.get_recent_announcements()
        for announcement in announcements:
            st.markdown(f"""
            <div class="support-card">
                <h4>{announcement['title']}</h4>
                <p>{announcement['message']}</p>
                <small>{announcement['date'].strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            """, unsafe_allow_html=True)

        # System status
        self._render_system_status()

    def _render_submit_ticket(self):
        """Render ticket submission form"""
        st.header("Submit Support Ticket")

        with st.form("support_ticket_form"):
            # Basic information
            category = st.selectbox(
                "Category",
                options=list(self.categories.keys()),
                format_func=lambda x: self.categories[x]
            )
            
            subject = st.text_input("Subject")
            description = st.text_area("Description")
            
            # Priority selection
            priority = st.select_slider(
                "Priority",
                options=list(self.priorities.keys()),
                format_func=lambda x: self.priorities[x]['label']
            )
            
            # Attachments
            files = st.file_uploader(
                "Attachments (optional)",
                accept_multiple_files=True
            )
            
            # Submit button
            submitted = st.form_submit_button("Submit Ticket")
            
            if submitted:
                self._handle_ticket_submission(
                    category,
                    subject,
                    description,
                    priority,
                    files
                )

    def _render_my_tickets(self):
        """Render user's support tickets"""
        st.header("My Support Tickets")

        # Ticket filters
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Status",
                ["All", "Open", "In Progress", "Closed"]
            )
        with col2:
            category_filter = st.selectbox(
                "Category",
                ["All"] + list(self.categories.values())
            )

        # Get filtered tickets
        tickets = self.support_ops.get_user_tickets(
            st.session_state.user_id,
            status=status_filter if status_filter != "All" else None,
            category=category_filter if category_filter != "All" else None
        )

        # Display tickets
        for ticket in tickets:
            self._render_ticket_card(ticket)

    def _render_live_chat(self):
        """Render live chat interface"""
        st.header("Live Chat Support")

        # Check support availability
        if not self._is_support_available():
            st.warning(
                "Live chat is currently unavailable. Please submit a support ticket."
            )
            return

        # Initialize chat if not exists
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = []

        # Display chat messages
        for message in st.session_state.chat_messages:
            self._render_chat_message(message)

        # Message input
        with st.form("chat_form"):
            message = st.text_input("Type your message")
            submitted = st.form_submit_button("Send")
            
            if submitted and message:
                self._handle_chat_message(message)

    def _render_knowledge_base(self):
        """Render knowledge base section"""
        st.header("Knowledge Base")

        # Search
        search_query = st.text_input("Search Knowledge Base")
        if search_query:
            search_results = self.support_ops.search_knowledge_base(search_query)
            self._render_search_results(search_results)

        # Browse by category
        st.subheader("Browse by Category")
        for category, articles in self.support_ops.get_knowledge_base_categories().items():
            with st.expander(category):
                for article in articles:
                    st.markdown(f"""
                    <div class="support-card">
                        <h4>{article['title']}</h4>
                        <p>{article['excerpt']}</p>
                        <a href="{article['url']}">Read more</a>
                    </div>
                    """, unsafe_allow_html=True)

    def _render_support_hours(self):
        """Render support hours information"""
        is_available = self._is_support_available()
        status = "Available" if is_available else "Unavailable"
        status_color = "#2ecc71" if is_available else "#e74c3c"
        
        st.markdown(f"""
        <div class="support-hours">
            <h3>Support Status: <span style="color: {status_color}">{status}</span></h3>
            <p>Support Hours:</p>
            <ul>
                <li>Weekdays: {self.support_hours['weekday']['start']}AM - 
                    {self.support_hours['weekday']['end']}PM</li>
                <li>Weekends: {self.support_hours['weekend']['start']}AM - 
                    {self.support_hours['weekend']['end']}PM</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    def _render_system_status(self):
        """Render system status information"""
        st.subheader("System Status")
        
        status = self.support_ops.get_system_status()
        
        for service, details in status.items():
            status_color = "#2ecc71" if details['status'] == "operational" else "#e74c3c"
            st.markdown(f"""
            <div class="support-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4>{service}</h4>
                    <span style="color: {status_color}">â—</span>
                </div>
                <p>{details['message']}</p>
            </div>
            """, unsafe_allow_html=True)

    def _render_ticket_card(self, ticket: Dict):
        """Render individual ticket card"""
        st.markdown(f"""
        <div class="support-card">
            <div class="ticket-header">
                <h4>#{ticket['id']} - {ticket['subject']}</h4>
                <span class="priority-badge" 
                      style="background-color: {self.priorities[ticket['priority']]['color']}">
                    {self.priorities[ticket['priority']]['label']}
                </span>
            </div>
            <p><strong>Status:</strong> {ticket['status'].title()}</p>
            <p><strong>Category:</strong> {self.categories[ticket['category']]}</p>
            <p><strong>Created:</strong> {ticket['created_at'].strftime('%Y-%m-%d %H:%M')}</p>
            <p>{ticket['description']}</p>
        </div>
        """, unsafe_allow_html=True)

        # Show updates if any
        if ticket.get('updates'):
            with st.expander("View Updates"):
                for update in ticket['updates']:
                    st.markdown(f"""
                    <div class="support-card">
                        <p>{update['message']}</p>
                        <small>{update['timestamp'].strftime('%Y-%m-%d %H:%M')}</small>
                    </div>
                    """, unsafe_allow_html=True)

        # Add update if ticket is open
        if ticket['status'] != 'closed':
            with st.form(f"update_ticket_{ticket['id']}"):
                update_message = st.text_area("Add Update")
                if st.form_submit_button("Submit Update"):
                    self._add_ticket_update(ticket['id'], update_message)

    def _render_chat_message(self, message: Dict):
        """Render chat message"""
        message_class = "user" if message['sender'] == "user" else "support"
        st.markdown(f"""
        <div class="chat-message {message_class}">
            <p>{message['message']}</p>
            <small>{message['timestamp'].strftime('%H:%M')}</small>
        </div>
        """, unsafe_allow_html=True)

    def _render_search_results(self, results: List[Dict]):
        """Render knowledge base search results"""
        if not results:
            st.info("No results found. Please try different keywords.")
            return

        for result in results:
            st.markdown(f"""
            <div class="support-card">
                <h4>{result['title']}</h4>
                <p>{result['excerpt']}</p>
                <a href="{result['url']}">Read more</a>
            </div>
            """, unsafe_allow_html=True)

    def _handle_ticket_submission(self,
                                category: str,
                                subject: str,
                                description: str,
                                priority: str,
                                files: List = None) -> bool:
        """Handle support ticket submission"""
        try:
            if not subject or not description:
                st.error("Please fill in all required fields.")
                return False

            # Create ticket
            ticket_data = {
                'user_id': st.session_state.user_id,
                'category': category,
                'subject': subject,
                'description': description,
                'priority': priority,
                'status': 'open',
                'created_at': datetime.utcnow()
            }

            # Handle file attachments
            if files:
                ticket_data['attachments'] = self._handle_attachments(files)

            ticket_id = self.support_ops.create_ticket(ticket_data)
            
            if ticket_id:
                st.success("Support ticket created successfully!")
                
                # Send confirmation email
                self._send_ticket_confirmation(ticket_data)
                
                # Notify support team
                self._notify_support_team(ticket_data)
                
                return True
            
            st.error("Failed to create support ticket.")
            return False

        except Exception as e:
            logger.error(f"Error creating support ticket: {str(e)}")
            st.error("An error occurred while creating the ticket.")
            return False

    def _handle_chat_message(self, message: str):
        """Handle new chat message"""
        if not message:
            return

        # Add user message
        st.session_state.chat_messages.append({
            'sender': 'user',
            'message': message,
            'timestamp': datetime.utcnow()
        })

        # Simulate support response
        # In production, this would integrate with your support chat system
        response = self._get_support_response(message)
        st.session_state.chat_messages.append({
            'sender': 'support',
            'message': response,
            'timestamp': datetime.utcnow()
        })

def _is_support_available(self) -> bool:
        """Check if support is currently available"""
        now = datetime.now()
        is_weekend = now.weekday() >= 5
        
        hours = self.support_hours['weekend'] if is_weekend else self.support_hours['weekday']
        current_hour = now.hour
        
        return hours['start'] <= current_hour < hours['end']

def _handle_attachments(self, files: List) -> List[str]:
        """Handle file attachments for tickets"""
        try:
            attachment_urls = []
            for file in files:
                # Upload file to storage
                success, url = self.support_ops.upload_attachment(
                    file.read(),
                    file.name,
                    st.session_state.user_id
                )
                if success:
                    attachment_urls.append(url)
            return attachment_urls
            
        except Exception as e:
            logger.error(f"Error handling attachments: {str(e)}")
            return []

def _send_ticket_confirmation(self, ticket_data: Dict):
        """Send ticket confirmation email"""
        user_data = self.user_ops.get_user(ticket_data['user_id'])
        
        template_data = {
            'user_name': user_data['name'],
            'ticket_id': ticket_data['id'],
            'subject': ticket_data['subject'],
            'category': self.categories[ticket_data['category']],
            'priority': self.priorities[ticket_data['priority']]['label'],
            'description': ticket_data['description'],
            'created_at': ticket_data['created_at'].strftime('%Y-%m-%d %H:%M'),
            'support_email': 'support@beaverinterviews.com'
        }
        
        email_service.send_email(
            user_data['email'],
            "Support Ticket Confirmation",
            'ticket_confirmation',
            template_data
        )

def _notify_support_team(self, ticket_data: Dict):
        """Notify support team about new ticket"""
        notification_service.send_notification(
            user_id="support_team",
            type=NotificationType.INFO,
            title=f"New Support Ticket: {ticket_data['subject']}",
            message=f"Priority: {self.priorities[ticket_data['priority']]['label']}",
            data=ticket_data
        )

def _add_ticket_update(self, ticket_id: str, message: str) -> bool:
        """Add update to support ticket"""
        try:
            if not message:
                st.error("Please enter an update message.")
                return False

            update_data = {
                'ticket_id': ticket_id,
                'user_id': st.session_state.user_id,
                'message': message,
                'timestamp': datetime.utcnow()
            }

            success = self.support_ops.add_ticket_update(update_data)
            
            if success:
                st.success("Update added successfully!")
                
                # Notify relevant parties
                self._notify_ticket_update(ticket_id, update_data)
                return True
            
            st.error("Failed to add update.")
            return False

        except Exception as e:
            logger.error(f"Error adding ticket update: {str(e)}")
            st.error("An error occurred while adding the update.")
            return False

def _notify_ticket_update(self, ticket_id: str, update_data: Dict):
        """Notify relevant parties about ticket update"""
        # Get ticket data
        ticket = self.support_ops.get_ticket(ticket_id)
        
        # Notify user if update is from support team
        if update_data['user_id'] != ticket['user_id']:
            notification_service.send_notification(
                user_id=ticket['user_id'],
                type=NotificationType.INFO,
                title=f"Update on Ticket #{ticket_id}",
                message=update_data['message'][:100] + "...",
                data={'ticket_id': ticket_id}
            )
        
        # Notify support team if update is from user
        else:
            notification_service.send_notification(
                user_id="support_team",
                type=NotificationType.INFO,
                title=f"User Update on Ticket #{ticket_id}",
                message=update_data['message'][:100] + "...",
                data={'ticket_id': ticket_id}
            )

def _get_support_response(self, message: str) -> str:
        """Get automated support response"""
        # In production, this would integrate with your support chat system
        # For now, return a simple automated response
        return (
            "Thank you for your message. A support representative will "
            "join the chat shortly. In the meantime, you might find helpful "
            "information in our Knowledge Base."
        )

def get_support_metrics(self) -> Dict:
        """Get support metrics for analytics"""
        try:
            metrics = {
                'total_tickets': self.support_ops.get_total_tickets(),
                'open_tickets': self.support_ops.get_open_tickets_count(),
                'avg_response_time': self.support_ops.get_average_response_time(),
                'satisfaction_rate': self.support_ops.get_satisfaction_rate(),
                'tickets_by_category': self.support_ops.get_tickets_by_category(),
                'tickets_by_priority': self.support_ops.get_tickets_by_priority()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting support metrics: {str(e)}")
            return {}

def export_ticket_history(self, user_id: str) -> Optional[str]:
        """Export user's ticket history to CSV"""
        try:
            tickets = self.support_ops.get_user_tickets(user_id)
            if not tickets:
                return None

            df = pd.DataFrame(tickets)
            csv = df.to_csv(index=False)
            
            # Create download link
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="ticket_history.csv">Download Ticket History</a>'
            
            return href
            
        except Exception as e:
            logger.error(f"Error exporting ticket history: {str(e)}")
            return None

def get_suggested_articles(self, ticket_data: Dict) -> List[Dict]:
        """Get suggested knowledge base articles based on ticket"""
        try:
            # Get keywords from ticket
            keywords = self._extract_keywords(
                f"{ticket_data['subject']} {ticket_data['description']}"
            )
            
            # Search knowledge base
            articles = self.support_ops.search_knowledge_base(" ".join(keywords))
            
            return articles[:3]  # Return top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error getting suggested articles: {str(e)}")
            return []

def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        # In production, use more sophisticated NLP
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to'}
        words = text.lower().split()
        return [word for word in words if word not in common_words]

# Initialize component
support_component = SupportComponent()

if __name__ == "__main__":
    support_component.render()