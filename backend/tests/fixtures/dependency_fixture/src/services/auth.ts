import { getUserPermissions } from './user';

export function authenticate(username: string): boolean {
  return getUserPermissions(username).includes('admin');
}

