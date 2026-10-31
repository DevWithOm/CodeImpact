import { authenticate } from './auth';

export function getUserPermissions(username: string): string[] {
  if (username === 'admin') {
    return ['admin', 'read', 'write'];
  }
  return ['read'];
}

export function validateUserSession(username: string): boolean {
  return authenticate(username);
}

