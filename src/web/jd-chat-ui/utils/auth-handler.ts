import { useSessionStore } from '@/stores/useSessionStore';

export function handleAuthError(message: string = '登录已过期，请重新登录') {
  if (typeof window !== 'undefined') {
    const { logout } = useSessionStore.getState();
    alert(message);
    logout();
  }
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(url, options);

  if (res.status === 401) {
    handleAuthError();
    throw new Error('AUTH_ERROR');
  }

  return res;
}

export function isAuthError(error: unknown): boolean {
  return error instanceof Error && error.message === 'AUTH_ERROR';
}
