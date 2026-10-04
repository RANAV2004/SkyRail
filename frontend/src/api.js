import axios from "axios";

export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.response.use(null, (err) => {
  if (!err.response) {
    err.response = {
      data: {
        detail: `Can't reach the server at ${API_BASE}. Is the backend running?`,
      },
    };
  } else if (Array.isArray(err.response.data?.detail)) {
    err.response.data.detail = err.response.data.detail
      .map(
        (d) =>
          `${d.loc?.at(-1) ?? "input"}: ${d.msg.replace("Value error, ", "")}`,
      )
      .join(". ");
  }
  return Promise.reject(err);
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("token");
    }
    return Promise.reject(err);
  },
);

export async function downloadFile(path, filename) {
  const res = await api.get(path, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default api;
