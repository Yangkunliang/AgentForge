"""测试认证端点"""

import pytest


def test_register_success(async_client):
    """POST /auth/register 返回 201 + user data"""
    resp = async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "read" in data["permissions"]


def test_register_duplicate_username(async_client, fake_user):
    """注册重复用户名返回 409"""
    resp = async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "StrongPass123",
        },
    )
    assert resp.status_code == 409


def test_register_duplicate_email(async_client, fake_user):
    """注册重复邮箱返回 409"""
    resp = async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "otheruser",
            "email": "test@example.com",
            "password": "StrongPass123",
        },
    )
    assert resp.status_code == 409


def test_register_invalid_password(async_client):
    """弱密码被拒绝"""
    resp = async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "weak",
        },
    )
    # 自定义验证错误处理器返回 400
    assert resp.status_code == 400


def test_login_success(async_client, fake_user):
    """POST /auth/login 返回 200 + access_token"""
    resp = async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "TestPass123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["username"] == "testuser"
    assert "refresh_token" in resp.cookies


def test_login_wrong_password(async_client, fake_user):
    """错误密码返回 401"""
    resp = async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword1",
        },
    )
    assert resp.status_code == 401
