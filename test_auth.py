#!/usr/bin/env python3
"""
Test script for authentication system (enhanced diagnostic)
"""

import sys
import os
sys.path.append('.')

# Set environment variables for testing
os.environ['FLASK_ENV'] = 'development'

try:
    from app import app, fallback_users, supabase_client
    print("✅ App imported successfully")

    # New diagnostic flow: use Flask test client to sign up and then login
    with app.app_context():
        print(f"USE_SUPABASE: {app.config.get('USE_SUPABASE', True)}")
        print(f"Supabase client present: {supabase_client is not None}")
        print(f"Initial fallback users count: {len(fallback_users)}")
        # Basic sanity: check for secret key (session persistence requires this)
        print(f"app.secret_key set: {bool(app.secret_key)}")

        client = app.test_client()

        # Test credentials
        test_email = "test_user_debug@example.com"
        test_password = "TestPassword123!"

        # 1) Attempt signup (POST)
        print("\n--- Attempting signup ---")
        signup_resp = client.post('/signup', data={
            'email': test_email,
            'password': test_password,
            'confirm_password': test_password  # include if your form expects it
        }, follow_redirects=False)
        print(f"Signup status: {signup_resp.status_code}")
        print(f"Signup headers: {dict(signup_resp.headers)}")
        body_snippet = signup_resp.get_data(as_text=True)[:600]
        print(f"Signup body (snippet):\n{body_snippet!r}")

        # If signup redirected, show target
        if 300 <= signup_resp.status_code < 400:
            print("Signup redirected to:", signup_resp.headers.get('Location'))

        # Check fallback users after signup
        print(f"Fallback users count after signup: {len(fallback_users)}")
        for u in fallback_users:
            if u.get('email') == test_email:
                print("Found fallback user entry:", {k: v for k, v in u.items() if k != 'password'})
                break

        # 2) Attempt login (POST)
        print("\n--- Attempting login ---")
        login_resp = client.post('/login', data={
            'email': test_email,
            'password': test_password
        }, follow_redirects=False)
        print(f"Login status: {login_resp.status_code}")
        print(f"Login headers: {dict(login_resp.headers)}")
        login_body_snippet = login_resp.get_data(as_text=True)[:600]
        print(f"Login body (snippet):\n{login_body_snippet!r}")

        # If login redirected, show target
        if 300 <= login_resp.status_code < 400:
            print("Login redirected to:", login_resp.headers.get('Location'))

        # Show Set-Cookie header (session cookie)
        set_cookie = login_resp.headers.get('Set-Cookie')
        print(f"Login Set-Cookie header: {set_cookie!r}")

        # Inspect Flask session after login (if any)
        try:
            with client.session_transaction() as sess:
                print("Session contents after login:", dict(sess))
        except Exception as e_sess:
            print("Could not read session_transaction():", e_sess)

        # 3) Follow redirect (if any) and check final page content & session cookie persistence
        if 300 <= login_resp.status_code < 400 and login_resp.headers.get('Location'):
            follow = client.get(login_resp.headers.get('Location'))
            print("Follow redirect status:", follow.status_code)
            print("Follow body snippet:", follow.get_data(as_text=True)[:400])

        print("\n✅ Diagnostic complete. Use the info above to identify why login did not establish a session.")

    print("\n🎉 Authentication diagnostic finished.")
    print("If login failed, check:")
    print(" - app.secret_key is set so Flask sessions persist")
    print(" - /login expects field names 'email'/'password' (or adjust test to match)")
    print(" - password hashing/verification matches between signup and login")
    print(" - USE_SUPABASE setting and Supabase client availability")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()