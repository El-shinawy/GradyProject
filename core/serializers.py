from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate


# register users


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[('patient','Patient'), ('donor','Donor')])
    organ = serializers.ChoiceField(choices=OrganType.choices, write_only=True)  # العضو المطلوب أو المتاح

    class Meta:
        model = User
        fields = [
            'national_id', 'first_name', 'last_name', 'role',
            'birthdate', 'height_cm', 'weight_kg',
            'blood_type', 'gender', 'phone', 'hospital',
            'organ','medical_record_number'
        ]

    #  تحقق من الرقم القومي
    def validate_national_id(self, value):
        if len(value) != 14 or not value.isdigit():
            raise serializers.ValidationError("National ID must be 14 digits")
        if User.objects.filter(national_id=value).exists():
            raise serializers.ValidationError("National ID already exists")
        return value

    #  إنشاء المستخدم والبروفايل حسب الدور
    def create(self, validated_data):
        organ = validated_data.pop('organ')  # نفصل العضو
        national_id = validated_data['national_id']
        role = validated_data['role']

        #  Password = آخر 4 أرقام من الرقم القومي
        password = national_id[-4:]

        # إنشاء المستخدم
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # إنشاء profile حسب الدور
        if role == 'patient':
            PatientMedicalProfile.objects.create(
                patient=user,
                organ_needed=organ
            )
        elif role == 'donor':
            DonorMedicalProfile.objects.create(
                donor=user,
                organ_available=organ
            )

        user._temp_password = password

        return user



# LOGIN  users

class LoginSerializer(serializers.Serializer):
    national_id = serializers.CharField()
    password = serializers.CharField(write_only=True)



# hospital register
class HospitalRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Hospital
        fields = ['name', 'location', 'license_number', 'phone', 'emergency_phone', 'email', 'working_hours', 'hospital_type', 'password']


# Hospital Login

class HospitalLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# ==========================
# User Serializer
# ==========================
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    # دمج بيانات Patient / Donor Profile
    organ_needed = serializers.SerializerMethodField()
    organ_available = serializers.SerializerMethodField()
    chronic_diseases = serializers.SerializerMethodField()
    hospital_detail = serializers.SerializerMethodField()
    supervisor_doctor_detail = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'national_id', 'first_name', 'last_name', 'full_name', 'role', 'status',
            'birthdate', 'height_cm', 'weight_kg', 'bmi', 'blood_type', 'gender',
            'HLA_A_1','HLA_A_2','HLA_B_1','HLA_B_2','HLA_DR_1','HLA_DR_2',
            'PRA','CMV_status','EBV_status','supervisor_doctor','hospital',
            'is_active','is_staff','created_at','medical_record_number',
            # بيانات profile
            'organ_needed','organ_available','chronic_diseases','hospital_detail','supervisor_doctor_detail'
        ]
        read_only_fields = ['bmi', 'created_at']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    # =========================
    # Patient fields
    # =========================
    def get_organ_needed(self, obj):
        if obj.role == 'patient' and hasattr(obj, 'patient_profile'):
            return obj.patient_profile.organ_needed
        return None

    def get_chronic_diseases(self, obj):
        if obj.role == 'patient' and hasattr(obj, 'patient_profile'):
            return [
                {"name": uc.disease.name, "severity": uc.severity} 
                for uc in obj.chronic_diseases.all()
            ]
        elif obj.role == 'donor' and hasattr(obj, 'donor_profile'):
            return [
                {"name": uc.disease.name, "severity": uc.severity} 
                for uc in obj.chronic_diseases.all()
            ]
        return []

    def get_hospital_detail(self, obj):
        if hasattr(obj, 'patient_profile') and obj.role == 'patient' and obj.hospital:
            from .serializers import HospitalSerializer
            return HospitalSerializer(obj.hospital).data
        elif hasattr(obj, 'donor_profile') and obj.role == 'donor' and obj.hospital:
            from .serializers import HospitalSerializer
            return HospitalSerializer(obj.hospital).data
        return None

    def get_supervisor_doctor_detail(self, obj):
        if hasattr(obj, 'patient_profile') and obj.role == 'patient' and obj.supervisor_doctor:
            from .serializers import DoctorSerializer
            return DoctorSerializer(obj.supervisor_doctor).data
        elif hasattr(obj, 'donor_profile') and obj.role == 'donor' and obj.supervisor_doctor:
            from .serializers import DoctorSerializer
            return DoctorSerializer(obj.supervisor_doctor).data
        return None

    def get_organ_available(self, obj):
        if obj.role == 'donor' and hasattr(obj, 'donor_profile'):
            return obj.donor_profile.organ_available
        return None

# ==========================
# Hospital & Doctor
# ==========================
class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = '__all__'

class HospitalUserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'role',
            'national_id',
            'gender',
            'blood_type',
            'status',
        ]


class HospitalStatsSerializer(serializers.ModelSerializer):
    patients = serializers.SerializerMethodField()
    donors = serializers.SerializerMethodField()
    patients_count = serializers.SerializerMethodField()
    donors_count = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            'id',
            'name',
            'hospital_type',
            'patients_count',
            'donors_count',
            'patients',
            'donors',
        ]

    def get_patients(self, obj):
        qs = obj.users.filter(role='patient')
        return HospitalUserMiniSerializer(qs, many=True).data

    def get_donors(self, obj):
        qs = obj.users.filter(role='donor')
        return HospitalUserMiniSerializer(qs, many=True).data

    def get_patients_count(self, obj):
        return obj.users.filter(role='patient').count()

    def get_donors_count(self, obj):
        return obj.users.filter(role='donor').count()


class DoctorSerializer(serializers.ModelSerializer):
    hospital_detail = HospitalSerializer(source='hospital', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialty', 'phone', 'hospital', 'hospital_detail']
    def validate_hospital(self, value):
        if not Hospital.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("المستشفى دي غير موجودة")
        return value


# ==========================
# Chronic Diseases
# ==========================
class ChronicDiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChronicDisease
        fields = '__all__'


class UserChronicDiseaseSerializer(serializers.ModelSerializer):
    disease_detail = ChronicDiseaseSerializer(source='disease', read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = UserChronicDisease
        fields = ['id', 'user', 'user_detail', 'disease', 'disease_detail', 'severity']


# ==========================
# Patient & Donor Profiles
# ==========================
class PatientMedicalProfileSerializer(serializers.ModelSerializer):
    patient_detail = UserSerializer(source='patient', read_only=True)  # ده حيجيب كل بيانات المريض
    chronic_diseases = serializers.SerializerMethodField()
    hospital_detail = serializers.SerializerMethodField()
    supervisor_doctor_detail = serializers.SerializerMethodField()
    class Meta:
        model = PatientMedicalProfile
        fields = ['patient_detail', 'organ_needed', 'chronic_diseases', 'hospital_detail', 'supervisor_doctor_detail']  


    def create(self, validated_data):
        patient = validated_data['patient']
        organ_needed = validated_data.get('organ_needed')

        profile, created = PatientMedicalProfile.objects.update_or_create(
            patient=patient,
            defaults={'organ_needed': organ_needed}
        )
        return profile
    def get_chronic_diseases(self, obj):
        # إحضار كل الأمراض المتعلقة بالمريض
        return [
            {"name": uc.disease.name, "severity": uc.severity} 
            for uc in obj.patient.chronic_diseases.all()
        ]
    def get_hospital_detail(self, obj):
        if obj.patient.hospital:
            from .serializers import HospitalSerializer  # لتجنب الاستدعاء الدائري
            return HospitalSerializer(obj.patient.hospital).data
        return None
    def get_supervisor_doctor_detail(self, obj):
        if obj.patient.supervisor_doctor:
            from .serializers import DoctorSerializer  # لتجنب الاستدعاء الدائري
            return DoctorSerializer(obj.patient.supervisor_doctor).data
        return None
    

class DonorMedicalProfileSerializer(serializers.ModelSerializer):
    donor_detail = UserSerializer(source='donor', read_only=True)  # ده حيجيب كل بيانات المريض
    chronic_diseases = serializers.SerializerMethodField()
    hospital_detail = serializers.SerializerMethodField()
    supervisor_doctor_detail = serializers.SerializerMethodField()
    class Meta:
        model = DonorMedicalProfile
        fields = [ 'id',
            'donor',
            'donor_detail',
            'organ_available',
            'chronic_diseases',
            'hospital_detail',
            'supervisor_doctor_detail',]
    def create(self, validated_data):
        donor = validated_data['donor']
        organ_available = validated_data.get('organ_available')

        profile, created = DonorMedicalProfile.objects.update_or_create(
            donor=donor,
            defaults={'organ_available': organ_available}
        )
        return profile
    def get_chronic_diseases(self, obj):
        # إحضار كل الأمراض المتعلقة بالمريض
        return [
            {"name": uc.disease.name, "severity": uc.severity} 
            for uc in obj.donor.chronic_diseases.all()
        ]
    def get_hospital_detail(self, obj):
        if obj.donor.hospital:
            from .serializers import HospitalSerializer  # لتجنب الاستدعاء الدائري
            return HospitalSerializer(obj.donor.hospital).data
        return None
    def get_supervisor_doctor_detail(self, obj):
        if obj.donor.supervisor_doctor:
            from .serializers import DoctorSerializer  # لتجنب الاستدعاء الدائري
            return DoctorSerializer(obj.donor.supervisor_doctor).data
        return None
    

    
# ==========================
# Appointment
# ==========================
class AppointmentSerializer(serializers.ModelSerializer):
    patient_detail = UserSerializer(source='patient', read_only=True)
    doctor_detail = DoctorSerializer(source='doctor', read_only=True)
    hospital_detail = HospitalSerializer(source='hospital', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_detail', 'doctor', 'doctor_detail',
            'hospital', 'hospital_detail', 'appointment_date', 'reason', 'status', 'created_at'
        ]
    def get_patient_detail(self, obj):
        return {"id": obj.patient.id, "full_name": f"{obj.patient.first_name} {obj.patient.last_name}"}

    def get_doctor_detail(self, obj):
        if obj.doctor:
            return {"id": obj.doctor.id, "name": obj.doctor.name, "specialty": obj.doctor.specialty}
        return None

    def get_hospital_detail(self, obj):
        if obj.hospital:
            return {"id": obj.hospital.id, "name": obj.hospital.name}
        return None

    def validate(self, data):
        # Doctor-Hospital check
        doctor = data.get('doctor')
        hospital = data.get('hospital')
        if doctor and hospital and doctor.hospital != hospital:
            raise serializers.ValidationError("Doctor must belong to selected hospital")

        # Appointment date in future
        if data.get("appointment_date") and data["appointment_date"] < timezone.now():
            raise serializers.ValidationError("Appointment date must be in the future")
        return data


# ==========================
# Organ & Matching
# ==========================
class OrganMatchingSerializer(serializers.ModelSerializer):
    patient_detail = UserSerializer(source='patient', read_only=True)
    donor_detail = UserSerializer(source='donor', read_only=True)
    hla_mismatch_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrganMatching
        fields = [
            'id', 'patient', 'patient_detail', 'donor', 'donor_detail',
            'organ_type', 'match_percentage', 'hla_mismatch_count',
            'ai_result', 'status', 'created_at'
        ]
        read_only_fields = ['hla_mismatch_count', 'match_percentage', 'ai_result', 'created_at']
        def get_patient_detail(self, obj):
            return {"id": obj.patient.id, "full_name": f"{obj.patient.first_name} {obj.patient.last_name}"}

    def get_donor_detail(self, obj):
        return {"id": obj.donor.id, "full_name": f"{obj.donor.first_name} {obj.donor.last_name}"}

# ==========================
# Surgery
# ==========================
class SurgerySerializer(serializers.ModelSerializer):
    organ_matching_detail = OrganMatchingSerializer(source='organ_matching', read_only=True)
    doctor_detail = DoctorSerializer(source='doctor', read_only=True)
    hospital_detail = HospitalSerializer(source='hospital', read_only=True)

    class Meta:
        model = Surgery
        fields = [
            'id', 'surgery_number', 'organ_matching', 'organ_matching_detail',
            'hospital', 'hospital_detail', 'doctor', 'doctor_detail',
            'scheduled_date', 'completed', 'created_at','duration_minutes','operation_room'
        ]


# ==========================
# MRI Reports
# ==========================
class MRIReportSerializer(serializers.ModelSerializer):
    patient_detail = UserSerializer(source='patient', read_only=True)

    class Meta:
        model = MRIReport
        fields = ['id', 'patient', 'patient_detail', 'before_scan', 'after_scan',
                  'ai_result', 'mismatch_alert', 'created_at']


# ==========================
# Patient Priority
# ==========================
class PatientPrioritySerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()

    class Meta:
        model = PatientPriority
        fields = ['id', 'patient', 'patient_detail', 'score', 'level', 'updated_at']

    def get_patient_detail(self, obj):
        return {"id": obj.patient.id, "full_name": f"{obj.patient.first_name} {obj.patient.last_name}"}


# ==========================
# Alerts
# ==========================
class AlertSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = ['id', 'user', 'user_detail', 'message', 'alert_type', 'read', 'created_at']

    def get_user_detail(self, obj):
        return {"id": obj.user.id, "full_name": f"{obj.user.first_name} {obj.user.last_name}"}



class UserReportSerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()

    class Meta:
        model = UserReport
        fields = [
            'id', 'patient', 'patient_detail', 'report_type',
            'report_file', 'description', 'created_at'
        ]

    def get_patient_detail(self, obj):
        if obj.patient:
            return {
                "id": obj.patient.id,
                "full_name": f"{obj.patient.first_name} {obj.patient.last_name}",
                "national_id": getattr(obj.patient, 'national_id', None),
                "role": getattr(obj.patient, 'role', None)
            }
        return None
    


class SurgeryReportSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='surgery.organ_matching.patient.__str__', read_only=True)
    doctor_name = serializers.CharField(source='surgery.doctor.name', read_only=True)
    hospital_name = serializers.CharField(source='surgery.hospital.name', read_only=True)

    duration_minutes = serializers.IntegerField(source='surgery.duration_minutes', read_only=True)
    operation_room = serializers.CharField(source='surgery.operation_room', read_only=True)

    class Meta:
        model = SurgeryReport
        fields = [
            'id',
            'surgery',
            'patient_name',
            'doctor_name',
            'hospital_name',
            'duration_minutes',
            'operation_room',
            'result_summary',
            'complications',
            'doctor_notes',
            'report_file',
            'report_image',
            'created_at',
        ]





class VitalSignSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSign
        fields = [
            'id',
            'surgery_report',
            'temperature_c',
            'heart_rate',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'respiratory_rate',
            'oxygen_saturation',
            'recorded_at'
        ]
        read_only_fields = ['recorded_at']