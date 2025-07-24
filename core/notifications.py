from django.conf import settings
import requests
import logging
from decouple import config

logger = logging.getLogger(__name__)

WEBONE_API_URL = "https://rest.payamakapi.ir/api/v1/SMS/Send"


def send_sms(phone_number: str, message: str) -> bool:
    if settings.DEBUG:
        logger.info("--- START SMS DEBUG (DEBUG=True) ---")
        logger.info(f"To: {phone_number}")
        logger.info(f"Message: {message}")
        logger.info("--- END SMS DEBUG ---")
        return True

    try:
        username = config("USERNAME")
        password = config("PASSWORD")
        sender_line = config("SMSSENDERLINE")

    except Exception as e:
        logger.critical(f"CRITICAL: SMS service environment variables are not defined! Error: {e}")
        return False

    normalized_phone = phone_number
    if phone_number.startswith('0'):
        normalized_phone = '+98' + phone_number[1:]
    elif not phone_number.startswith('+98'):
        normalized_phone = '+98' + phone_number

    payload = {
        'UserName': username,
        'Password': password,
        'From': sender_line,
        'To': normalized_phone,
        'Message': message,
    }

    logger.info(f"Attempting to send SMS to {normalized_phone} via PayamakAPI...")
    logger.debug(f"Sending payload to PayamakAPI: {payload}")

    try:
        # Send request to PayamakAPI
        response = requests.post(WEBONE_API_URL, json=payload, timeout=20)
        logger.debug(f"Full API response: {response.text}")
        response.raise_for_status()  # Raise exception for non-2xx status codes
        response_data = response.json()

        # Check API response
        status_value = response_data.get('Status')
        ret_status_value = response_data.get('RetStatus')
        message_id = response_data.get('Id')

        # Validate success based on Status or RetStatus
        if (status_value is True or str(status_value) == '1' or
                ret_status_value is True or str(ret_status_value) == '1'):
            logger.info(
                f"SMS sent successfully to {normalized_phone}. Message ID: {message_id}. Response: {response_data}")
            return True
        else:
            error_message = response_data.get('Message', 'Unknown API error')
            logger.error(
                f"PayamakAPI returned an error for {normalized_phone}: {error_message}. Full Response: {response_data}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error sending SMS to {normalized_phone}.")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error sending SMS to {normalized_phone}.")
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for {normalized_phone}: {e.response.status_code}. Body: {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"A generic network error occurred for {normalized_phone}: {e}")
        return False
    except ValueError as e:
        logger.error(f"Invalid JSON response from PayamakAPI for {normalized_phone}: {e}. Response: {response.text}")
        return False
    except Exception as e:
        logger.critical(f"An unexpected critical error in send_sms for {normalized_phone}: {e}")
        return False