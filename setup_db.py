# NOTE: For production deployments, use Alembic for migrations instead of
# create_all(). Run: alembic upgrade head
# See alembic/env.py and alembic/versions/ for migration files.

from datetime import date
from app.db.session import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.site_content import SiteContent
from app.models.service import Service
from app.models.gallery_item import GalleryItem
from app.models.testimonial import Testimonial
from app.models.lead import Lead
from app.models.lead_event import LeadEvent
from app.models.refresh_token import RefreshToken
from app.models.blog import BlogPost
from app.models.page_section import PageSection
from app.models.academic_term import AcademicTerm
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.models.class_subject import ClassSubject
from app.models.academic_record import AcademicRecord
from app.models.attendance import Attendance
import os
import time

def wait_for_db():
    import psycopg2
    from app.core.config import settings
    db_url = os.getenv("DATABASE_URL", settings.database_url)
    for i in range(30):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            return
        except Exception:
            time.sleep(1)
    print("Could not connect to database after 30 seconds")

def setup():
    print("Waiting for database...")
    wait_for_db()

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing is None:
            print("Seeding initial data...")
            admin = User(
                email="admin@destinedchampions.com",
                full_name="Admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.flush()

            services_data = [
                ("Early Childhood", "early-childhood", "A nurturing program for ages 3-5 focusing on foundational skills through play-based learning.", "Book", 1),
                ("Primary Education", "primary", "Grades 1-6 with a strong foundation in literacy, numeracy, science, and social studies.", "BookOpen", 2),
                ("Secondary Education", "secondary", "Grades 7-12 college-preparatory curriculum with diverse subject offerings.", "GraduationCap", 3),
                ("Extracurricular", "extracurricular", "Sports, music, arts, debate, coding, and leadership programs.", "Star", 4),
            ]
            for title, slug, desc, icon, order in services_data:
                db.add(Service(title=title, slug=slug, description=desc, icon_name=icon, display_order=order, is_active=True))

            term = AcademicTerm(name="Term 1", year="2026", start_date=date(2026, 1, 15), end_date=date(2026, 4, 30), is_active=True)
            db.add(term)
            db.flush()

            subjects_data = [
                ("Mathematics", "MATH", "Mathematics and numeracy"),
                ("English", "ENG", "English language and literature"),
                ("Science", "SCI", "General science"),
                ("Social Studies", "SST", "Social studies and citizenship"),
            ]
            for name, code, desc in subjects_data:
                db.add(Subject(name=name, code=code, description=desc))



        sections = [
            ("hero", "headline", "Welcome to DESTINED CHAMPIONS FOUNDATION — Nurturing Future Leaders", "text"),
            ("hero", "subheadline", "Providing quality education in a safe, supportive environment for every child.", "text"),
            ("about", "description", "At DESTINED CHAMPIONS FOUNDATION, we believe every child has the potential to excel. Our mission is to provide a well-rounded education that nurtures academic excellence, character, and creativity.", "text"),
            ("about", "feature_1_title", "Experienced Teachers", "text"),
            ("about", "feature_1_desc", "Our dedicated educators bring years of experience and a passion for teaching, ensuring each student receives personalized attention.", "text"),
            ("about", "feature_2_title", "Modern Curriculum", "text"),
            ("about", "feature_2_desc", "We follow a comprehensive, up-to-date curriculum that prepares students for higher education and future careers.", "text"),
            ("about", "feature_3_title", "Safe Environment", "text"),
            ("about", "feature_3_desc", "Student safety is our top priority. Our campus is secure, monitored, and designed to provide a nurturing atmosphere.", "text"),
            ("about", "feature_4_title", "Holistic Development", "text"),
            ("about", "feature_4_desc", "Beyond academics, we offer sports, arts, and character-building programs to develop well-rounded individuals.", "text"),
            ("hero", "badge_text", "Excellence in Education", "text"),
            ("hero", "button_1_text", "Enroll Now", "text"),
            ("hero", "button_2_text", "Learn More", "text"),
            ("hero", "stat_1_value", "500+", "text"),
            ("hero", "stat_1_label", "Students Enrolled", "text"),
            ("hero", "stat_2_value", "15+", "text"),
            ("hero", "stat_2_label", "Years of Excellence", "text"),
            ("hero", "stat_3_value", "98%", "text"),
            ("hero", "stat_3_label", "Pass Rate", "text"),
            ("services", "heading", "Our Academic Programs", "text"),
            ("services", "subtitle", "From early childhood to secondary education, we offer programs designed for every stage of development.", "text"),
            ("gallery", "heading", "School Life", "text"),
            ("gallery", "subtitle", "Moments that capture the spirit of learning and community at DESTINED CHAMPIONS FOUNDATION.", "text"),
            ("testimonials", "heading", "What Parents Say", "text"),
            ("contact", "heading", "Get in Touch", "text"),
            ("contact", "subtitle", "Ready to give your child the best education? Contact us today.", "text"),
            ("contact", "company_name", "DESTINED CHAMPIONS FOUNDATION", "text"),
            ("contact", "phone", "+15550000", "text"),
            ("contact", "email", "info@destinedchampions.com", "text"),
            ("contact", "working_hours", "Mon-Fri: 8:00 AM - 3:00 PM", "text"),
            ("contact", "address", "123 Education Avenue, City, State 12345", "text"),
            ("faq", "subtitle", "Answers to common questions about our school.", "text"),
            ("about", "heading", "Why Choose DESTINED CHAMPIONS FOUNDATION?", "text"),
            ("theme", "primary-black", "#800020", "text"),
            ("theme", "primary-gold", "#0A2463", "text"),
            ("theme", "light-gray", "#F0F2F5", "text"),
            ("theme", "dark-gray", "#1A1A2E", "text"),
            ("theme", "gold-start", "#0A2463", "text"),
            ("theme", "gold-end", "#152B5E", "text"),
            ("footer", "copyright", "© 2026 DESTINED CHAMPIONS FOUNDATION. All rights reserved.", "text"),
            ("faq", "heading", "Frequently Asked Questions", "text"),
            ("faq", "What are the school hours?", "School runs from 8:00 AM to 3:00 PM, Monday through Friday.", "text"),
            ("faq", "How do I enroll my child?", "Visit our admissions office or fill out the online enrollment form on our website.", "text"),
            ("faq", "What is the teacher-to-student ratio?", "We maintain small class sizes with an average ratio of 1:20.", "text"),
            ("faq", "Do you offer extracurricular activities?", "Yes! We offer sports, music, art, debate, coding club and more.", "text"),
            ("faq", "What is the school fee structure?", "Please contact our admissions office for detailed fee information and payment plans.", "text"),
            ("service_area", "heading", "Service Area", "text"),
            ("service_area", "description", "We proudly serve students and families across the greater metropolitan area and surrounding communities.", "text"),
            ("team", "heading", "Meet our dedicated team of educators and staff.", "text"),
            ("team", "member_John_Smith", "Principal with 15+ years of experience in educational leadership and curriculum development.", "text"),
            ("team", "member_Sarah_Jones", "Head of Academics specializing in innovative teaching methods and student assessment.", "text"),
            ("privacy", "body", "DESTINED CHAMPIONS FOUNDATION respects your privacy. This policy explains how we collect, use, and safeguard your personal information.\n\nInformation We Collect: We collect information you provide when filling out forms on our website, including your name, phone number, email address, and student information.\n\nHow We Use Your Information: We use your information to process enrollments, communicate with you about school activities, and send academic updates.\n\nData Protection: We implement industry-standard security measures to protect your personal information from unauthorized access or disclosure.\n\nThird-Party Sharing: We do not sell or share your personal information with third parties except as necessary to provide our services or as required by law.\n\nContact: If you have questions about this policy, please contact us at info@destinedchampions.com.", "rich_text"),
            ("privacy", "last_updated", "January 1, 2026", "text"),
            ("terms", "body", "By using the DESTINED CHAMPIONS FOUNDATION website and services, you agree to the following terms and conditions.\n\nServices: We provide educational services as described on our website. Programs, schedules, and fees are subject to change without notice.\n\nEnrollment: Enrollment is subject to availability and completion of all required documentation. Late enrollments may incur additional fees.\n\nPayment: Tuition fees are due as per the schedule provided at enrollment. Late payments may result in service suspension.\n\nLiability: DESTINED CHAMPIONS FOUNDATION takes utmost care of your child during school hours but is not liable for incidents beyond reasonable control.\n\nModifications: We reserve the right to modify these terms at any time. Continued use of our services constitutes acceptance of updated terms.", "rich_text"),
            ("terms", "last_updated", "January 1, 2026", "text"),
        ]
        old_faq = db.query(SiteContent).filter(
            SiteContent.section == "faq",
            SiteContent.field_key.like("question_%"),
        ).all()
        for o in old_faq:
            db.delete(o)

        for section, key, value, ctype in sections:
            exists = db.query(SiteContent).filter(
                SiteContent.section == section,
                SiteContent.field_key == key,
            ).first()
            if not exists:
                db.add(SiteContent(section=section, field_key=key, field_value=value, content_type=ctype))

        page_sections = [
            ("hero", "Hero", 1),
            ("about", "About", 2),
            ("services", "Services", 3),
            ("gallery", "Gallery", 4),
            ("testimonials", "Testimonials", 5),
            ("faq", "FAQ", 6),
            ("service_area", "Service Area", 7),
            ("contact", "Contact", 8),
            ("footer", "Footer", 9),
        ]
        for name, _label, order in page_sections:
            exists = db.query(PageSection).filter(PageSection.name == name).first()
            if not exists:
                db.add(PageSection(name=name, is_visible=True, display_order=order))

        db.commit()
        print("Seed data ready. Admin login: admin@destinedchampions.com / admin123")
    finally:
        db.close()

if __name__ == "__main__":
    setup()
