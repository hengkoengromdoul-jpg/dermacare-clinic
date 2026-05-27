
-- DermaCare clinic database
-- this file creates all 13 tables and adds 10 medicines.
--
-- it does NOT create user accounts here because passwords need to be hashed
-- by flask. you'll create users through the website instead:
--   - admin: through the /setup_admin_one_time trick (one time only)
--   - doctors and pharmacists: admin creates them at /admin/create_staff
--   - patients: self-register at /register
--
-- HOW TO RUN:
--   1. open mysql workbench
--   2. open this file
--   3. press the lightning bolt to run everything
--   4. you should see 13 tables created and 10 medicines inserted

drop database if exists dermacare;
create database dermacare;
use dermacare;


-- ─── 1. user 
create table user (
    user_id     int auto_increment primary key,
    user_name   varchar(100) not null,
    password    varchar(255) not null,
    email       varchar(100) unique,
    role        enum('admin','doctor','patient','pharmacist') not null,
    status      enum('active','inactive','pending') default 'active',
    create_time datetime default current_timestamp,
    profile     text,
    national    varchar(50)
);


-- ─── 2. admin
create table admin (
    admin_id int auto_increment primary key,
    user_id  int not null,
    name     varchar(100) not null,
    email    varchar(100),
    phone    varchar(20),
    foreign key (user_id) references user(user_id) on delete cascade
);


-- ─── 3. patient 
create table patient (
    patient_id        int auto_increment primary key,
    user_id           int not null,
    name              varchar(100) not null,
    gender            varchar(20),
    phone             varchar(50),
    email             varchar(100),
    profile           text,
    national          varchar(50),
    date_of_birth     date,
    address           varchar(500),
    emergency_contact varchar(255),
    medical_history   text,
    foreign key (user_id) references user(user_id) on delete cascade
);


-- ─── 4. doctor 
create table doctor (
    doctor_id        int auto_increment primary key,
    user_id          int not null,
    name             varchar(100) not null,
    gender           varchar(10),
    phone            varchar(20),
    email            varchar(100),
    profile          text,
    national         varchar(50),
    specialization   varchar(100) default 'dermatology',
    experience_year  int,
    hired_date       date,
    consultation_fee decimal(10,2) default 18.00,
    foreign key (user_id) references user(user_id) on delete cascade
);


-- ─── 5. pharmacist
create table pharmacist (
    pharmacist_id int auto_increment primary key,
    user_id       int not null,
    name          varchar(100) not null,
    gender        varchar(10),
    phone         varchar(20),
    email         varchar(100),
    profile       text,
    national      varchar(50),
    foreign key (user_id) references user(user_id) on delete cascade
);


-- ─── 6. schedule 
create table schedule (
    schedule_id    int auto_increment primary key,
    doctor_id      int not null,
    available_date date not null,
    start_time     time not null,
    end_time       time not null,
    status         enum('available','booked','cancelled') default 'available',
    foreign key (doctor_id) references doctor(doctor_id) on delete cascade
);


-- ─── 7. appointment 
create table appointment (
    appointment_id        int auto_increment primary key,
    doctor_id             int not null,
    patient_id            int not null,
    schedule_id           int,
    appointment_date_time datetime not null,
    status                enum('pending','confirmed','completed','cancelled','no_show') default 'pending',
    booking_fee           decimal(10,2) default 18.00,
    booking_type          enum('online','walk_in') default 'online',
    notes                 text,
    created_at            datetime default current_timestamp,
    foreign key (doctor_id)   references doctor(doctor_id),
    foreign key (patient_id)  references patient(patient_id),
    foreign key (schedule_id) references schedule(schedule_id)
);


-- ─── 8. medicine
create table medicine (
    medicine_id    int auto_increment primary key,
    medicine_name  varchar(100) not null,
    medicine_type  varchar(50),
    price          decimal(10,2) not null,
    stock_quantity int default 0,
    expiry_date    date
);


-- ─── 9. prescription 
create table prescription (
    prescription_id        int auto_increment primary key,
    patient_id             int not null,
    doctor_id              int not null,
    appointment_id         int not null,
    pharmacist_id          int,
    diagnosis              text,
    notes                  text,
    status                 enum('pending','dispensed','cancelled') default 'pending',
    prescription_date_time datetime default current_timestamp,
    dispensed_at           datetime,
    foreign key (patient_id)     references patient(patient_id),
    foreign key (doctor_id)      references doctor(doctor_id),
    foreign key (appointment_id) references appointment(appointment_id),
    foreign key (pharmacist_id)  references pharmacist(pharmacist_id)
);


-- ─── 10. prescription_medicine
create table prescription_medicine (
    prescription_medicine_id int auto_increment primary key,
    prescription_id int not null,
    medicine_id     int not null,
    quantity        int not null default 1,
    instruction     text,
    purchase_status enum('not_bought','bought') default 'not_bought',
    foreign key (prescription_id) references prescription(prescription_id) on delete cascade,
    foreign key (medicine_id)     references medicine(medicine_id)
);


-- ─── 11. invoice
create table invoice (
    invoice_id        int auto_increment primary key,
    appointment_id    int not null,
    invoice_type      varchar(50) default 'consultation',
    total_amount      decimal(10,2) not null,
    invoice_date_time datetime default current_timestamp,
    foreign key (appointment_id) references appointment(appointment_id) on delete cascade
);


-- ─── 12. payments
create table payment (
    payment_id        int auto_increment primary key,
    invoice_id        int not null,
    payment_method    enum('cash','card','aba_pay','wing','bakong') not null,
    amount            decimal(10,2) not null,
    status            enum('pending','paid','refunded','failed') default 'paid',
    transaction_ref   varchar(100),
    payment_date_time datetime default current_timestamp,
    foreign key (invoice_id) references invoice(invoice_id) on delete cascade
);


-- ─── 13. activity_log
create table activity_log (
    log_id      int auto_increment primary key,
    user_id     int,
    action_type varchar(255) not null,
    action_time datetime default current_timestamp,
    description text,
    foreign key (user_id) references user(user_id) on delete set null
);

-- seed the medicine inventory
insert into medicine (medicine_name, medicine_type, price, stock_quantity, expiry_date) values
('Hydrocortisone Cream',     'topical', 15.50, 100, '2027-12-31'),
('Salicylic Acid Cleanser',  'topical', 12.00,  50, '2028-08-15'),
('Tretinoin 0.025%',         'topical', 22.00,  30, '2027-06-30'),
('Doxycycline 100mg',        'oral',     8.50, 200, '2027-03-20'),
('Benzoyl Peroxide 5%',      'topical', 10.00,  80, '2028-01-15'),
('Clindamycin Lotion',       'topical', 18.00,  60, '2027-09-30'),
('Adapalene Gel 0.1%',       'topical', 25.00,  40, '2027-11-20'),
('Cetirizine 10mg',          'oral',     5.50, 150, '2028-04-10'),
('Vitamin E Cream',          'topical',  8.50, 120, '2028-07-25'),
('Sunscreen SPF50',          'topical', 20.00, 200, '2028-12-31');

-- verification — these queries show that everything work

-- count of tables (should be 13)
select count(*) as total_tables
from information_schema.tables
where table_schema = 'dermacare';

-- list all tables
show tables;

-- check medicine inventory (should be 10 rows)
select * from medicine;

USE dermacare;
DELETE FROM user WHERE email = 'admin@dermacare.com';