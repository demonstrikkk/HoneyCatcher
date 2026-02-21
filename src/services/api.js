import { API_BASE_URL, API_KEY } from '../config/constants';

const defaultHeaders = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

const handleResponse = async (res, endpoint) => {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${endpoint} failed [${res.status}]: ${body}`);
  }
  return res.json();
};

export const api = {
  get: (endpoint) =>
    fetch(`${API_BASE_URL}${endpoint}`, { headers: defaultHeaders })
      .then(res => handleResponse(res, endpoint)),

  post: (endpoint, data) =>
    fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(data),
    }).then(res => handleResponse(res, endpoint)),

  postForm: (endpoint, formData) =>
    fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'X-API-Key': API_KEY },
      body: formData,
    }).then(res => handleResponse(res, endpoint)),

  delete: (endpoint) =>
    fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
      headers: defaultHeaders,
    }).then(res => handleResponse(res, endpoint)),
};