from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.utils import timezone

from .models import OrderStatusLog


def user_is_driver(user):
    return user.is_authenticated and user.groups.filter(name='driver').exists()


def user_is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='admin').exists()
    )


def can_manage_order_status(user):
    """
    Admin και απλοί users μπορούν να αλλάζουν status παραγγελίας.
    Driver δεν αλλάζει από dropdown — έχει δικά του κουμπιά Παραλαβή / Παράδοση.
    """
    return user.is_authenticated and not user_is_driver(user)


def create_status_log(order, user, old_status, new_status, comment=''):
    OrderStatusLog.objects.create(
        order=order,
        changed_by=user,
        old_status=old_status or '',
        new_status=new_status,
        comment=comment,
    )


def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_km * c


def set_estimated_arrival(order):
    source = order.source_branch
    destination = order.destination_branch

    if (
        source.latitude is not None and source.longitude is not None and
        destination.latitude is not None and destination.longitude is not None
    ):
        distance_km = haversine_km(
            float(source.latitude),
            float(source.longitude),
            float(destination.latitude),
            float(destination.longitude),
        )

        average_city_speed_kmh = 28
        estimated_minutes = max(8, round((distance_km / average_city_speed_kmh) * 60))
    else:
        estimated_minutes = 20

    order.estimated_minutes = estimated_minutes
    order.estimated_arrival = timezone.now() + timedelta(minutes=estimated_minutes)


def order_has_map_data(order):
    source = order.source_branch
    destination = order.destination_branch

    return (
        source.latitude is not None and source.longitude is not None and
        destination.latitude is not None and destination.longitude is not None
    )