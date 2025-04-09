#!/usr/bin/env python3
"""
Script to check Django settings for the authentication configuration.
"""
import os
import sys
import importlib.util

def check_settings():
    # Add the api directory to the Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
    
    try:
        # Try to import settings module
        from mcg import settings
        
        print("=== Django Settings Check ===")
        
        # Check if REST_FRAMEWORK is defined
        if hasattr(settings, 'REST_FRAMEWORK'):
            print("REST_FRAMEWORK settings found.")
            rest_settings = settings.REST_FRAMEWORK
            
            # Check authentication classes
            auth_classes = rest_settings.get('DEFAULT_AUTHENTICATION_CLASSES', [])
            print(f"Authentication classes: {auth_classes}")
            
            # Check if our class is in the list
            if 'api.authentication.SupabaseAuthentication' in auth_classes:
                print("SUCCESS: SupabaseAuthentication is configured in settings.")
            else:
                print("ERROR: SupabaseAuthentication not found in authentication classes.")
        else:
            print("ERROR: REST_FRAMEWORK settings not found.")
        
        # Check if auth module exists
        auth_path = os.path.join(os.path.dirname(__file__), 'api', 'authentication.py')
        if os.path.exists(auth_path):
            print(f"Authentication module exists at: {auth_path}")
            
            try:
                # Try to import the module
                spec = importlib.util.spec_from_file_location("authentication", auth_path)
                auth_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(auth_module)
                
                # Check if SupabaseAuthentication exists in the module
                if hasattr(auth_module, 'SupabaseAuthentication'):
                    print("SUCCESS: SupabaseAuthentication class found in authentication module.")
                else:
                    print("ERROR: SupabaseAuthentication class not found in authentication module.")
            except Exception as e:
                print(f"ERROR importing authentication module: {str(e)}")
        else:
            print(f"ERROR: Authentication module not found at: {auth_path}")
    
    except ImportError as e:
        print(f"ERROR: Could not import Django settings: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    check_settings() 