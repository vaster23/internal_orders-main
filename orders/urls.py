from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('shop/', views.order_shop, name='order_shop'),
    path('export/csv/', views.export_orders_csv, name='export_orders_csv'),
    path('<int:order_id>/pickup/', views.driver_pickup_order, name='driver_pickup_order'),
    path('<int:order_id>/deliver/', views.driver_deliver_order, name='driver_deliver_order'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
]