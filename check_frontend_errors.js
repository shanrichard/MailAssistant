// 获取前端错误日志并发送到后端
async function checkAndSendErrors() {
    // 获取本地存储的错误
    const errors = window.debugLogs ? window.debugLogs.get() : [];
    console.log('Frontend errors count:', errors.length);
    
    if (errors.length > 0) {
        console.log('Recent errors:', errors.slice(-5));
        
        // 发送到后端
        try {
            const response = await fetch('http://localhost:8000/api/debug/logs/all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ frontend_errors: errors })
            });
            
            const result = await response.json();
            console.log('Errors sent to backend, total errors:', result.errors.length);
            
            // 显示最近的WebSocket相关错误
            const wsErrors = result.errors.filter(e => 
                e.message && (e.message.includes('WebSocket') || e.message.includes('socket.io'))
            );
            
            console.log('WebSocket related errors:', wsErrors);
            return wsErrors;
        } catch (error) {
            console.error('Failed to send errors:', error);
        }
    } else {
        console.log('No frontend errors found');
    }
}

// 执行检查
checkAndSendErrors();