import type { LoginResponse, User } from '../types/user';
import { http } from '../utils/request';

export const authApi = {
  login: (email: string, password: string) =>
    http.post<LoginResponse>('/auth/login', { email, password }),
  me: () => http.get<User>('/auth/me'),
};
