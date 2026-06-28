from fastapi import APIRouter
from app.api.v1 import auth, users, locations, drivers, trips, bookings, reviews, payments, messages, notifications, admin

api_router = APIRouter()

api_router.include_router(auth.router,          prefix="/auth",          tags=["Auth"])
api_router.include_router(users.router,         prefix="/users",         tags=["Users"])
api_router.include_router(locations.router,     prefix="/locations",     tags=["Locations"])
api_router.include_router(drivers.router,       prefix="/drivers",       tags=["Drivers"])
api_router.include_router(trips.router,         prefix="/trips",         tags=["Trips"])
api_router.include_router(bookings.router,      prefix="/bookings",      tags=["Bookings"])
api_router.include_router(reviews.router,       prefix="/reviews",       tags=["Reviews"])
api_router.include_router(payments.router,      prefix="/payments",      tags=["Payments"])
api_router.include_router(messages.router,      prefix="/messages",      tags=["Messages"])
api_router.include_router(notifications.router, prefix="/notifications",  tags=["Notifications"])
api_router.include_router(admin.router,         prefix="/admin",         tags=["Admin"])
