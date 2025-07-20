// 在浏览器控制台检查Socket.IO状态
// 请将此代码粘贴到浏览器控制台执行

// 1. 检查配置
console.log('=== Checking Socket.IO Configuration ===');
if (window.appConfig) {
    console.log('wsUrl:', window.appConfig.wsUrl);
} else {
    // 尝试从React组件获取配置
    const reactRoot = document.getElementById('root');
    if (reactRoot && reactRoot._reactRootContainer) {
        console.log('Trying to access React internals...');
    }
}

// 2. 检查Socket.IO连接
console.log('\n=== Checking Socket.IO Connection ===');
// 查找全局Socket.IO实例
if (window.io) {
    console.log('Socket.IO library loaded');
    
    // 查找所有socket连接
    if (window.io.sockets) {
        console.log('Active sockets:', window.io.sockets);
    }
} else {
    console.log('Socket.IO library not found in window');
}

// 3. 检查localStorage中的配置和认证
console.log('\n=== Checking Authentication ===');
const authToken = localStorage.getItem('mailassistant_auth_token');
if (authToken) {
    try {
        const parsed = JSON.parse(authToken);
        console.log('Auth token exists:', !!parsed.state?.token);
        console.log('User authenticated:', parsed.state?.isAuthenticated);
    } catch (e) {
        console.log('Failed to parse auth token');
    }
} else {
    console.log('No auth token found');
}

// 4. 检查网络请求
console.log('\n=== Checking Network Requests ===');
console.log('Open Network tab and filter by "socket.io" to see WebSocket connections');
console.log('Expected URL should be: http://localhost:8000/socket.io/');

// 5. 手动创建Socket.IO连接测试
console.log('\n=== Manual Connection Test ===');
if (window.io) {
    console.log('Creating test connection to http://localhost:8000...');
    const testSocket = window.io('http://localhost:8000', {
        transports: ['websocket'],
        auth: {
            token: 'test-token'
        }
    });
    
    testSocket.on('connect', () => {
        console.log('✅ Test connection successful!');
        testSocket.disconnect();
    });
    
    testSocket.on('connect_error', (error) => {
        console.log('❌ Test connection failed:', error.message);
        console.log('Error type:', error.type);
    });
} else {
    console.log('Cannot test - Socket.IO not available');
}