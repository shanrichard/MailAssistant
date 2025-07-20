// Auth utilities
// 这些工具函数主要用于向后兼容和WebSocket连接
// 推荐使用authStore来管理认证状态

export const getToken = (): string | null => {
  try {
    // 先尝试从新的存储格式读取（authStore使用的格式）
    const authData = localStorage.getItem('mailassistant_auth_token');
    if (authData) {
      const parsed = JSON.parse(authData);
      return parsed.state?.token || null;
    }
    
    // 回退到旧的存储格式（向后兼容）
    return localStorage.getItem('access_token');
  } catch {
    // 如果解析失败，回退到旧格式
    return localStorage.getItem('access_token');
  }
};

export const setToken = (token: string): void => {
  // 注意：这个函数目前未被使用，但为了保持一致性，更新为与authStore相同的存储格式
  // 如果需要直接设置token，建议使用authStore.login()或authStore.setToken()
  const existingData = localStorage.getItem('mailassistant_auth_token');
  if (existingData) {
    try {
      const parsed = JSON.parse(existingData);
      parsed.state.token = token;
      localStorage.setItem('mailassistant_auth_token', JSON.stringify(parsed));
    } catch {
      // 如果解析失败，创建新的结构
      const newData = {
        state: { token }
      };
      localStorage.setItem('mailassistant_auth_token', JSON.stringify(newData));
    }
  } else {
    // 创建新的存储结构
    const newData = {
      state: { token }
    };
    localStorage.setItem('mailassistant_auth_token', JSON.stringify(newData));
  }
  
  // 同时清理旧的存储位置
  localStorage.removeItem('access_token');
};

export const removeToken = (): void => {
  // 注意：这个函数目前未被使用，建议使用authStore.logout()
  // 清理两个可能的存储位置
  localStorage.removeItem('access_token');
  localStorage.removeItem('mailassistant_auth_token');
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};