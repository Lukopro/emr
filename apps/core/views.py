from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import get_user_model
User = get_user_model()
from datetime import datetime
from django.contrib import messages
from django.db import transaction
from core.models import *

# Page views

def emr_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            #RBAC routing
            if user.role == User.Role.ADMIN:
                return redirect("admin_dashboard")
            elif user.role == User.Role.CLINICAL:
                return redirect("clinical_dashboard")
            else:
                return redirect("patient_dashboard")

        return render(request, 'core/emr_login.html', {
            "error": "Invalid credentials"
        })

    return render(request, 'core/emr_login.html')

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT)
def patient_dashboard(request):
    patient = Patient.objects.get(user=request.user)

    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by("-date", "-time")

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-date_sent")

    return render(request, "core/patient_dashboard.html", {
        "patient": patient,
        "appointments": appointments,
        "notifications": notifications
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT)
def patient_profile(request):
    return render(request, 'core/patient_profile.html')

def patient_registration(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
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
            username, password, email, phone,
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

                user.phone = phone
                user.role = User.Role.PATIENT
                user.save()

                Patient.objects.create(
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
        except Exception as e:
            return render(request, 'core/patient_registration.html', {
                "error": f"Registration failed: {e}"
            })

        return redirect("emr_login")

    return render(request, 'core/patient_registration.html')

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT)
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
            redirect("appointment_scheduling")

        time = request.POST.get('time')
        try:
            time = datetime.strptime(time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time")
            redirect("appointment_scheduling")

        location = request.POST.get('location')
        visit_type = request.POST.get('visit_type')

        if not provider_id or not date or not time:
            messages.error(request, "Missing appointment details.")
            return redirect("appointment_scheduling")

        try:
            provider = ClinicalStaff.objects.get(user_id=provider_id)

            Appointment.objects.create(
                patient=patient,
                clinical_staff=provider,
                date=date,
                time=time,
                location=location,
                visit_type=visit_type,
                status=Appointment.Status.PENDING
            )

            messages.success(request, "Appointment requested successfully.")
            return redirect("patient_dashboard")

        except ClinicalStaff.DoesNotExist:
            messages.error(request, "No clinical staff found.")

    return render(request, 'core/appointment_scheduling.html', {
        "providers": providers,
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.PATIENT)
def medical_records(request):
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        return redirect("emr_login")

    records = MedicalRecord.objects.filter(
        patient=patient
    ).order_by("-date_created")

    return render(request, 'core/medical_records.html', {
        "records": records,
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.CLINICAL)
def clinical_dashboard(request):
    staff = ClinicalStaff.objects.get(user=request.user)

    appointments = Appointment.objects.filter(
        clinical_staff=staff,
        status=Appointment.Status.PENDING
    ).order_by("-date", "-time")

    return render(request, 'core/clinical_dashboard.html', {
        "appointments": appointments,
    })

@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN)
def admin_dashboard(request):
    users = User.objects.all()
    logs = AuditLog.objects.order_by("-timestamp")

    return render(request, 'core/admin_dashboard.html', {
        "users": users,
        "logs": logs,
    })

# Action views

def logout_view(request):
    logout(request)
    return redirect("emr_login")

@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN)
def create_clinical_staff(request):
    if request.method != "POST":
        return redirect("admin_dashboard")

    username = request.POST.get("username")
    password = request.POST.get("password")
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

    required = [username, password, email, phone, license_number, speciality, hire_date]
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

            user.phone = phone
            user.role = User.Role.CLINICAL
            user.save()

            ClinicalStaff.objects.create(
                user=user,
                license_number=license_number,
                specialization=specialization,
                hire_date=hire_date,
            )

        messages.success(request, "Clinical staff created successfully.")
        return redirect("admin_dashboard")
    except Exception as e:
        messages.error(request, f"Error creating staff: {str(e)}")
        return redirect("admin_dashboard")
