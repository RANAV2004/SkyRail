

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
FAR_AHEAD = (date.today() + timedelta(days=60)).isoformat()  # past the 5 day forecast
PAST = "2020-01-01"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def sign_up(client, username, password="secret12", **extra):
    """register + verify the OTP + log in, returns the token"""
    body = {
        "username": username,
        "full_name": username.title(),
        "email": f"{username}@example.com",
        "password": password,
        **extra,
    }
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    otp = r.json()["dev_otp"]
    client.post("/auth/verify-otp", json={"email": body["email"], "otp": otp})
    return login(client, username, password).json()["access_token"]


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # "with" runs startup, which seeds trains and the admin
        yield c


@pytest.fixture(scope="module")
def admin(client):
    r = login(client, "admin", "admin123")
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def asha(client):
    return sign_up(client, "asha")


@pytest.fixture(scope="module")
def ravi(client):
    return sign_up(client, "ravi")


def search(
    client, token, source="Hyderabad", destination="Kolkata", travel_date=TOMORROW
):
    return client.get(
        "/user/train-search",
        headers=auth(token),
        params={
            "source": source,
            "destination": destination,
            "travel_date": travel_date,
        },
    )


# ---------- sign-up and login


def test_cant_log_in_before_verifying_email(client):
    r = client.post(
        "/auth/register",
        json={
            "username": "meena",
            "email": "meena@example.com",
            "password": "secret12",
        },
    )
    assert r.status_code == 201
    assert login(client, "meena", "secret12").status_code == 403


def test_wrong_otp_is_rejected_and_right_one_works(client):
    r = client.post(
        "/auth/register",
        json={
            "username": "kiran",
            "email": "kiran@example.com",
            "password": "secret12",
        },
    )
    otp = r.json()["dev_otp"]
    wrong = "000000" if otp != "000000" else "111111"
    assert (
        client.post(
            "/auth/verify-otp", json={"email": "kiran@example.com", "otp": wrong}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/auth/verify-otp", json={"email": "kiran@example.com", "otp": otp}
        ).status_code
        == 200
    )
    assert login(client, "kiran", "secret12").status_code == 200


def test_wrong_password(client, asha):
    assert login(client, "asha", "wrongpass").status_code == 401


def test_duplicate_username(client, asha):
    r = client.post(
        "/auth/register",
        json={"username": "asha", "email": "other@example.com", "password": "secret12"},
    )
    assert r.status_code == 400


def test_bad_email(client):
    r = client.post(
        "/auth/register",
        json={"username": "zed", "email": "not-an-email", "password": "secret12"},
    )
    assert r.status_code == 422


@pytest.mark.xfail(
    strict=True, reason="known hole: no minimum password length at sign-up"
)
def test_very_short_password_is_rejected(client):
    r = client.post(
        "/auth/register",
        json={"username": "shorty", "email": "shorty@example.com", "password": "1"},
    )
    assert r.status_code == 422


def test_sign_up_cant_create_an_admin(client):
    # the page has no role option any more, but someone could still send it to the API
    sign_up(client, "mallory", role="admin")
    r = login(client, "mallory", "secret12")
    assert r.json()["role"] == "user"
    assert (
        client.get("/admin/users", headers=auth(r.json()["access_token"])).status_code
        == 403
    )


@pytest.mark.xfail(strict=True, reason="known hole: unlimited OTP guesses")
def test_otp_guessing_is_limited(client):
    client.post(
        "/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "secret12"},
    )
    codes = [
        client.post(
            "/auth/verify-otp", json={"email": "bob@example.com", "otp": f"{i:06d}"}
        ).status_code
        for i in range(30)
    ]
    assert 429 in codes


# ---------- who can see what


def test_admin_api_needs_a_token(client):
    assert client.get("/admin/users").status_code == 401


def test_forged_token(client):
    assert client.get("/admin/users", headers=auth("abc.def.ghi")).status_code == 401


def test_passenger_cant_use_admin_api(client, asha):
    assert client.get("/admin/users", headers=auth(asha)).status_code == 403
    r = client.post(
        "/admin/weather-route",
        headers=auth(asha),
        json={"source": "Hyderabad", "destination": "Kolkata"},
    )
    assert r.status_code == 403


def test_admin_sees_name_username_and_email(client, admin, asha):
    users = client.get("/admin/users", headers=auth(admin)).json()
    row = next(u for u in users if u["username"] == "asha")
    assert row["full_name"] == "Asha" and row["email"] == "asha@example.com"


@pytest.mark.xfail(
    strict=True,
    reason="known hole: /admin/users sends the bcrypt hashes to the browser",
)
def test_admin_api_doesnt_send_password_hashes(client, admin):
    users = client.get("/admin/users", headers=auth(admin)).json()
    assert "password" not in users[0]


@pytest.mark.xfail(
    strict=True, reason="known hole: CORS allows every origin by default"
)
def test_cors_doesnt_allow_any_website(client):
    r = client.options(
        "/user/trains",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") not in (
        "*",
        "https://evil.example",
    )


# ---------- passenger train search


def test_search_returns_trains_best_first(client, asha):
    r = search(client, asha)
    assert r.status_code == 200
    res = r.json()["results"]
    assert len(res) >= 2
    adjusted = [t["adjusted_minutes"] for t in res]
    assert adjusted == sorted(adjusted)
    assert [t["rank"] for t in res] == list(range(1, len(res) + 1))
    for t in res:
        assert (t["board"], t["alight"]) == ("Hyderabad", "Kolkata")


def test_search_rejects_bad_input(client, asha):
    assert search(client, asha, "Kolkata", "Kolkata").status_code == 400
    assert search(client, asha, "Atlantis", "Kolkata").status_code == 404
    assert search(client, asha, travel_date="banana").status_code == 422


def test_no_direct_train_gives_empty_list(client, asha):
    r = search(client, asha, "Chennai", "Pune")
    assert r.status_code == 200 and r.json()["results"] == []


def test_past_trip_is_marked_completed(client, asha):
    res = search(client, asha, travel_date=PAST).json()["results"]
    assert res and all(t["status"] == "completed" for t in res)


def test_trip_too_far_ahead_has_no_made_up_forecast(client, asha):
    res = search(client, asha, travel_date=FAR_AHEAD).json()["results"]
    assert res
    for t in res:
        assert not t["available"]
        assert all(s["forecast"] is None for s in t["stops"])


def test_demo_weather_is_labelled(client, asha):
    assert search(client, asha).json()["weather_source"] == "demo"


# ---------- admin route planner


def test_planner_recommends_the_route_that_arrives_first(client, admin):
    r = client.post(
        "/admin/weather-route",
        headers=auth(admin),
        json={
            "source": "Hyderabad",
            "destination": "Kolkata",
            "departure": f"{TOMORROW}T09:00",
            "k": 4,
        },
    )
    assert r.status_code == 200
    d = r.json()
    best = d["routes"][d["recommended_index"]]
    assert best["adjusted_minutes"] == min(x["adjusted_minutes"] for x in d["routes"])
    assert d["reasons"]


@pytest.mark.parametrize("k", [0, 7])
def test_planner_rejects_silly_k(client, admin, k):
    r = client.post(
        "/admin/weather-route",
        headers=auth(admin),
        json={"source": "Hyderabad", "destination": "Kolkata", "k": k},
    )
    assert r.status_code == 422


def test_planner_unknown_station(client, admin):
    r = client.post(
        "/admin/weather-route",
        headers=auth(admin),
        json={"source": "Atlantis", "destination": "Kolkata"},
    )
    assert r.status_code == 404


# ---------- saved trips


def save(
    client, token, train=12703, source="Hyderabad", destination="Kolkata", day=TOMORROW
):
    return client.post(
        "/user/tickets",
        headers=auth(token),
        json={
            "train_number": train,
            "source": source,
            "destination": destination,
            "booking_date": day,
        },
    )


def test_save_trip_and_get_its_forecast(client, asha):
    r = save(client, asha)
    assert r.status_code == 201
    tid = r.json()["ticket_id"]
    mine = client.get("/user/tickets", headers=auth(asha)).json()
    assert any(t["ticket_id"] == tid and t["train_name"] for t in mine)
    fc = client.get(f"/user/tickets/{tid}/forecast", headers=auth(asha))
    assert fc.status_code == 200 and fc.json()["stops"]


def test_same_train_same_day_cant_be_saved_twice(client, asha):
    save(client, asha, day=FAR_AHEAD)
    assert save(client, asha, day=FAR_AHEAD).status_code == 400


def test_bad_trips_are_rejected(client, asha):
    assert (
        save(client, asha, source="Kolkata", destination="Hyderabad").status_code == 400
    )  # wrong direction
    assert save(client, asha, train=99999).status_code == 404
    assert save(client, asha, day="not-a-date").status_code == 422
    assert save(client, asha, day="2026-13-40").status_code == 422


def test_other_people_cant_see_or_delete_my_trip(client, asha, ravi):
    tid = save(client, asha, train=12129).json()["ticket_id"]
    assert (
        client.get(f"/user/tickets/{tid}/forecast", headers=auth(ravi)).status_code
        == 404
    )
    assert client.delete(f"/user/tickets/{tid}", headers=auth(ravi)).status_code == 404
    assert all(
        t["ticket_id"] != tid
        for t in client.get("/user/tickets", headers=auth(ravi)).json()
    )
    # and it's still there for asha
    assert (
        client.get(f"/user/tickets/{tid}/forecast", headers=auth(asha)).status_code
        == 200
    )


# ---------- admin password reset


def test_admin_password_reset(client, admin):
    sign_up(client, "nisha")
    uid = next(
        u["user_id"]
        for u in client.get("/admin/users", headers=auth(admin)).json()
        if u["username"] == "nisha"
    )
    url = f"/admin/users/{uid}/reset-password"

    assert (
        client.post(url, headers=auth(admin), json={"new_password": "abc"}).status_code
        == 422
    )
    assert (
        client.post(
            url, headers=auth(admin), json={"new_password": "brandnew1"}
        ).status_code
        == 200
    )
    assert login(client, "nisha", "secret12").status_code == 401
    assert login(client, "nisha", "brandnew1").status_code == 200


def test_reset_unknown_user(client, admin):
    r = client.post(
        "/admin/users/99999/reset-password",
        headers=auth(admin),
        json={"new_password": "brandnew1"},
    )
    assert r.status_code == 404


def test_passenger_cant_reset_passwords(client, asha, ravi):
    users_url = "/admin/users/1/reset-password"
    r = client.post(users_url, headers=auth(ravi), json={"new_password": "hacked123"})
    assert r.status_code == 403
