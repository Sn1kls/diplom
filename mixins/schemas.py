from ninja import Schema


class ErrorSchema(Schema):
    """Schema for error responses"""

    error: str


class MessageSchema(Schema):
    """Message response with a single detail field"""

    detail: str
