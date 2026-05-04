from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import get_user_model
User = get_user_model()
from datetime import datetime
from django.contrib import messages
from django.db import transaction
from core.models import *
from django.db import IntegrityError

# Page views

def emr_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            AuditLog.objects.create(
                user=user,
                action="LOGIN",
                affected_table=User.__name__,
                affected_record_id=user.id,
                description=(
                    f"User logged in: {username}"
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

            #RBAC routing
            if user.role == User.Role.ADMIN:
                return redirect("admin_dashboard")
            elif user.role == User.Role.CLINICAL:
                return redirect("clinical_dashboard")
            else:
                return redirect("patient_dashboard")

        AuditLog.objects.create(
            user=user if user else None,
            action="FAILED_LOGIN",
            affected_table=User.__name__,
            affected_record_id=0,
            description=(
                f"Failed login attempt for {username}"
            ),
            ip_address=request.META.get("REMOTE_ADDR")
        )

        return render(request, 'core/emr_login.html', {
            "error": "Invalid credentials"
        })

    return render(request, 'core/emr_login.html')

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT, login_url='emr_login')
def patient_dashboard(request):
    patient = Patient.objects.get(user=request.user)

    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by("-date", "-time")

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-date_sent")

    records = MedicalRecord.objects.filter(
        patient=patient
    ).order_by("-date_created")

    return render(request, "core/patient_dashboard.html", {
        "patient": patient,
        "appointments": appointments,
        "notifications": notifications,
        "records": records,
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT, login_url='emr_login')
def patient_profile(request):
    return render(request, 'core/patient_profile.html')

def patient_registration(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        name = request.POST.get('name')
        phone = request.POST.get('phone')

        date_of_birth = request.POST.get('date_of_birth')
        try:
            date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date of birth")
            return redirect("patient_registration")

        gender = request.POST.get('gender')
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        insurance_provider = request.POST.get('insurance_provider')
        policy_number = request.POST.get('policy_number')

        required_fields = [
            username, password, name, email, phone,
            date_of_birth, gender, street, city, state, zip_code,
        ]

        if any(not f for f in required_fields):
            return render(request, 'core/patient_registration.html', {
                "error": "Missing information"
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'core/patient_registration.html', {
                "error": "Username already in use"
            })

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )

                user.name = name
                user.phone = phone
                user.role = User.Role.PATIENT
                user.save()

                patient = Patient.objects.create(
                    user=user,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    street=street,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    insurance_provider=insurance_provider,
                    policy_number=policy_number,
                )

                AuditLog.objects.create(
                    user=user,
                    action="CREATE",
                    affected_table=Patient.__name__,
                    affected_record_id=patient.id,
                    description=(
                        f"Created Patient for new User {username} "
                        f"(User ID: {user.id})"
                    ),
                    ip_address=request.META.get("REMOTE_ADDR")
                )

        except Exception as e:
            AuditLog.objects.create(
                user=None,
                action="FAILED_CREATE",
                affected_table=Patient.__name__,
                affected_record_id=0,
                description=(
                    f"Failed to create new Patient: {str(e)}"
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

            return render(request, 'core/patient_registration.html', {
                "error": f"Registration failed: {e}"
            })

        return redirect("emr_login")

    return render(request, 'core/patient_registration.html')

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT, login_url='emr_login')
def appointment_scheduling(request):
    patient = Patient.objects.get(user=request.user)
    providers = ClinicalStaff.objects.select_related("user").all()

    if request.method == "POST":
        provider_id = request.POST.get('provider_id')
        date = request.POST.get('date')
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date")
            return redirect("appointment_scheduling")

        time = request.POST.get('time')
        try:
            time = datetime.strptime(time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time")
            return redirect("appointment_scheduling")

        location = request.POST.get('location')
        visit_type = request.POST.get('visit_type')

        if not provider_id or not date or not time:
            messages.error(request, "Missing appointment details.")
            return redirect("appointment_scheduling")

        try:
            provider = ClinicalStaff.objects.get(user_id=provider_id)
            with transaction.atomic():
                appointment = Appointment.objects.create(
                    patient=patient,
                    clinical_staff=provider,
                    date=date,
                    time=time,
                    location=location,
                    visit_type=visit_type,
                    status=Appointment.Status.PENDING
                )

                AuditLog.objects.create(
                    user=request.user,
                    action="CREATE",
                    affected_table=Appointment.__name__,
                    affected_record_id=appointment.id,
                    description=(
                        f"Created appointment for {request.user.username} "
                        f"with provider {provider.user.username} on {date} at {time}"
                    ),
                    ip_address=request.META.get("REMOTE_ADDR")
                )

                # Patient notification
                Notification.objects.create(
                    user=request.user,
                    message=f"Your appointment request for {date} at {time} has been submitted.",
                    type="APPOINTMENT",
                )

                # Clinician notification
                Notification.objects.create(
                    user=provider.user,
                    message="An appointment with you has been scheduled, please confirm.",
                    type="APPOINTMENT",
                )

            messages.success(request, "Appointment requested successfully.")
            return redirect("patient_dashboard")

        except ClinicalStaff.DoesNotExist:
            AuditLog.objects.create(
                user=request.user,
                action="FAILED_CREATE",
                affected_table=Appointment.__name__,
                affected_record_id=0,
                description=(
                    f"Failed to create new Appointment for {request.user.username}: "
                    f"Provider {provider_id} does not exist."
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

            messages.error(request, "No clinical staff found.")

        except IntegrityError:
            AuditLog.objects.create(
                user=request.user,
                action="FAILED_CREATE",
                affected_table=Appointment.__name__,
                affected_record_id=0,
                description=(
                    f"Failed to create new Appointment for {request.user.username}: "
                    f"Conflicting appointment for {date} at {time}."
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

            messages.error(request, "This time slot is already booked, please use another time.")

    return render(request, 'core/appointment_scheduling.html', {
        "patient": patient,
        "providers": providers,
    })

@login_required
def medical_records(request):
    user = request.user

    if user.role == User.Role.PATIENT:
        patient = Patient.objects.get(user=user)
        records = MedicalRecord.objects.filter(
            patient=patient
        ).order_by("-date_created")
    elif user.role == User.Role.CLINICAL:
        clinical = ClinicalStaff.objects.get(user=user)
        records = MedicalRecord.objects.filter(
            clinical_staff=clinical
        ).order_by("-date_created")
    else:
        return redirect("emr_login")

    return render(request, 'core/medical_records.html', {
        "records": records,
        "can_edit": user.role == User.Role.CLINICAL,
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.CLINICAL, login_url='emr_login')
def clinical_dashboard(request):
    staff = ClinicalStaff.objects.get(user=request.user)

    appointments = Appointment.objects.filter(
        clinical_staff=staff,
        status=Appointment.Status.PENDING
    ).order_by("-date", "-time")

    notifications = Notification.objects.filter(
        user=request.user
    )

    return render(request, 'core/clinical_dashboard.html', {
        "appointments": appointments,
        "notifications": notifications
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN, login_url='emr_login')
def admin_dashboard(request):
    users = User.objects.all()
    logs = AuditLog.objects.order_by("-timestamp")
    notifications = Notification.objects.filter(
        user=request.user,
    ).order_by("-date_sent")

    return render(request, 'core/admin_dashboard.html', {
        "users": users,
        "logs": logs,
        "notifications": notifications
    })

# Action views

def logout_view(request):
    user = request.user
    ip = request.META.get("REMOTE_ADDR")

    logout(request)

    AuditLog.objects.create(
        user=user,
        action="LOGOUT",
        affected_table=User.__name__,
        affected_record_id=user.id,
        description=(
            f"User logged out: {user.username}"
        ),
        ip_address=ip
    )

    return redirect("emr_login")

@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN, login_url='emr_login')
def create_clinical_staff(request):
    if request.method != "POST":
        return redirect("admin_dashboard")

    username = request.POST.get("username")
    password = request.POST.get("password")
    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")

    license_number = request.POST.get("license_number")
    specialization = request.POST.get("specialization")
    hire_date = request.POST.get("hire_date")
    try:
        hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date")
        return redirect("admin_dashboard")

    required = [username, password, name, email, phone, license_number, specialization, hire_date]
    if any(not f for f in required):
        messages.error(request, "Missing required information.")
        return redirect("admin_dashboard")

    if User.objects.filter(username=username).exists():
        messages.error(request, "Username already exists.")
        return redirect("admin_dashboard")

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
            )

            user.name = name
            user.phone = phone
            user.role = User.Role.CLINICAL
            user.save()

            clinical = ClinicalStaff.objects.create(
                user=user,
                license_number=license_number,
                specialization=specialization,
                hire_date=hire_date,
            )

            AuditLog.objects.create(
                user=request.user,
                action="CREATE",
                affected_table=ClinicalStaff.__name__,
                affected_record_id=clinical.id,
                description=(
                    f"Created ClinicalStaff for new User {username} "
                    f"(User ID: {user.id})"
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

        messages.success(request, "Clinical staff created successfully.")
        return redirect("admin_dashboard")
    except Exception as e:
        AuditLog.objects.create(
            user=request.user,
            action="FAILED_CREATE",
            affected_table=ClinicalStaff.__name__,
            affected_record_id=0,
            description=(
                f"Failed to create new ClinicalStaff due to server error "
            ),
            ip_address=request.META.get("REMOTE_ADDR")
        )

        messages.error(request, f"Error creating staff: {str(e)}")
        return redirect("admin_dashboard")

@login_required
@user_passes_test(lambda u: u.role == User.Role.CLINICAL, login_url='emr_login')
def create_clinical_record(request, appointment_id):
    try:
        appointment = Appointment.objects.select_related(
            "patient", "clinical_staff"
        ).get(id=appointment_id)
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found.")
        return redirect("clinical_dashboard")

    if appointment.clinical_staff.user != request.user:
        messages.error(request, "Unauthorized clinical staff.")
        return redirect("clinical_dashboard")

    if request.method == "POST":
        visit_summary = request.POST.get("visit_summary")
        diagnosis = request.POST.get("diagnosis")
        clinical_notes = request.POST.get("clinical_notes")
        treatment_plan = request.POST.get("treatment_plan")

        # optional prescription fields
        medication_name = request.POST.get("medication_name")
        dosage = request.POST.get("dosage")
        frequency = request.POST.get("frequency")
        start_date = request.POST.get("start_date")
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date")
                return redirect("clinical_dashboard")
        end_date = request.POST.get("end_date")
        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date")
                return redirect("clinical_dashboard")

        # optional test fields
        test_name = request.POST.get("test_name")
        test_date = request.POST.get("test_date")
        if test_date:
            try:
                test_date = datetime.strptime(test_date, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date")
                return redirect("clinical_dashboard")

        try:
            with transaction.atomic():
                record = MedicalRecord.objects.create(
                    patient=appointment.patient,
                    clinical_staff=appointment.clinical_staff,
                    visit_summary=visit_summary,
                    diagnosis=diagnosis,
                    clinical_notes=clinical_notes,
                    treatment_plan=treatment_plan,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action="CREATE",
                    affected_table=MedicalRecord.__name__,
                    affected_record_id=record.id,
                    description=(
                            f"Created medical record for {record.patient.user.username} "
                            f"(Appointment ID: {appointment.id})"
                        ),
                    ip_address=request.META.get("REMOTE_ADDR")
                )

                if medication_name:
                    prescription = Prescription.objects.create(
                        medical_record=record,
                        medication_name=medication_name,
                        dosage=dosage,
                        frequency=frequency,
                        start_date=start_date,
                        end_date=end_date,
                        status=Prescription.Status.ACTIVE,
                    )

                    AuditLog.objects.create(
                        user=request.user,
                        action="CREATE",
                        affected_table=Prescription.__name__,
                        affected_record_id=prescription.id,
                        description=(
                            f"Created prescription for {record.patient.user.username} "
                            f"(Record ID: {record.id})"
                        ),
                        ip_address=request.META.get("REMOTE_ADDR")
                    )

                if test_name:
                    test_result = TestResult.objects.create(
                        medical_record=record,
                        ordered_by=appointment.clinical_staff,
                        test_name=test_name,
                        test_date=test_date,
                        status=TestResult.Status.PENDING,
                    )

                    AuditLog.objects.create(
                        user=request.user,
                        action="CREATE",
                        affected_table=TestResult.__name__,
                        affected_record_id=test_result.id,
                        description=(
                            f"Created test result for {record.patient.user.username} "
                            f"(Record ID: {record.id})"
                        ),
                        ip_address=request.META.get("REMOTE_ADDR")
                    )

                appointment.status = Appointment.Status.COMPLETED
                appointment.save()

                AuditLog.objects.create(
                    user=request.user,
                    action="UPDATE",
                    affected_table=Appointment.__name__,
                    affected_record_id=appointment.id,
                    description=(
                        f"Marked appointment as COMPLETED for {record.patient.user.username} "
                    ),
                    ip_address=request.META.get("REMOTE_ADDR")
                )

                Notification.objects.create(
                    user=appointment.patient.user,
                    message="Appointment has been completed, your clinical record has been updated.",
                    type="MEDICAL_RECORD",
                )

            messages.success(request, "Record saved successfully.")
            return redirect("clinical_dashboard")

        except Exception as e:
            AuditLog.objects.create(
                user=request.user,
                action="FAILED_CREATE",
                affected_table=MedicalRecord.__name__,
                affected_record_id=0,
                description=(
                    f"Failed to create new medical record "
                    f"for {appointment.patient.user.username} due to server error"
                ),
                ip_address=request.META.get("REMOTE_ADDR")
            )

            messages.error(request, f"Error creating record: {str(e)}")

    return render(request, "create_record.html", {
        "appointment": appointment
    })