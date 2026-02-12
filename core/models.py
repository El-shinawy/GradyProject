from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime
from django.urls import reverse


# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, national_id, password=None, **extra_fields):
        if not national_id:
            raise ValueError("National ID is required")
        user = self.model(national_id=national_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, national_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(national_id, password, **extra_fields)


# User
class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('donor', 'Donor'),
    )
    STATUS_CHOICES = (
        ('pending', 'قيد الانتظار'),
        ('approved', 'موافق عليه'),
        ('under_review', 'قيد المراجعة'),
        ('rejected', 'مرفوض'),
    )

    BLOOD_TYPE_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    )

    GENDER_CHOICES = (
        ('male', 'ذكر '),
        ('female',"انثي"),

    )
    

    national_id = models.CharField(max_length=14, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    birthdate = models.DateField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPE_CHOICES, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    medical_record_number = models.CharField(max_length=50, blank=True, null=True)
    HLA_A_1 = models.CharField(max_length=10, null=True, blank=True)
    HLA_A_2 = models.CharField(max_length=10, null=True, blank=True)
    HLA_B_1 = models.CharField(max_length=10, null=True, blank=True)
    HLA_B_2 = models.CharField(max_length=10, null=True, blank=True)
    HLA_DR_1 = models.CharField(max_length=10, null=True, blank=True)
    HLA_DR_2 = models.CharField(max_length=10, null=True, blank=True)

    PRA = models.FloatField(null=True, blank=True)
    CMV_status = models.BooleanField(null=True, blank=True)
    EBV_status = models.BooleanField(null=True, blank=True)

    supervisor_doctor = models.ForeignKey(
        'Doctor', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='supervised_users'
    )

    hospital = models.ForeignKey(
        'Hospital', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='users'
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'national_id'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()
    def save(self, *args, **kwargs):
        if self.height_cm and self.height_cm > 0 and self.weight_kg:
            height_m = self.height_cm / 100
            self.bmi = round(self.weight_kg / (height_m ** 2), 2)
        else:
            self.bmi = None
        super().save(*args, **kwargs)


    def is_donor_medically_eligible(self):
        if self.role != 'donor' or self.bmi is None:
            return True
        return 18.5 <= self.bmi <= 35

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"



class OrganType(models.TextChoices):
    KIDNEY = 'kidney', 'كلية'
    LIVER = 'liver', 'كبد'
    HEART = 'heart', 'قلب'
    LUNG = 'lung', 'رئة'
    PANCREAS = 'pancreas', 'بنكرياس'


# Hospital & Doctor
class Hospital(models.Model):
    HOSPITAL_TYPE_CHOICES = (
        ('public', 'حكومي'),
        ('private', 'خاص'),
    )
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=50, default="Cairo")
    location = models.CharField(max_length=200)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True , default="email@gmail.com")
    working_hours = models.CharField(max_length=100, blank=True, null=True)
    hospital_type = models.CharField(max_length=10, choices=HOSPITAL_TYPE_CHOICES, default='public')
    password = models.CharField(max_length=128 , default="enter your password")  # hashed password
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(update_fields=['password'])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors')
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Dr. {self.name}"


# Chronic Diseases
class ChronicDisease(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class UserChronicDisease(models.Model):
    SEVERITY_CHOICES = (
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chronic_diseases')
    disease = models.ForeignKey(ChronicDisease, on_delete=models.CASCADE)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    def __str__(self):
        return f"{self.user} - {self.disease}"


# Patient & Donor Profiles
class PatientMedicalProfile(models.Model):
    patient = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )
    organ_needed = models.CharField(
        max_length=20,
        choices=OrganType.choices,default="Kindy"
    )

    def __str__(self):
        return f"{self.patient} needs {self.organ_needed}"



class DonorMedicalProfile(models.Model):
    donor = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='donor_profile'
    )
    organ_available = models.CharField(
        max_length=20,
        choices=OrganType.choices,
        default="Kindy"
    )

    def __str__(self):
        return f"{self.donor} donates {self.organ_available}"


# Appointment
class Appointment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)

    appointment_date = models.DateTimeField()
    reason = models.TextField(blank=True, null=True)

    STATUS_CHOICES = (
        ('scheduled', 'مجدول'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغى'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        super().clean()   

        if self.doctor and self.hospital and self.doctor.hospital != self.hospital:
            raise ValidationError("Doctor must belong to selected hospital")
        
        if self.appointment_date < timezone.now():
            raise ValidationError("Appointment date must be in the future")

    class Meta:
        ordering = ['-appointment_date']

    def clean(self):
        if self.doctor and self.hospital and self.doctor.hospital != self.hospital:
            raise ValidationError("Doctor must belong to selected hospital")

    def __str__(self):
        return f"{self.patient} - {self.appointment_date}"


# Organ & AI Matching
class OrganMatching(models.Model):
    STATUS_CHOICES = (
        ('pending', 'قيد الانتظار'),
        ('matched', 'مطابق'),
        ('rejected', 'مرفوض'),
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_matches')
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donor_matches')
    organ_type = models.CharField(max_length=50)
    match_percentage = models.FloatField(default=0) 
    ai_result = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_percentage']


    @staticmethod
    def calculate_match(patient, donor):
        mismatches = 0
        hla_fields = ['HLA_A_1','HLA_A_2','HLA_B_1','HLA_B_2','HLA_DR_1','HLA_DR_2']
        for field in hla_fields:
            patient_val = getattr(patient, field, None)
            donor_val = getattr(donor, field, None)
            if patient_val and donor_val and patient_val != donor_val:
                mismatches += 1

        score = max(0, 100 - mismatches * 10)

        if hasattr(donor, 'is_donor_medically_eligible') and not donor.is_donor_medically_eligible():
            score -= 20
            score = max(score, 0)

        return {
            "hla_mismatch_count": mismatches,
            "match_percentage": score,
            "ai_result": {
                "hla_mismatches": mismatches,
                "bmi": getattr(donor, 'bmi', None),
                "eligible": getattr(donor, 'is_donor_medically_eligible', lambda: False)()
            }
        }

    def update_match(self):
        result = self.calculate_match(self.patient, self.donor)
        self.match_percentage = result['match_percentage']
        self.ai_result = result['ai_result']
        self.status = 'pending'
        self.save()

    def __str__(self):
        return f"{self.patient} ↔ {self.donor} ({self.match_percentage}%)"

    # HLA mismatch ديناميكي

    @property
    def hla_mismatch_count(self):
        mismatches = 0
        hla_fields = ['HLA_A_1','HLA_A_2','HLA_B_1','HLA_B_2','HLA_DR_1','HLA_DR_2']
        for field in hla_fields:
            patient_val = getattr(self.patient, field, None)
            donor_val = getattr(self.donor, field, None)
            if patient_val and donor_val and patient_val != donor_val:
                mismatches += 1
        return mismatches


    @staticmethod
    def calculate_match(patient, donor):
        mismatches = 0
        hla_fields = ['HLA_A_1','HLA_A_2','HLA_B_1','HLA_B_2','HLA_DR_1','HLA_DR_2']
        for field in hla_fields:
            patient_val = getattr(patient, field, None)
            donor_val = getattr(donor, field, None)
            if patient_val and donor_val and patient_val != donor_val:
                mismatches += 1

        score = max(0, 100 - mismatches * 10)

        if hasattr(donor, 'is_donor_medically_eligible') and not donor.is_donor_medically_eligible():
            score -= 20
            score = max(score, 0)
        return {
            "hla_mismatch_count": mismatches,
            "match_percentage": score,
            "ai_result": {
                "hla_mismatches": mismatches,
                "bmi": getattr(donor, 'bmi', None),
                "eligible": getattr(donor, 'is_donor_medically_eligible', lambda: False)()
            }
        }

    def update_match(self):
        result = self.calculate_match(self.patient, self.donor)
        self.match_percentage = result['match_percentage']
        self.ai_result = result['ai_result']
        self.status = 'pending'  
        self.save()

# Surgery
class Surgery(models.Model):
    surgery_number = models.CharField(max_length=50, unique=True)
    organ_matching = models.OneToOneField(OrganMatching, on_delete=models.CASCADE)

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)

    scheduled_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)  
    operation_room = models.CharField(max_length=100, null=True, blank=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.scheduled_date < timezone.now():
            raise ValidationError("Surgery date must be in the future")

    def __str__(self):
        return f"Surgery {self.surgery_number}"
    
    def get_admin_url(self):
        return reverse("admin:core_surgery_change", args=[self.id])


# MRI Reports
class MRIReport(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mri_reports')
    # organ_type = models.CharField(max_length=50)

    before_scan = models.ImageField(upload_to='mri/before/', null=True, blank=True)
    after_scan = models.ImageField(upload_to='mri/after/', null=True, blank=True)

    ai_result = models.TextField(null=True, blank=True)
    mismatch_alert = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MRI - {self.patient}"


# Patient Priority
class PatientPriority(models.Model):
    patient = models.OneToOneField(User, on_delete=models.CASCADE, related_name='priority')
    score = models.FloatField(default=0)
    level = models.CharField(
        max_length=20,
    choices = [
    ('low', 'منخفض'),
    ('medium', 'متوسط'),
    ('high', 'مرتفع'),
    ('critical', 'حرج')
]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient} - {self.level}"


# Alerts
class Alert(models.Model):
    ALERT_TYPES = (
    ('info', 'معلومة'),
    ('warning', 'تحذير'),
    ('medical', 'طبي'),
    ('critical', 'حرج'),
)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.alert_type}"


class UserReport(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_reports')
    report_type = models.CharField(max_length=50)  # زي "MRI", "Blood Test", "X-Ray" أو أي نوع آخر
    report_file = models.FileField(upload_to='user_reports/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} - {self.report_type}"



class SurgeryReport(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, related_name='report')

    result_summary = models.TextField()
    complications = models.TextField(null=True, blank=True)
    doctor_notes = models.TextField(null=True, blank=True)

    # Vital Signs
    temperature_c = models.FloatField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    oxygen_saturation = models.FloatField(null=True, blank=True)

    report_file = models.FileField(upload_to='surgery_reports/files/', null=True, blank=True)
    report_image = models.ImageField(upload_to='surgery_reports/images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)




class VitalSign(models.Model):
    surgery_report = models.ForeignKey(
        SurgeryReport,
        on_delete=models.CASCADE,
        related_name='vital_signs'
    )

    temperature_c = models.FloatField(null=True, blank=True)   # درجة الحرارة
    heart_rate = models.PositiveIntegerField(null=True, blank=True)  # النبض
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)  # الضغط العالي
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True) # الضغط الواطي
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)  # معدل التنفس
    oxygen_saturation = models.FloatField(null=True, blank=True)  # نسبة الأكسجين %

    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vitals for {self.surgery_report.surgery.surgery_number} @ {self.recorded_at}"
