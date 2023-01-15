from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import HealthInsuranceCompany, HealthInsurancePriceList, HealthInsuranceUserDiscount, HealthInsuranceRequest
from .serializers import HealthInsurancePriceListSerializer, HealthInsuranceCompanySerializer, HealthInsuranceRequestSerializer, HealthInsuranceUserDiscountSerializer
from main.models import Wallet, Currency


def checkid(id):
    if not id.isnumeric():
        return Response({'status': False, 'data': 'ID Should Be a Number'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# Create your views here.


class HealthInsuranceDetails(APIView):

    def post(self, request):
        checkid(request.data['id'])
        if not len(HealthInsuranceRequest.objects.filter(id=request.data['id'])):
            return Response({'status': False, 'data': 'Invalid ID'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        query = HealthInsuranceRequest.objects.filter(id=request.data['id'])
        serializer = HealthInsuranceRequestSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data[0]})


class HealthInsurancePriceList(APIView):

    def post(self, request):
        serializer = []
        query1 = HealthInsuranceCompany.objects.all()
        for item in query1:
            if len(HealthInsurancePriceList.objects.filter(company=item, start_age__lte=int(request.data['age']), end_age__gte=int(request.data['age']))):
                serializer.append({'company': HealthInsuranceCompanySerializer([item], many=True).data[0], 'pricelist': HealthInsurancePriceListSerializer(
                    HealthInsurancePriceList.objects.filter(company=item, start_age__lte=int(request.data['age']), end_age__gte=int(request.data['age'])), many=True).data[0]})
        return Response({'status': True, 'data': tuple(serializer)})


class HealthInsuranceRequest(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if (not 'insurance' in request.data):
            return Response({'status': False, 'data': {'message': 'Insurance is required'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        request.data._mutable = True
        request.data['user'] = request.user.id
        if len(HealthInsuranceUserDiscount.objects.filter(user=request.user)):
            dis = HealthInsuranceUserDiscount.objects.filter(
                user=request.user).order_by('-last_modify_date').last()
            request.data['discount'] = dis
            request.data['discount_percent'] = dis.percent
        elif len(HealthInsuranceUserDiscount.objects.filter(user=None)):
            dis = HealthInsuranceUserDiscount.objects.filter(
                user=None).order_by('-last_modify_date').last()
            request.data['discount'] = dis
            request.data['discount_percent'] = dis.percent
        else:
            request.data['discount'] = None
            request.data['discount_percent'] = 0
        if not 'insurance' in request.data:
            return Response({'status': False, 'data': 'Insurance is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif request.data['insurance'] == '':
            return Response({'status': False, 'data': 'Insurance is required'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not len(HealthInsurancePriceList.objects.filter(id=request.data['insurance'])):
            return Response({'status': False, 'data': {'message': 'Invalid insurance'}}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        insurance = HealthInsurancePriceList.objects.get(
            id=request.data['insurance'])
        request.data['insurance'] = int(request.data['insurance'])
        request.data['first_year_price'] = insurance.first_year
        request.data['second_year_price'] = insurance.second_year
        serializer = HealthInsuranceRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': True, 'data': serializer.data})
        else:
            return Response({'status': False, 'data': serializer.errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class CheckDiscount(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if len(HealthInsuranceUserDiscount.objects.filter(user=request.user)):
            dis = HealthInsuranceUserDiscount.objects.filter(
                user=request.user).order_by('-last_modify_date')
            serializer = HealthInsuranceUserDiscountSerializer(dis, many=True)
            return Response({'status': True, 'data': serializer.data[0]}, status=status.HTTP_200_OK)
        elif len(HealthInsuranceUserDiscount.objects.filter(user=None)):
            dis = HealthInsuranceUserDiscount.objects.filter(
                user=None).order_by('-last_modify_date')
            serializer = HealthInsuranceUserDiscountSerializer(dis, many=True)
            return Response({'status': True, 'data': serializer.data[0]}, status=status.HTTP_200_OK)
        else:
            return Response({'status': False, 'data': {'message': 'There is no discount for you'}}, status=status.HTTP_404_NOT_FOUND)


class MyInsurances(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = HealthInsuranceRequest.objects.filter(user=request.user.id)
        serializer = HealthInsuranceRequestSerializer(query, many=True)
        return Response({'status': True, 'data': serializer.data})


class HealthInsurancePayment(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        checkid(request.data['id'])
        if not len(HealthInsuranceRequest.objects.filter(id=request.data['id'])):
            return Response({'status': False, 'data': 'ID Not Found'}, status=status.HTTP_404_NOT_FOUND)
        req = HealthInsuranceRequest.objects.get(id=request.data['id'])
        if req.period == 1:
            price = req.first_year
        else:
            price = req.second_year
        wallet = Wallet.objects.get(
            user=request.user, currency=Currency.objects.get(symbol='TRL').id)
        if wallet.balance >= price:
            wallet.balance = wallet.balance - price
            wallet.save()
            req.payment_status = True
        else:
            return Response({'status': False, 'data': 'Insufficient Balance'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
