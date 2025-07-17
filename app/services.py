from . import models , Count

#  """
#     محصولاتی را پیدا می‌کند که توسط کاربرانی که محصول ورودی را دیده‌اند،
#     بیشترین بازدید را داشته‌اند.
#     """

def find_related_products(product_id , limit = 5):

    viewer_sessions = models.UserEvent.objects.filter(product_id=product_id, event_type=models.UserEvent.EventType.PRODUCT_VIEW).values_list('session_id', flat=True).distinct()
    
    if not viewer_sessions:
        return models.Product.objects.none()

    related_products = models.UserEvent.objects.filter(
        session_id__in=list(viewer_sessions),
        event_type=models.UserEvent.EventType.PRODUCT_VIEW
    ).exclude(
        product_id=product_id  
    ).values(
        'product_id'  
    ).annotate(
        relevance=Count('product_id')  
    ).order_by('-relevance') 
    
    # ۳. شناسه‌ها را استخراج کرده و محصولات نهایی را برمی‌گردانیم
    related_product_ids = [item['product_id'] for item in related_products[:limit]]
    
    # برای حفظ ترتیب ارتباط، باید به شکل خاصی کوئری بزنیم
    preserved_order = models.Case(*[models.When(pk=pk, then=pos) for pos, pk in enumerate(related_product_ids)])
    return models.Product.objects.filter(id__in=related_product_ids).order_by(preserved_order)