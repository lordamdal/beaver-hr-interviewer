# app/services/payment_service.py

import stripe
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from app.config.settings import settings
from app.database.operations import UserOperations
import json
import asyncio
from pathlib import Path
import hmac
import hashlib

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        """Initialize payment service with Stripe"""
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY.get_secret_value()
            self.user_ops = UserOperations()
            self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET.get_secret_value()
            
            # Price IDs for different plans
            self.price_ids = {
                'basic': settings.STRIPE_BASIC_PRICE_ID,
                'premium': settings.STRIPE_PREMIUM_PRICE_ID
            }
            
            # Setup webhook handler
            self.webhook_handlers = {
                'checkout.session.completed': self._handle_checkout_completed,
                'invoice.paid': self._handle_invoice_paid,
                'invoice.payment_failed': self._handle_payment_failed,
                'customer.subscription.deleted': self._handle_subscription_deleted
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize payment service: {str(e)}")
            raise

    async def create_checkout_session(self, 
                                    user_id: str, 
                                    plan: str) -> Tuple[bool, Optional[str]]:
        """
        Create Stripe checkout session for subscription
        
        Args:
            user_id: User ID
            plan: Subscription plan name
            
        Returns:
            Tuple of (success_status, session_url)
        """
        try:
            user = self.user_ops.get_user(user_id)
            
            # Create or get Stripe customer
            if not user.get('stripe_customer_id'):
                customer = await self._create_stripe_customer(user)
                self.user_ops.update_user(user_id, {
                    'stripe_customer_id': customer.id
                })
            else:
                customer = stripe.Customer.retrieve(user['stripe_customer_id'])

            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': self.price_ids[plan],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{settings.APP_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.APP_URL}/subscription/cancel",
                metadata={
                    'user_id': user_id,
                    'plan': plan
                }
            )
            
            return True, session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return False, None

    async def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user subscription"""
        try:
            user = self.user_ops.get_user(user_id)
            if not user.get('stripe_subscription_id'):
                return False

            # Cancel subscription at period end
            stripe.Subscription.modify(
                user['stripe_subscription_id'],
                cancel_at_period_end=True
            )
            
            # Update user record
            self.user_ops.update_user(user_id, {
                'subscription_end_date': datetime.utcnow() + timedelta(days=30),
                'cancellation_date': datetime.utcnow()
            })
            
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return False

    async def update_payment_method(self, 
                                  user_id: str, 
                                  payment_method_id: str) -> bool:
        """Update payment method"""
        try:
            user = self.user_ops.get_user(user_id)
            if not user.get('stripe_customer_id'):
                return False

            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user['stripe_customer_id']
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                user['stripe_customer_id'],
                invoice_settings={
                    'default_payment_method': payment_method.id
                }
            )
            
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating payment method: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating payment method: {str(e)}")
            return False

    def get_payment_history(self, user_id: str) -> List[Dict]:
        """Get user's payment history"""
        try:
            user = self.user_ops.get_user(user_id)
            if not user.get('stripe_customer_id'):
                return []

            # Get all payments
            payments = stripe.PaymentIntent.list(
                customer=user['stripe_customer_id'],
                limit=100
            )
            
            return [{
                'date': datetime.fromtimestamp(payment.created),
                'amount': payment.amount / 100,  # Convert cents to dollars
                'status': payment.status,
                'description': payment.description
            } for payment in payments.data]
            
        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}")
            return []

    async def handle_webhook(self, payload: bytes, signature: str) -> bool:
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            # Handle event
            handler = self.webhook_handlers.get(event.type)
            if handler:
                await handler(event.data.object)
                return True
            
            logger.warning(f"Unhandled webhook event type: {event.type}")
            return False
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return False

    async def _create_stripe_customer(self, user: Dict) -> stripe.Customer:
        """Create Stripe customer"""
        return stripe.Customer.create(
            email=user['email'],
            metadata={
                'user_id': user['id']
            }
        )

    async def _handle_checkout_completed(self, session: stripe.checkout.Session):
        """Handle successful checkout"""
        try:
            user_id = session.metadata['user_id']
            plan = session.metadata['plan']
            
            # Update user subscription
            self.user_ops.update_user(user_id, {
                'subscription_plan': plan,
                'stripe_subscription_id': session.subscription,
                'subscription_start_date': datetime.utcnow(),
                'subscription_end_date': datetime.utcnow() + timedelta(days=30)
            })
            
        except Exception as e:
            logger.error(f"Error handling checkout completion: {str(e)}")

    async def _handle_invoice_paid(self, invoice: stripe.Invoice):
        """Handle successful payment"""
        try:
            subscription = stripe.Subscription.retrieve(invoice.subscription)
            user = self.user_ops.get_user_by_stripe_customer(invoice.customer)
            
            if user:
                # Update subscription end date
                self.user_ops.update_user(user['id'], {
                    'subscription_end_date': datetime.fromtimestamp(
                        subscription.current_period_end
                    )
                })
                
        except Exception as e:
            logger.error(f"Error handling invoice payment: {str(e)}")

    async def _handle_payment_failed(self, invoice: stripe.Invoice):
        """Handle failed payment"""
        try:
            user = self.user_ops.get_user_by_stripe_customer(invoice.customer)
            if user:
                # Send payment failure notification
                # Implement notification service
                pass
                
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}")

    async def _handle_subscription_deleted(self, subscription: stripe.Subscription):
        """Handle subscription cancellation"""
        try:
            user = self.user_ops.get_user_by_stripe_subscription(subscription.id)
            if user:
                # Update user to free plan
                self.user_ops.update_user(user['id'], {
                    'subscription_plan': 'free',
                    'stripe_subscription_id': None,
                    'subscription_end_date': None
                })
                
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {str(e)}")

    def get_subscription_status(self, user_id: str) -> Dict:
        """Get detailed subscription status"""
        try:
            user = self.user_ops.get_user(user_id)
            if not user.get('stripe_subscription_id'):
                return {
                    'status': 'inactive',
                    'plan': 'free'
                }

            subscription = stripe.Subscription.retrieve(user['stripe_subscription_id'])
            return {
                'status': subscription.status,
                'plan': user['subscription_plan'],
                'current_period_end': datetime.fromtimestamp(
                    subscription.current_period_end
                ),
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Initialize payment service
payment_service = PaymentService()

if __name__ == "__main__":
    # Test payment service
    async def test_payment_service():
        # Test checkout session creation
        success, url = await payment_service.create_checkout_session(
            "test_user_id",
            "basic"
        )
        print(f"Checkout session created: {success}, URL: {url}")
        
        # Test payment history
        history = payment_service.get_payment_history("test_user_id")
        print(f"Payment history: {history}")
        
        # Test subscription status
        status = payment_service.get_subscription_status("test_user_id")
        print(f"Subscription status: {status}")

    asyncio.run(test_payment_service())