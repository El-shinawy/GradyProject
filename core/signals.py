from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from .models import User, DonorMedicalProfile, PatientMedicalProfile, ChronicDisease, PatientPriority, OrganMatching

# # ==========================
# # 1. Update BMI / eligibility
# # ==========================
# @receiver(post_save, sender=User)
# def update_donor_eligibility(sender, instance, created, **kwargs):
#     if instance.role == 'donor':
#         # لو height أو weight موجودة
#         if instance.height_cm and instance.weight_kg:
#             height_m = instance.height_cm / 100
#             instance.bmi = round(instance.weight_kg / (height_m ** 2), 2)
#             instance.save(update_fields=['bmi'])
#         # تحديث كل الـ OrganMatching اللي متعلقين بالـ donor
#         for match in instance.donor_matches.all():
#             match.update_match()

# # ==========================
# # 2. Update Patient Priority
# # ==========================
# @receiver(post_save, sender=PatientMedicalProfile)
# def recalc_patient_priority(sender, instance, **kwargs):
#     patient = instance.patient
#     if hasattr(patient, 'priority'):
#         patient.priority.delete()  # delete old
#     # إعادة حساب
#     score = 0
#     if patient.chronic_diseases.exists():
#         score += patient.chronic_diseases.count() * 10
#     if instance.organ_needed:
#         score += 20
#     level = 'low'
#     if score >= 50:
#         level = 'critical'
#     elif score >= 30:
#         level = 'high'
#     elif score >= 10:
#         level = 'medium'
#     PatientPriority.objects.create(patient=patient, score=score, level=level)

# # ==========================
# # 3. Update Priority on chronic diseases changes
# # ==========================
# @receiver(m2m_changed, sender=User.chronic_diseases.through)
# def recalc_priority_on_disease_change(sender, instance, **kwargs):
#     if hasattr(instance, 'priority'):
#         instance.priority.delete()
#     score = 0
#     if instance.chronic_diseases.exists():
#         score += instance.chronic_diseases.count() * 10
#     if hasattr(instance, 'patient_profile') and instance.patient_profile.organ_needed:
#         score += 20
#     level = 'low'
#     if score >= 50:
#         level = 'critical'
#     elif score >= 30:
#         level = 'high'
#     elif score >= 10:
#         level = 'medium'
#     PatientPriority.objects.create(patient=instance, score=score, level=level)

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VitalSign, Alert

@receiver(post_save, sender=PatientMedicalProfile)
def recalc_patient_priority(sender, instance, **kwargs):
    patient = instance.patient
    if hasattr(patient, 'priority'):
        patient.priority.delete()
    score = 0
    if patient.chronic_diseases.exists():
        score += patient.chronic_diseases.count() * 10
    if instance.organ_needed:
        score += 20
    level = 'low'
    if score >= 50:
        level = 'critical'
    elif score >= 30:
        level = 'high'
    elif score >= 10:
        level = 'medium'
    PatientPriority.objects.create(patient=patient, score=score, level=level)
@receiver(m2m_changed, sender=User.chronic_diseases.through)
def recalc_priority_on_disease_change(sender, instance, **kwargs):
    if hasattr(instance, 'priority'):
        instance.priority.delete()
    score = 0
    if instance.chronic_diseases.exists():
        score += instance.chronic_diseases.count() * 10
    if hasattr(instance, 'patient_profile') and instance.patient_profile.organ_needed:
        score += 20
    level = 'low'
    if score >= 50:
        level = 'critical'
    elif score >= 30:
        level = 'high'
    elif score >= 10:
        level = 'medium'
    PatientPriority.objects.create(patient=instance, score=score, level=level)



# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VitalSign, Alert, PatientPriority

@receiver(post_save, sender=VitalSign)
def vital_sign_alert_and_priority(sender, instance, created, **kwargs):
    if not created:
        return

    surgery = instance.surgery_report.surgery
    patient = surgery.organ_matching.patient

    alerts = []
    critical = False
    score_delta = 0

    if instance.oxygen_saturation is not None and instance.oxygen_saturation < 92:
        alerts.append("انخفاض نسبة الأكسجين")
        critical = True
        score_delta += 15

    if instance.temperature_c is not None and instance.temperature_c >= 38:
        alerts.append("ارتفاع درجة الحرارة")
        score_delta += 10

    if instance.heart_rate is not None and instance.heart_rate > 120:
        alerts.append("ارتفاع ضربات القلب")
        score_delta += 10

    if instance.blood_pressure_systolic and instance.blood_pressure_systolic > 160:
        alerts.append("ارتفاع ضغط الدم")
        score_delta += 10

    if alerts:
        Alert.objects.create(
            user=patient,
            message="تحذير بعد العملية: " + "، ".join(alerts),
            alert_type="critical" if critical else "medical"
        )

    # تحديث Patient Priority
    priority, _ = PatientPriority.objects.get_or_create(patient=patient, defaults={"score": 0, "level": "low"})
    priority.score += score_delta

    if priority.score >= 70:
        priority.level = "critical"
    elif priority.score >= 40:
        priority.level = "high"
    elif priority.score >= 20:
        priority.level = "medium"
    else:
        priority.level = "low"

    priority.save()

    if not created:
        return

    patient = instance.surgery_report.surgery.organ_matching.patient

    alerts = []

    if instance.oxygen_saturation is not None and instance.oxygen_saturation < 92:
        alerts.append("انخفاض نسبة الأكسجين")

    if instance.temperature_c is not None and instance.temperature_c >= 38:
        alerts.append("ارتفاع درجة الحرارة")

    if instance.heart_rate is not None and instance.heart_rate > 120:
        alerts.append("ارتفاع معدل ضربات القلب")

    if alerts:
        Alert.objects.create(
            user=patient,
            message="تحذير بعد العملية: " + "، ".join(alerts),
            alert_type="critical"
        )