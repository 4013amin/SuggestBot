from woocommerce import API
import logging


class WooCommerceService:
    def __init__(self, store):
        # با گرفتن آبجکت Store، به تمام اطلاعات اتصال دسترسی پیدا می‌کنیم.
        self.store = store
        self.api = API(
            url=store.site_url,
            consumer_key=store.woocommerce_consumer_key,
            consumer_secret=store.woocommerce_consumer_secret,
            version="wc/v3",
            timeout=20
        )

    def _fetch_all_paginated(self, endpoint, params=None):
