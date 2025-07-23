from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from accounts.models import SubscriptionPlan, UserSubscription, User
from django.contrib.auth import login


# Create your views here.

# این ویو فقط برای تست است تا بتوانید به سادگی لاگین کنید
def dummy_login_view(request):
    # یک کاربر را برای تست انتخاب می‌کنیم (مثلا اولین کاربر)
    # مطمئن شوید حداقل یک کاربر در دیتابیس شما وجود دارد
    test_user = User.objects.first()
    if not test_user:
        # اگر کاربری نبود، یکی می‌سازیم
        test_user = User.objects.create_user(username='09123456789', password='testpassword')

        # فعال‌سازی پلن آزمایشی برای کاربر جدید
        try:
            trial_plan = SubscriptionPlan.objects.get(is_trial=True)
            if not UserSubscription.objects.filter(user=test_user, plan__is_trial=True).exists():
                now = timezone.now()
                UserSubscription.objects.create(
                    user=test_user,
                    plan=trial_plan,
                    start_date=now,
                    end_date=now + timedelta(days=trial_plan.duration_days)
                )
        except SubscriptionPlan.DoesNotExist:
            print("خطا: پلن آزمایشی برای کاربر تستی یافت نشد.")

    login(request, test_user)
    return redirect('subscription_frontend:dashboard')


@login_required(login_url='/subscription-test/login/')
def subscription_dashboard_view(request):
    user = request.user
    current_subscription = UserSubscription.objects.filter(user=user).first()

    # فقط پلن‌های عمومی و غیرآزمایشی برای خرید نمایش داده می‌شوند
    available_plans = SubscriptionPlan.objects.filter(is_public=True, is_trial=False)

    context = {
        'current_subscription': current_subscription,
        'available_plans': available_plans,
    }
    return render(request, 'app/dashboard.html', context)


@login_required(login_url='/subscription-test/login/')
def purchase_confirmation_view(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_public=True, is_trial=False)

    if request.method == 'POST':
        now = timezone.now()

        # این منطق دقیقا معادل چیزی است که در API View شما وجود دارد
        UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'start_date': now,
                'end_date': now + timedelta(days=plan.duration_days)
            }
        )
        return redirect('subscription_frontend:dashboard')

    context = {
        'plan': plan,
    }
    return render(request, 'app/purchase_confirmation.html', context)
