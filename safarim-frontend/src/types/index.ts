// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  phone: string;
  email: string | null;
  full_name: string;
  profile_photo: string | null;
  talk_level: "silent" | "normal" | "talkative";
  is_phone_verified: boolean;
  is_driver: boolean;
  is_admin: boolean;
  admin_role: "super_admin" | "moderator" | null;
  is_blocked: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

// ─── Locations ────────────────────────────────────────────────────────────────

export interface Region {
  id: number;
  name_uz: string;
  name_ru: string;
  slug: string;
  order: number;
}

export interface District {
  id: number;
  name_uz: string;
  name_ru: string;
  slug: string;
}

// ─── Trips ───────────────────────────────────────────────────────────────────

export interface LocationBrief {
  id: number;
  name_uz: string;
  name_ru: string;
}

export interface TripDriverInfo {
  id: string;
  full_name: string;
  profile_photo: string | null;
  talk_level: "silent" | "normal" | "talkative";
  rating_avg: number;
  rating_count: number;
  total_trips: number;
}

export interface WaypointResponse {
  id: string;
  region: LocationBrief;
  district: LocationBrief | null;
  address: string | null;
  order_index: number;
  price_from_start: number;
  arrival_time: string | null;
}

export type TripStatus = "active" | "completed" | "cancelled" | "full" | "expired";
export type LuggageSize = "small" | "medium" | "large";
export type PaymentType = "cash" | "click" | "payme" | "any";

export interface TripResponse {
  id: string;
  driver: TripDriverInfo;
  from_region: LocationBrief;
  from_district: LocationBrief | null;
  from_address: string | null;
  to_region: LocationBrief;
  to_district: LocationBrief | null;
  to_address: string | null;
  departure_date: string;      // "YYYY-MM-DD"
  departure_time: string;      // "HH:MM:SS"
  total_seats: number;
  available_seats: number;
  price_per_seat: number;
  payment_type: PaymentType;
  smoking_allowed: boolean;
  pets_allowed: boolean;
  women_only: boolean;
  luggage_size: LuggageSize;
  description: string | null;
  has_waypoints: boolean;
  waypoints: WaypointResponse[];
  status: TripStatus;
  share_token: string;
  created_at: string;
}

export interface DriverProfileResponse {
  id: string;
  user_id: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  vehicle_color: string;
  vehicle_plate: string;
  vehicle_seats: number;
  smoking_allowed: boolean;
  pets_allowed: boolean;
  music_allowed: boolean;
  luggage_size: LuggageSize;
  women_only: boolean;
  status: DriverStatus;
  rejection_reason: string | null;
  rating_avg: number;
  rating_count: number;
  total_trips: number;
  warning_count: number;
  is_on_pause: boolean;
  created_at: string;
}

// ─── Bookings ─────────────────────────────────────────────────────────────────

export type BookingStatus =
  | "pending"
  | "confirmed"
  | "awaiting_confirmation"
  | "disputed"
  | "cancelled"
  | "completed"
  | "no_show";
export type ConfirmAnswer = "yes" | "no" | null;
export type PaymentMethod = "cash" | "click" | "payme";
export type BookingPaymentStatus = "pending" | "paid" | "refunded" | "partial_refunded";

export interface BookingPassengerInfo {
  id: string;
  full_name: string;
  phone: string | null;
  profile_photo: string | null;
}

export interface BookingResponse {
  id: string;
  trip_id: string;
  passenger: BookingPassengerInfo;
  seats_count: number;
  price_per_seat: number;
  total_price: number;
  commission_rate: number;
  commission_amount: number;
  driver_amount: number;
  payment_method: PaymentMethod;
  payment_status: BookingPaymentStatus;
  status: BookingStatus;
  cancelled_by: "driver" | "passenger" | null;
  cancellation_reason: string | null;
  cancelled_at: string | null;
  refund_amount: number | null;
  no_show_reported_at: string | null;
  completed_at: string | null;
  // Ikki tomonlama safar tasdiqi
  driver_confirmed: ConfirmAnswer;
  passenger_confirmed: ConfirmAnswer;
  confirmation_requested_at: string | null;
  needs_my_confirmation: boolean;
  created_at: string;
  driver_phone: string | null;
  // trip included when fetching single booking
  trip?: TripResponse;
}

// ─── Messages ────────────────────────────────────────────────────────────────

export interface MessageSender {
  id: string;
  full_name: string;
  profile_photo: string | null;
}

export interface MessageResponse {
  id: string;
  booking_id: string;
  sender: MessageSender;
  content: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

// WebSocket dan keluvchi eventlar
export type WsEvent =
  | { type: "message";      data: MessageResponse }
  | { type: "read";         data: { reader_id: string } }
  | { type: "online_status"; data: { user_id: string; online: boolean } }
  | { type: "error";        data: { detail: string } };

// ─── Reviews ─────────────────────────────────────────────────────────────────

export interface ReviewerInfo {
  id: string;
  full_name: string;
  profile_photo: string | null;
}

export interface ReviewResponse {
  id: string;
  booking_id: string;
  reviewer: ReviewerInfo;
  reviewee: ReviewerInfo;
  reviewer_type: "passenger" | "driver";
  rating: number;
  comment: string | null;
  is_visible: boolean;
  review_deadline: string;
  created_at: string;
}

export interface DriverReviewsResponse {
  driver_id: string;
  rating_avg: number;
  rating_count: number;
  total_trips: number;
  reviews: ReviewResponse[];
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export type DriverStatus = "pending" | "approved" | "rejected" | "suspended";

export interface AdminDriverListItem {
  id: string;
  user_id: string;
  vehicle_plate: string;
  vehicle_make: string;
  vehicle_model: string;
  status: DriverStatus;
  created_at: string;
  user: {
    id: string;
    full_name: string;
    phone: string;
    profile_photo: string | null;
  };
}

export interface AdminDriverDocuments {
  license_url: string;
  vehicle: {
    make: string;
    model: string;
    year: number;
    color: string;
    plate: string;
    seats: number;
  };
}

export interface AdminStats {
  total_users: number;
  total_drivers: number;
  pending_drivers: number;
  total_trips: number;
  total_bookings: number;
  completed_bookings: number;
  disputed_bookings: number;
}

export interface AdminUsersResponse {
  total: number;
  page: number;
  users: User[];
}

// ─── Notifications ────────────────────────────────────────────────────────────

export type NotificationRefType = "booking" | "trip" | "review" | "system";

export interface NotificationResponse {
  id: string;
  title: string;
  body: string;
  ref_type: NotificationRefType | null;
  ref_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}
