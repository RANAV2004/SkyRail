import { useEffect, useRef, useState } from "react";
import api from "../api";

// a <select> with 4,700 stations was unusable
export default function StationPicker({
  id,
  label,
  value,
  onChange,
  cities = true,
  placeholder = "City, station or code",
}) {
  const [text, setText] = useState(value?.label || "");
  const [options, setOptions] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef(null);

  // parent can change the value (swap button), keep the text in sync
  useEffect(() => setText(value?.label || ""), [value]);

  useEffect(() => {
    if (!open || text.trim().length < 2) {
      setOptions([]);
      return;
    }
    // wait until the user stops typing for a moment
    const t = setTimeout(() => {
      api
        .get("/user/stations", { params: { q: text.trim() } })
        .then((r) => {
          setOptions(cities ? r.data : r.data.filter((o) => o.kind !== "city"));
          setActive(0);
        })
        .catch(() => setOptions([]));
    }, 200);
    return () => clearTimeout(t);
  }, [text, open, cities]);

  useEffect(() => {
    function close(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) {
        setOpen(false);
        setText(value?.label || "");
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [value]);

  function choose(o) {
    const name =
      o.kind === "city" ? o.label.replace(" (all stations)", "") : o.label;
    onChange({ value: o.value, label: name });
    setText(name);
    setOpen(false);
  }

  function onKey(e) {
    if (!open || !options.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, options.length - 1));
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    }
    if (e.key === "Enter") {
      e.preventDefault();
      choose(options[active]);
    }
    if (e.key === "Escape") setOpen(false);
  }

  return (
    <div className="form-row picker" ref={boxRef}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={text}
        autoComplete="off"
        placeholder={placeholder}
        onFocus={(e) => {
          setOpen(true);
          e.target.select();
        }}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
        }}
        onKeyDown={onKey}
        role="combobox"
        aria-expanded={open && options.length > 0}
        aria-controls={`${id}-list`}
      />
      {open && options.length > 0 && (
        <ul className="picker-list" id={`${id}-list`} role="listbox">
          {options.map((o, i) => (
            <li
              key={o.value}
              role="option"
              aria-selected={i === active}
              className={i === active ? "on" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(o);
              }}
            >
              <span>{o.label}</span>
              <span className="mono muted">
                {o.kind === "city" ? o.detail : o.value}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
