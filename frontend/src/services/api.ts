import axios from 'axios';
import type {
  Server,
  UpdateHistory,
  Schedule,
  Stats,
  LoginCredentials,
  AuthResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login if unauthorized
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (credentials: LoginCredentials) =>
    api.post<AuthResponse>('/login', credentials),

  logout: () => api.post('/logout'),
};

export const serversAPI = {
  getAll: () => api.get<Server[]>('/servers'),

  getOne: (id: number) => api.get<Server>(`/servers/${id}`),

  create: (server: Omit<Server, 'id' | 'created_at' | 'status' | 'updates_available' | 'last_check'>) =>
    api.post<Server>('/servers', server),

  update: (id: number, server: Partial<Server>) =>
    api.put<Server>(`/servers/${id}`, server),

  delete: (id: number) => api.delete(`/servers/${id}`),

  checkUpdates: (id: number, securityOnly: boolean = false) =>
    api.post(`/servers/${id}/check`, { security_only: securityOnly }),

  applyUpdates: (id: number, securityOnly: boolean = false, autoReboot: boolean = true) =>
    api.post(`/servers/${id}/update`, {
      security_only: securityOnly,
      auto_reboot: autoReboot,
    }),
};

export const schedulesAPI = {
  getForServer: (serverId: number) =>
    api.get<Schedule[]>(`/servers/${serverId}/schedules`),

  create: (serverId: number, schedule: Partial<Schedule>) =>
    api.post<Schedule>(`/servers/${serverId}/schedules`, schedule),

  update: (scheduleId: number, schedule: Partial<Schedule>) =>
    api.put<Schedule>(`/schedules/${scheduleId}`, schedule),

  delete: (scheduleId: number) => api.delete(`/schedules/${scheduleId}`),
};

export const historyAPI = {
  getAll: (serverId?: number) =>
    api.get<UpdateHistory[]>('/history', serverId ? { params: { server_id: serverId } } : {}),
};

export const statsAPI = {
  get: () => api.get<Stats>('/stats'),
};

export default api;
