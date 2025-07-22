from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from payme.payme.methods.generate_link import GeneratePayLink
from .aws_s3 import upload_image
from .logix_api import logix_post
from .models import Pills, Branch, Diseases, Order, OrderToPills, OrderToDiseases, User, Image, OrderItems, Payment, \
    TelegramUser, Language, DeliveryCost, Messages
from .serializers import PillsSerializer, BranchSerializer, DiseasesSerializer, OrderSerializer, OrderToPillsSerializer, \
    OrderToDiseasesSerializer, UserLoginSerializer, UserSignupSerializer, UserMeSerializer, ImageSerializer, \
    TelegramUserSerializer, LanguageSerializer, PaymentSerializer, OrderItemsSerializer, DeliveryCostSerializer, \
    MessageSerializer, ClickPrepareRequestSerializer, ClickCompleteRequestSerializer, PaymeLinkSerializer,UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.decorators import login_required
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q, Count, OuterRef, Subquery
from urllib.parse import urlencode
import os,json,hashlib,requests
from dotenv import load_dotenv
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from urllib.parse import urlparse
from django.conf import settings as django_settings
from .ai import generate_prompt
from rest_framework.pagination import PageNumberPagination


class ConditionalPaginationMixin:
    class OptionalPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
    
    def list(self, request, *args, **kwargs):
        is_paginated = request.query_params.get('isPaginated', 'false').lower() == 'true'
        
        if is_paginated:
            self.pagination_class = self.OptionalPagination
        else:
            self.pagination_class = None
            
        return super().list(request, *args, **kwargs)


class TriggerNotification(APIView):
    def post(self, request):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications", {"type": "notify", "message": {"message": "New notification received!"}}
        )
        return Response({"status": "sent"})

@csrf_exempt  # Only if you need to bypass CSRF protection
def ai_model_prediction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        order=Order.objects.get(id=order_id)
        last_message = order.messages.last()
        
        # Extract just the path from the URL
        image_url = str(last_message.image_url)
        parsed_url = urlparse(image_url)
        relative_path  = parsed_url.path

        # Remove the /media/ prefix if it exists (since MEDIA_ROOT already includes this)
        if relative_path.startswith('/media/'):
            relative_path = relative_path[7:]  # Remove '/media/'
        
        # Combine with MEDIA_ROOT to get the full system path
        full_image_path = os.path.join(django_settings.MEDIA_ROOT, relative_path)
        response=generate_prompt(full_image_path)
        if response:
            disease=Diseases.objects.filter(name__contains=response).first()
            # pill_ids listiga UUID lar string formatida saqlanadi
            pill_ids = [str(uuid_obj) for uuid_obj in disease.pills.values_list('id', flat=True)]
            return JsonResponse({
                'success': True,
                'pills': pill_ids,
                'diseases': [disease.id],  # Optional
                'order_id':order_id,
                "response":response
            })
        # diseases = list(Diseases.objects.values_list("id", "name", "description"))
        # formatted_diseases = [f"{str(disease_id)}:{name}.{description}" for disease_id, name, description in diseases]
        # diseases=list(Diseases.objects.values("id", "name", "description"))
        
        # Here you would call your AI model with the order information
        # This is a placeholder for your actual AI logic
        # Replace with your actual implementation
        
        # Example response with pill IDs
        pill_ids = [1, 3, 5]  # Replace with your actual AI-predicted pill IDs
        disease_ids = [2, 4]  # Optional: disease IDs if your API returns these
        
        return JsonResponse({
            'success': True,
            # 'pills': pill_ids,
            'diseases': disease_ids,  # Optional
            'order_id':order_id,
            "response":response
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

class GeneratePayLinkAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = PaymeLinkSerializer(data=request.data)
        if serializer.is_valid():
            order_id = serializer.validated_data['order_id']
            amount = serializer.validated_data['amount']

            try:
                pay_link_generator = GeneratePayLink(order_id=order_id, amount=amount)
                pay_link = pay_link_generator.generate_link()

                return Response({"payme_link": pay_link}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClickPrepareAPIView(APIView):
    permission_classes = [AllowAny]
    load_dotenv()

    def post(self, request, *args, **kwargs):
        serializer = ClickPrepareRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            click_trans_id = data["click_trans_id"]
            service_id = data["service_id"]
            merchant_trans_id = data["merchant_trans_id"]
            amount = data["amount"]
            action = data["action"]
            sign_time = data["sign_time"]
            sign_string = data["sign_string"]
            print('data:', data)

            # Kutilgan sign_string ni yaratish
            # generated_sign_string = self.generate_sign_string(
            #     data=data, SECRET_KEY=os.getenv("CLICK_SERVICE_ID")
            # )
            #
            # # sign_string ni tekshirish
            # print('generated_sign_string:', generated_sign_string)
            # if sign_string != generated_sign_string:
            #     return JsonResponse({
            #         "click_trans_id": click_trans_id,
            #         "merchant_trans_id": merchant_trans_id,
            #         "merchant_prepare_id": None,
            #         "error": -1,
            #         "error_note": "Signature verification error"
            #     }, status=400)

            if action == 0:
                if service_id != int(os.getenv("CLICK_SERVICE_ID")):
                    print("Service ID does not match")
                    return JsonResponse({
                        "error": -4,
                        "error_note": "Service ID does not match"
                    }, status=400)
                order = Order.objects.get(id=merchant_trans_id)
                if order:
                    if float(order.total_amount) != float(amount):
                        print("Invalid payme amount")
                        return JsonResponse({
                            "error": -2,
                            "error_note": "Invalid payme amount"
                        }, status=400)
                    return JsonResponse({
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": 123456,
                        "error": 0,
                        "error_note": "Success"
                    })
                print("Order does not exist")
                return JsonResponse({
                    "error": -5,
                    "error_note": "Order does not exist"
                }, status=400)

            else:
                print("Unknown action")
                return JsonResponse({
                    "error": -3,
                    "error_note": "Unknown action"
                }, status=400)
        return Response(serializer.errors, status=400)

    def generate_sign_string(self, data, SECRET_KEY):
        sign_string = f"{data['click_trans_id']}{data['service_id']}{SECRET_KEY}{data['merchant_trans_id']}{data['amount']}{data['action']}{data['sign_time']}"
        return hashlib.md5(sign_string.encode()).hexdigest()


class ClickCompleteAPIView(APIView):
    permission_classes = [AllowAny]
    load_dotenv()

    def post(self, request, *args, **kwargs):
        serializer = ClickCompleteRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            click_trans_id = data["click_trans_id"]
            service_id = data["service_id"]
            merchant_trans_id = data["merchant_trans_id"]
            click_paydoc_id = data["click_paydoc_id"]
            amount = data["amount"]
            action = data["action"]
            sign_time = data["sign_time"]
            sign_string = data["sign_string"]
            print('data:', data)

            # Kutilgan sign_string ni yaratish
            # generated_sign_string = self.generate_sign_string(
            #     data=data, SECRET_KEY=os.getenv("CLICK_SERVICE_ID")
            # )
            #
            # # sign_string ni tekshirish
            # print('generated_sign_string:', generated_sign_string)
            # if sign_string != generated_sign_string:
            #     return JsonResponse({
            #         "click_trans_id": click_trans_id,
            #         "merchant_trans_id": merchant_trans_id,
            #         "merchant_prepare_id": None,
            #         "error": -1,
            #         "error_note": "Invalid sign string"
            #     }, status=400)

            # Complete bosqichiga qarab javob berish
            if action == 1:  # Complete bosqichi
                if service_id != int(os.getenv("CLICK_SERVICE_ID")):
                    print("Service ID does not match")
                    return JsonResponse({
                        "error": -4,
                        "error_note": "Service ID does not match"
                    }, status=400)
                order = Order.objects.get(id=merchant_trans_id)
                if order:
                    if float(order.total_amount) != float(amount):
                        print("Invalid payme amount")
                        return JsonResponse({
                            "error": -2,
                            "error_note": "Invalid payme amount"
                        }, status=400)
                    try:
                        payment_exists = Payment.objects.filter(order=order).exists()
                        order.status = 'COMPLETED'
                        order.save()
                        if not payment_exists:
                            Payment.objects.create(
                                order=order,
                                payment_method='click',
                                amount=amount,
                                payment_status='completed'
                            )
                    except Exception as error:
                        print('Clickda payment yaartishda xatolik yuz berdi: ', error)

                    load_dotenv()
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    chat_id = order.user.telegram_id
                    language = order.user.language.name
                    if language == 'uz':
                        text = """To'lov muvaffaqiyatli amalga oshildi ✅
Buyurtma 24 soat ichida yetkazib beriladi.
Ishonchingiz uchun minnatdormiz
IFODA kompaniyasini tanlaganingizdan mamnunmiz
Birgalikda yetishtiramiz!"""
                        keyword_text = 'Yangi Buyurtma'
                    elif language == 'ru':
                        text = 'Платеж прошел успешно ✅\nСпасибо за ваш заказ!'
                        keyword_text = 'Новый Заказ'
                    else:
                        text = 'The payment was successfully ✅\nThank you for your order!'
                        keyword_text = 'New Order'
                    reply_keyboard = {
                        "keyboard": [
                            [{"text": keyword_text}]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True
                    }
                    try:
                        response = requests.post(
                            url=f'https://api.telegram.org/bot{bot_token}/sendMessage',
                            data={
                                'chat_id': chat_id,
                                'text': text,
                                'parse_mode': 'HTML',
                                'reply_markup': json.dumps(reply_keyboard)
                            }
                        ).json()
                    except Exception as e:
                        print('clickda Telegramga xabar yuborishda xatolik yuz berdi: ', e)

                    timestamp = int(datetime.strptime(sign_time, "%Y-%m-%d %H:%M:%S").timestamp())
                    digest = hashlib.sha1((str(timestamp) + os.getenv("CLICK_SECRET_KEY")).encode()).hexdigest()
                    headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'Auth': f'{os.getenv("click_merchant_user_id")}:{digest}:{timestamp}',
                    }
                    print('headers:', headers)

                    items = []
                    order_items = OrderItems.objects.filter(order=order)
                    try:
                        branch_id = order.branch.branch_id
                        for item in order_items:
                            product_id = item.pills.product_id
                            quantity = item.quantity
                            price = item.price
                            if not item.pills.small_product:
                                res_logix = logix_post(branch_id=branch_id, product_id=product_id, quantity=quantity, price=price)
                                if not res_logix:
                                    item.logix_status = 'ERROR'
                    except Exception as e:
                        print('LogiX apida xatolik: ', e)

                    for item in order_items:
                        items.append({
                            'Name': item.pills.name,
                            'Price': float(item.price)*100 * int(item.quantity),
                            'SPIC': item.pills.spic,
                            'PackageCode': item.pills.package_code,
                            'Amount': int(item.quantity) * 1000,
                            'VAT': (float(float(item.price)*100 * int(item.quantity))/1.12) * 0.12,
                            'VATPercent': 12,
                            'CommissionInfo': {
                                 "TIN": '206019226'
                            },
                        })

                    if order.delivery_method == 'DELIVERY':
                        items.append({
                            'Name': "Доставка",
                            'Price': float(order.delivery_price) * 100,
                            'SPIC': '10112006002000000',
                            'PackageCode': '1542432',
                            'Amount': 1000,
                            'VAT': (float(order.delivery_price) * 100 / 1.12) * 0.12,
                            'VATPercent': 12,
                            'CommissionInfo': {
                                "TIN": '206019226'
                            },
                        })

                    json_data = {
                        'service_id': service_id,
                        'payment_id': click_paydoc_id,
                        'items': items,
                        'received_ecash': amount * 100,
                        'received_cash': 0,
                        'received_card': 0,
                    }
                    print('json_data:',json_data)

                    response = requests.post('https://api.click.uz/v2/merchant/payment/ofd_data/submit_items',
                                             headers=headers, json=json_data)
                    print('check status: ', response.status_code, response.json())

                    return JsonResponse({
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": 123456,
                        "error": 0,
                        "error_note": "Success"
                    })
                print("Order does not exist")
                return JsonResponse({
                    "error": -5,
                    "error_note": "Order does not exist"
                }, status=400)


            else:
                print("Unknown action")
                return JsonResponse({
                    "error": -3,
                    "error_note": "Unknown action"
                }, status=400)
        return Response(serializer.errors, status=400)

    def generate_sign_string(self, data, SECRET_KEY):
        sign_string = f"{data['click_trans_id']}{data['service_id']}{SECRET_KEY}{data['merchant_trans_id']}{data['amount']}{data['action']}{data['sign_time']}"
        return hashlib.md5(sign_string.encode()).hexdigest()


class MessageViewSet(ModelViewSet):
    # queryset = Messages.objects.all()
    serializer_class = MessageSerializer
    filterset_fields=["order"]
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Messages.objects.all()
        params = self.request.query_params

        order_id = params.get("order")
        if order_id:
            qs = qs.filter(order__id=order_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()
            channel_layer = get_channel_layer()
            print('message', message)
            order_id = message.order.id
            # async_to_sync(channel_layer.group_send)(
            #     f'chat_{order_id}',
            #     {
            #         "type": "chat_message",
            #         "text": message.text if message.text else "",
            #         "message_type": message.type,
            #         "sender": message.sender,
            #         "image_url": message.image_url if message.image_url else "",
            #         "timestamp": str(message.timestamp),
            #     },
            # )
            async_to_sync(channel_layer.group_send)(
                f'chat_{order_id}',
                {
                    "type": "chat_message",
                    "message": {
                        "id": str(message.id),
                        "type": message.type,
                        "sender": message.sender,
                        "status": message.status,
                        "text": message.text if message.text else "",
                        "image_url": request.build_absolute_uri(message.image.url) if message.image else "",
                        "timestamp": str(message.timestamp),
                    }
                },
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PillsViewSet(ConditionalPaginationMixin, ModelViewSet):
    queryset = Pills.objects.order_by("-created_at")
    serializer_class = PillsSerializer
    filterset_fields = { 'name': ['icontains'] }
    permission_classes = [IsAuthenticatedOrReadOnly]

class BranchViewSet(ConditionalPaginationMixin, ModelViewSet):
    queryset = Branch.objects.order_by("-created_at")
    serializer_class = BranchSerializer
    filterset_fields = { 'name': ['icontains'] }

class DiseasesViewSet(ConditionalPaginationMixin, ModelViewSet):
    queryset = Diseases.objects.order_by("-created_at")
    serializer_class = DiseasesSerializer
    filterset_fields = { 'name': ['icontains'] }

class OrderViewSet(ConditionalPaginationMixin, ModelViewSet):
    queryset = Order.objects.all().order_by('-order_updated_date')
    serializer_class = OrderSerializer
    filterset_fields = { 'user__fullname': ['icontains'],'is_chat': ['exact'],'status': ['exact'],}
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        user_id=request.GET.get("user_id")
        user=TelegramUser.objects.get(telegram_id=user_id)
        queryset=self.filter_queryset(self.get_queryset()).filter(user=user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class ImageViewSet(ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer

class DeliveryCostViewSet(ModelViewSet):
    queryset = DeliveryCost.objects.all()
    serializer_class = DeliveryCostSerializer


class OrderToPillsViewSet(ModelViewSet):
    queryset = OrderToPills.objects.all()
    serializer_class = OrderToPillsSerializer

    @action(detail=False, methods=['get'], url_path='get-order-id/(?P<order_id>[^/.]+)')
    def get_by_order_id(self, request, order_id=None):
        if not order_id:
            return Response(
                {"error": "order_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            orders = OrderToPills.objects.filter(order_id=order_id)
            serializer = self.get_serializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except OrderToPills.DoesNotExist:
            return Response(
                {"error": f"OrderToPills with order_id {order_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )


class OrderToDiseasesViewSet(ModelViewSet):
    queryset = OrderToDiseases.objects.all()
    serializer_class = OrderToDiseasesSerializer

    @action(detail=False, methods=['get'], url_path='get-order-id/(?P<order_id>[^/.]+)')
    def get_by_order_id(self, request, order_id=None):
        if not order_id:
            return Response(
                {"error": "order_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            orders = OrderToDiseases.objects.filter(order_id=order_id)
            serializer = self.get_serializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except OrderToDiseases.DoesNotExist:
            return Response(
                {"error": f"OrderToDiseases with order_id {order_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

class UsersViewSet(ConditionalPaginationMixin, ModelViewSet):
    queryset = User.objects.order_by("-created_at")
    serializer_class = UserSerializer
    filterset_fields = { 'fullname': ['icontains'] }

class TelegramUserViewSet(ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    permission_classes = (AllowAny,)

    @action(detail=False, methods=['get'], url_path='get-telegram-id/(?P<telegram_id>[^/.]+)')
    def get_by_telegram_id(self, request, telegram_id=None):
        if not telegram_id:
            return Response(
                {"error": "telegram_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TelegramUser.DoesNotExist:
            return Response(
                {"error": f"TelegramUser with telegram_id {telegram_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

class LanguageViewSet(ModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

    @action(detail=False, methods=['get'], url_path='get-language-name/(?P<name>[^/.]+)')
    def get_by_name(self, request, name=None):
        if not name:
            return Response(
                {"error": "name parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            language = Language.objects.get(name=name)
            serializer = self.get_serializer(language)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Language.DoesNotExist:
            return Response(
                {"error": f"Language with name {name} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


class OrderItemsViewSet(ModelViewSet):
    queryset = OrderItems.objects.all()
    serializer_class = OrderItemsSerializer
    filterset_fields = { 'order': ['exact'] }

# Register your models here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSignupSerializer


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})
        return Response(serializer.errors, status=400)


class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)




# Template views START

def log_in(request):
    error_message: str = ''
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', None)
        password = request.POST.get('password', None)
        cutomer = authenticate(phone_number=phone_number, password=password)
        print(cutomer)
        if cutomer:
            login(request, cutomer)
            return redirect('home')
        else:
            error_message = 'Email yoki parol xato kiritildi!'
    return render(
        request=request,
        template_name='auth/signin.html',
        context={
            'header': 'signin',
            'error_message': error_message
        }
    )


def log_out(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('signin')


def signup(request):
    print('POST: ', request.POST)
    user_message: str = ''
    password_message: str = ''
    if request.method == 'POST':
        # first_name=request.POST.get('first_name',None)
        # last_name = request.POST.get('last_name', None)
        email = request.POST.get('email', None)
        # gender=request.POST.get('gender',None)
        password = request.POST.get('password1', None)
        password1 = request.POST.get('password2', None)
        user = User.objects.filter(email=email)
        if user:
            user_message = 'Bu email avval ro\'yhatdan o\'tgan'
        elif password1 != password:
            password_message = 'Iltimos, parollar bir xil ekanligiga ishonch hosil qiling!'
        else:
            user = User.objects.create(
                # first_name=first_name,
                # last_name=last_name,
                email=email,
                # gender=gender,
                password=password
            )
            user.set_password(password)
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    return render(
        request=request,
        template_name='auth/signup.html',
        context={
            'header': 'signup',
            'user_message': user_message,
            'password_message': password_message
        }
    )

from django.core.cache import cache
@login_required(login_url='/signin/')
def home(request):
    stats = cache.get('home_stats')

    if not stats:
        stats = {
            'user_count': TelegramUser.objects.count(),
            'order_count': Order.objects.count(),
            'dori_count': Pills.objects.count(),
            'kasallik_count': Diseases.objects.count(),
        }
        # Cache'ga saqlash (masalan, 5 daqiqaga)
        cache.set('home_stats', stats, timeout=300)  # 300 soniya = 5 daqiqa

    return render(
        request=request,
        template_name='index.html',
        context={
            'header': 'home',
            **stats,
        }
    )


@login_required(login_url='/signin/')
def order(request):
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if search:
        orders = Order.objects.filter(
            Q(user__fullname__icontains=search) |
            Q(user__phone_number__icontains=search)
        ).order_by('-order_updated_date')
    else:
        orders = Order.objects.all().order_by('-order_updated_date')
    orders = orders.annotate(
        unread_messages=Count('messages', filter=Q(messages__status='UNREAD', messages__sender='BOT'))
    )
    total = len(orders)
    return render(
        request=request,
        template_name='order.html',
        context={
            'header': 'order',
            'orders': orders[(page-1)*page_size:(page-1)*page_size+page_size],
            'search': search,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    )

@login_required(login_url='/signin/')
def order_detail(request, id):
    order = get_object_or_404(Order, id=id)
    if order.status == 'PENDING':
        order.status = 'PROCESS'
        order.save()
    messages = Messages.objects.filter(order=order).order_by('timestamp')
    Messages.objects.filter(order=order, status='UNREAD').update(status='READ')
    images = order.images.all()
    if request.method == "POST":
        selected_dori_ids = request.POST.getlist('dori')
        selected_kasallik_ids = request.POST.getlist('kasallik')

        OrderToPills.objects.filter(order=order).delete()
        OrderToDiseases.objects.filter(order=order).delete()

        dori_objects = [
            OrderToPills(order=order, pills_id=dori_id)
            for dori_id in selected_dori_ids
        ]
        OrderToPills.objects.bulk_create(dori_objects)

        kasallik_objects = [
            OrderToDiseases(order=order, diseases_id=kasallik_id)
            for kasallik_id in selected_kasallik_ids
        ]
        OrderToDiseases.objects.bulk_create(kasallik_objects)

        load_dotenv()
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = order.user.telegram_id
        language = order.user.language.name
        if language == 'uz':
            text = 'Javoblarni kurish uchun status tugmasini bosing'
        elif language == 'ru':
            text = 'Нажмите кнопку статуса, чтобы просмотреть ответы.'
        else:
            text = 'Click the status button to view responses.'
        reply_keyboard = {
            "keyboard": [
                [{"text": "Status"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        try:
            response = requests.post(
                url=f'https://api.telegram.org/bot{bot_token}/sendMessage',
                data={
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'HTML',
                    'reply_markup': json.dumps(reply_keyboard)
                }
            ).json()
        except Exception as e:
            error_message = f"{e} xatolik"
            query_params = urlencode({'error': error_message})
            return redirect(f'/order?{query_params}')
        return redirect('order')

        # GET so'rovi uchun barcha ma'lumotlarni olish
    selected_dori_ids = order.order_pills.values_list('pills_id', flat=True)
    selected_kasallik_ids = order.order_diseases.values_list('diseases_id', flat=True)
    all_dori = Pills.objects.all()
    all_kasallik = Diseases.objects.all()
    related_dori_data = {
        str(kasallik.id): [str(dori_id) for dori_id in kasallik.pills.values_list('id', flat=True)]
        for kasallik in all_kasallik
    }
    print('related_dori_data:', related_dori_data)

    context = {
        'header': 'order_detail',
        'order': order,
        'messages': messages,
        'images': images,
        'all_dori': all_dori,
        'selected_dori_ids': selected_dori_ids,
        'all_kasallik': all_kasallik,
        'selected_kasallik_ids': selected_kasallik_ids,
        'related_dori_data': related_dori_data,
    }
    return render(request, 'order_detail.html', context)

@login_required(login_url='/signin/')
def delete_dori(request, id):
    if request.method == 'POST':
        if id:
            Pills.objects.filter(id=id).delete()
            return redirect('dori')

@login_required(login_url='/signin/')
def dori(request, id=None):
    error_message = ''
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if request.method == 'POST':
        if id:
            product_id = request.POST.get('product_id', None)
            small_product = str(request.POST.get('small_product'))=='on'
            title = request.POST.get('name', None)
            price = request.POST.get('price', None)
            spic = request.POST.get('spic', None)
            image = request.FILES.get('image', None)
            package_code = request.POST.get('package_code', None)
            description = request.POST.get('description', None)
            delete_image = request.POST.get('delete_image', None)
            if title and price and description:
                pill = Pills.objects.get(id=id)
                pill.product_id = product_id
                pill.small_product = small_product
                pill.name = title
                pill.price = price
                pill.spic = spic
                if (not delete_image) and image:
                    pill.image = image
                elif delete_image:
                    pill.image = None
                pill.package_code = package_code
                pill.description = description
                pill.save()
                return redirect('dori')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'
        product_id = request.POST.get('product_id', None)
        small_product = str(request.POST.get('small_product'))=='on'
        title = request.POST.get('name', None)
        image = request.FILES.get('image', None)
        price = request.POST.get('price', None)
        spic = request.POST.get('spic', None)
        package_code = request.POST.get('package_code', None)
        description = request.POST.get('description', None)
        delete_image = request.POST.get('delete_image', None)
        if title and price and description:
            if id:
                pill = Pills.objects.get(id=id)
                pill.product_id = product_id
                pill.small_product = small_product
                pill.name = title
                pill.price = price
                pill.spic = spic
                if (not delete_image) and image:
                    pill.image = image
                elif delete_image:
                    pill.image = None
                pill.package_code = package_code
                pill.description = description
                pill.save()
            else:
                Pills.objects.create(
                    product_id=product_id,
                    small_product=small_product,
                    name=title,
                    price=price,
                    spic=spic,
                    image=image,
                    package_code=package_code,
                    description=description
                )
            return redirect('dori')
        else:
            error_message = 'Iltimos, barcha maydonlarni to\'ldiring!'

    if search:
        doris = Pills.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(price__icontains=search)
        ).order_by('-created_at')
    else:
        doris = Pills.objects.order_by('-created_at')
    total = len(doris)

    return render(
        request=request,
        template_name='dori.html',
        context={
            'header': 'dori',
            'doris': doris[(page-1)*page_size:(page-1)*page_size+page_size],
            'search': search,
            'total': total,
            'page': page,
            'page_size': page_size,
            'error_message': error_message
        }
    )



@login_required(login_url='/signin/')
def kasallik(request, id=None):
    error_message = ''
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if request.method == 'POST':
        if id:
            title = request.POST.get('title', None)
            description = request.POST.get('description', None)
            if title and description:
                Diseases.objects.filter(id=id).update(
                    name=title,
                    description=description
                )
                return redirect('kasallik')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'
        title = request.POST.get('title', None)
        description = request.POST.get('description', None)
        if title and description:
            if id:
                Diseases.objects.filter(id=id).update(
                    name=title,
                    description=description
                )
            else:
                Diseases.objects.create(
                    name=title,
                    description=description
                )
            return redirect('kasallik')
        else:
            error_message = 'Iltimos, barcha maydonlarni to\'ldiring!'

    if search:
        kasalliklar = Diseases.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        ).order_by('-created_at')
    else:
        kasalliklar = Diseases.objects.order_by('-created_at')
    total = len(kasalliklar)
    return render(
        request=request,
        template_name='kasallik.html',
        context={
            'header': 'kasallik',
            'kasalliklar': kasalliklar[(page - 1) * page_size:(page - 1) * page_size + page_size],
            'search': search,
            'total': total,
            'page': page,
            'page_size': page_size,
            'error_message': error_message
        }
    )


@login_required(login_url='/signin/')
def kasallik_detail(request, id):
    disease = get_object_or_404(Diseases, id=id)
    if request.method == "POST":
        selected_dori_ids = request.POST.getlist('dori')
        disease.pills.set(selected_dori_ids)
        return redirect('kasallik')

    all_dori = Pills.objects.all()
    related_dori_ids = disease.pills.values_list('id', flat=True)

    context = {
        'header': 'kasallik_detail',
        'disease': disease,
        'all_dori': all_dori,
        'related_dori_ids': related_dori_ids,
    }
    return render(request, 'kasallik_detail.html', context)

@login_required(login_url='/signin/')
def delete_kasallik(request, id):
    if request.method == 'POST':
        if id:
            Diseases.objects.filter(id=id).delete()
            return redirect('kasallik')


@login_required(login_url='/signin/')
def delete_order(request, id):
    if request.method == 'POST':
        if id:
            Order.objects.filter(id=id).delete()
            return redirect('order')


@login_required(login_url='/signin/')
def delete_user(request, id):
    if request.method == 'POST':
        if id:
            User.objects.filter(id=id).delete()
            return redirect('users')


@login_required(login_url='/signin/')
def users(request, id=None):
    error_message = ''
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if request.method == 'POST':
        if id:
            fullname = request.POST.get('fullname', None)
            phone_number = request.POST.get('phone_number', None)
            password = request.POST.get('password', None)
            if fullname and password and phone_number:
                user = User.objects.get(id=id)
                user.fullname = fullname
                user.phone_number = phone_number
                user.set_password(password)
                user.save()
                return redirect('users')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'
                return redirect('users')
        fullname = request.POST.get('fullname', None)
        phone_number = request.POST.get('phone_number', None)
        password = request.POST.get('password', None)
        password2 = request.POST.get('password2', None)
        user = User.objects.filter(phone_number=phone_number)
        if user:
            error_message = 'Bu telefon nomer avval ro\'yhatdan o\'tgan'
        elif password2 != password:
            error_message = 'Iltimos, parollar bir xil ekanligiga ishonch hosil qiling!'
        else:
            if fullname and phone_number and password:
                user = User.objects.create(
                    fullname=fullname,
                    phone_number=phone_number,
                    password=password
                )
                user.set_password(password)
                user.save()
                return redirect('users')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'

    if search:
        users = User.objects.filter(
            Q(fullname__icontains=search) |
            Q(phone_number__icontains=search)
        ).order_by('-created_at')
    else:
        users = User.objects.order_by('-created_at')
    total = len(users)
    return render(
        request=request,
        template_name='users.html',
        context={
            'header': 'users',
            'users': users[(page - 1) * page_size:(page - 1) * page_size + page_size],
            'search': search,
            'total': total,
            'page': page,
            'page_size': page_size,
            'error_message': error_message
        }
    )


@login_required(login_url='/signin/')
def branch(request, id=None):
    error_message = ''
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if request.method == 'POST':
        if id:
            branch_id = request.POST.get('branch_id', None)
            title = request.POST.get('title', None)
            phone_number = request.POST.get('phone_number', None)
            location1 = request.POST.get('location1', None)
            location2 = request.POST.get('location2', None)
            if title and phone_number and location1 and location2:
                try:
                    latitude = float(location1) if location1 else None
                    longitude = float(location2) if location2 else None
                except ValueError:
                    error_message = "Koordinatalar noto‘g‘ri formatda kiritilgan."
                    query_params = urlencode({'error': error_message})
                    return redirect(f'/branch?{query_params}')
                Branch.objects.filter(id=id).update(
                    branch_id=branch_id,
                    name=title,
                    phone_number=phone_number,
                    latitude=latitude,
                    longitude=longitude
                )
                return redirect('branch')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'
        branch_id = request.POST.get('branch_id', None)
        title = request.POST.get('title', None)
        phone_number = request.POST.get('phone_number', None)
        location1 = request.POST.get('location1', None)
        location2 = request.POST.get('location2', None)
        if title and phone_number and location1 and location2:
            try:
                latitude = float(location1) if location1 else None
                longitude = float(location2) if location2 else None
            except ValueError:
                error_message = "Koordinatalar noto‘g‘ri formatda kiritilgan."
                query_params = urlencode({'error': error_message})
                return redirect(f'/branch?{query_params}')

            if id:
                Branch.objects.filter(id=id).update(
                    branch_id=branch_id,
                    name=title,
                    phone_number=phone_number,
                    latitude=latitude,
                    longitude=longitude
                )
            else:
                Branch.objects.create(
                    branch_id=branch_id,
                    name=title,
                    phone_number=phone_number,
                    latitude=latitude,
                    longitude=longitude
                )
            return redirect('branch')
        else:
            error_message = 'Iltimos, barcha maydonlarni to\'ldiring!'

    if search:
        branchs = Branch.objects.filter(
            Q(name__icontains=search) |
            Q(phone_number__icontains=search)
        ).order_by('-created_at')
    else:
        branchs = Branch.objects.order_by('-created_at')
    total = len(branchs)
    return render(
        request=request,
        template_name='branch.html',
        context={
            'header': 'regions',
            'branchs': branchs[(page - 1) * page_size:(page - 1) * page_size + page_size],
            'search': search,
            'total': total,
            'page': page,
            'page_size': page_size,
            'error_message': error_message
        }
    )


@login_required(login_url='/signin/')
def delete_branch(request, id):
    if request.method == 'POST' and id:
        Branch.objects.filter(id=id).delete()
    return redirect('branch')

@login_required(login_url='/signin/')
def translate(request):
    return render(
        request=request,
        template_name='translate.html',
        context={
            'header': 'translate'
        }
    )


@login_required(login_url='/signin/')
def get_order_items(request, id=None):
    order = Order.objects.get(id=id)
    items = OrderItems.objects.filter(order=order)
    data = {
        "items": [
            {
                "name": item.pills.name,
                "quantity": item.quantity,
                "price": float(item.price),
                "logix_status": item.logix_status,
            } for item in items
        ]
    }
    return JsonResponse(data)


@login_required(login_url='/signin/')
def settings(request, id=None):
    error_message = ''
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    if request.method == 'POST':
        if id:
            price = request.POST.get('price', None)
            if price:
                try:
                    price = int(price) if price else None
                except ValueError:
                    error_message = "Narx noto'g'ri formatda kiritilgan."
                    query_params = urlencode({'error': error_message})
                    return redirect(f'/branch?{query_params}')
                delivery = DeliveryCost.objects.get(id=id)
                delivery.price = price
                delivery.save()
                return redirect('settings')
            else:
                error_message = 'Iltimos, barcha maydonlar to\'ldiring!'
    delivery = DeliveryCost.objects.all()
    return render(
        request=request,
        template_name='settings.html',
        context={
            'header': 'settings',
                'delivery': delivery,
                'search': search,
                'page': page,
                'page_size': page_size,
                'error_message': error_message
        }
    )



async def upload_image_view(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        try:
            image_url = await upload_image(image_file, image_file.name)
            if image_url:
                return JsonResponse({'status': 'success', 'image_url': image_url})
            else:
                return JsonResponse({'status': 'error', 'message': 'Image upload failed'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'No image provided'}, status=400)

@csrf_exempt  # Only if you need to bypass CSRF protection
def order_select(request, id):
    if request.method == "POST":
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=id)

        dori_ids = data.get("dori", [])
        kasallik_ids = data.get("kasallik", [])

        OrderToPills.objects.filter(order=order).delete()
        OrderToDiseases.objects.filter(order=order).delete()

        OrderToPills.objects.bulk_create(
            [OrderToPills(order=order, pills_id=p) for p in dori_ids]
        )
        OrderToDiseases.objects.bulk_create(
            [OrderToDiseases(order=order, diseases_id=d) for d in kasallik_ids]
        )

        load_dotenv()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = order.user.telegram_id
        lang = getattr(order.user.language, "name", "").lower()

        if lang == "uz":
            text = "Javoblarni ko‘rish uchun status tugmasini bosing"
        elif lang == "ru":
            text = "Нажмите кнопку статуса, чтобы просмотреть ответы."
        else:
            text = "Click the status button to view responses."

        reply_markup = json.dumps(
            {
                "keyboard": [[{"text": "Status"}]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        )

        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup,
                },
                timeout=5,
            )

            if order.status == 'PENDING':
                order.status = 'PROCESS'
                order.save()
        except Exception:
            return JsonResponse({}, status=500)

        return JsonResponse({}, status=200)
# def order_select(request,id):
#     if request.method == 'POST':
#         data = json.loads(request.body)
#         order = get_object_or_404(Order, id=id)

#         dori_ids = data.get("dori", [])
#         kasallik_ids = data.get("kasallik", [])

#         OrderToPills.objects.filter(order=order).delete()
#         OrderToDiseases.objects.filter(order=order).delete()

#         OrderToPills.objects.bulk_create(
#             [OrderToPills(order=order, pills_id=p) for p in dori_ids]
#         )
#         OrderToDiseases.objects.bulk_create(
#             [OrderToDiseases(order=order, diseases_id=d) for d in kasallik_ids]
#         )

#         load_dotenv()
#         bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
#         chat_id = order.user.telegram_id
#         lang = getattr(order.user.language, "name", "").lower()

#         if lang == "uz":
#             text = "Javoblarni ko‘rish uchun status tugmasini bosing"
#         elif lang == "ru":
#             text = "Нажмите кнопку статуса, чтобы просмотреть ответы."
#         else:
#             text = "Click the status button to view responses."

#         reply_markup = json.dumps(
#             {
#                 "keyboard": [[{"text": "Status"}]],
#                 "resize_keyboard": True,
#                 "one_time_keyboard": True,
#             }
#         )

#         try:
#             requests.post(
#                 f"https://api.telegram.org/bot{bot_token}/sendMessage",
#                 data={
#                     "chat_id": chat_id,
#                     "text": text,
#                     "parse_mode": "HTML",
#                     "reply_markup": reply_markup,
#                 },
#                 timeout=5,
#             )
#         except Exception:
#             return JsonResponse({},status=500)

#         return JsonResponse({}, status=200)

class StatisticsAPIView(APIView):
    def get(self, request):
        data = {
            "users": User.objects.count(),
            "telegram_users": TelegramUser.objects.count(),
            "orders": Order.objects.count(),
            "pills": Pills.objects.count(),
            "diseases": Diseases.objects.count(),
            "branches": Branch.objects.count(),
        }

        return JsonResponse(data, status=200)
