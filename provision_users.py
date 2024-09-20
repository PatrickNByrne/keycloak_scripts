#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) 2024 Patrick Byrne

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import csv
import tomllib

import requests


def load_config():
    """Load the toml format config file and return it as a dict"""
    with open("config.toml", "rb") as toml_file:
        conf_data = tomllib.load(toml_file)
    return conf_data


def load_users():
    """Read the CSV formatted user list and return a list of dicts"""
    users = []
    with open("users.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for user in reader:
            user["Groups"] = user["Groups"].split(",")
            users.append(user)
    return users


def get_token(keycloak_root, keycloak_realm, keycloak_admin, keycloak_admin_password):
    """Retrieve an access token from our Keycloak instance and return it as a string."""
    print("Getting access token...")
    resp = requests.post(
        f"{keycloak_root}/realms/{keycloak_realm}/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": keycloak_admin,
            "password": keycloak_admin_password,
            "grant_type": "password",
        },
        timeout=10,
    )

    resp.raise_for_status()
    data = resp.json()
    access_token = data["access_token"]

    print(
        "Token",
        f"{access_token[:20]}...{access_token[-20:]}",
        f"Expires in {data['expires_in']}s",
    )

    return access_token


def check_user(keycloak_root, keycloak_realm, token, user_name):
    """Check if a user exists and return a bool (True if user exists)."""
    print("Checking if", user_name, "exists")

    auth_headers = {
        "Authorization": f"Bearer {token}",
    }

    resp = requests.get(
        f"{keycloak_root}/admin/realms/{keycloak_realm}/users/count/?q=username:{user_name}",
        json={},
        headers=auth_headers,
        timeout=10,
    )

    resp.raise_for_status()

    # Check our count and return the appropriate bool
    user_count = resp.json()
    if user_count == 0:
        print("User not found")
        return False
    print("User found")
    return True


def create_user(keycloak_root, keycloak_realm, token, user):
    """Create the keycloak user."""
    print(
        "Creating user:", user["First Name"], user["Last Name"], "-", user["User Name"]
    )
    # Predefine authorization headers for later use.
    auth_headers = {
        "Authorization": f"Bearer {token}",
    }

    user_settings = {
        "firstName": user["First Name"],
        "lastName": user["Last Name"],
        "username": user["User Name"],
        "email": user["Email"],
        "groups": user["Groups"],
        "enabled": True,
    }

    resp = requests.post(
        f"{keycloak_root}/admin/realms/{keycloak_realm}/users",
        json=user_settings,
        headers=auth_headers,
        timeout=10,
    )

    resp.raise_for_status()
    location = resp.headers["Location"]
    user_id = location.split("/")[-1]
    print("Created user id:", user_id)
    return user_id


def reset_user_password(keycloak_root, keycloak_realm, token, user_id):
    """Execute a keycloak action to send a password reset email for a user account."""
    print("Sending password reset email for", user_id)

    auth_headers = {
        "Authorization": f"Bearer {token}",
    }

    resp = requests.put(
        f"{keycloak_root}/admin/realms/{keycloak_realm}/users/{user_id}/execute-actions-email",
        json=["UPDATE_PASSWORD"],
        headers=auth_headers,
        timeout=10,
    )

    resp.raise_for_status()


def main():
    """Script entry point."""
    config = load_config()
    users = load_users()
    token = get_token(**config)
    for user in users:
        if not check_user(
            config["keycloak_root"], config["keycloak_realm"], token, user["User Name"]
        ):
            user_id = create_user(
                config["keycloak_root"], config["keycloak_realm"], token, user
            )
            reset_user_password(
                config["keycloak_root"], config["keycloak_realm"], token, user_id
            )


if __name__ == "__main__":
    main()
