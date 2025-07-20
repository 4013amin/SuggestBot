import requests
import logging
from decouple import config

from SuggestBot import settings

logger = logging.getLogger(__name__)

WEBONE_API_URL = "https://rest.payamakapi.ir/api/v1/SMS/Send"


def send_sms_Testi(phone_number: str, message: str) -> bool:
    if settings.DEBUG:
        print("Send SMS Testi")
        print(f"TO {phone_number}")
        print(message)
        print("END DEBUG")

    try:
        username = config('WEBONE_USERNAME')
        password = config('WEBONE_PASSWORD')
        sender_line = config('WEBONE_SENDER_LINE')
    except Exception:
        logger.critical("CRITICAL: SMS service environment variables are not defined on the server.")
        return False

    payload = {
        'UserName': username,
        'Password': password,
        'From': sender_line,
        'To': phone_number,
        'Message': message,
    }

    try:
        response = requests.post(WEBONE_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        response_data = response.json()

        status_value = response_data.get('Status')
        ret_status_value = response_data.get('RetStatus')

        if (status_value is True or str(status_value) == '1' or
                ret_status_value is True or str(ret_status_value) == '1'):
            logger.info(f"SMS sent successfully to {phone_number}. Response: {response_data}")
            return True
        else:
            error_message = response_data.get('Message', 'Unknown API error')
            logger.error(f"PayamakAPI Error for {phone_number}: {error_message}. Full Response: {response_data}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Network/HTTP error sending SMS to {phone_number}: {e}")
        return False
    except Exception as e:
        logger.critical(f"Unexpected error in send_sms for {phone_number}: {e}")
        return False
