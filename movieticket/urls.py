

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('system/', admin.site.urls),
    path('', include("booking.urls")),
    path('accounts/', include("accounts.urls")),
    path('admin/', include("staff.urls")),
]


# handler401 = 'staff.views.handler401'
# handler404 = 'staff.views.handler404'
# handler500 = 'staff.views.handler500'