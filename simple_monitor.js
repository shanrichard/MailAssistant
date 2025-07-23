// 简单的WebSocket监控
// 不修改任何原生函数，只是观察

(function() {
  console.log('=== Simple WebSocket Monitor ===');
  
  // 定期检查并报告状态
  let checkCount = 0;
  
  const checkStatus = () => {
    checkCount++;
    console.log(`\n--- Check #${checkCount} at ${new Date().toLocaleTimeString()} ---`);
    
    // 检查React组件
    const rootElement = document.getElementById('root');
    if (rootElement && rootElement._reactRootContainer) {
      console.log('React app is mounted');
    }
    
    // 检查localStorage中的token
    const authToken = localStorage.getItem('mailassistant_auth_token');
    const oldToken = localStorage.getItem('access_token');
    console.log('Auth token exists:', !!authToken);
    console.log('Old token exists:', !!oldToken);
    
    // 检查window上是否有调试信息
    if (window.debugLogs) {
      const logs = window.debugLogs.get();
      const recentErrors = logs.filter(log => 
        Date.now() - new Date(log.timestamp).getTime() < 30000
      );
      console.log(`Recent errors (last 30s): ${recentErrors.length}`);
      
      recentErrors.forEach(err => {
        console.log(`  - ${new Date(err.timestamp).toLocaleTimeString()}: ${err.message.substring(0, 50)}...`);
      });
    }
    
    // 检查Socket.IO
    if (window.io && window.io.sockets) {
      console.log('Socket.IO sockets:', window.io.sockets.length);
    }
  };
  
  // 立即检查一次
  checkStatus();
  
  // 每5秒检查一次
  const interval = setInterval(checkStatus, 5000);
  
  // 提供停止函数
  window.stopMonitor = () => {
    clearInterval(interval);
    console.log('Monitor stopped');
  };
  
  console.log('Monitor started. Use window.stopMonitor() to stop.');
})();