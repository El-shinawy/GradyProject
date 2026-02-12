# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import *

# router = DefaultRouter()
# router.register('users', UserViewSet)
# router.register('hospitals', HospitalViewSet)
# router.register('doctors', DoctorViewSet)
# router.register('chronic-diseases', ChronicDiseaseViewSet)
# router.register('user-chronic-diseases', UserChronicDiseaseViewSet)
# router.register('patients-profile', PatientMedicalProfileViewSet)
# router.register('donors-profile', DonorMedicalProfileViewSet)
# router.register('appointments', AppointmentViewSet)
# router.register('organs', OrganViewSet)
# router.register('organ-matches', OrganMatchingViewSet)
# router.register('surgeries', SurgeryViewSet)
# router.register('UserReport', MRIReportViewSet)
# router.register('patient-priorities', PatientPriorityViewSet)
# router.register('medicines', MedicineViewSet)
# router.register('patient-medicines', PatientMedicineViewSet)
# router.register('alerts', AlertViewSet)

# urlpatterns = [
#     path('api/', include(router.urls)),
# ]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'hospitals', HospitalViewSet, basename='hospital')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'chronic-diseases', ChronicDiseaseViewSet, basename='chronic-disease')
router.register(r'user-chronic-diseases', UserChronicDiseaseViewSet, basename='user-chronic-disease')
router.register(r'patient-profiles', PatientMedicalProfileViewSet, basename='patient-profile')
router.register(r'donor-profiles', DonorMedicalProfileViewSet, basename='donor-profile')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'organ-matching', OrganMatchingViewSet, basename='organ-matching')
router.register(r'surgeries', SurgeryViewSet, basename='surgery')
router.register(r'mri-reports', MRIReportViewSet, basename='mri-report')
router.register(r'UserReport', UserReportViewSet, basename='UserReport')
router.register(r'surgery-reports', SurgeryReportViewSet, basename='surgery-reports')
router.register(r'patient-priority', PatientPriorityViewSet, basename='patient-priority')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'vital-signs', VitalSignViewSet, basename='vital-signs')





urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterUserView.as_view(), name='register-user'),
    path('login/', LoginUserView.as_view(), name='login-user'),
    path('logout/', LogoutUserView.as_view(), name='logout-user'),
    path('hospital/register/', HospitalRegisterView.as_view(), name='hospital-register'),
    path('hospital/login/', HospitalLoginView.as_view(), name='hospital-login'),
    # path('users/search_by_organ/', search_users_by_organ, name='search_by_organ'),
]
