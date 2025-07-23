// WebSocket连接测试脚本
// 用于监控和测试WebSocket连接的稳定性

const { io } = require('socket.io-client');

console.log('Starting WebSocket connection test...\n');

// 连接计数器
let connectionCount = 0;
let disconnectionCount = 0;
let errorCount = 0;
let lastConnectionTime = null;

// 创建Socket.IO客户端
const socket = io('http://localhost:8000', {
  auth: {
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMDc5OTE5LCJpYXQiOjE3NTI5OTM1MTl9.6B6fPR6-o30pXOism8I61jEQwYu9rEmuwDkjQvsZHhE'
  },
  path: '/socket.io/',
  transports: ['polling', 'websocket'],
  upgrade: true,
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
});

// 监听连接事件
socket.on('connect', () => {
  connectionCount++;
  const now = new Date();
  const timeSinceLastConnection = lastConnectionTime ? 
    `(${(now - lastConnectionTime) / 1000}s since last connection)` : '';
  
  console.log(`✅ [${now.toISOString()}] Connected! Socket ID: ${socket.id}`);
  console.log(`   Connection #${connectionCount} ${timeSinceLastConnection}`);
  console.log(`   Transport: ${socket.io.engine.transport.name}\n`);
  
  lastConnectionTime = now;
});

// 监听断开事件
socket.on('disconnect', (reason) => {
  disconnectionCount++;
  console.log(`❌ [${new Date().toISOString()}] Disconnected! Reason: ${reason}`);
  console.log(`   Disconnection #${disconnectionCount}\n`);
});

// 监听错误事件
socket.on('connect_error', (error) => {
  errorCount++;
  console.error(`⚠️  [${new Date().toISOString()}] Connection error #${errorCount}:`, error.type, error.message);
});

// 监听重连尝试
socket.on('reconnect_attempt', (attemptNumber) => {
  console.log(`🔄 [${new Date().toISOString()}] Reconnection attempt ${attemptNumber}`);
});

// 监听成功重连
socket.on('reconnect', (attemptNumber) => {
  console.log(`✅ [${new Date().toISOString()}] Reconnected after ${attemptNumber} attempts\n`);
});

// 监听重连失败
socket.on('reconnect_failed', () => {
  console.error(`❌ [${new Date().toISOString()}] Reconnection failed after maximum attempts\n`);
});

// 定期报告状态
setInterval(() => {
  console.log(`📊 Status Report [${new Date().toISOString()}]`);
  console.log(`   Connected: ${socket.connected}`);
  console.log(`   Total Connections: ${connectionCount}`);
  console.log(`   Total Disconnections: ${disconnectionCount}`);
  console.log(`   Total Errors: ${errorCount}`);
  console.log(`   Current Transport: ${socket.io.engine.transport.name || 'N/A'}\n`);
}, 30000); // 每30秒报告一次

// 优雅退出
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down test...');
  socket.disconnect();
  process.exit(0);
});

console.log('Test is running. Press Ctrl+C to stop.\n');