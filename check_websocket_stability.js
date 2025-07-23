// 检查WebSocket连接稳定性
// 模拟多个连接和断开场景

const { io } = require('socket.io-client');

const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMDc5OTE5LCJpYXQiOjE3NTI5OTM1MTl9.6B6fPR6-o30pXOism8I61jEQwYu9rEmuwDkjQvsZHhE';

console.log('🧪 WebSocket稳定性测试开始...\n');

// 测试1: 快速连接和断开
async function testRapidReconnect() {
  console.log('📋 测试1: 快速连接和断开（模拟组件重复挂载）');
  
  let connections = [];
  
  // 创建3个连接
  for (let i = 0; i < 3; i++) {
    const socket = io('http://localhost:8000', {
      auth: { token },
      path: '/socket.io/',
      autoConnect: false
    });
    
    socket.on('connect', () => {
      console.log(`  ✅ 连接 ${i + 1} 成功: ${socket.id}`);
    });
    
    socket.on('disconnect', () => {
      console.log(`  ❌ 连接 ${i + 1} 断开`);
    });
    
    socket.connect();
    connections.push(socket);
    
    // 短暂延迟
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // 等待所有连接建立
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  console.log(`\n  活跃连接数: ${connections.filter(s => s.connected).length}`);
  
  // 断开所有连接
  connections.forEach(socket => socket.disconnect());
  
  await new Promise(resolve => setTimeout(resolve, 500));
  console.log('  测试1完成\n');
}

// 测试2: 并发连接
async function testConcurrentConnections() {
  console.log('📋 测试2: 并发连接（模拟多个组件同时初始化）');
  
  const promises = [];
  
  // 同时创建5个连接
  for (let i = 0; i < 5; i++) {
    promises.push(new Promise((resolve) => {
      const socket = io('http://localhost:8000', {
        auth: { token },
        path: '/socket.io/'
      });
      
      socket.on('connect', () => {
        console.log(`  ✅ 并发连接 ${i + 1} 成功: ${socket.id}`);
        setTimeout(() => {
          socket.disconnect();
          resolve();
        }, 1000);
      });
      
      socket.on('connect_error', (error) => {
        console.error(`  ⚠️ 并发连接 ${i + 1} 失败:`, error.message);
        resolve();
      });
    }));
  }
  
  await Promise.all(promises);
  console.log('  测试2完成\n');
}

// 测试3: 长时间连接稳定性
async function testLongConnection() {
  console.log('📋 测试3: 长时间连接稳定性（10秒）');
  
  const socket = io('http://localhost:8000', {
    auth: { token },
    path: '/socket.io/'
  });
  
  let disconnectCount = 0;
  let reconnectCount = 0;
  
  socket.on('connect', () => {
    console.log(`  ✅ 连接成功: ${socket.id}`);
  });
  
  socket.on('disconnect', (reason) => {
    disconnectCount++;
    console.log(`  ❌ 连接断开 (${disconnectCount}次): ${reason}`);
  });
  
  socket.on('reconnect', () => {
    reconnectCount++;
    console.log(`  🔄 重新连接成功 (${reconnectCount}次)`);
  });
  
  // 等待10秒
  await new Promise(resolve => setTimeout(resolve, 10000));
  
  console.log(`\n  📊 统计: 断开${disconnectCount}次, 重连${reconnectCount}次`);
  socket.disconnect();
  console.log('  测试3完成\n');
}

// 运行所有测试
async function runAllTests() {
  try {
    await testRapidReconnect();
    await testConcurrentConnections();
    await testLongConnection();
    
    console.log('✅ 所有测试完成！');
    process.exit(0);
  } catch (error) {
    console.error('❌ 测试失败:', error);
    process.exit(1);
  }
}

runAllTests();