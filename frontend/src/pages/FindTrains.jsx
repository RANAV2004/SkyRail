import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import api from "../api";
import TrainSearch from "../components/TrainSearch.jsx";

export default function FindTrains() {
  const params = new URLSearchParams(useLocation().search);
  const [network, setNetwork] = useState(null);

  useEffect(() => {
    api
      .get("/user/network")
      .then((r) => setNetwork(r.data))
      .catch(() => {});
  }, []);

  // ?from=SC&fromName=Secunderabad&to=HWH from the timetable page
  const station = (key) =>
    params.get(key) && {
      value: params.get(key),
      label: params.get(key + "Name") || params.get(key),
    };
  const initial = {
    from: station("from"),
    to: station("to"),
    date: params.get("date"),
  };

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Find trains</div>
          <h1 className="page-title">Where are you going?</h1>
          <p className="page-sub">
            Trains are sorted by journey time plus the delay we expect, so the
            train most likely to get you there first is on top. The delay comes
            from a model trained on a month of real running data. Booking is
            done on IRCTC.
          </p>
        </div>
      </div>
      <TrainSearch initial={initial} network={network} />
    </div>
  );
}
