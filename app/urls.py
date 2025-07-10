from django.urls import path

from .views import *

urlpatterns = [
    path("api/statistics/", StatisticsAPIView.as_view(), name="statistics"),
    path('ai_model_prediction/', ai_model_prediction, name='ai_model_prediction'),
    path('order_select_api/<str:id>/', order_select),
    path("api/notify/", TriggerNotification.as_view(), name="notify"),

    path('registration/', RegisterView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('me/', UserMeView.as_view(), name='me'),

    path('signin/', log_in, name='signin'),
    path('log_out/', log_out, name='log_out'),

    path('',home,name='home'),
    path('order/',order,name='order'),
    path('order/<str:id>/',order_detail,name='order_detail'),
    path('get_order_items/<str:id>/', get_order_items, name='get_order_items'),
    path('order/delete/<str:id>/', delete_order, name='delete_order'),
    path('dori/',dori,name='dori'),
    path('dori/<str:id>/',dori,name='dori'),
    path('dori/delete/<str:id>/', delete_dori, name='delete_dori'),
    path('kasallik/',kasallik,name='kasallik'),
    path('kasallik/<str:id>/',kasallik,name='kasallik'),
    path('kasallik/detail/<str:id>/',kasallik_detail,name='kasallik_detail'),
    path('kasallik/delete/<str:id>/', delete_kasallik, name='delete_kasallik'),
    path('users/',users,name='users'),
    path('users/<str:id>/',users,name='users'),
    path('users/delete/<str:id>/', delete_user, name='delete_user'),
    path('branch/', branch, name='branch'),
    path('branch/<str:id>/', branch, name='branch'),
    path('branch/delete/<str:id>/', delete_branch, name='delete_branch'),
    path('translate/',translate,name='translate'),
    path('settings/',settings,name='settings'),
    path('settings/<str:id>/',settings,name='settings'),

    path('upload_image/', upload_image_view, name='upload_image'),

    path('api/click-prepare/', ClickPrepareAPIView.as_view(), name='click-prepare'),
    path('api/click-complete/', ClickCompleteAPIView.as_view(), name='click-complete'),
    path('generate-payme-link/', GeneratePayLinkAPIView.as_view(), name='generate-pay-link'),

]
