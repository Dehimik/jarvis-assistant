import axios from 'axios'

// Adjust baseURL to your FastAPI address (daemon). Typically http://127.0.0.1:8000
export const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 5000
})