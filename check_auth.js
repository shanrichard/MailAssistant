// 在浏览器控制台执行此代码
console.log('=== Checking Authentication ===');

// 1. 检查localStorage
console.log('\n1. LocalStorage contents:');
console.log('- access_token:', localStorage.getItem('access_token'));
console.log('- mailassistant_auth_token:', localStorage.getItem('mailassistant_auth_token'));

// 2. 解析新格式
const authData = localStorage.getItem('mailassistant_auth_token');
if (authData) {
    try {
        const parsed = JSON.parse(authData);
        console.log('\n2. Parsed auth data:');
        console.log('- Token exists:', !!parsed.state?.token);
        console.log('- Is authenticated:', parsed.state?.isAuthenticated);
        console.log('- User:', parsed.state?.user?.email);
        console.log('- Token preview:', parsed.state?.token?.substring(0, 20) + '...');
    } catch (e) {
        console.log('Failed to parse auth data:', e);
    }
}

// 3. 测试getToken函数
console.log('\n3. Testing getToken function:');
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
console.log('- getToken result:', token ? 'Token found' : 'No token found');

// 4. 检查Socket.IO连接
console.log('\n4. Checking Socket.IO:');
if (window.io) {
    console.log('- Socket.IO library: Loaded');
    
    // 测试连接
    console.log('- Creating test connection...');
    const testSocket = io('http://localhost:8000', {
        auth: { token: token || 'no-token' },
        transports: ['websocket']
    });
    
    testSocket.on('connect', () => {
        console.log('✅ Socket.IO connected!');
        testSocket.disconnect();
    });
    
    testSocket.on('connect_error', (error) => {
        console.log('❌ Socket.IO error:', error.message);
    });
} else {
    console.log('- Socket.IO library: Not loaded');
}

// 5. 建议
console.log('\n=== Suggestions ===');
if (!token) {
    console.log('❌ No authentication token found. Please login again.');
} else {
    console.log('✅ Token found. If Socket.IO still fails, check:');
    console.log('   1. Backend is running on http://localhost:8000');
    console.log('   2. CORS is properly configured');
    console.log('   3. Token is valid and not expired');
}