from django.contrib import admin
from .models import Category, Trainer, TrainerProfile, Activity, StudentProfile, Enrollment


admin.site.site_header = "Beni-Suef University Portal Administration"
admin.site.site_title = "Beni-Suef University Portal"
admin.site.index_title = "Courses and activities management"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_id", "name", "description")
    search_fields = ("name",)
    ordering = ("name",)

    fieldsets = (("Category Information", {"fields": ("name", "description")}),)


class TrainerProfileInline(admin.TabularInline):
    model = TrainerProfile
    extra = 0
    fieldsets = (
        (
            "Professional Information",
            {
                "fields": (
                    "professional_title",
                    "biography",
                    "specialization",
                    "years_of_experience",
                )
            },
        ),
    )


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("trainer_id", "full_name", "email", "phone_number")
    search_fields = ("full_name", "email")
    ordering = ("full_name",)
    inlines = [TrainerProfileInline]

    fieldsets = (
        ("Basic Information", {"fields": ("full_name", "email", "phone_number")}),
    )


@admin.register(TrainerProfile)
class TrainerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "profile_id",
        "get_trainer_name",
        "professional_title",
        "specialization",
    )
    search_fields = ("trainer__full_name", "professional_title", "specialization")
    ordering = ("trainer__full_name",)

    fieldsets = (
        ("Trainer Link", {"fields": ("trainer",)}),
        (
            "Professional Information",
            {
                "fields": (
                    "professional_title",
                    "biography",
                    "specialization",
                    "years_of_experience",
                )
            },
        ),
    )

    def get_trainer_name(self, obj):
        return obj.trainer.full_name

    get_trainer_name.short_description = "Trainer"


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "activity_id",
        "title",
        "category",
        "trainer",
        "start_date",
        "duration",
        "max_students",
        "level",
        "availability_status",
    )
    search_fields = ("title", "category__name", "trainer__full_name")
    list_filter = ("category", "level", "availability_status", "start_date")
    ordering = ("start_date", "title")

    fieldsets = (
        (
            "Activity Information",
            {
                "fields": (
                    "title",
                    "short_description",
                    "full_description",
                    "learning_outcomes",
                    "prerequisites",
                    "level",
                )
            },
        ),
        (
            "Schedule & Capacity",
            {
                "fields": (
                    "start_date",
                    "duration",
                    "max_students",
                    "availability_status",
                )
            },
        ),
        ("Assignment", {"fields": ("category", "trainer")}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "get_username",
        "university",
        "faculty",
        "academic_year",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "university",
    )
    list_filter = ("faculty", "academic_year", "university")
    ordering = ("user__username",)

    fieldsets = (
        ("User Link", {"fields": ("user",)}),
        (
            "University Information",
            {"fields": ("university", "faculty", "academic_year")},
        ),
        ("Contact Information", {"fields": ("phone_number",)}),
    )

    def get_username(self, obj):
        return f"{obj.user.username} ({obj.user.get_full_name()})"

    get_username.short_description = "User"
    get_username.admin_order_field = "user__username"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'activity', 'enrolled_at')
    search_fields = (
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'activity__title',
    )
    list_filter = ('enrolled_at', 'activity__category')
    list_select_related = ('student__user', 'activity')
    readonly_fields = ('id', 'student', 'activity', 'enrolled_at')
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
