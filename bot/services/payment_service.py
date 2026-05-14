import hashlib
from urllib.parse import urlencode
from bot.config import get_settings

class RobokassaService:
    @staticmethod
    def generate_payment_url(order_id: int, amount: int, description: str) -> str:
        settings = get_settings()
        
        login = settings.robokassa_merchant_login
        pass1 = settings.robokassa_pass1
        is_test = settings.robokassa_is_test
        
        # signature = md5(login:amount:order_id:pass1)
        signature_base = f"{login}:{amount}:{order_id}:{pass1}"
        signature = hashlib.md5(signature_base.encode()).hexdigest()
        
        params = {
            "MerchantLogin": login,
            "OutSum": amount,
            "InvId": order_id,
            "Description": description,
            "SignatureValue": signature,
        }
        
        if is_test:
            params["IsTest"] = 1
            
        base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
        return f"{base_url}?{urlencode(params)}"

    @staticmethod
    def verify_result_signature(amount: str, order_id: str, signature: str) -> bool:
        settings = get_settings()
        pass2 = settings.robokassa_pass2
        
        # signature = md5(amount:order_id:pass2)
        signature_base = f"{amount}:{order_id}:{pass2}"
        expected_signature = hashlib.md5(signature_base.encode()).hexdigest()
        
        return signature.lower() == expected_signature.lower()
