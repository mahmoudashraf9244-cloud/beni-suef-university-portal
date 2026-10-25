from itertools import islice
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import ActivityFilterForm, StudentProfileForm, UserRegisterForm
from .models import Activity, Category, Enrollment, StudentProfile
from .services import EnrollmentResult, enroll_student


def home(request):
    today = timezone.localdate()
    candidates = (
        Activity.objects.select_related('category', 'trainer')
        .filter(availability_status=True)
        .annotate(enrollment_total=Count('enrollments'))
        .filter(enrollment_total__lt=F('max_students'))
        .order_by('start_date', 'title')
    )
    activities = list(islice(
        (activity for activity in candidates.iterator() if activity.is_joinable_on(today)),
        3,
    ))
    return render(request, 'shop/home.html', {'activities': activities})


def activity_list(request):
    query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    filter_form = ActivityFilterForm({'q': query, 'category': selected_category})

    activities = Activity.objects.select_related('category', 'trainer').all()

    if filter_form.is_valid():
        query = filter_form.cleaned_data['q']
        category_id = filter_form.cleaned_data['category']
        if query:
            localized_ids = []
            if getattr(request, 'LANGUAGE_CODE', 'en') == 'ar':
                localized_ids = [pk for pk, title in activities.values_list('pk', 'title')
                                 if query.casefold() in _(title).casefold()]
            activities = activities.filter(Q(title__icontains=query) | Q(pk__in=localized_ids))
        if category_id is not None:
            selected_category = str(category_id)
            activities = activities.filter(category_id=category_id)
    else:
        activities = activities.none()

    activities = activities.order_by('start_date', 'title')
    paginator = Paginator(activities, 3)
    page_obj = paginator.get_page(request.GET.get('page'))
    if page_obj.number > 1 and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    categories = Category.objects.all().order_by('name')

    return render(
        request,
        'shop/activity_list.html',
        {
            'activities': page_obj.object_list,
            'page_obj': page_obj,
            'categories': categories,
            'query': query,
            'selected_category': selected_category,
        },
    )


def activity_detail(request, activity_id):
    activity = get_object_or_404(
        Activity.objects.select_related('category', 'trainer'),
        pk=activity_id,
    )
    profile = getattr(request.user, 'student_profile', None) if request.user.is_authenticated else None
    enrollment_count = activity.enrollments.count()
    is_enrolled = (
        Enrollment.objects.filter(student=profile, activity=activity).exists()
        if profile is not None else False
    )
    return render(request, 'shop/activity_detail.html', {
        'activity': activity,
        'student_profile': profile,
        'enrollment_count': enrollment_count,
        'remaining_seats': max(0, activity.max_students - enrollment_count),
        'is_enrolled': is_enrolled,
    })


@transaction.non_atomic_requests
@login_required
@require_POST
def enroll_activity(request, activity_id):
    profile = getattr(request.user, 'student_profile', None)
    if profile is None or not request.user.is_active:
        raise PermissionDenied('A student account is required.')
    try:
        result = enroll_student(student_id=profile.pk, activity_id=activity_id)
    except Activity.DoesNotExist as error:
        raise Http404('Activity not found.') from error
    if result == EnrollmentResult.INELIGIBLE:
        raise PermissionDenied('An active student account is required.')
    feedback = {
        EnrollmentResult.CREATED: (messages.SUCCESS, 'You have enrolled in this activity.'),
        EnrollmentResult.ALREADY_ENROLLED: (messages.INFO, 'You are already enrolled in this activity.'),
        EnrollmentResult.FULL: (messages.ERROR, 'This activity is full. There are no remaining seats.'),
        EnrollmentResult.CLOSED: (messages.ERROR, 'This activity is closed and is not accepting enrollments.'),
        EnrollmentResult.COMPLETED: (messages.ERROR, 'This activity has completed and is not accepting enrollments.'),
        EnrollmentResult.BUSY: (messages.WARNING, 'Registration is busy. Please try again in a moment.'),
    }
    level, text = feedback[result]
    messages.add_message(request, level, _(text))
    return redirect('shop:activity_detail', activity_id=activity_id)


def register(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            StudentProfile.objects.get_or_create(user=user)
            messages.success(request, _('Your account has been created. Please log in.'))
            login_url = reverse('shop:login')
            if next_url:
                login_url = f'{login_url}?next={quote(next_url, safe="")}'
            return redirect(login_url)
    else:
        form = UserRegisterForm()

    return render(request, 'shop/register.html', {'form': form, 'next_url': next_url})


@login_required
def student_profile(request):
    today = timezone.localdate()
    profile = getattr(request.user, 'student_profile', None)
    profile_fields = (profile.phone_number, profile.university, profile.faculty, profile.academic_year) if profile else ()
    completed_fields = sum(bool(value) for value in profile_fields)
    profile_completion = round((completed_fields / 4) * 100)
    enrollments = list(
        Enrollment.objects.filter(student=profile)
        .select_related('activity')
        .order_by('-enrolled_at', '-pk')
    ) if profile is not None else []
    dashboard_stats = {
        'available_activities': sum(
            activity.is_joinable_on(today)
            for activity in Activity.objects.filter(availability_status=True)
            .annotate(enrollment_total=Count('enrollments'))
            .filter(enrollment_total__lt=F('max_students'))
            .only('start_date', 'duration', 'availability_status').iterator()
        ),
        'enrolled_activities': len(enrollments),
        'categories': Category.objects.count(),
        'profile_completion': profile_completion,
    }
    return render(
        request,
        'shop/profile.html',
        {'profile': profile, 'user': request.user, 'dashboard_stats': dashboard_stats, 'enrollments': enrollments},
    )


def custom_404(request, exception):
    return render(request, '404.html', status=404)


@login_required
def edit_student_profile(request):
    profile = getattr(request.user, 'student_profile', None)
    if profile is None:
        profile = StudentProfile(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Your profile was updated successfully.'))
            return redirect('shop:student_profile')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'shop/profile_edit.html', {'form': form})

