from django.contrib import admin
from .models import CustomUser, MobileConfirmationCode, Notification, EmailConfirmationCode, Country, DepartmentService, DepartmentBanner, State, City, Department, Wallet, Currency


class DateAdmin(admin.ModelAdmin):
    readonly_fields = ('date',)
# Register your models here.


admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(Currency)
admin.site.register(CustomUser)
admin.site.register(MobileConfirmationCode, DateAdmin)
admin.site.register(EmailConfirmationCode, DateAdmin)
admin.site.register(Notification, DateAdmin)
admin.site.register(Department)
admin.site.register(DepartmentBanner)
admin.site.register(DepartmentService)
admin.site.register(Wallet)
