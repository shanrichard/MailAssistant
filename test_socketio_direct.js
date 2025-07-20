// 在浏览器控制台执行此代码直接测试Socket.IO连接

console.log('=== Direct Socket.IO Test ===');

// 获取认证token
function getToken() {
    try {
        const authData = localStorage.getItem('mailassistant_auth_token');
        if (authData) {
            const parsed = JSON.parse(authData);
            return parsed.state?.token || null;
        }
        return localStorage.getItem('access_token');
    } catch {
        return localStorage.getItem('access_token');
    }
}

const token = getToken();
console.log('Auth token:', token ? 'Found' : 'Not found');

if (!token) {
    console.error('No auth token available. Please login first.');
} else {
    // 测试不同的连接配置
    console.log('\n--- Test 1: Polling only ---');
    const socket1 = io('http://localhost:8000', {
        auth: { token },
        transports: ['polling']
    });
    
    socket1.on('connect', () => {
        console.log('✅ Test 1: Connected via polling');
        socket1.disconnect();
    });
    
    socket1.on('connect_error', (error) => {
        console.error('❌ Test 1 error:', error.message);
    });
    
    setTimeout(() => {
        console.log('\n--- Test 2: Polling then WebSocket ---');
        const socket2 = io('http://localhost:8000', {
            auth: { token },
            transports: ['polling', 'websocket'],
            upgrade: true
        });
        
        socket2.on('connect', () => {
            console.log('✅ Test 2: Connected');
            console.log('Transport:', socket2.io.engine.transport.name);
            
            // 监听升级事件
            socket2.io.on('upgrade', (transport) => {
                console.log('✅ Upgraded to:', transport.name);
            });
            
            setTimeout(() => {
                console.log('Final transport:', socket2.io.engine.transport.name);
                socket2.disconnect();
            }, 2000);
        });
        
        socket2.on('connect_error', (error) => {
            console.error('❌ Test 2 error:', error.message);
        });
    }, 3000);
    
    setTimeout(() => {
        console.log('\n--- Test 3: Force WebSocket only ---');
        const socket3 = io('http://localhost:8000', {
            auth: { token },
            transports: ['websocket'],
            upgrade: false
        });
        
        socket3.on('connect', () => {
            console.log('✅ Test 3: Connected via WebSocket directly');
            socket3.disconnect();
        });
        
        socket3.on('connect_error', (error) => {
            console.error('❌ Test 3 error:', error.message, error.type);
        });
    }, 6000);
}

console.log('\nTests scheduled. Please wait...');