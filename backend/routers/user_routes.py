from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..database import get_db
from ..auth import get_current_user
from .. import route_planner
from ..cities import CITIES, city_matches
from ..network import get_network

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/trains")
def view_trains(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _: models.User = Depends(get_current_user),
):
    # timetable page. 3,900 trains so it's searched + paged
    net = get_network()
    trains = sorted(net.trains.values(), key=lambda t: t["number"])
    if q:
        ql = q.strip().lower()
        trains = [
            t
            for t in trains
            if ql in t["name"].lower()
            or ql in str(t["number"])
            or any(
                ql == s["code"].lower() or ql in net.name(s["code"]).lower()
                for s in t["stops"]
            )
        ]
    page = trains[offset : offset + min(limit, 200)]
    return {
        "total": len(trains),
        "trains": [
            {
                "train_number": t["number"],
                "train_name": t["name"],
                "type": t["type"],
                "source": t["source"],
                "destination": t["destination"],
                "source_name": net.name(t["source"]),
                "destination_name": net.name(t["destination"]),
                "departure": t["departure"],
                "arrival": t["arrival"],
                "duration_minutes": t["duration_min"],
                "distance_km": t["distance_km"],
                "stops": len(t["stops"]),
                "run_days": t["run_days"],
            }
            for t in page
        ],
    }


@router.get("/stations")
def station_search(q: str, _: models.User = Depends(get_current_user)):
    # cities first ("Hyderabad - all stations"), then single stations
    net = get_network()
    out = []
    for city in city_matches(q):
        codes = [c for c in CITIES[city] if c in net.stations]
        if codes:
            out.append(
                {
                    "value": f"city:{city}",
                    "label": f"{city} (all stations)",
                    "detail": ", ".join(codes),
                    "kind": "city",
                }
            )
    for s in net.search(q, 10 - len(out)):
        out.append(
            {
                "value": s["code"],
                "label": s["name"],
                "detail": s["code"],
                "kind": "station",
                "trains": s["trains"],
            }
        )
    return out


@router.post("/tickets", response_model=schemas.TicketOut, status_code=201)
def book_ticket(
    ticket: schemas.TicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    train = get_network().trains.get(ticket.train_number)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    stops = [s["code"] for s in train["stops"]]
    if (
        ticket.source not in stops
        or ticket.destination not in stops
        or stops.index(ticket.source) >= stops.index(ticket.destination)
    ):
        raise HTTPException(
            status_code=400,
            detail=f"{train['name']} doesn't run {ticket.source} to {ticket.destination}",
        )
    for t in crud.list_tickets_for_user(db, current_user.user_id):
        if (
            t.status == "CONFIRMED"
            and t.train_number == ticket.train_number
            and t.booking_date == ticket.booking_date
        ):
            raise HTTPException(
                status_code=400, detail="You already saved this train for that day"
            )
    return crud.book_ticket(db, current_user.user_id, ticket)


@router.get("/tickets")
def my_tickets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # add names so the page doesn't need the whole network
    return with_names(crud.list_tickets_for_user(db, current_user.user_id))


def with_names(tickets):
    net = get_network()
    out = []
    for t in tickets:
        row = schemas.TicketOut.model_validate(t).model_dump()
        train = net.trains.get(t.train_number)
        row.update(
            train_name=train["name"] if train else None,
            source_name=net.name(t.source),
            destination_name=net.name(t.destination),
        )
        out.append(row)
    return out


@router.get("/tickets/export.csv")
def export_my_tickets_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download the current user's bookings as a CSV file."""
    tickets = crud.list_tickets_for_user(db, current_user.user_id)
    csv_text = crud.tickets_to_csv(
        tickets, {current_user.user_id: current_user.username}
    )
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_bookings.csv"},
    )


@router.put("/tickets/{ticket_id}/reschedule", response_model=schemas.TicketOut)
def reschedule(
    ticket_id: int,
    data: schemas.TicketReschedule,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status == "CANCELLED":
        raise HTTPException(
            status_code=400, detail="Cannot reschedule a cancelled ticket"
        )
    return crud.reschedule_ticket(db, ticket, data)


@router.delete("/tickets/{ticket_id}", response_model=schemas.TicketOut)
def cancel(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return crud.cancel_ticket(db, ticket)


# journey weather for passengers
@router.get("/network")
def rail_network(_: models.User = Depends(get_current_user)):
    return get_network().map_data()


@router.get("/train-search")
def train_search(
    source: str,
    destination: str,
    travel_date: date,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    net = get_network()
    sources, dests = net.resolve(source), net.resolve(destination)
    if not sources or not dests:
        raise HTTPException(status_code=404, detail="Unknown station")
    if set(sources) & set(dests):
        raise HTTPException(status_code=400, detail="Pick two different stations")
    results = route_planner.search_trains(sources, dests, travel_date)
    return {
        "source": source,
        "destination": destination,
        "source_name": net.label(source),
        "destination_name": net.label(destination),
        "travel_date": travel_date.isoformat(),
        "results": results,
        "weather_source": results[0]["weather_source"] if results else None,
    }


@router.get("/journey-forecast")
def journey_forecast(
    train_number: int,
    travel_date: date,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    train = get_network().trains.get(train_number)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    return route_planner.train_journey(train, travel_date, source, destination)


@router.get("/tickets/{ticket_id}/forecast")
def ticket_forecast(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    train = get_network().trains.get(ticket.train_number)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    try:
        travel = date.fromisoformat(ticket.booking_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ticket has an invalid travel date")
    return route_planner.train_journey(train, travel, ticket.source, ticket.destination)
