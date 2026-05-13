Django-based EMR system for a school project. Intended to run on Windows 11. To get set up:

1. Install Python
 - https://www.python.org/downloads/windows/
2. Install MySQL
 - https://dev.mysql.com/downloads/installer/
 - take note of your root password during installation
3. Clone or download the project
4. Run the setup script
 - python setup.py emr_db root
 - Follow prompts as necessary
5. From the created python virtual environment, run the server
 - if there is no (venv) on your terminal, activate the venv: venv\Scripts\activate
 - python manage.py runserver
6. Open application in browser
 - http://127.0.0.1:8000/
 - Ensure your browser allows for http connections

TODO:
- Appointment confirmation and management
- Clinicians viewing/updating medical records
- Provider availability viewing
- Finish notifications and audit logging
- Test result + prescription lifecycle?