from rest_framework import viewsets, status 
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import *
from .serializers import *
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Count, Q



class PatientMedicalProfileListView(generics.ListAPIView):
    queryset = PatientMedicalProfile.objects.all()
    serializer_class = PatientMedicalProfileSerializer

class DonorMedicalProfileListView(generics.ListAPIView):
    queryset = DonorMedicalProfile.objects.all()
    serializer_class = DonorMedicalProfileSerializer

# register 
class RegisterUserView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "id": user.id,
            "national_id": user.national_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "password": user._temp_password,
            "token": token.key,
            "message": "User registered successfully"
        }, status=status.HTTP_201_CREATED)


# login
class LoginSerializer(serializers.Serializer):
    national_id = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)


# ======================
# View
# ======================
class LoginUserView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # تحقق من البيانات أولاً
        if not serializer.is_valid():
            return Response({
                "detail": "Invalid input",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        national_id = serializer.validated_data['national_id']
        password = serializer.validated_data['password']

        user = authenticate(request ,username=national_id, password=password)
        if not user:
            return Response({
                "Message": "Invalid credentials. Please check national_id and password."
            }, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "id": user.id,
            "national_id": user.national_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "token": token.key,
            "Message": "Login successful"
        })

# LOGOUT
class LogoutUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({"message": "Logged out successfully"})





# hospital register 
class HospitalRegisterView(generics.GenericAPIView):
    serializer_class = HospitalRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = serializer.save()
        hospital.set_password(request.data['password'])
        return Response({
            "id": hospital.id,
            "name": hospital.name,
            "hospital_type": hospital.hospital_type,
            "email": hospital.email
        }, status=status.HTTP_201_CREATED)

# ==========================
# Hospital Login
# ==========================
class HospitalLoginView(generics.GenericAPIView):
    serializer_class = HospitalLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            hospital = Hospital.objects.get(email=email)
        except Hospital.DoesNotExist:
            return Response({"Message": "Hospital not found"}, status=status.HTTP_404_NOT_FOUND)

        if not hospital.check_password(password):
            return Response({"Message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        users = User.objects.filter(hospital=hospital)
        users_data = [
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "national_id": u.national_id
            } for u in users
        ]

        return Response({
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "hospital_type": hospital.hospital_type,
            "users": users_data
        })





# ==========================
# Hospital & Doctor
# ==========================
class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer

    @action(detail=False, methods=['get'])
    def stats_all(self, request):
        hospitals = Hospital.objects.all()
        data = []

        for hospital in hospitals:
            users = User.objects.filter(hospital=hospital)

            # تصفية المرضى والمتبرعين بالقيم الصحيحة
            patients = users.filter(role='patient')
            donors = users.filter(role='donor')

            # بيانات المرضى مع ملفهم الطبي
            patients_data = []
            for p in patients:
                try:
                    profile = p.patient_profile  # اسم related_name في OneToOneField
                    patients_data.append(PatientMedicalProfileSerializer(profile).data)
                except PatientMedicalProfile.DoesNotExist:
                    # لو الملف مش موجود
                    patients_data.append({
                        "id": p.id,
                        "first_name": p.first_name,
                        "last_name": p.last_name,
                        "national_id": p.national_id,
                        "role": p.role,
                        "note": "No patient profile"
                    })

            # بيانات المتبرعين مع ملفهم الطبي
            donors_data = []
            for d in donors:
                try:
                    profile = d.donor_profile
                    donors_data.append(DonorMedicalProfileSerializer(profile).data)
                except DonorMedicalProfile.DoesNotExist:
                    donors_data.append({
                        "id": d.id,
                        "first_name": d.first_name,
                        "last_name": d.last_name,
                        "national_id": d.national_id,
                        "role": d.role,
                        "note": "No donor profile"
                    })

            data.append({
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "total_users": users.count(),
                "total_patients": patients.count(),
                "total_donors": donors.count(),
                "patients": patients_data,
                "donors": donors_data
            })

        return Response(data)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    def get_queryset(self):
        queryset = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)
        return queryset


# ==========================
# Chronic Diseases
# ==========================
class ChronicDiseaseViewSet(viewsets.ModelViewSet):
    queryset = ChronicDisease.objects.all()
    serializer_class = ChronicDiseaseSerializer


class UserChronicDiseaseViewSet(viewsets.ModelViewSet):
    queryset = UserChronicDisease.objects.all()
    serializer_class = UserChronicDiseaseSerializer


# ==========================
# Patient & Donor Profiles
# ==========================
class PatientMedicalProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientMedicalProfile.objects.all()
    serializer_class = PatientMedicalProfileSerializer


class DonorMedicalProfileViewSet(viewsets.ModelViewSet):
    queryset = DonorMedicalProfile.objects.all()
    serializer_class = DonorMedicalProfileSerializer


# ==========================
# Appointments
# ==========================
class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def perform_create(self, serializer):
        doctor = serializer.validated_data.get('doctor')
        hospital = serializer.validated_data.get('hospital')
        if doctor and hospital and doctor.hospital != hospital:
            raise ValidationError("Doctor must belong to selected hospital")
        serializer.save()




# ==========================
# Organ & Matching
# ==========================
class OrganMatchingViewSet(viewsets.ModelViewSet):
    queryset = OrganMatching.objects.all()
    serializer_class = OrganMatchingSerializer

    @action(detail=False, methods=['post'])
    def auto_match(self, request):
        patients = User.objects.filter(role='patient', status='approved')
        all_matches = []
        for patient in patients:
            donors = User.objects.filter(role='donor', status='approved')
            for donor in donors:
                result = OrganMatching.calculate_match(patient, donor)
                # تخزين الـ match
                match, created = OrganMatching.objects.update_or_create(
                    patient=patient,
                    donor=donor,
                    defaults={
                        "organ_type": getattr(patient.patient_profile, 'organ_needed', 'N/A'),
                        "match_percentage": result['match_percentage'],
                        "ai_result": result['ai_result'],
                        "status": 'pending'
                    }
                )
                all_matches.append({
                    "patient": str(patient),
                    "donor": str(donor),
                    "organ_type": getattr(patient.patient_profile, 'organ_needed', 'N/A'),
                    "match_percentage": result['match_percentage']
                })
        return Response(all_matches)


# ==========================
# Surgery
# ==========================
class SurgeryViewSet(viewsets.ModelViewSet):
    queryset = Surgery.objects.all()
    serializer_class = SurgerySerializer


# ==========================
# MRI Reports
# ==========================
class MRIReportViewSet(viewsets.ModelViewSet):
    queryset = MRIReport.objects.all()
    serializer_class = MRIReportSerializer


# ==========================
# Patient Priority
# ==========================
class PatientPriorityViewSet(viewsets.ModelViewSet):
    queryset = PatientPriority.objects.all()
    serializer_class = PatientPrioritySerializer

    @action(detail=False, methods=['post'])
    def calculate_priority(self, request):
        patients = User.objects.filter(role='patient')
        results = []
        for patient in patients:
            score = 0
            if patient.chronic_diseases.exists():
                score += patient.chronic_diseases.count() * 10
            if hasattr(patient, 'patient_profile') and patient.patient_profile.organ_needed:
                score += 20

            # تحديد المستوى
            level = 'low'
            if score >= 50:
                level = 'critical'
            elif score >= 30:
                level = 'high'
            elif score >= 10:
                level = 'medium'

            # حفظ أو تحديث
            priority, _ = PatientPriority.objects.update_or_create(
                patient=patient,
                defaults={'score': score, 'level': level}
            )

            results.append({
                "patient": str(patient),
                "score": score,
                "level": level
            })

        return Response(results)
# ==========================
# Alerts
# ==========================
class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer

    def get_queryset(self):
            return Alert.objects.all().order_by('-created_at')  # مؤقتًا بدون auth

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
            alert = self.get_object()
            alert.read = True
            alert.save()
            return Response({"detail": "Alert marked as read"})


from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    # 🔹 إحصائيات عامة لكل users
    @action(detail=False, methods=['get'])
    def stats(self, request):
        stats = User.objects.aggregate(
            total_users=Count('id'),
            patients_count=Count('id', filter=Q(role='patient')),
            donors_count=Count('id', filter=Q(role='donor')),
        )
        return Response(stats)

    # 🔹 إحصائيات حسب مستشفى
    @action(detail=False, methods=['get'])
    def stats_by_hospital(self, request):
        hospital_id = request.query_params.get('hospital')
        qs = User.objects.all()
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        return Response({
            "total_users": qs.count(),
            "patients": qs.filter(role='patient').count(),
            "donors": qs.filter(role='donor').count(),
        })

    # 🔹 كل المستخدمين مع التفاصيل الكاملة (patients + donors)
    @action(detail=False, methods=['get'])
    def stats_all(self, request):
        patients_qs = User.objects.filter(role='patient')
        donors_qs = User.objects.filter(role='donor')

        # استخدام UserSerializer اللي فيه كل بيانات profile
        patients_data = UserSerializer(patients_qs, many=True).data
        donors_data = UserSerializer(donors_qs, many=True).data

        return Response({
            "total_patients": patients_qs.count(),
            "total_donors": donors_qs.count(),
            "patients": patients_data,
            "donors": donors_data
        })

class UserReportViewSet(viewsets.ModelViewSet):
    queryset = UserReport.objects.all()
    serializer_class = UserReportSerializer

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and not user.is_anonymous:
            # لو في مستخدم مسجل، جِب تقاريره فقط
            return UserReport.objects.filter(patient=user).order_by('-report_date', '-created_at')
        # لو مفيش مستخدم مسجل، رجع فاضي
        return UserReport.objects.none()

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        if user and not user.is_anonymous:
            # لو مستخدم مسجل، اربط التقرير به
            serializer.save(patient=user)
        else:
            # لو مفيش، خلي الـ patient لازم يُرسل في البيانات
            serializer.save()



class SurgeryReportViewSet(viewsets.ModelViewSet):
    queryset = SurgeryReport.objects.select_related(
        'surgery__organ_matching__patient',
        'surgery__doctor'
    )
    serializer_class = SurgeryReportSerializer

    def perform_create(self, serializer):
        report = serializer.save()

        patient = report.surgery.organ_matching.patient

        # 🔔 إنشاء Alert للمريض
        Alert.objects.create(
            user=patient,
            message="تم إضافة تقرير العملية الجراحية الخاصة بك.",
            alert_type='medical'
        )

        # 📊 تحديث أولوية المريض
        priority, created = PatientPriority.objects.get_or_create(patient=patient)

        # مثال بسيط للتحديث
        priority.score += 10
        if priority.score >= 80:
            priority.level = 'critical'
        elif priority.score >= 50:
            priority.level = 'high'
        elif priority.score >= 20:
            priority.level = 'medium'
        else:
            priority.level = 'low'

        priority.save()




class VitalSignViewSet(viewsets.ModelViewSet):
    queryset = VitalSign.objects.all().order_by('-recorded_at')
    serializer_class = VitalSignSerializer




