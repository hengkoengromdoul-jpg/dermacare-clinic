import mysql.connector
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dermacare_secure_key"


#  DB CONNECTION 
def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Romdoul",
        database="dermacare"
    )


def log_action(user_id, action_type, description=""):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO activity_log (user_id, action_type, description) VALUES (%s, %s, %s)",
            (user_id, action_type, description)
        )
        db.commit()
        cursor.close()
        db.close()
    except:
        pass


# HOME 
@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.schedule_id, d.name AS doctor_name, d.specialization,
               s.available_date, s.start_time, s.end_time
        FROM schedule s
        JOIN doctor d ON s.doctor_id = d.doctor_id
        WHERE s.status = 'available'
        ORDER BY s.available_date ASC
        LIMIT 6
    """)
    schedules = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("index.html", schedules=schedules)


# REGISTER 
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name")
        email    = request.form.get("email", "").strip()
        password = request.form.get("password")
        phone    = request.form.get("phone")
        national = request.form.get("national") or "N/A"
        gender   = request.form.get("gender")
        form_role = request.form.get("role", "patient")
        role     = form_role.lower().strip()
        profile_selection = request.form.get("profile") or f"new {role} registration account"

        hashed_password = generate_password_hash(password)
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO user (user_name, password, email, role, status, profile, national)
                VALUES (%s, %s, %s, %s, 'active', %s, %s)
            """, (name, hashed_password, email, role, profile_selection, national))
            user_id = cursor.lastrowid

            if role == "patient":
                cursor.execute("""
                    INSERT INTO patient (user_id, name, gender, phone, email, national, profile)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, name, gender, phone, email, national, profile_selection))
            elif role == "doctor":
                cursor.execute("""
                    INSERT INTO doctor (user_id, name, gender, phone, email, profile, national, specialization)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Dermatology')
                """, (user_id, name, gender, phone, email, profile_selection, national))
            elif role == "pharmacist":
                cursor.execute("""
                    INSERT INTO pharmacist (user_id, name, gender, phone, email, profile, national)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, name, gender, phone, email, profile_selection, national))
            elif role == "admin":
                cursor.execute("""
                    INSERT INTO admin (user_id, name, email, phone)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, name, email, phone))

            db.commit()
            log_action(user_id, "REGISTER", f"{role} account created")
            session["user_id"] = user_id
            session["role"]    = role
            session["name"]    = name
            session["email"]   = email
            flash("Account created successfully!", "success")

            if role == "patient":
                return redirect(url_for("patient_dashboard"))
            elif role == "doctor":
                return redirect(url_for("doctor_dashboard"))
            elif role == "pharmacist":
                return redirect(url_for("pharmacist_dashboard"))
            elif role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("home"))
        except Exception as e:
            db.rollback()
            print(f"REGISTER ERROR: {e}")
            flash("Registration failed. Email might already exist.")
            return render_template("register.html")
        finally:
            cursor.close()
            db.close()
    return render_template("register.html")


# LOGIN 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        session.clear()

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password")
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user["password"], password):
            db_role = user["role"].lower().strip()
            session["user_id"] = user["user_id"]
            session["role"]    = db_role
            session["name"]    = user["user_name"]
            session["email"]   = user["email"]
            log_action(user["user_id"], "LOGIN", f"{db_role} logged in")
            if db_role == "patient":
                return redirect(url_for("patient_dashboard"))
            elif db_role == "doctor":
                return redirect(url_for("doctor_dashboard"))
            elif db_role == "pharmacist":
                return redirect(url_for("pharmacist_dashboard"))
            elif db_role == "admin":
                return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid email or password.")
    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    uid = session.get("user_id")
    if uid:
        log_action(uid, "LOGOUT", "User logged out")
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("home"))


#TEAM PAGE
@app.route("/team")
def team():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM doctor ORDER BY doctor_id")
    doctors = cursor.fetchall()
    cursor.execute("SELECT * FROM pharmacist ORDER BY pharmacist_id")
    pharmacists = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("team.html", doctors=doctors, pharmacists=pharmacists)


# PATIENT ROUTES
@app.route("/patient_dashboard")
def patient_dashboard():
    if "user_id" not in session or session.get("role") != "patient":
        flash("Please log in to access your dashboard.")
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # available schedules
    cursor.execute("""
        SELECT s.schedule_id, s.doctor_id, d.name AS doctor_name,
               d.specialization, s.available_date, s.start_time, s.end_time
        FROM schedule s
        JOIN doctor d ON s.doctor_id = d.doctor_id
        WHERE s.status = 'available'
        ORDER BY s.available_date ASC
    """)
    schedules = cursor.fetchall()

    # patient's own appointments + prescriptions
    cursor.execute("SELECT patient_id FROM patient WHERE user_id = %s", (session["user_id"],))
    pat = cursor.fetchone()
    booked_appointments = []
    prescriptions = []

    if pat:
        pid = pat["patient_id"]
        cursor.execute("""
            SELECT a.appointment_id, a.appointment_date_time, a.status,
                   a.booking_fee, d.name AS doctor_name, d.specialization,
                   i.invoice_id,
                   pay.status AS payment_status, pay.payment_method
            FROM appointment a
            JOIN doctor d ON a.doctor_id = d.doctor_id
            LEFT JOIN invoice i ON i.appointment_id = a.appointment_id
            LEFT JOIN payment pay ON pay.invoice_id = i.invoice_id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_date_time DESC
        """, (pid,))
        booked_appointments = cursor.fetchall()

        cursor.execute("""
            SELECT pr.prescription_id, pr.prescription_date_time,
                   d.name AS doctor_name,
                   m.medicine_name, m.medicine_type, m.price,
                   pm.quantity, pm.instruction, pm.purchase_status
            FROM prescription pr
            JOIN doctor d ON pr.doctor_id = d.doctor_id
            JOIN prescription_medicine pm ON pm.prescription_id = pr.prescription_id
            JOIN medicine m ON m.medicine_id = pm.medicine_id
            WHERE pr.patient_id = %s
            ORDER BY pr.prescription_date_time DESC
        """, (pid,))
        prescriptions = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("patient_dashboard.html",
                           schedules=schedules,
                           appointments=booked_appointments,
                           prescriptions=prescriptions)


@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    if "user_id" not in session or session.get("role") != "patient":
        flash("Please log in as a patient first.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    schedule_id = request.form.get("schedule_id")
    doctor_id = request.form.get("doctor_id")

    # patient details
    name = request.form.get("name") or session.get("name") or "Unnamed Patient"
    gender = request.form.get("gender")
    phone = request.form.get("phone")
    email = request.form.get("email") or session.get("email") or ""
    national = request.form.get("national") or "N/A"
    date_of_birth = request.form.get("date_of_birth")
    profile = request.form.get("profile") or "Skin care patient"
    emergency_contact = request.form.get("emergency_phone")
    medical_history = request.form.get("medical_history") or ""

    # combine address
    street = request.form.get("addr_street") or ""
    city = request.form.get("addr_city") or ""
    province = request.form.get("addr_province") or ""
    combined_address = f"{street}, {city}, {province}".strip(", ")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # 1. find slot
        cursor.execute(
            "SELECT available_date, start_time FROM schedule WHERE schedule_id = %s",
            (schedule_id,)
        )
        slot = cursor.fetchone()
        if not slot:
            flash("That schedule slot is no longer available.")
            return redirect(url_for("patient_dashboard"))

        appt_dt = f"{slot['available_date']} {slot['start_time']}"

        # 2. upsert patient record
        cursor.execute("SELECT patient_id FROM patient WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()

        if existing:
            patient_id = existing["patient_id"]
            cursor.execute("""
                UPDATE patient
                SET name=%s, gender=%s, phone=%s, email=%s, profile=%s,
                    national=%s, date_of_birth=%s, address=%s,
                    emergency_contact=%s, medical_history=%s
                WHERE patient_id=%s
            """, (name, gender, phone, email, profile, national,
                  date_of_birth, combined_address, emergency_contact,
                  medical_history, patient_id))
        else:
            cursor.execute("""
                INSERT INTO patient (user_id, name, gender, phone, email, profile,
                                     national, date_of_birth, address,
                                     emergency_contact, medical_history)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (user_id, name, gender, phone, email, profile, national,
                  date_of_birth, combined_address, emergency_contact, medical_history))
            patient_id = cursor.lastrowid

        # 3. mark slot as booked
        cursor.execute(
            "UPDATE schedule SET status='booked' WHERE schedule_id=%s",
            (schedule_id,)
        )

        # 4. create appointment
        cursor.execute("""
            INSERT INTO appointment
                (doctor_id, patient_id, schedule_id, appointment_date_time,
                 status, booking_fee, booking_type)
            VALUES (%s, %s, %s, %s, 'confirmed', 18.00, 'online')
        """, (doctor_id, patient_id, schedule_id, appt_dt))
        appointment_id = cursor.lastrowid

        # 5. auto-create invoice + pending payment
        cursor.execute("""
            INSERT INTO invoice (appointment_id, invoice_type, total_amount)
            VALUES (%s, 'consultation', 18.00)
        """, (appointment_id,))
        invoice_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO payment (invoice_id, payment_method, amount, status)
            VALUES (%s, 'cash', 18.00, 'pending')
        """, (invoice_id,))

        db.commit()
        log_action(user_id, "BOOK_APPOINTMENT", f"Booked appointment #{appointment_id}")
        flash("Booking confirmed! Please pay $18 at the clinic on your visit.", "success")

    except Exception as e:
        db.rollback()
        print(f"\n CRITICAL BOOKING ERROR: {e}\n")
        flash(f"Could not complete booking: {e}")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("patient_dashboard"))


# VIEW INVOICE (read-only — patient pays at clinic)
@app.route("/view_invoice/<int:invoice_id>")
def view_invoice(invoice_id):
    if "user_id" not in session or session.get("role") != "patient":
        flash("Please log in as a patient.")
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.invoice_id, i.invoice_type, i.total_amount, i.invoice_date_time,
               a.appointment_date_time,
               d.name AS doctor_name,
               pay.status AS payment_status
        FROM invoice i
        JOIN appointment a ON i.appointment_id = a.appointment_id
        JOIN doctor d ON a.doctor_id = d.doctor_id
        LEFT JOIN payment pay ON pay.invoice_id = i.invoice_id
        WHERE i.invoice_id = %s
    """, (invoice_id,))
    invoice = cursor.fetchone()

    cursor.close()
    db.close()

    if not invoice:
        flash("Invoice not found.")
        return redirect(url_for("patient_dashboard"))

    return render_template("invoice.html", invoice=invoice)


# DOCTOR ROUTES
@app.route("/doctor_dashboard")
def doctor_dashboard():
    if "user_id" not in session or session.get("role") != "doctor":
        flash("Doctor access only.")
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT doctor_id, name, specialization, experience_year FROM doctor WHERE user_id=%s",
                   (session["user_id"],))
    doctor = cursor.fetchone()
    if not doctor:
        flash("Doctor profile not found.")
        return redirect(url_for("logout"))

    did = doctor["doctor_id"]

    # doctor's schedules
    cursor.execute("""
        SELECT * FROM schedule
        WHERE doctor_id = %s
        ORDER BY available_date DESC, start_time
    """, (did,))
    schedules = cursor.fetchall()

    # doctor's bookings (with payment status)
    cursor.execute("""
        SELECT a.appointment_id, a.appointment_date_time, a.status, a.booking_fee,
               a.booking_type,
               p.name AS patient_name, p.phone, p.gender, p.medical_history,
               p.patient_id,
               pay.status AS payment_status,
               (SELECT COUNT(*) FROM prescription pr WHERE pr.appointment_id=a.appointment_id) AS has_prescription
        FROM appointment a
        JOIN patient p ON a.patient_id = p.patient_id
        LEFT JOIN invoice i ON i.appointment_id = a.appointment_id
        LEFT JOIN payment pay ON pay.invoice_id = i.invoice_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date_time DESC
    """, (did,))
    bookings = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("doctor_dashboard.html",
                           doctor=doctor,
                           schedules=schedules,
                           bookings=bookings)


@app.route("/add_schedule", methods=["POST"])
def add_schedule():
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT doctor_id FROM doctor WHERE user_id=%s", (session["user_id"],))
    doc = cursor.fetchone()

    if doc:
        date       = request.form.get("available_date")
        start_time = request.form.get("start_time")
        end_time   = request.form.get("end_time")
        try:
            cursor.execute("""
                INSERT INTO schedule (doctor_id, available_date, start_time, end_time, status)
                VALUES (%s, %s, %s, %s, 'available')
            """, (doc["doctor_id"], date, start_time, end_time))
            db.commit()
            log_action(session["user_id"], "ADD_SCHEDULE", f"Added schedule on {date}")
            flash("New schedule slot published successfully!", "success")
        except Exception as e:
            db.rollback()
            print(f"\nADD SCHEDULE ERROR: {str(e)}\n")
            flash("Failed to add schedule slot.")
        finally:
            cursor.close()
            db.close()
    else:
        cursor.close()
        db.close()
    return redirect(url_for("doctor_dashboard"))


@app.route("/delete_schedule/<int:schedule_id>")
def delete_schedule(schedule_id):
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "DELETE FROM schedule WHERE schedule_id=%s AND status='available'",
            (schedule_id,)
        )
        db.commit()
        log_action(session["user_id"], "DELETE_SCHEDULE", f"Deleted schedule #{schedule_id}")
        flash("Schedule slot removed.", "success")
    except Exception as e:
        db.rollback()
        print(f"DELETE SCHEDULE ERROR: {e}")
        flash("Could not delete this slot.")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("doctor_dashboard"))


@app.route("/complete_appointment/<int:appointment_id>", methods=["POST"])
def complete_appointment(appointment_id):
    """Doctor completes consultation AND writes prescription in one step."""
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    diagnosis = request.form.get("diagnosis")
    notes = request.form.get("notes")
    med_names = request.form.getlist("med_name[]")
    med_dosages = request.form.getlist("med_dosage[]")
    med_qtys = request.form.getlist("med_qty[]")
    med_instr = request.form.getlist("med_instr[]")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # get doctor + patient IDs from the appointment
        cursor.execute(
            "SELECT doctor_id, patient_id FROM appointment WHERE appointment_id=%s",
            (appointment_id,)
        )
        appt = cursor.fetchone()
        if not appt:
            flash("Appointment not found.")
            return redirect(url_for("doctor_dashboard"))

        # mark appointment as completed
        cursor.execute(
            "UPDATE appointment SET status='completed' WHERE appointment_id=%s",
            (appointment_id,)
        )

        # create the prescription
        cursor.execute("""
            INSERT INTO prescription
                (appointment_id, doctor_id, patient_id, diagnosis, notes, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (appointment_id, appt["doctor_id"], appt["patient_id"], diagnosis, notes))
        prescription_id = cursor.lastrowid

        # attach each medicine
        for name, dose, qty, ins in zip(med_names, med_dosages, med_qtys, med_instr):
            if name and name.strip():
                try:
                    qty_int = int(qty) if qty else 1
                except ValueError:
                    qty_int = 1

                # find existing medicine OR create new one in inventory
                cursor.execute(
                    "SELECT medicine_id FROM medicine WHERE medicine_name=%s LIMIT 1",
                    (name.strip(),)
                )
                med = cursor.fetchone()
                if med:
                    medicine_id = med["medicine_id"]
                else:
                    cursor.execute("""
                        INSERT INTO medicine (medicine_name, medicine_type, price, stock_quantity)
                        VALUES (%s, 'topical', 0.00, 0)
                    """, (name.strip(),))
                    medicine_id = cursor.lastrowid

                # link medicine to prescription
                cursor.execute("""
                    INSERT INTO prescription_medicine
                        (prescription_id, medicine_id, quantity, instruction, purchase_status)
                    VALUES (%s, %s, %s, %s, 'not_bought')
                """, (prescription_id, medicine_id, qty_int, ins))

        db.commit()
        log_action(session["user_id"], "COMPLETE_APPOINTMENT",
                   f"Completed appointment #{appointment_id} + wrote prescription")
        flash("Consultation completed and prescription saved!", "success")

    except Exception as e:
        db.rollback()
        print(f"COMPLETE APPOINTMENT ERROR: {e}")
        flash(f"Error saving prescription: {e}")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("doctor_dashboard"))


# PHARMACIST ROUTES
@app.route("/pharmacist_dashboard")
def pharmacist_dashboard():
    if "user_id" not in session or session.get("role") != "pharmacist":
        flash("Pharmacist access only.")
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # all prescriptions (pending + dispensed)
    cursor.execute("""
        SELECT pr.prescription_id, pr.diagnosis, pr.notes, pr.status,
               pr.prescription_date_time, pr.dispensed_at,
               d.name AS doctor_name,
               p.name AS patient_name, p.phone
        FROM prescription pr
        JOIN doctor d  ON pr.doctor_id  = d.doctor_id
        JOIN patient p ON pr.patient_id = p.patient_id
        ORDER BY pr.prescription_date_time DESC
    """)
    prescriptions = cursor.fetchall()

    # attach medicines to each prescription
    for pr in prescriptions:
        cursor.execute("""
            SELECT pm.prescription_medicine_id, pm.quantity, pm.instruction, pm.purchase_status,
                   m.medicine_name, m.medicine_type, m.price
            FROM prescription_medicine pm
            JOIN medicine m ON pm.medicine_id = m.medicine_id
            WHERE pm.prescription_id = %s
        """, (pr["prescription_id"],))
        pr["medicines"] = cursor.fetchall()

    # medicine inventory
    cursor.execute("SELECT * FROM medicine ORDER BY medicine_name")
    medicines = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("pharmacist_dashboard.html",
                           prescriptions=prescriptions,
                           medicines=medicines)


@app.route("/dispense/<int:prescription_id>", methods=["POST"])
def dispense(prescription_id):
    """Mark a whole prescription as dispensed."""
    if "user_id" not in session or session.get("role") != "pharmacist":
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT pharmacist_id FROM pharmacist WHERE user_id=%s", (session["user_id"],))
        ph = cursor.fetchone()
        pharmacist_id = ph["pharmacist_id"] if ph else None

        # update prescription status
        cursor.execute("""
            UPDATE prescription
            SET status='dispensed', pharmacist_id=%s, dispensed_at=NOW()
            WHERE prescription_id=%s
        """, (pharmacist_id, prescription_id))

        # mark all the medicines in this prescription as bought
        cursor.execute("""
            UPDATE prescription_medicine
            SET purchase_status='bought'
            WHERE prescription_id=%s
        """, (prescription_id,))

        db.commit()
        log_action(session["user_id"], "DISPENSE", f"Dispensed prescription #{prescription_id}")
        flash("Prescription marked as dispensed.", "success")
    except Exception as e:
        db.rollback()
        print(f"DISPENSE ERROR: {e}")
        flash("Could not dispense.")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("pharmacist_dashboard"))


@app.route("/add_medicine", methods=["POST"])
def add_medicine():
    if "user_id" not in session or session.get("role") != "pharmacist":
        return redirect(url_for("login"))
    name  = request.form.get("medicine_name")
    mtype = request.form.get("medicine_type")
    price = request.form.get("price")
    stock = request.form.get("stock")
    expiry_date = request.form.get("expiry_date")
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO medicine (medicine_name, medicine_type, price, stock_quantity, expiry_date)
            VALUES (%s,%s,%s,%s,%s)
        """, (name, mtype, price, stock, expiry_date))
        db.commit()
        log_action(session["user_id"], "ADD_MEDICINE", f"Added {name}")
        flash("Medicine added successfully!", "success")
    except Exception as e:
        db.rollback()
        print(f"ADD MEDICINE ERROR: {e}")
        flash("Failed to add medicine.")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("pharmacist_dashboard"))

# ADMIN ROUTES
@app.route("/admin_dashboard")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        flash("Admin access only.")
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # KPI counts
    cursor.execute("SELECT COUNT(*) AS cnt FROM user WHERE role='patient'")
    patient_count = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) AS cnt FROM user WHERE role='doctor'")
    doctor_count = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) AS cnt FROM appointment")
    appt_count = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM payment WHERE status='paid'")
    total_revenue = float(cursor.fetchone()["total"])

    cursor.execute("SELECT * FROM user ORDER BY create_time DESC")
    users = cursor.fetchall()

    cursor.execute("""
        SELECT a.appointment_id, a.appointment_date_time, a.status, a.booking_fee,
               p.name AS patient_name, d.name AS doctor_name,
               pay.status AS payment_status
        FROM appointment a
        JOIN patient p ON a.patient_id=p.patient_id
        JOIN doctor d ON a.doctor_id=d.doctor_id
        LEFT JOIN invoice i ON i.appointment_id = a.appointment_id
        LEFT JOIN payment pay ON pay.invoice_id = i.invoice_id
        ORDER BY a.appointment_date_time DESC
        LIMIT 20
    """)
    appointments = cursor.fetchall()

    cursor.execute("""
        SELECT py.payment_id, py.amount, py.payment_method, py.status,
               py.payment_date_time,
               p.name AS patient_name, d.name AS doctor_name
        FROM payment py
        JOIN invoice i ON py.invoice_id=i.invoice_id
        JOIN appointment a ON i.appointment_id=a.appointment_id
        JOIN patient p ON a.patient_id=p.patient_id
        JOIN doctor d ON a.doctor_id=d.doctor_id
        ORDER BY py.payment_date_time DESC
        LIMIT 20
    """)
    payments = cursor.fetchall()

    cursor.execute("SELECT * FROM activity_log ORDER BY action_time DESC LIMIT 30")
    logs = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("admin_dashboard.html",
                           patient_count=patient_count,
                           doctor_count=doctor_count,
                           appt_count=appt_count,
                           total_revenue=total_revenue,
                           stats={
                               "users": patient_count + doctor_count,
                               "doctors": doctor_count,
                               "patients": patient_count,
                               "appointments": appt_count,
                               "revenue": total_revenue,
                           },
                           users=users,
                           appointments=appointments,
                           payments=payments,
                           logs=logs)


@app.route("/admin/toggle_user/<int:user_id>")
def admin_toggle_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT status FROM user WHERE user_id=%s", (user_id,))
    u = cursor.fetchone()
    if u:
        new_status = "inactive" if u["status"] == "active" else "active"
        cursor.execute("UPDATE user SET status=%s WHERE user_id=%s", (new_status, user_id))
        db.commit()
        flash(f"User status set to {new_status}.", "success")
    cursor.close()
    db.close()
    return redirect(url_for("admin_dashboard"))

# =============================================================
# ADMIN — CREATE STAFF (doctor / pharmacist)
# Paste this into app.py, just below the admin_toggle_user route
# =============================================================

@app.route("/admin/create_staff", methods=["GET", "POST"])
def admin_create_staff():
    if "user_id" not in session or session.get("role") != "admin":
        flash("Admin access only.")
        return redirect(url_for("login"))

    if request.method == "POST":
        role = request.form.get("role")  # 'doctor' or 'pharmacist'
        name = request.form.get("name")
        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        phone = request.form.get("phone")
        gender = request.form.get("gender")
        national = request.form.get("national") or "Cambodian"
        profile = request.form.get("profile") or ""
        specialization = request.form.get("specialization") or "Dermatology"

        if role not in ("doctor", "pharmacist"):
            flash("Invalid role.")
            return redirect(url_for("admin_create_staff"))

        hashed_password = generate_password_hash(password)
        db = get_db()
        cursor = db.cursor()

        try:
            # 1. create user row
            cursor.execute("""
                INSERT INTO user (user_name, password, email, role, status, profile, national)
                VALUES (%s, %s, %s, %s, 'active', %s, %s)
            """, (name, hashed_password, email, role, profile, national))
            user_id = cursor.lastrowid

            # 2. create role-specific row
            if role == "doctor":
                cursor.execute("""
                    INSERT INTO doctor (user_id, name, gender, phone, email, profile, national, specialization)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, name, gender, phone, email, profile, national, specialization))
            else:  # pharmacist
                cursor.execute("""
                    INSERT INTO pharmacist (user_id, name, gender, phone, email, profile, national)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, name, gender, phone, email, profile, national))

            db.commit()
            log_action(session["user_id"], "CREATE_STAFF", f"Admin created {role} account: {name}")
            flash(f"{role.capitalize()} account created successfully! They can now log in with their email and password.", "success")

        except Exception as e:
            db.rollback()
            print(f"CREATE STAFF ERROR: {e}")
            flash("Could not create account. Email might already exist.")
        finally:
            cursor.close()
            db.close()

        return redirect(url_for("admin_create_staff"))

    return render_template("admin_create_staff.html")

if __name__ == "__main__":
    app.run(debug=True)