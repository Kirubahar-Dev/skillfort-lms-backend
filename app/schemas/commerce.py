from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    course_id: int
    amount: int


class ConfirmOrderRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class OrderOut(BaseModel):
    id: int
    order_id: str
    course_id: int
    amount: int
    status: str


class SendMailRequest(BaseModel):
    recipient: str
    subject: str
    body: str
