import os
import subprocess
import sys
import getpass

IS_WINDOWS = os.name == "nt"

def run(cmd):
    print(f"\n>>> {cmd}")
    subprocess.check_call(cmd, shell=True)

def main(DB_NAME, DB_USER):
    if not os.path.exists("venv"):
        run("python -m venv venv")

    python = os.path.join("venv", "Scripts" if IS_WINDOWS else "bin", "python")

    run(f"{python} -m pip install --upgrade pip")
    run(f"{python} -m pip install django mysqlclient mysql-connector-python python-dotenv")

    import mysql.connector

    DB_PASSWORD = getpass.getpass(prompt="MySQL password: ")

    with open(".env", "w") as f:
        f.write(f"DB_NAME={DB_NAME}\n")
        f.write(f"DB_USER={DB_USER}\n")
        f.write(f"DB_PASSWORD={DB_PASSWORD}\n")

    conn = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
    )

    sql = f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)

    run(f"{python} manage.py makemigrations")
    run(f"{python} manage.py migrate")

    print("\nCreating superuser (follow prompts)")
    run(f"{python} manage.py createsuperuser")

    print("\n Setup complete, run the server with: ")
    print(f"{python} manage.py runserver")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python setup.py DB_NAME DB_USER")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])