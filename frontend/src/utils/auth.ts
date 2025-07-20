// Auth utilities
export const getToken = (): string | null => {
  try {
    // 先尝试从新的存储格式读取
    const authData = localStorage.getItem('mailassistant_auth_token');
    if (authData) {
      const parsed = JSON.parse(authData);
      return parsed.state?.token || null;
    }
    
    // 回退到旧的存储格式
    return localStorage.getItem('access_token');
  } catch {
    // 如果解析失败，回退到旧格式
    return localStorage.getItem('access_token');
  }
};

export const setToken = (token: string): void => {
  localStorage.setItem('access_token', token);
};

export const removeToken = (): void => {
  localStorage.removeItem('access_token');
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};