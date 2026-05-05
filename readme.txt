// Database creation and testing user
CREATE DATABASE emr_db;

// For settings.py
import os
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}

Still need:
- Appointment confirmation and management
- Clinicians viewing/updating medical records
- Provider availability viewing
- Finish notifications and audit logging
- Patient profile editing?
- Test result + prescription lifecycle?

User.objects.create_user(username="admin", password="123", role=User.Role.ADMIN, name="System Admin", email="admin@emr.com")

admin_user.is_staff = True
admin_user.is_superuser = False
admin_user.save()