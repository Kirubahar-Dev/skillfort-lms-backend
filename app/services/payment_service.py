import razorpay
from app.utils.config import get_settings


class RazorpayService:
    def __init__(self):
        settings = get_settings()
        self.enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
        self.key_id = settings.razorpay_key_id
        self.client = None
        if self.enabled:
            self.client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    def create_order(self, amount: int, receipt: str) -> dict:
        if not self.enabled:
            return {"id": f"demo_{receipt}", "amount": amount, "currency": "INR", "status": "created"}
        return self.client.order.create({"amount": amount, "currency": "INR", "receipt": receipt, "payment_capture": 1})

    def verify_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        if not self.enabled:
            return True
        self.client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return True
