# app/components/help.py

import streamlit as st
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import json
from app.database.operations import SupportOperations, UserOperations
from app.services.notification_service import notification_service, NotificationType
from app.auth.authentication import require_auth
from app.utils.helpers import ValidationHelpers
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class HelpComponent:
    def __init__(self):
        """Initialize help component"""
        self.support_ops = SupportOperations()
        self.user_ops = UserOperations()
        self.validators = ValidationHelpers()
        
        # Load help content
        self.help_content = self._load_help_content()
        
        # Support ticket categories
        self.ticket_categories = {
            'technical': 'Technical Issues',
            'account': 'Account Management',
            'billing': 'Billing & Subscription',
            'feature': 'Feature Questions',
            'interview': 'Interview Process',
            'other': 'Other'
        }
        
        # Ticket priorities
        self.ticket_priorities = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High',
            'urgent': 'Urgent'
        }

    def _load_help_content(self) -> Dict:
        """Load help content from JSON file"""
        try:
            help_path = Path(__file__).parent.parent / 'data' / 'help_content.json'
            with open(help_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading help content: {str(e)}")
            return {}

    @require_auth
    def render(self):
        """Render the help interface"""
        st.title("Help & Support")

        # Apply custom styling
        self._apply_custom_styles()

        # Create main sections
        tabs = st.tabs([
            "Quick Help",
            "FAQ",
            "Support Tickets",
            "Tutorials",
            "Contact Support"
        ])

        with tabs[0]:
            self._render_quick_help()

        with tabs[1]:
            self._render_faq()

        with tabs[2]:
            self._render_support_tickets()

        with tabs[3]:
            self._render_tutorials()

        with tabs[4]:
            self._render_contact_support()

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .help-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .faq-question {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 0.5rem;
        }
        .tutorial-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .ticket-status {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        .status-open {
            background-color: #e1f5fe;
            color: #0288d1;
        }
        .status-closed {
            background-color: #e8f5e9;
            color: #388e3c;
        }
        .priority-urgent {
            color: #d32f2f;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_quick_help(self):
        """Render quick help section"""
        st.header("Quick Help")

        # Search bar
        search_query = st.text_input("Search for help", placeholder="Type your question...")
        
        if search_query:
            search_results = self._search_help_content(search_query)
            self._render_search_results(search_results)

        # Common issues
        st.subheader("Common Issues")
        for issue in self.help_content.get('common_issues', []):
            with st.expander(issue['title']):
                st.markdown(issue['solution'])
                if issue.get('video_url'):
                    st.video(issue['video_url'])

        # Quick tips
        st.subheader("Quick Tips")
        cols = st.columns(3)
        for i, tip in enumerate(self.help_content.get('quick_tips', [])):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="help-card">
                    <h4>{tip['title']}</h4>
                    <p>{tip['description']}</p>
                </div>
                """, unsafe_allow_html=True)

    def _render_faq(self):
        """Render FAQ section"""
        st.header("Frequently Asked Questions")

        # FAQ categories
        faq_category = st.selectbox(
            "Select Category",
            list(self.help_content.get('faq', {}).keys())
        )

        # Display FAQs for selected category
        if faq_category:
            for qa in self.help_content['faq'][faq_category]:
                with st.expander(qa['question']):
                    st.markdown(qa['answer'])
                    if qa.get('related_links'):
                        st.markdown("### Related Links")
                        for link in qa['related_links']:
                            st.markdown(f"- [{link['title']}]({link['url']})")

    def _render_support_tickets(self):
        """Render support tickets section"""
        st.header("Support Tickets")

        # Ticket actions
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Your Tickets")
        with col2:
            if st.button("Create New Ticket"):
                st.session_state.show_ticket_form = True

        # Show ticket form if requested
        if st.session_state.get('show_ticket_form', False):
            self._render_ticket_form()

        # Display existing tickets
        tickets = self.support_ops.get_user_tickets(st.session_state.user_id)
        if tickets:
            self._render_ticket_list(tickets)
        else:
            st.info("You don't have any support tickets yet.")

    def _render_tutorials(self):
        """Render tutorials section"""
        st.header("Tutorials")

        # Tutorial categories
        tutorial_category = st.selectbox(
            "Select Category",
            list(self.help_content.get('tutorials', {}).keys())
        )

        if tutorial_category:
            tutorials = self.help_content['tutorials'][tutorial_category]
            
            # Display tutorials
            for tutorial in tutorials:
                st.markdown(f"""
                <div class="tutorial-card">
                    <h4>{tutorial['title']}</h4>
                    <p>{tutorial['description']}</p>
                    <div style="margin-top: 1rem;">
                        <strong>Duration:</strong> {tutorial['duration']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if tutorial.get('video_url'):
                    st.video(tutorial['video_url'])
                
                if tutorial.get('steps'):
                    with st.expander("Step by Step Guide"):
                        for i, step in enumerate(tutorial['steps'], 1):
                            st.markdown(f"**Step {i}:** {step}")

    def _render_contact_support(self):
        """Render contact support section"""
        st.header("Contact Support")

        # Contact methods
        st.subheader("Contact Methods")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="help-card">
                <h4>Email Support</h4>
                <p>support@beaverinterviews.com</p>
                <p>Response time: 24 hours</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="help-card">
                <h4>Live Chat</h4>
                <p>Available 9 AM - 5 PM EST</p>
                <p>Response time: Immediate</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="help-card">
                <h4>Phone Support</h4>
                <p>1-800-BEAVER-HELP</p>
                <p>Available for Premium users</p>
            </div>
            """, unsafe_allow_html=True)

        # Contact form
        st.subheader("Send us a Message")
        with st.form("contact_form"):
            subject = st.text_input("Subject")
            message = st.text_area("Message")
            priority = st.select_slider(
                "Priority",
                options=list(self.ticket_priorities.keys()),
                format_func=lambda x: self.ticket_priorities[x]
            )
            
            if st.form_submit_button("Send Message"):
                self._handle_contact_submission(subject, message, priority)

    def _render_ticket_form(self):
        """Render support ticket creation form"""
        st.subheader("Create Support Ticket")
        
        with st.form("ticket_form"):
            category = st.selectbox(
                "Category",
                list(self.ticket_categories.keys()),
                format_func=lambda x: self.ticket_categories[x]
            )
            
            subject = st.text_input("Subject")
            description = st.text_area("Description")
            priority = st.select_slider(
                "Priority",
                options=list(self.ticket_priorities.keys()),
                format_func=lambda x: self.ticket_priorities[x]
            )
            
            files = st.file_uploader(
                "Attach Files (optional)",
                accept_multiple_files=True
            )
            
            if st.form_submit_button("Submit Ticket"):
                self._create_support_ticket(
                    category,
                    subject,
                    description,
                    priority,
                    files
                )

    def _render_ticket_list(self, tickets: List[Dict]):
        """Render list of support tickets"""
        for ticket in tickets:
            with st.expander(
                f"#{ticket['id']} - {ticket['subject']} "
                f"({self.ticket_priorities[ticket['priority']]})"
            ):
                st.markdown(f"""
                <div class="ticket-status status-{ticket['status']}">
                    {ticket['status'].title()}
                </div>
                <p><strong>Category:</strong> {self.ticket_categories[ticket['category']]}</p>
                <p><strong>Created:</strong> {ticket['created_at'].strftime('%Y-%m-%d %H:%M')}</p>
                <p>{ticket['description']}</p>
                """, unsafe_allow_html=True)
                
                # Show ticket updates
                if ticket.get('updates'):
                    st.markdown("### Updates")
                    for update in ticket['updates']:
                        st.markdown(f"""
                        <div class="help-card">
                            <p>{update['message']}</p>
                            <small>{update['timestamp'].strftime('%Y-%m-%d %H:%M')}</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Add update if ticket is open
                if ticket['status'] == 'open':
                    with st.form(f"update_ticket_{ticket['id']}"):
                        update_message = st.text_area("Add Update")
                        if st.form_submit_button("Submit Update"):
                            self._add_ticket_update(ticket['id'], update_message)

    def _search_help_content(self, query: str) -> List[Dict]:
        """Search help content for matching items"""
        results = []
        query = query.lower()
        
        # Search FAQs
        for category, faqs in self.help_content.get('faq', {}).items():
            for qa in faqs:
                if query in qa['question'].lower() or query in qa['answer'].lower():
                    results.append({
                        'type': 'FAQ',
                        'category': category,
                        'content': qa
                    })

        # Search tutorials
        for category, tutorials in self.help_content.get('tutorials', {}).items():
            for tutorial in tutorials:
                if query in tutorial['title'].lower() or query in tutorial['description'].lower():
                    results.append({
                        'type': 'Tutorial',
                        'category': category,
                        'content': tutorial
                    })

        return results

    def _render_search_results(self, results: List[Dict]):
        """Render search results"""
        if not results:
            st.info("No results found. Please try different keywords.")
            return

        st.subheader(f"Search Results ({len(results)})")
        
        for result in results:
            st.markdown(f"""
            <div class="help-card">
                <h4>{result['type']}: {result['content']['title']}</h4>
                <p>{result['content'].get('description', result['content'].get('answer', ''))}</p>
                <small>Category: {result['category']}</small>
            </div>
            """, unsafe_allow_html=True)

    def _create_support_ticket(self,
                             category: str,
                             subject: str,
                             description: str,
                             priority: str,
                             files: List = None) -> bool:
        """Create new support ticket"""
        try:
            if not subject or not description:
                st.error("Please fill in all required fields.")
                return False

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
                ticket_data['attachments'] = self._handle_file_attachments(files)

            # Create ticket
            ticket_id = self.support_ops.create_ticket(ticket_data)
            
            if ticket_id:
                st.success("Support ticket created successfully!")
                st.session_state.show_ticket_form = False
                
                # Notify support team
                self._notify_support_team(ticket_data)
                
                return True
            
            st.error("Failed to create support ticket.")
            return False

        except Exception as e:
            logger.error(f"Error creating support ticket: {str(e)}")
            st.error("An error occurred while creating the ticket.")
            return False

    def _handle_file_attachments(self, files: List) -> List[str]:
        """Handle file attachments for support tickets"""
        # Implementation depends on your file storage solution
        pass

    def _notify_support_team(self, ticket_data: Dict):
        """Notify support team about new ticket"""
        notification_service.send_notification(
            user_id="support_team",
            type=NotificationType.INFO,
            title=f"New Support Ticket: {ticket_data['subject']}",
            message=f"Priority: {self.ticket_priorities[ticket_data['priority']]}",
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

    def _handle_contact_submission(self, subject: str, message: str, priority: str) -> bool:
        """Handle contact form submission"""
        try:
            if not subject or not message:
                st.error("Please fill in all required fields.")
                return False

            contact_data = {
                'user_id': st.session_state.user_id,
                'subject': subject,
                'message': message,
                'priority': priority,
                'submitted_at': datetime.utcnow()
            }

            # Create support ticket from contact form
            ticket_id = self.support_ops.create_ticket({
                **contact_data,
                'category': 'other',
                'status': 'open'
            })

            if ticket_id:
                st.success("Message sent successfully! We'll get back to you soon.")
                
                # Send confirmation email to user
                self._send_contact_confirmation(contact_data)
                
                # Notify support team
                self._notify_support_team(contact_data)
                
                return True
            
            st.error("Failed to send message.")
            return False

        except Exception as e:
            logger.error(f"Error submitting contact form: {str(e)}")
            st.error("An error occurred while sending your message.")
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

    def _send_contact_confirmation(self, contact_data: Dict):
        """Send confirmation email for contact form submission"""
        from app.services.email_service import email_service
        
        user_data = self.user_ops.get_user(contact_data['user_id'])
        
        template_data = {
            'user_name': user_data['name'],
            'subject': contact_data['subject'],
            'message': contact_data['message'],
            'submitted_at': contact_data['submitted_at'].strftime('%Y-%m-%d %H:%M'),
            'support_email': 'support@beaverinterviews.com'
        }
        
        email_service.send_email(
            user_data['email'],
            "We've Received Your Message",
            'contact_confirmation',
            template_data
        )

    def get_help_article(self, article_id: str) -> Optional[Dict]:
        """Get specific help article by ID"""
        try:
            # Search through all content types
            for content_type, content in self.help_content.items():
                if isinstance(content, dict):
                    for category, items in content.items():
                        for item in items:
                            if item.get('id') == article_id:
                                return {
                                    'type': content_type,
                                    'category': category,
                                    'content': item
                                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting help article: {str(e)}")
            return None

    def mark_article_helpful(self, article_id: str) -> bool:
        """Mark help article as helpful"""
        try:
            return self.support_ops.update_article_metrics(
                article_id,
                {'helpful_votes': 1}
            )
        except Exception as e:
            logger.error(f"Error marking article as helpful: {str(e)}")
            return False

    def get_recommended_articles(self, user_id: str) -> List[Dict]:
        """Get recommended help articles based on user's history"""
        try:
            # Get user's interaction history
            user_history = self.support_ops.get_user_help_history(user_id)
            
            # Get user's tickets and common issues
            user_tickets = self.support_ops.get_user_tickets(user_id)
            
            # Simple recommendation logic
            recommended = []
            
            # Add articles related to user's tickets
            for ticket in user_tickets:
                related_articles = self._find_related_articles(
                    ticket['category'],
                    ticket['subject']
                )
                recommended.extend(related_articles)
            
            # Add popular articles in categories user hasn't seen
            seen_categories = {article['category'] for article in user_history}
            for category, articles in self.help_content.get('faq', {}).items():
                if category not in seen_categories:
                    recommended.extend(articles[:2])  # Add top 2 articles
            
            return recommended[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommended articles: {str(e)}")
            return []

    def _find_related_articles(self, category: str, query: str) -> List[Dict]:
        """Find articles related to a category and query"""
        related = []
        query = query.lower()
        
        # Search in FAQs
        if category in self.help_content.get('faq', {}):
            for article in self.help_content['faq'][category]:
                if query in article['question'].lower():
                    related.append(article)
        
        # Search in tutorials
        if category in self.help_content.get('tutorials', {}):
            for tutorial in self.help_content['tutorials'][category]:
                if query in tutorial['title'].lower():
                    related.append(tutorial)
        
        return related

# Initialize component
help_component = HelpComponent()

if __name__ == "__main__":
    help_component.render()