// 在浏览器控制台执行此脚本来检查WebSocket连接状态

console.log('=== WebSocket连接状态检查 ===');

// 查看localStorage中的错误
const errors = JSON.parse(localStorage.getItem('mailassistant_frontend_errors') || '[]');
const wsErrors = errors.filter(e => e.message.includes('WebSocket') || e.message.includes('connect'));
console.log(`WebSocket相关错误数: ${wsErrors.length}`);
if (wsErrors.length > 0) {
  console.log('最近的WebSocket错误:');
  wsErrors.slice(-5).forEach(err => {
    console.log(`  [${new Date(err.timestamp).toLocaleTimeString()}] ${err.message}`);
  });
}

// 检查window对象中的调试信息
if (window.debugLogs) {
  console.log('\n=== 调试日志 ===');
  const logs = window.debugLogs.get();
  const recentLogs = logs.slice(-10);
  recentLogs.forEach(log => {
    console.log(`  [${new Date(log.timestamp).toLocaleTimeString()}] ${log.message}`);
  });
}

// 尝试获取React DevTools中的store状态
console.log('\n=== 提示 ===');
console.log('1. 请打开React DevTools查看ChatStore的状态');
console.log('2. 查看isConnected, connectionStatus, connectionLock等字段');
console.log('3. 查看Network面板中的WebSocket连接');
console.log('4. 访问 /websocket-test 页面进行详细测试');