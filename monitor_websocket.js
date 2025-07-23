// WebSocket连接监控工具
// 在浏览器控制台中运行此脚本来监控WebSocket连接

(function() {
  console.log('%c=== WebSocket Monitor Started ===', 'color: blue; font-weight: bold');
  
  let effectCount = 0;
  let socketCount = 0;
  const sockets = new Map();
  
  // 监控MainLayout的effect执行
  const originalUseEffect = React.useEffect;
  React.useEffect = function(...args) {
    const [effect, deps] = args;
    
    // 检测MainLayout的effect
    if (deps && deps.length >= 3 && effect.toString().includes('connectWebSocket')) {
      effectCount++;
      console.log(`%c[Effect #${effectCount}] MainLayout effect executed`, 'color: orange');
      console.log('Dependencies:', deps);
      
      // 包装原始effect
      const wrappedEffect = () => {
        console.log(`%c[Effect #${effectCount}] Running effect body`, 'color: orange');
        const cleanup = effect();
        if (cleanup) {
          return () => {
            console.log(`%c[Effect #${effectCount}] Running cleanup`, 'color: red');
            cleanup();
          };
        }
      };
      
      return originalUseEffect.call(this, wrappedEffect, deps);
    }
    
    return originalUseEffect.apply(this, args);
  };
  
  // 监控Socket.IO连接
  if (window.io) {
    const originalIo = window.io;
    window.io = function(...args) {
      socketCount++;
      const socketId = `socket_${socketCount}`;
      console.log(`%c[${socketId}] Creating new socket`, 'color: green', args);
      
      const socket = originalIo.apply(this, args);
      sockets.set(socketId, socket);
      
      // 监控socket事件
      const originalOn = socket.on.bind(socket);
      socket.on = function(event, handler) {
        console.log(`%c[${socketId}] Listening to event: ${event}`, 'color: cyan');
        
        const wrappedHandler = (...args) => {
          if (event === 'connect') {
            console.log(`%c[${socketId}] Connected! ID: ${socket.id}`, 'color: green; font-weight: bold');
          } else if (event === 'disconnect') {
            console.log(`%c[${socketId}] Disconnected!`, 'color: red; font-weight: bold');
          }
          return handler(...args);
        };
        
        return originalOn(event, wrappedHandler);
      };
      
      // 监控disconnect
      const originalDisconnect = socket.disconnect.bind(socket);
      socket.disconnect = function() {
        console.log(`%c[${socketId}] disconnect() called`, 'color: red');
        console.trace('Disconnect call stack');
        return originalDisconnect();
      };
      
      return socket;
    };
  }
  
  // 提供状态查看函数
  window.wsMonitor = {
    getStats: () => {
      console.log(`
=== WebSocket Monitor Stats ===
Effect executions: ${effectCount}
Sockets created: ${socketCount}
Active sockets: ${Array.from(sockets.values()).filter(s => s.connected).length}
      `);
      
      sockets.forEach((socket, id) => {
        console.log(`${id}: ${socket.connected ? 'Connected' : 'Disconnected'} (ID: ${socket.id || 'none'})`);
      });
    },
    
    reset: () => {
      effectCount = 0;
      socketCount = 0;
      sockets.clear();
      console.log('%c=== Monitor Reset ===', 'color: blue');
    }
  };
  
  console.log('Use window.wsMonitor.getStats() to view statistics');
  console.log('Use window.wsMonitor.reset() to reset counters');
})();