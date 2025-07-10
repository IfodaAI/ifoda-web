from rest_framework.routers import DefaultRouter

from app.views import PillsViewSet, BranchViewSet, DiseasesViewSet, OrderViewSet, OrderToPillsViewSet, \
    OrderToDiseasesViewSet, ImageViewSet, TelegramUserViewSet, LanguageViewSet, PaymentViewSet, OrderItemsViewSet, \
    DeliveryCostViewSet, MessageViewSet,UsersViewSet

router = DefaultRouter()
router.register(r'pills_api', PillsViewSet, basename='pills')
router.register(r'branch_api', BranchViewSet, basename='branch')
router.register(r'diseases_api', DiseasesViewSet, basename='diseases')
router.register(r'order_api', OrderViewSet, basename='order')
router.register(r'images_api', ImageViewSet, basename='images')
router.register(r'ordertopills_api', OrderToPillsViewSet, basename='ordertopills')
router.register(r'ordertodiseases_api', OrderToDiseasesViewSet, basename='ordertodiseases')
router.register(r'telegramuser_api', TelegramUserViewSet, basename='telegramuser')
router.register(r'language_api', LanguageViewSet, basename='language')
router.register(r'payment_api', PaymentViewSet, basename='payme')
router.register(r'deliverycost_api', DeliveryCostViewSet, basename='deliverycost')
router.register(r'orderitems_api', OrderItemsViewSet, basename='orderitems')
router.register(r'message_api', MessageViewSet, basename='message')
router.register(r"users_api", UsersViewSet, basename="user")