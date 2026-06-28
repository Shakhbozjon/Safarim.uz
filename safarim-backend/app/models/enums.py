import enum


class TalkLevel(str, enum.Enum):
    silent = "silent"
    normal = "normal"
    talkative = "talkative"


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    moderator = "moderator"


class OtpPurpose(str, enum.Enum):
    register = "register"
    login = "login"
    password_reset = "password_reset"
    change_phone = "change_phone"


class DriverStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LuggageSize(str, enum.Enum):
    small = "small"
    medium = "medium"
    large = "large"


class PaymentType(str, enum.Enum):
    cash = "cash"
    click = "click"
    payme = "payme"
    any = "any"


class TripStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    full = "full"
    expired = "expired"   # Vaqti o'tdi, yo'lovchi yig'ilmadi — jazosiz arxiv


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    click = "click"
    payme = "payme"


class BookingPaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"
    partial_refunded = "partial_refunded"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    awaiting_confirmation = "awaiting_confirmation"  # safar o'tdi, ikki tomon tasdiqi kutilmoqda
    disputed = "disputed"                            # nizo (yo'lovchi vs haydovchi) — admin hal qiladi
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


# Safar tasdiqi javoblari (bookings.driver_confirmed / passenger_confirmed)
# String sifatida saqlanadi; NULL = javob bermadi (jim)
CONFIRM_YES = "yes"
CONFIRM_NO = "no"


class CancelledBy(str, enum.Enum):
    driver = "driver"
    passenger = "passenger"


class ReviewerType(str, enum.Enum):
    passenger = "passenger"
    driver = "driver"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    partial_refunded = "partial_refunded"


class NotificationChannel(str, enum.Enum):
    sms = "sms"
    telegram = "telegram"
    email = "email"
    inapp = "inapp"


class NotificationRefType(str, enum.Enum):
    booking = "booking"
    trip = "trip"
    review = "review"
    system = "system"


class WalletTxType(str, enum.Enum):
    cash_commission = "cash_commission"   # naqd safardan komissiya ushildi (-)
    online_earning  = "online_earning"    # online safar tugadi, daromad (+)
    topup           = "topup"             # haydovchi to'ldirdi (+)
    withdrawal      = "withdrawal"        # haydovchi yechib oldi (-)
    refund          = "refund"            # bekor qilingandan qaytarildi (+)


class AdminActionType(str, enum.Enum):
    approve_driver = "approve_driver"
    reject_driver = "reject_driver"
    block_user = "block_user"
    unblock_user = "unblock_user"
    warn_driver = "warn_driver"
    cancel_trip = "cancel_trip"
