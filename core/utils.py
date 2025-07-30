# core/utils.py

import pandas as pd
import numpy as np
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate, TruncMonth

from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.linear_model import LinearRegression

from .models import Product, ProductEvent, Customer, ABTestEvent

logger = logging.getLogger(__name__)


def calculate_funnel_analysis(user, start_date, end_date):
    """تحلیل قیف فروش بر اساس مشتریان یکتا."""
    events = ProductEvent.objects.filter(
        product__owner=user, created_at__range=(start_date, end_date)
    )
    total_views = events.filter(event_type='VIEW').values('customer').distinct().count()
    total_carts = events.filter(event_type='ADD_TO_CART').values('customer').distinct().count()
    total_purchases = events.filter(event_type='PURCHASE').values('customer').distinct().count()

    return {
        'views': total_views,
        'carts': total_carts,
        'purchases': total_purchases,
        'view_to_cart_rate': (total_carts / total_views * 100) if total_views > 0 else 0,
        'cart_to_purchase_rate': (total_purchases / total_carts * 100) if total_carts > 0 else 0,
        'overall_conversion_rate': (total_purchases / total_views * 100) if total_views > 0 else 0,
    }


def get_customer_segments(owner_user, start_date, end_date):
    """بخش‌بندی کاربران بر اساس رفتارشان."""
    customers = Customer.objects.filter(owner=owner_user)
    events = ProductEvent.objects.filter(customer__in=customers, created_at__range=(start_date, end_date))

    high_value_users = events.filter(event_type='PURCHASE').values('customer__identifier').annotate(
        total_spent=Sum('product__price')
    ).order_by('-total_spent')[:5]

    loyal_users = events.filter(event_type='PURCHASE').values('customer__identifier').annotate(
        purchase_count=Count('id')
    ).order_by('-purchase_count')[:5]

    window_shoppers = events.values('customer__identifier').annotate(
        view_count=Count('id', filter=Q(event_type='VIEW')),
        purchase_count=Count('id', filter=Q(event_type='PURCHASE'))
    ).filter(view_count__gt=10, purchase_count=0).order_by('-view_count')[:5]

    return {
        'high_value': list(high_value_users),
        'loyal': list(loyal_users),
        'window_shoppers': list(window_shoppers)
    }


def get_market_basket_analysis(user):
    """تحلیل سبد خرید برای یافتن محصولات هم‌خرید."""
    all_purchases = list(ProductEvent.objects.filter(
        product__owner=user, event_type='PURCHASE'
    ).values('customer__identifier', 'created_at__date', 'product__name'))

    if len(all_purchases) < 20:
        return None, "داده کافی برای تحلیل سبد خرید وجود ندارد."

    df = pd.DataFrame(all_purchases)
    try:
        basket = df.groupby(['customer__identifier', 'created_at__date', 'product__name'])[
            'product__name'].count().unstack().reset_index().fillna(0).set_index(
            ['customer__identifier', 'created_at__date'])
        basket_sets = basket.map(lambda x: x > 0)
        frequent_itemsets = apriori(basket_sets, min_support=0.01, use_colnames=True)
        if frequent_itemsets.empty:
            return None, "هیچ الگوی پرتکراری در خریدها یافت نشد."

        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
        if rules.empty:
            return None, "هیچ قانون وابستگی معناداری یافت نشد."

        rules["antecedents"] = rules["antecedents"].apply(lambda x: ', '.join(list(x)))
        rules["consequents"] = rules["consequents"].apply(lambda x: ', '.join(list(x)))
        return rules.sort_values('confidence', ascending=False).head(5), "تحلیل با موفقیت انجام شد."
    except Exception as e:
        logger.error(f"Market Basket Analysis failed: {e}")
        return None, "خطا در پردازش تحلیل سبد خرید."


def predict_future_sales(product_id, days_to_predict=30):
    """پیش‌بینی فروش با رگرسیون خطی."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    purchases = list(ProductEvent.objects.filter(
        product_id=product_id, event_type='PURCHASE', created_at__range=(start_date, end_date)
    ).annotate(date=TruncDate('created_at')).values('date').annotate(daily_sales=Count('id')).order_by('date'))

    if len(purchases) < 10:
        return None, "داده‌های کافی برای پیش‌بینی فروش این محصول وجود ندارد."

    df = pd.DataFrame(purchases)
    df['date'] = pd.to_datetime(df['date'])
    df['day_number'] = (df['date'] - df['date'].min()).dt.days
    X, y = df[['day_number']], df['daily_sales']

    model = LinearRegression().fit(X, y)
    last_day_number = df['day_number'].max()
    future_days = np.arange(last_day_number + 1, last_day_number + 1 + days_to_predict).reshape(-1, 1)
    predicted_sales = np.maximum(0, model.predict(future_days))
    future_dates = pd.to_datetime(df['date'].min()) + pd.to_timedelta(future_days.flatten(), unit='d')
    predictions = {date.strftime('%Y-%m-%d'): round(sale) for date, sale in zip(future_dates, predicted_sales)}
    return predictions, "پیش‌بینی با موفقیت انجام شد."


def get_ab_test_results(test):
    """محاسبه نتایج برای یک تست A/B."""
    events = ABTestEvent.objects.filter(test=test)
    control_views = events.filter(variant_shown='CONTROL', event_type='VIEW').count()
    variant_views = events.filter(variant_shown='VARIANT', event_type='VIEW').count()
    control_conversions = events.filter(variant_shown='CONTROL', event_type='CONVERSION').count()
    variant_conversions = events.filter(variant_shown='VARIANT', event_type='CONVERSION').count()

    control_rate = (control_conversions / control_views * 100) if control_views > 0 else 0
    variant_rate = (variant_conversions / variant_views * 100) if variant_views > 0 else 0

    winner = "هنوز مشخص نیست"
    if control_rate > variant_rate:
        winner = "نسخه کنترل"
    elif variant_rate > control_rate:
        winner = "نسخه جدید"

    return {
        'control': {'views': control_views, 'conversions': control_conversions, 'rate': control_rate},
        'variant': {'views': variant_views, 'conversions': variant_conversions, 'rate': variant_rate},
        'winner': winner
    }


def get_cohort_analysis(user):
    """تحلیل بازگشت مشتریان در گروه‌های (کوهورت‌های) ماهانه."""
    customers = Customer.objects.filter(owner=user).annotate(
        cohort_month=TruncMonth('first_seen')
    ).values('id', 'cohort_month')

    if not customers.exists():
        return pd.DataFrame(), "مشتری برای تحلیل یافت نشد."

    customer_cohorts = {c['id']: c['cohort_month'] for c in customers}
    events = ProductEvent.objects.filter(customer__in=customers.values('id')).annotate(
        event_month=TruncMonth('created_at')
    ).values('customer_id', 'event_month').distinct()

    if not events.exists():
        return pd.DataFrame(), "رویدادی برای تحلیل یافت نشد."

    df_events = pd.DataFrame(list(events))
    df_events['cohort_month'] = df_events['customer_id'].map(lambda x: customer_cohorts.get(x))
    df_events.dropna(inplace=True)  # Ensure no missing cohorts

    df_events['cohort_month'] = pd.to_datetime(df_events['cohort_month'].apply(lambda d: d.strftime('%Y-%m-%d')))
    df_events['event_month'] = pd.to_datetime(df_events['event_month'].apply(lambda d: d.strftime('%Y-%m-%d')))

    def get_month_diff(row):
        return (row['event_month'].year - row['cohort_month'].year) * 12 + (
                    row['event_month'].month - row['cohort_month'].month)

    df_events['month_number'] = df_events.apply(get_month_diff, axis=1)

    cohort_data = df_events.groupby(['cohort_month', 'month_number'])['customer_id'].nunique().reset_index()
    cohort_counts = cohort_data.pivot_table(index='cohort_month', columns='month_number', values='customer_id')

    cohort_sizes = df_events.groupby('cohort_month')['customer_id'].nunique()
    cohort_percents = cohort_counts.divide(cohort_sizes, axis=0).multiply(100)

    cohort_percents.index = cohort_percents.index.strftime('%Y-%m')
    cohort_percents.columns = [f"ماه {i}" for i in cohort_percents.columns]

    return cohort_percents.round(1).fillna(''), "تحلیل با موفقیت انجام شد."