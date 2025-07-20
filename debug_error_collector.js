// 调试错误收集器的脚本 - 直接检查前端
console.log('Opening browser to check error collector...');

const checkErrorCollector = async () => {
  // 等待用户在浏览器中打开 http://localhost:3000
  console.log('Please open http://localhost:3000 in your browser');
  console.log('Then open the browser console and run:');
  console.log('');
  console.log('// 检查 debugLogs 是否存在');
  console.log('console.log("debugLogs exists:", typeof window.debugLogs !== "undefined");');
  console.log('');
  console.log('// 检查环境变量');
  console.log('console.log("NODE_ENV:", process?.env?.NODE_ENV);');
  console.log('');
  console.log('// 检查 localStorage');
  console.log('console.log("localStorage errors:", localStorage.getItem("mailassistant_frontend_errors"));');
  console.log('');
  console.log('// 创建测试错误');
  console.log('console.error("Test error", new Date().toISOString());');
  console.log('');
  console.log('// 检查错误是否被捕获');
  console.log('setTimeout(() => {');
  console.log('  console.log("Errors after test:", localStorage.getItem("mailassistant_frontend_errors"));');
  console.log('}, 1000);');
  console.log('');
  console.log('// 如果 debugLogs 存在，使用它');
  console.log('if (window.debugLogs) {');
  console.log('  console.log("Errors via debugLogs:", window.debugLogs.get());');
  console.log('  window.debugLogs.send().then(result => console.log("Send result:", result));');
  console.log('}');
};

checkErrorCollector();