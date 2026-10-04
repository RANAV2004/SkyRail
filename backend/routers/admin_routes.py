from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..database import get_db
from ..auth import require_admin
from ..dijkstra import dijkstra, all_distances
from ..sample_data import estimated_time
from ..network import get_network
from .. import weather, route_planner, delay_model
from .user_routes import with_names

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(
    admin: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    return {
        "message": f"Welcome, {admin.username}",
        "total_users": len(crud.list_users(db)),
        "total_trains": len(get_network().trains),
        "total_stations": len(get_network().stations),
        "real_data": get_network().real,
        "total_tickets": len(crud.list_all_tickets(db)),
    }


@router.get("/users", response_model=List[schemas.UserAdminOut])
def view_users(
    admin: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    # FIXME UserAdminOut still sends the bcrypt hash, the page doesn't even use it
    return crud.list_users(db)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    data: schemas.AdminPasswordReset,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    crud.admin_set_password(db, user, data.new_password)
    return {"message": f"Password for {user.username} has been reset."}


@router.get("/tickets")
def view_all_tickets(
    admin: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    return with_names(crud.list_all_tickets(db))


@router.get("/tickets/export.csv")
def export_all_tickets_csv(
    admin: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Download every booking as a CSV file, tracked by user ID."""
    tickets = crud.list_all_tickets(db)
    username_by_id = {u.user_id: u.username for u in crud.list_users(db)}
    csv_text = crud.tickets_to_csv(tickets, username_by_id)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=all_bookings.csv"},
    )


@router.get("/cities")
def cities(admin: models.User = Depends(require_admin)):
    # biggest stations, used by the old charts
    return {"cities": [s["code"] for s in get_network().major(25)]}


@router.post("/shortest-route", response_model=schemas.RouteResult)
def shortest_route(
    req: schemas.RouteRequest, admin: models.User = Depends(require_admin)
):
    graph = get_network().graph
    cost, path = dijkstra(graph, req.source, req.destination)

    if cost == float("inf") or not path:

        return schemas.RouteResult(
            source=req.source,
            destination=req.destination,
            path=[],
            total_distance=0.0,
            estimated_time=0.0,
            hops=[],
        )

    hops = []
    for i in range(len(path) - 1):
        frm, to = path[i], path[i + 1]
        hops.append(schemas.RouteHop(frm=frm, to=to, distance=graph[frm][to]))

    return schemas.RouteResult(
        source=req.source,
        destination=req.destination,
        path=path,
        total_distance=round(cost, 2),
        estimated_time=estimated_time(cost),
        hops=hops,
    )


@router.get("/optimization-chart")
def optimization_chart(source: str, admin: models.User = Depends(require_admin)):
    """Data for the green-on-black scatter/line graph: distance & time from `source`
    to every other reachable city."""
    net = get_network()
    dist = all_distances(net.graph, source)
    # only the big stations, 4,700 points on a chart is unreadable
    major = {s["code"] for s in net.major(30)}
    points = []
    for city, d in sorted(dist.items(), key=lambda kv: kv[1]):
        if city == source or d == float("inf") or city not in major:
            continue
        points.append(
            {
                "city": net.name(city),
                "distance": round(d, 1),
                "time": estimated_time(d),
            }
        )
    return {"source": source, "points": points}


# weather routes (this is where CLOUDY got merged in)
@router.get("/network")
def rail_network(admin: models.User = Depends(require_admin)):
    return get_network().map_data()


@router.post("/weather-route")
def weather_route(
    req: schemas.WeatherRouteRequest, admin: models.User = Depends(require_admin)
):
    net = get_network()
    # the planner works station to station, so "city:Hyderabad" becomes its main station
    src = (net.resolve(req.source) or [None])[0]
    dst = (net.resolve(req.destination) or [None])[0]
    if src not in net.graph or dst not in net.graph:
        raise HTTPException(status_code=404, detail="Unknown station")
    if src == dst:
        raise HTTPException(
            status_code=400, detail="Source and destination must differ"
        )

    departure = req.departure or (datetime.now(weather.IST) + timedelta(hours=1))
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=weather.IST)  # treat form input as IST
    departure = departure.astimezone(weather.IST)
    return route_planner.plan(src, dst, departure, req.k)


@router.get("/weather/{code}")
def station_weather(code: str, admin: models.User = Depends(require_admin)):
    try:
        fc = weather.get_forecast(code)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown station")
    return {**fc, "risk": route_planner.assess_slot(fc["current"])}


@router.get("/weather-overview")
def weather_overview(admin: models.User = Depends(require_admin)):
    # for the admin dashboard
    net = get_network()
    data = weather.get_forecasts([s["code"] for s in net.major(20)])
    out = []
    for code, fc in data.items():
        now = fc["current"]
        out.append(
            {
                "code": code,
                "city": fc["city"],
                "lat": fc["lat"],
                "lon": fc["lon"],
                "current": now,
                "trains": net.stations[code]["trains"],
                "risk": route_planner.assess_slot(now),
            }
        )
    return {
        "weather_source": weather.source_label(data),
        "cache": weather.cache_stats(),
        "stations": out,
    }


@router.get("/model")
def model_report(admin: models.User = Depends(require_admin)):
    m = delay_model.metrics()
    if not m:
        return {"trained": False}
    return {"trained": True, "in_use": delay_model.get_model() is not None, **m}
