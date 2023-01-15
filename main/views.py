from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .models import CustomUser, MobileConfirmationCode, EmailConfirmationCode, Notification, Country, State, City, Department, DepartmentBanner, DepartmentService, Address, Chat, BankCard, BankSheba, Withdraw, Wallet, Currency, Transaction, Banner
from .serializers import CurrentUserSerializer, NotificationSerializer, CountrySerializer, StateSerializer, CitySerializer, DepartmentSerializer, DepartmentBannerSerializer, DepartmentServiceSerializer, AddressSerializer, ChatSerializer, BankCardSerializer, BankShebaSerializer, WithdrawSerializer, WalletSerializer, TransactionSerializer, BannerSerializer, CurrencySerializer, MobileConfirmationCodeSerializer, EmailConfirmationCodeSerializer, SetPhoneSerializer, SetPasswordSerializer, SetProfileSerializer, LoginSerializer, SetCurrentPasswordSerializer, CurrencyConvertSerializer
from django.db.models import Q
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
import datetime
from random import randint
from etlo.settings import TR_SMS_ID, TR_SMS_KEY, IR_SMS_KEY

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail

import json
import requests
from bs4 import BeautifulSoup
import urllib

from time import sleep

from rest_framework.permissions import BasePermission


def checkid(id):
    if not id.isnumeric():
        return Response({'status': False, 'data': 'ID Should Be a Number'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class IsUser(BasePermission):
    MY_SAFE_METHODS = ['POST']

    def has_permission(self, request, view):
        return bool(
            request.method in self.MY_SAFE_METHODS or
            request.user and
            request.user.is_authenticated
        )


def tr_sms(message, number):
    url = "https://api.vatansms.net/api/v1/1toN"

    data = json.dumps({
        "api_id": TR_SMS_ID,
        "api_key": TR_SMS_KEY,
        "sender": "NEGARSHETAB",
        "message_type": "turkce",
        "message": f"{message}",
        "phones": [
            f'{number}'
        ]
    })
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, headers=headers, data=data, verify=False)

    print(response.json())


def ir_sms(code, number):
    url = "https://api.sms.ir/v1/send/verify"

    data = json.dumps({
        "mobile": f"{number}",
        "templateId": 100000,
        "parameters": [
            {
                "name": "Code",
                "value": f"{code}"
            }
        ]
    }
    )
    headers = {'Content-Type': 'application/json', 'X-API-KEY': IR_SMS_KEY}

    response = requests.post(url, headers=headers, data=data, verify=False)

    print(response.json())


class Login(APIView):

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)

        return {
            'refresh_token': str(refresh),
            'access_token': str(refresh.access_token),
            'expiration_time': datetime.datetime.fromtimestamp(refresh['exp'])
        }

    def post(self, request, format=None):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if not len(CustomUser.objects.filter(Q(phone_number=serializer.data['username']) | Q(email=serializer.data['username']))):
                if not len(MobileConfirmationCode.objects.filter(phone_number=serializer.data['username'])):
                    return Response({'status': False, 'data': {'message': 'Wrong or Expired Code'}}, status=status.HTTP_403_FORBIDDEN)
                elif MobileConfirmationCode.objects.get(phone_number=serializer.data['username']).code != int(serializer.data['password']):
                    return Response({'status': False, 'data': {'message': 'Wrong Code'}}, status=status.HTTP_403_FORBIDDEN)
                elif MobileConfirmationCode.objects.get(phone_number=serializer.data['username']).date + datetime.timedelta(minutes=1) < timezone.now():
                    return Response({'status': False, 'data': {'message': 'Expired Code'}}, status=status.HTTP_403_FORBIDDEN)
                else:
                    cc = CustomUser(phone_number=serializer.data['username'], country_code=Country.objects.get(
                        dial_code=int(serializer.data['country_code'])), phone_verification=True)
                    cc.save()
            user = CustomUser.objects.filter(Q(phone_number=serializer.data['username']) | Q(
                email=serializer.data['username'])).last()
            if (str(MobileConfirmationCode.objects.get(phone_number=user.phone_number).code) != serializer.data['password']):
                if user.password:
                    if not check_password(serializer.data['password'], user.password):
                        return Response({'status': False, 'data': {'message': 'Wrong Password'}}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({'status': False, 'data': {'message': 'Wrong Password'}}, status=status.HTTP_403_FORBIDDEN)
            refresh = self.get_tokens_for_user(user)
            return Response({'status': True, 'data': refresh}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class CreateCode(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsUser]

    def get(self, request):
        code = randint(111111, 999999)
        for item in MobileConfirmationCode.objects.filter(phone_number=request.user.phone_number):
            item.delete()
        mm = MobileConfirmationCode(
            phone_number=request.user.phone_number, code=code)
        mm.save()
        if request.user.country_code.dial_code == '98':
            ir_sms(code=code, number=request.user.phone_number)
        elif request.user.country_code.dial_code == '90':
            tr_sms(
                message=f"Your Verification Code is : {code}", number=request.user.phone_number)
        else:
            pass
        return Response({'status': True, 'data': True}, status=status.HTTP_201_CREATED)

    def post(self, request, format=None):
        serializer = MobileConfirmationCodeSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            for item in MobileConfirmationCode.objects.filter(phone_number=request.data['phone_number']):
                item.delete()
            code = randint(111111, 999999)
            mm = MobileConfirmationCode(
                phone_number=request.data['phone_number'], code=code)
            mm.save()
            if request.data['country_code'] == '98':
                ir_sms(code=code, number=request.data['phone_number'])
            elif request.data['country_code'] == '90':
                tr_sms(
                    message=f"Your Verification Code is : {code}", number=request.data['phone_number'])
            else:
                pass
            return Response({'status': True, 'data': True}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class CheckPhone(APIView):

    def post(self, request, format=None):
        if (not 'username' in request.data) or (request.data['username'] == ''):
            return Response({'status': False, 'data': {'message': 'Username is Required'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not len(CustomUser.objects.filter(phone_number=request.data['username'])):
            return Response({'status': False, 'data': {'message': 'User Not Found'}}, status=status.HTTP_200_OK)
        user = CustomUser.objects.get(phone_number=request.data['username'])
        if not user.password:
            for item in MobileConfirmationCode.objects.filter(phone_number=user.phone_number):
                item.delete()
            code = randint(111111, 999999)
            mm = MobileConfirmationCode(
                phone_number=user.phone_number, code=code)
            mm.save()
            if user.country_code == '98':
                ir_sms(code=code, number=user.phone_number)
            else:
                tr_sms(
                    message=f"Your Verification Code is : {code}", number=user.phone_number)
            return Response({'status': True, 'data': False}, status=status.HTTP_200_OK)
        else:
            return Response({'status': True, 'data': True}, status=status.HTTP_200_OK)


class CurrentUser(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = CustomUser.objects.filter(id=request.user.id)
        serializer = CurrentUserSerializer(user, many=True)
        return Response({'status': True, 'data': serializer.data[0]})


class CreateEmailCode(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsUser]

    def post(self, request, format=None):

        serializer = EmailConfirmationCodeSerializer(request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                validate_email(serializer.data['email'])
            except ValidationError as e:
                return Response({'status': False, 'data': {'message': 'Wrong Email Format'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            code = randint(111111, 999999)
            mm = EmailConfirmationCode(
                email=serializer.data['email'], code=code)
            mm.save()
            to = [serializer.data['email']]
            send_mail("Verification Code for etlo",
                      f"Your Code is : {code}", "armansaheb94@gmail.com", to)
            return Response({'status': True, 'data': True}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def get(self, request, format=None):
        if not request.user.email or request.user.email == '':
            return Response({'status': False, 'data': {'message': "You Don't Have an email in Your Account Yet"}}, status=status.HTTP_404_NOT_FOUND)
        code = randint(111111, 999999)
        mm = EmailConfirmationCode(email=request.user.email, code=code)
        mm.save()
        to = [request.user.email]
        send_mail("Verification Code for etlo",
                  F"Your Code is : {code}", "armansaheb94@gmail.com", to)
        return Response({'status': True, 'data': True}, status=status.HTTP_200_OK)


class SetPhone(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = SetPhoneSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if int(serializer.data['phone_code']) != MobileConfirmationCode.objects.filter(phone=serializer.data['phone']).last().code:
                return Response({'status': False, 'data': {'message': f'Wrong Code'}}, status=status.HTTP_403_FORBIDDEN)
            user = request.user
            if user.phone != serializer.data['phone']:
                return Response({'status': False, 'data': {'message': f'Wrong phone number'}}, status=status.HTTP_403_FORBIDDEN)
            user.phone_verification = True
            user.save()
            user = CustomUser.objects.filter(id=request.user.id)
            serializer = CurrentUserSerializer(user, many=True)
            return Response({'status': True, 'data': serializer.data[0]}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Currencies(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        query = Currency.objects.all()
        serializer = CurrencySerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class SetEmail(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = EmailConfirmationCodeSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if int(serializer.data['email_code']) != EmailConfirmationCode.objects.filter(email=serializer.data['email']).last().code:
                return Response({'status': False, 'data': {'message': f'Wrong Code'}}, status=status.HTTP_403_FORBIDDEN)
            user = request.user
            user.email = serializer.data['email']
            user.email_verification = True
            user.save()
            user = CustomUser.objects.filter(id=request.user.id)
            serializer = CurrentUserSerializer(user, many=True)
            return Response({'status': True, 'data': serializer.data[0]}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class SetPassword(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        if request.user.password:
            serializer = SetCurrentPasswordSerializer(data=request.data)
        else:
            serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                validate_password(serializer.data['new_password'])
            except ValidationError as e:
                errors = ''
                for item in e:
                    errors = item + '\\n'
                return Response({'status': False, 'data': {'message': errors}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            user = request.user
            user.password = make_password(
                serializer.data['new_password'])
            user.save()
            user = CustomUser.objects.filter(id=request.user.id)
            serializer = CurrentUserSerializer(user, many=True)
            return Response({'status': True, 'data': serializer.data[0]}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class SetProfileDetails(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = CustomUser.objects.get(id=request.user.id)
        serializer = SetProfileSerializer(instance=user, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response({'status': True, 'data': serializer.data}, status=status.HTTP_200_OK)


class Balances(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        for item in Currency.objects.all():
            if not len(Wallet.objects.filter(user=request.user.id, currency=item)):
                wal = Wallet(user=request.user, currency=item, balance=0)
                wal.save()
        query = Wallet.objects.filter(user=request.user.id)
        serializer = WalletSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class Transactions(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = Transaction.objects.filter(user=request.user.id)
        serializer = TransactionSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def post(self, request):
        if not len(Currency.objects.filter(id=int(serializer.data['currency_id']))):
            return Response({'status': False, 'data': {'message': 'Invalid Currency Id'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        query = Transaction.objects.filter(
            user=request.user.id, currency=Currency.objects.get(id=int(serializer.data['currency_id'])))
        serializer = TransactionSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class Notification(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        query = Notification.objects.filter(id=request.user.id)
        read = True
        for item in query:
            if not item.read:
                read = False
        serializer = NotificationSerializer(query, many=True)
        return Response({'status': True, 'data': {'read': read, 'notifications': serializer.data}})


class Countries(APIView):

    def get(self, request):
        query = Country.objects.all()
        serializer = CountrySerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class States(APIView):

    def get(self, request, id):
        checkid(id)
        if not len(Country.objects.filter(id=id)):
            return Response({'status': False, 'data': {'message': 'Wrong State Id'}}, status=status.HTTP_404_NOT_FOUND)
        query = State.objects.filter(country=Country.objects.get(id=id))
        serializer = StateSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class Cities(APIView):

    def get(self, request, id):
        checkid(id)
        if not len(State.objects.filter(id=id)):
            return Response({'status': False, 'data': {'message': 'Wrong State Id'}}, status=status.HTTP_404_NOT_FOUND)
        query = City.objects.filter(state=State.objects.get(id=id))
        serializer = CitySerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class ActiveCountries(APIView):

    def get(self, request):
        query = Country.objects.filter(have_service=True)
        serializer = CountrySerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def put(self, request, id):
        checkid(id)
        data = {'have_service': True}
        serializer = CountrySerializer(
            Country.objects.get(id=id), data=data, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response({'status': True, 'data': serializer.data})


class Banners(APIView):

    def get(self, request):
        query = Banner.objects.all()
        serializer = BannerSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class Departments(APIView):

    def get(self, request):
        serializers = []
        query = Department.objects.all()
        for item in query:
            serializer = DepartmentSerializer([item], many=True)
            query2 = DepartmentBanner.objects.filter(department=item)
            serializer2 = DepartmentBannerSerializer(query2, many=True)
            serializer.data[0]['banners'] = serializer2.data

            serializers.append(serializer.data[0])

        return Response({'status': True, 'data': serializers})


class DepartmentsServices(APIView):

    def get(self, request, id):
        checkid(id)
        if not len(Department.objects.filter(id=id)):
            return Response({'status': False, 'data': {'message': 'Department Not Found'}}, status=status.HTTP_404_NOT_FOUND)
        query = DepartmentService.objects.filter(
            department=Department.objects.get(id=id))
        serializer = DepartmentServiceSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class GetImage(APIView):

    def max_value(self, inputlist):
        return max([sublist for sublist in inputlist])

    def getdata(self, url):
        r = requests.get(url)
        return r.text

    def post(self, request):
        if not 'url' in request.data:
            return Response({'status': False, 'data': 'url is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif request.data['url'] == '':
            return Response({'status': False, 'data': 'url is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        list = []
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-extension')
        options.add_argument('start-maximized')
        options.add_argument('disable-infobars')
        driver = webdriver.Chrome(
            "/usr/bin/chromedriver", chrome_options=options)
        driver.get(request.data['url'])
        sleep(2)
        htmldata = driver.page_source
        driver.close()
        soup = BeautifulSoup(htmldata, 'html.parser')
        for item in soup.find_all('img'):
            try:
                f = open('test.jpg', 'wb')
                f.write(urllib.request.urlopen(item['src']).read())
                f.close()
                size = os.path.getsize('test.jpg')
                if (size):
                    if len(list):
                        if int(size) > int(list[1]):
                            list = [item['src'], int(size)]
                    else:
                        list = [item['src'], int(size)]
            except:
                pass
        if not len(list):
            return Response(htmldata)
        return Response(list)


class CurrencyConvert(APIView):

    def post(self, request):
        serializer = CurrencyConvertSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if (not len(Currency.objects.filter(id=serializer.data['from_currency']))) | (not len(Currency.objects.filter(id=serializer.data['to_currency']))):
                return Response({'status': False, 'data': 'Invalid currency'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            f = Currency.objects.get(id=serializer.data['from_currency'])
            t = Currency.objects.get(id=serializer.data['to_currency'])
            irt = float(serializer.data['amount']) * float(f.to_irt)
            result = float(irt) / float(t.to_irt)
            return Response({'status': True, 'data': {'from_currency': f.name, 'to_currency': t.name, 'amount': serializer.data['amount'], 'converted': result}})
        else:
            return Response({'status': False, 'data': serializer.errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Addresses(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = Address.objects.all()
        serializer = AddressSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def post(self, request):
        request.data._mutable = True
        request.data['last_modify_user'] = request.user.id
        request.data['user'] = request.user.id
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            return Response({'status': False, 'data': serializer.errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def put(self, request, id):
        checkid(id)
        try:
            request.data._mutable = True
            request.data['last_modify_date'] = datetime.utcnow()
            request.data['last_modify_user'] = request.user.id
            serializer = AddressSerializer(
                Address.objects.get(id=id), data=request.data,)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'status': True, 'data': serializer.data})
            else:
                return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except:
            return Response({'status': False, 'data': 'ID Not Found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id):
        checkid(id)
        Address.objects.get(id=id).delete()
        return Response({'status': True, 'data': True})


class Chats(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = Chat.objects.filter(owner=request.user.id)
        serializer = ChatSerializer(query, many=True)
        return Response({'status': True, 'data': {'unread': Chat.objects.filter(owner=request.user.id, user_read=False).count(), 'messages': serializer.data}})

    def post(self, request):
        request.data._mutable = True
        request.data['last_modify_user'] = request.user.id
        request.data['user'] = request.user.id
        request.data['user_read'] = True
        request.data['owner'] = request.user.id
        serializer = ChatSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            errors = ''
            for item in serializer.errors:
                for itemm in serializer.errors[item]:
                    errors = errors + item + ' : ' + itemm + '\\n'
            return Response({'status': False, 'data': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ChatsDep(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, department):
        query = Chat.objects.filter(
            owner=request.user.id, department=department)
        serializer = ChatSerializer(query, many=True)
        return Response({'status': True, 'data': {'unread': Chat.objects.filter(owner=request.user.id, user_read=False).count(), 'messages': serializer.data}})


class ChatsSer(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, department, service):
        query = Chat.objects.filter(
            owner=request.user.id, department=department, service=service)
        serializer = ChatSerializer(query, many=True)
        return Response({'status': True, 'data': {'unread': Chat.objects.filter(owner=request.user.id, user_read=False).count(), 'messages': serializer.data}})


class ChatsUnreads(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'status': True, 'data': {'unreads': Chat.objects.filter(owner=request.user.id, user_read=False).count()}})


class ChatsUnreadsDep(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, department):
        return Response({'status': True, 'data': {'unreads': Chat.objects.filter(owner=request.user.id, user_read=False, department=department).count()}})


class ChatsUnreadsSer(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, department, service):
        return Response({'status': True, 'data': {'unreads': Chat.objects.filter(owner=request.user.id, user_read=False, department=department, service=service).count()}})


class BankCards(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = BankCard.objects.filter(user=request.user.id)
        serializer = BankCardSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def post(self, request):
        request.data._mutable = True
        request.data['user'] = request.user.id
        serializer = BankCardSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            errors = ''
            for item in serializer.errors:
                for itemm in serializer.errors[item]:
                    errors = errors + item + ' : ' + itemm + '\\n'
            return Response({'status': False, 'data': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def put(self, request, id):
        checkid(id)
        try:
            request.data._mutable = True
            request.data['user'] = request.user.id
            serializer = BankCardSerializer(
                BankCard.objects.get(id=id), data=request.data,)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'status': True, 'data': serializer.data})
            else:
                return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except:
            return Response({'status': False, 'data': 'ID Not Found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id):
        checkid(id)
        BankCard.objects.get(id=id).delete()
        return Response({'status': True, 'data': True})


class ActiveBankCards(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = BankCard.objects.filter(user=request.user.id, status=1)
        serializer = BankCardSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class BankShebas(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = BankSheba.objects.filter(user=request.user.id)
        serializer = BankShebaSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def post(self, request):
        request.data._mutable = True
        request.data['user'] = request.user.id
        serializer = BankShebaSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            errors = ''
            for item in serializer.errors:
                for itemm in serializer.errors[item]:
                    errors = errors + item + ' : ' + itemm + '\\n'
            return Response({'status': False, 'data': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def put(self, request, id):
        checkid(id)
        try:
            request.data._mutable = True
            request.data['user'] = request.user.id
            serializer = BankShebaSerializer(
                BankSheba.objects.get(id=id), data=request.data,)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'status': True, 'data': serializer.data})
            else:
                return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except:
            return Response({'status': False, 'data': 'ID Not Found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id):
        checkid(id)
        BankSheba.objects.get(id=id).delete()
        return Response({'status': True, 'data': True})


class ActiveBankShebas(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = BankSheba.objects.filter(user=request.user.id, status=1)
        serializer = BankShebaSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class Withdraw(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = Withdraw.objects.filter(user=request.user.id)
        serializer = WithdrawSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})

    def post(self, request):
        if (not 'banksheba' in request.data) and (not 'bankcard' in request.data):
            return Response({'status': False, 'data': 'Bank Sheba or Bank Card is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif (request.data['banksheba'] == '') and (request.data['bankcard'] == ''):
            return Response({'status': False, 'data': 'Bank Sheba or Bank Card is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        request.data._mutable = True
        request.data['user'] = request.user.id
        serializer = WithdrawSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            errors = ''
            for item in serializer.errors:
                for itemm in serializer.errors[item]:
                    errors = errors + item + ' : ' + itemm + '\\n'
            return Response({'status': False, 'data': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def delete(self, request, id):
        checkid(id)
        if not len(Withdraw.objects.filter(id=id)):
            return Response({'status': False, 'data': {'message': 'Invalid Id'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        withdraw = Withdraw.objects.get(id=id)
        withdraw.status = 2
        withdraw.save()
        return Response({'status': True, 'data': True})
