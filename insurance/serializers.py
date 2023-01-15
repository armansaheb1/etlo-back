from rest_framework import serializers
from django.contrib.auth.models import User
from .models import HealthInsuranceCompany, HealthInsurancePriceList, HealthInsuranceUserDiscount, HealthInsuranceRequest


class HealthInsuranceCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthInsuranceCompany
        fields = (
            "id",
            "add_date",
            "last_modify_date",
            "last_modify_user",
            "name",
            "image",
            "get_image",
        )


class HealthInsurancePriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthInsurancePriceList
        fields = (
            "id",
            "company",
            "start_age",
            "end_age",
            "add_date",
            "last_modify_date",
            "last_modify_user",
            "get_company_name",
            "get_company_image",
            "first_year",
            "second_year"
        )


class HealthInsuranceUserDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthInsuranceUserDiscount
        fields = (
            "add_date",
            "last_modify_date",
            "last_modify_user",
            "id",
            "name",
            "user",
            "percent",
            "expiration_time",
        )


class HealthInsuranceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthInsuranceRequest
        fields = (
            "id",
            "user",
            "insurance",
            "passport_number",
            "cimlinc_number",
            "country",
            "state",
            "city",
            "birthday_date",
            "weight",
            "height",
            "first_name",
            "last_name",
            "father_name",
            "description",
            "phone_number",
            "email_address",
            "start_date",
            "code",
            "status",
            "first_year_price",
            "second_year_price",
            "discount_percent",
            "discount",
            "price",
            "file"
        )
