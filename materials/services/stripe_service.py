import stripe
from django.conf import settings
from django.core.exceptions import ValidationError

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    @staticmethod
    def create_product(name, description=None, metadata=None):
        """
        Создание продукта в Stripe
        https://stripe.com/docs/api/products/create
        """
        try:
            product = stripe.Product.create(
                name=name,
                description=description,
                metadata=metadata or {}
            )
            return product
        except stripe.error.StripeError as e:
            raise ValidationError(f"Ошибка создания продукта в Stripe: {str(e)}")

    @staticmethod
    def create_price(product_id, unit_amount, currency='usd', recurring=None):
        """
        Создание цены в Stripe
        https://stripe.com/docs/api/prices/create
        """
        try:
            price_data = {
                'product': product_id,
                'unit_amount': int(unit_amount * 100),  # Конвертируем в центы
                'currency': currency,
            }

            if recurring:
                price_data['recurring'] = recurring

            price = stripe.Price.create(**price_data)
            return price
        except stripe.error.StripeError as e:
            raise ValidationError(f"Ошибка создания цены в Stripe: {str(e)}")

    @staticmethod
    def create_checkout_session(price_id, success_url, cancel_url, metadata=None):
        """
        Создание сессии для получения ссылки на оплату
        https://stripe.com/docs/api/checkout/sessions/create
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            return session
        except stripe.error.StripeError as e:
            raise ValidationError(f"Ошибка создания сессии оплаты: {str(e)}")

    @staticmethod
    def retrieve_session(session_id):
        """
        Получение информации о сессии
        """
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            raise ValidationError(f"Ошибка получения сессии: {str(e)}")

    @staticmethod
    def create_product_with_price(name, description, amount, currency='usd'):
        """
        Упрощенный метод: создает продукт и цену за один вызов
        """
        product = StripeService.create_product(name, description)
        price = StripeService.create_price(product.id, amount, currency)

        return {
            'product': product,
            'price': price
        }