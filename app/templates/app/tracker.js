// Smart Analyzer Script v1.0

(function() {
    // ------------------- CONFIGURATION -------------------
    // مشتری شما فقط این بخش را ویرایش می‌کند
    const config = {
        apiKey: 'KLID-API-MONHASER-BE-FARD-MOSHTARI', // کلید API اختصاصی هر مشتری
        analyzerServerUrl: 'https://your-analyzer-app.com/api/v2/track-product/' // آدرس API سرور جنگوی شما
    };
    // -----------------------------------------------------

    // تابع برای استخراج داده‌های محصول از صفحه
    function getProductData() {
        try {
            // این بخش چالش‌برانگیزترین قسمت است، چون ساختار HTML سایت‌ها متفاوت است.
            // ما از سلکتورهای رایج استفاده می‌کنیم.
            const productName = document.querySelector('h1.product_title, h1.product-title, h1[itemprop="name"]');
            const productPrice = document.querySelector('.price .amount, .product-price, span[itemprop="price"]');

            if (!productName || !productPrice) {
                // اگر در صفحه‌ای هستیم که محصول ندارد، کاری انجام نده
                return null;
            }

            // پاک‌سازی داده‌ها
            const name = productName.innerText.trim();
            // استخراج عدد از قیمت (حذف واحد پول و جداکننده‌ها)
            const price = productPrice.innerText.match(/[\d,.]+/g).join('');

            return {
                name: name,
                price: parseFloat(price.replace(/,/g, '')),
                url: window.location.href // آدرس صفحه‌ای که بازدید شده
            };
        } catch (error) {
            console.error("Smart Analyzer: Error extracting product data.", error);
            return null;
        }
    }

    // تابع برای ارسال داده‌ها به سرور
    async function sendData(data) {
        try {
            const response = await fetch(config.analyzerServerUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': config.apiKey // ارسال کلید در هدر
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                console.log("Smart Analyzer: Product view tracked successfully.");
            } else {
                console.error("Smart Analyzer: Failed to track data. Server responded with:", response.status);
            }
        } catch (error) {
            console.error("Smart Analyzer: Network error while sending data.", error);
        }
    }

    // وقتی صفحه به طور کامل بارگذاری شد، اسکریپت را اجرا کن
    window.addEventListener('load', () => {
        const productData = getProductData();
        if (productData) {
            console.log("Smart Analyzer: Found product data:", productData);
            sendData(productData);
        }
    });

})();