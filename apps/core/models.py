from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "PATIENT"
        CLINICAL = "CLINICAL"
        ADMIN = "ADMIN"

    # username, password, email, is_active, date_joined are all provided by AbstractUser

    name = models.CharField(max_length=40, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=15, blank=True, null=True)


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1)

    street = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)

    insurance_provider = models.CharField(max_length=50, blank=True)
    policy_number = models.CharField(max_length=50, blank=True)


class EmergencyContact(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    priority = models.IntegerField(default=1)


class ClinicalStaff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    license_number = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=50)
    hire_date = models.DateField()


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        COMPLETED = "COMPLETED"
        CANCELED = "CANCELED"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinical_staff = models.ForeignKey(ClinicalStaff, on_delete=models.CASCADE)

    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    location = models.CharField(max_length=100)
    visit_type = models.CharField(max_length=100)
    chief_complaint = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["clinical_staff", "date", "time"],
                condition=Q(status__in=["PENDING", "CONFIRMED"]),
                name="no_conflicts"
            )
        ]


class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinical_staff = models.ForeignKey(ClinicalStaff, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, null=True, blank=True, on_delete=models.SET_NULL)

    visit_summary = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class Prescription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE'
        COMPLETED = 'COMPLETED'
        CANCELED = 'CANCELED'

    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE)

    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    note = models.TextField(blank=True)


class TestResult(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        COMPLETED = 'COMPLETED'

    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE)
    ordered_by = models.ForeignKey(ClinicalStaff, on_delete=models.CASCADE)

    test_name = models.CharField(max_length=100)
    test_date = models.DateField()
    result_date = models.DateField(null=True, blank=True)

    results = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)


class Notification(models.Model):
    class Status(models.TextChoices):
        READ = 'READ'
        UNREAD = 'UNREAD'

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNREAD)
    type = models.CharField(max_length=50)


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    action = models.CharField(max_length=50)
    affected_table = models.CharField(max_length=50)
    affected_record_id = models.IntegerField()

    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
