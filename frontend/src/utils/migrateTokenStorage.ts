/**
 * Token存储迁移工具
 * 用于将旧的access_token迁移到新的存储格式
 */

export const migrateTokenStorage = (): void => {
  try {
    // 检查是否存在旧的token
    const oldToken = localStorage.getItem('access_token');
    if (!oldToken) {
      return; // 没有旧token，无需迁移
    }

    // 检查新的存储是否已存在
    const newStorageData = localStorage.getItem('mailassistant_auth_token');
    if (newStorageData) {
      try {
        const parsed = JSON.parse(newStorageData);
        if (parsed.state?.token) {
          // 新存储已有token，删除旧的
          localStorage.removeItem('access_token');
          console.log('[Token Migration] 新存储已存在token，清理旧存储');
          return;
        }
      } catch {
        // 解析失败，继续迁移流程
      }
    }

    // 执行迁移
    const newData = {
      state: {
        token: oldToken,
        // 注意：这里没有user和isAuthenticated，因为我们只迁移token
        // authStore会在下次验证token时更新这些字段
      }
    };
    
    localStorage.setItem('mailassistant_auth_token', JSON.stringify(newData));
    localStorage.removeItem('access_token');
    
    console.log('[Token Migration] 成功将token从旧格式迁移到新格式');
  } catch (error) {
    console.error('[Token Migration] 迁移失败:', error);
  }
};

// 自动执行迁移（只在首次导入时运行）
if (typeof window !== 'undefined') {
  migrateTokenStorage();
}