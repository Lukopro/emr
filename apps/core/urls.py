from django.urls import path
from . import views

urlpatterns = [
    path('', views.emr_login, name='emr_login'),
    path('patient_dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('clinical_dashboard/', views.clinical_dashboard, name='clinical_dashboard'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('create_clinical_staff/', views.create_clinical_staff, name='create_clinical_staff'),
    path('medical_records/', views.medical_records, name='medical_records'),
    path('appointment_scheduling/', views.appointment_scheduling, name='appointment_scheduling'),
    path('patient_profile/', views.patient_profile, name='patient_profile'),
    path('patient_registration/', views.patient_registration, name='patient_registration'),

    #update URLs change/edit as you like
    path('patient_profile/<int:patient_id>/update_contact/', views.update_contact, name='update_contact'),
    path('medical_records/update_record/', views.patient_registration, name='update_record'),

    path('logout/', views.logout_view, name='logout'),
]
