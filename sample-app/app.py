"""Sample app — demonstrates the full identity → payment flow using the Python SDK."""

from elcorp_sdk import ElcorpClient


def main():
    base = input("API base URL [http://localhost:5000/api/v1]: ").strip()
    if not base:
        base = "http://localhost:5000/api/v1"

    client = ElcorpClient(base_url=base)

    print("\n--- 1. Sign Up ---")
    auth = client.signup(
        email="demo@elcorp.na",
        password="Demo1234!",
        first_name="Demo",
        last_name="User",
    )
    print(f"User ID : {auth['user']['id']}")
    print(f"Verified: {auth['user']['is_verified']}")

    print("\n--- 2. Upload KYC (national ID) ---")
    # Create a tiny placeholder file for the demo
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(b"FAKE_PNG_DATA_FOR_DEMO")
    tmp.close()
    try:
        doc = client.upload_kyc("national_id", tmp.name)
        print(f"Document ID: {doc['id']}  Status: {doc['status']}")
    finally:
        os.unlink(tmp.name)

    print("\n--- 3. Check profile ---")
    me = client.get_me()
    print(f"Verification status: {me['verification_status']}")

    print("\n--- 4. Create payment (requires a merchant — use admin to onboard one first) ---")
    merchant_id = input("Merchant ID (leave blank to skip): ").strip()
    if merchant_id:
        payment = client.create_payment(
            merchant_id=merchant_id,
            amount=7500,
            currency="NAD",
            description="Sample clinic payment",
        )
        print(f"Payment ID : {payment['id']}")
        print(f"Reference  : {payment['reference']}")
        print(f"Status     : {payment['status']}")

        print("\n--- 5. Process payment ---")
        result = client.process_payment(payment["id"])
        print(f"Status     : {result['status']}")
        print(f"Gateway ref: {result['gateway_ref']}")
    else:
        print("Skipped payment demo.")

    print("\nDone!")


if __name__ == "__main__":
    main()
