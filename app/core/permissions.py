ATTENDANCE_SUBMIT = "attendance:submit"
ATTENDANCE_VIEW = "attendance:view"
GRADES_SUBMIT = "grades:submit"
GRADES_VIEW = "grades:view"
STUDENTS_VIEW = "students:view"
STUDENTS_CREATE = "students:create"
STUDENTS_EDIT = "students:edit"
STUDENTS_DELETE = "students:delete"
CLASSES_VIEW = "classes:view"
CLASSES_CREATE = "classes:create"
CLASSES_EDIT = "classes:edit"
CLASSES_DELETE = "classes:delete"
SUBJECTS_VIEW = "subjects:view"
SUBJECTS_CREATE = "subjects:create"
SUBJECTS_EDIT = "subjects:edit"
SUBJECTS_DELETE = "subjects:delete"
STAFF_VIEW = "staff:view"
STAFF_CREATE = "staff:create"
STAFF_EDIT = "staff:edit"
STAFF_DELETE = "staff:delete"
TERMS_VIEW = "terms:view"
TERMS_MANAGE = "terms:manage"
CURRICULUM_VIEW = "curriculum:view"
CURRICULUM_MANAGE = "curriculum:manage"
SYLLABUS_VIEW = "syllabus:view"
SYLLABUS_MANAGE = "syllabus:manage"
TIMETABLE_VIEW = "timetable:view"
TIMETABLE_MANAGE = "timetable:manage"
REPORTS_VIEW = "reports:view"
DASHBOARD_VIEW = "dashboard:view"
GRADING_MANAGE = "grading:manage"

CONTENT_MANAGER = "content:manage"
HERO_MANAGE = "hero:manage"
ABOUT_MANAGE = "about:manage"
SERVICES_MANAGE = "services:manage"
GALLERY_MANAGE = "gallery:manage"
REVIEWS_MANAGE = "reviews:manage"
FAQ_MANAGE = "faq:manage"
TEAM_MANAGE = "team:manage"
LEGAL_MANAGE = "legal:manage"
BLOG_MANAGE = "blog:manage"
THEME_MANAGE = "theme:manage"
SECTIONS_MANAGE = "sections:manage"
LEADS_VIEW = "leads:view"
FORM_MANAGE = "form:manage"
CONTACT_MANAGE = "contact:manage"

ROLE_DEFAULT_PERMISSIONS = {
    "teacher": [
        ATTENDANCE_SUBMIT,
        ATTENDANCE_VIEW,
        GRADES_SUBMIT,
        GRADES_VIEW,
        STUDENTS_VIEW,
        CLASSES_VIEW,
        SUBJECTS_VIEW,
        CURRICULUM_VIEW,
        SYLLABUS_VIEW,
        TIMETABLE_VIEW,
        TERMS_VIEW,
        DASHBOARD_VIEW,
    ],
    "viewer": [
        ATTENDANCE_VIEW,
        GRADES_VIEW,
        STUDENTS_VIEW,
        CLASSES_VIEW,
        SUBJECTS_VIEW,
        CURRICULUM_VIEW,
        SYLLABUS_VIEW,
        TIMETABLE_VIEW,
        TERMS_VIEW,
        DASHBOARD_VIEW,
    ],
    "hr": [
        ATTENDANCE_VIEW,
        GRADES_VIEW,
        STUDENTS_VIEW,
        STUDENTS_CREATE,
        STUDENTS_EDIT,
        CLASSES_VIEW,
        CLASSES_CREATE,
        CLASSES_EDIT,
        SUBJECTS_VIEW,
        SUBJECTS_CREATE,
        SUBJECTS_EDIT,
        STAFF_VIEW,
        STAFF_CREATE,
        STAFF_EDIT,
        STAFF_DELETE,
        CURRICULUM_VIEW,
        CURRICULUM_MANAGE,
        SYLLABUS_VIEW,
        TIMETABLE_VIEW,
        TIMETABLE_MANAGE,
        TERMS_VIEW,
        REPORTS_VIEW,
        DASHBOARD_VIEW,
    ],
    "editor": [
        CONTENT_MANAGER,
        HERO_MANAGE, ABOUT_MANAGE, SERVICES_MANAGE,
        GALLERY_MANAGE, REVIEWS_MANAGE, FAQ_MANAGE,
        TEAM_MANAGE, LEGAL_MANAGE, BLOG_MANAGE,
        THEME_MANAGE, SECTIONS_MANAGE,
        LEADS_VIEW, FORM_MANAGE, CONTACT_MANAGE,
    ],
    "proprietor": [
        ATTENDANCE_SUBMIT, ATTENDANCE_VIEW,
        GRADES_SUBMIT, GRADES_VIEW,
        STUDENTS_VIEW, STUDENTS_CREATE, STUDENTS_EDIT, STUDENTS_DELETE,
        CLASSES_VIEW, CLASSES_CREATE, CLASSES_EDIT, CLASSES_DELETE,
        SUBJECTS_VIEW, SUBJECTS_CREATE, SUBJECTS_EDIT, SUBJECTS_DELETE,
        STAFF_VIEW, STAFF_CREATE, STAFF_EDIT, STAFF_DELETE,
        TERMS_VIEW, TERMS_MANAGE,
        CURRICULUM_VIEW, CURRICULUM_MANAGE,
        SYLLABUS_VIEW, SYLLABUS_MANAGE,
        TIMETABLE_VIEW, TIMETABLE_MANAGE,
        REPORTS_VIEW,
        DASHBOARD_VIEW,
        GRADING_MANAGE,
    ],
    "admin": ["*"],
}

ALL_PERMISSIONS = [
    ATTENDANCE_SUBMIT, ATTENDANCE_VIEW,
    GRADES_SUBMIT, GRADES_VIEW,
    STUDENTS_VIEW, STUDENTS_CREATE, STUDENTS_EDIT, STUDENTS_DELETE,
    CLASSES_VIEW, CLASSES_CREATE, CLASSES_EDIT, CLASSES_DELETE,
    SUBJECTS_VIEW, SUBJECTS_CREATE, SUBJECTS_EDIT, SUBJECTS_DELETE,
    STAFF_VIEW, STAFF_CREATE, STAFF_EDIT, STAFF_DELETE,
    TERMS_VIEW, TERMS_MANAGE,
    CURRICULUM_VIEW, CURRICULUM_MANAGE,
    SYLLABUS_VIEW, SYLLABUS_MANAGE,
    TIMETABLE_VIEW, TIMETABLE_MANAGE,
    REPORTS_VIEW,
    DASHBOARD_VIEW,
    GRADING_MANAGE,
    CONTENT_MANAGER, HERO_MANAGE, ABOUT_MANAGE, SERVICES_MANAGE,
    GALLERY_MANAGE, REVIEWS_MANAGE, FAQ_MANAGE,
    TEAM_MANAGE, LEGAL_MANAGE, BLOG_MANAGE,
    THEME_MANAGE, SECTIONS_MANAGE,
    LEADS_VIEW, FORM_MANAGE, CONTACT_MANAGE,
]


def get_default_permissions(role: str) -> list[str]:
    return ROLE_DEFAULT_PERMISSIONS.get(role, ROLE_DEFAULT_PERMISSIONS.get("viewer", []))


def get_effective_permissions(user) -> list[str]:
    perms = user.permissions
    if perms is None:
        perms = get_default_permissions(user.role)
    if not isinstance(perms, list):
        perms = []
    return perms


def has_permission(user, permission: str) -> bool:
    if user.role == "admin":
        return True
    effective = get_effective_permissions(user)
    if "*" in effective:
        return True
    return permission in effective
