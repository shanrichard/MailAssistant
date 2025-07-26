#!/usr/bin/env python3
"""
MailAssistant 部署测试脚本
用于验证生产环境部署是否正确配置
"""
import os
import sys
import json
import time
import requests
import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin, urlparse
import ssl

class DeploymentTester:
    """部署测试器"""
    
    def __init__(self, backend_url: str, frontend_url: str = None):
        self.backend_url = backend_url.rstrip('/')
        self.frontend_url = frontend_url.rstrip('/') if frontend_url else None
        self.session = requests.Session()
        self.session.timeout = 30
        
        # 测试结果收集
        self.results = []
        self.errors = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: dict = None):
        """记录测试结果"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        
        if not success:
            self.errors.append(result)
            if details:
                print(f"   Details: {details}")
    
    def test_backend_health(self) -> bool:
        """测试后端健康检查"""
        try:
            response = self.session.get(f"{self.backend_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ['status', 'app', 'version']
                
                if all(field in data for field in expected_fields):
                    self.log_result(
                        "Backend Health Check", 
                        True, 
                        f"Backend is healthy (v{data.get('version', 'unknown')})",
                        {'response_data': data}
                    )
                    return True
                else:
                    self.log_result(
                        "Backend Health Check", 
                        False, 
                        "Health endpoint missing required fields",
                        {'response_data': data}
                    )
                    return False
            else:
                self.log_result(
                    "Backend Health Check", 
                    False, 
                    f"Health endpoint returned {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Backend Health Check", 
                False, 
                f"Connection failed: {str(e)}"
            )
            return False
    
    def test_cors_headers(self) -> bool:
        """测试CORS配置"""
        try:
            # 预检请求测试
            headers = {
                'Origin': self.frontend_url or 'https://test.example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Authorization,Content-Type'
            }
            
            response = self.session.options(
                f"{self.backend_url}/api/auth/google-auth-url",
                headers=headers
            )
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            }
            
            if response.status_code in [200, 204] and cors_headers['Access-Control-Allow-Origin']:
                self.log_result(
                    "CORS Configuration",
                    True,
                    "CORS headers present and configured",
                    {'cors_headers': cors_headers}
                )
                return True
            else:
                self.log_result(
                    "CORS Configuration",
                    False,
                    f"CORS preflight failed ({response.status_code})",
                    {'cors_headers': cors_headers}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "CORS Configuration",
                False,
                f"CORS test failed: {str(e)}"
            )
            return False
    
    def test_auth_endpoints(self) -> bool:
        """测试认证端点"""
        try:
            # 测试 Google Auth URL 生成
            response = self.session.get(f"{self.backend_url}/api/auth/google-auth-url")
            
            if response.status_code == 200:
                data = response.json()
                if 'auth_url' in data and data['auth_url'].startswith('https://accounts.google.com'):
                    self.log_result(
                        "Authentication Endpoints",
                        True,
                        "Google Auth URL generation working",
                        {'auth_url_domain': urlparse(data['auth_url']).netloc}
                    )
                    return True
                else:
                    self.log_result(
                        "Authentication Endpoints",
                        False,
                        "Invalid auth URL response",
                        {'response_data': data}
                    )
                    return False
            else:
                self.log_result(
                    "Authentication Endpoints",
                    False,
                    f"Auth endpoint returned {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Authentication Endpoints",
                False,
                f"Auth endpoint test failed: {str(e)}"
            )
            return False
    
    async def test_websocket_connection(self) -> bool:
        """测试WebSocket连接"""
        if not self.backend_url.startswith('https://'):
            self.log_result(
                "WebSocket Connection",
                False,
                "WebSocket test requires HTTPS backend URL"
            )
            return False
            
        ws_url = self.backend_url.replace('https://', 'wss://') + '/socket.io/?EIO=4&transport=websocket'
        
        try:
            # 创建SSL上下文
            ssl_context = ssl.create_default_context()
            
            # 尝试连接WebSocket
            async with websockets.connect(
                ws_url, 
                ssl=ssl_context,
                timeout=10,
                extra_headers={'Origin': self.frontend_url or 'https://test.example.com'}
            ) as websocket:
                
                # 发送心跳消息
                await websocket.send('2probe')  # Socket.IO ping frame
                
                # 等待响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    
                    self.log_result(
                        "WebSocket Connection",
                        True,
                        "WebSocket connection and ping successful",
                        {'response': response}
                    )
                    return True
                    
                except asyncio.TimeoutError:
                    self.log_result(
                        "WebSocket Connection",
                        False,
                        "WebSocket connected but no ping response"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "WebSocket Connection",
                False,
                f"WebSocket connection failed: {str(e)}"
            )
            return False
    
    def test_frontend_accessibility(self) -> bool:
        """测试前端可访问性"""
        if not self.frontend_url:
            self.log_result(
                "Frontend Accessibility",
                False,
                "No frontend URL provided"
            )
            return False
            
        try:
            response = self.session.get(self.frontend_url)
            
            if response.status_code == 200:
                # 检查基本HTML内容
                content = response.text.lower()
                if 'mailassistant' in content or 'react' in content:
                    self.log_result(
                        "Frontend Accessibility",
                        True,
                        "Frontend is accessible and contains expected content"
                    )
                    return True
                else:
                    self.log_result(
                        "Frontend Accessibility",
                        False,
                        "Frontend accessible but unexpected content",
                        {'content_length': len(content)}
                    )
                    return False
            else:
                self.log_result(
                    "Frontend Accessibility",
                    False,
                    f"Frontend returned {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Frontend Accessibility",
                False,
                f"Frontend test failed: {str(e)}"
            )
            return False
    
    def test_security_headers(self) -> bool:
        """测试安全头配置"""
        try:
            response = self.session.get(f"{self.backend_url}/health")
            
            security_headers = {
                'x-content-type-options': response.headers.get('x-content-type-options'),
                'x-frame-options': response.headers.get('x-frame-options'),
                'strict-transport-security': response.headers.get('strict-transport-security'),
            }
            
            # 检查是否有基本的安全头
            present_headers = {k: v for k, v in security_headers.items() if v}
            
            if len(present_headers) >= 1:  # 至少有一个安全头
                self.log_result(
                    "Security Headers",
                    True,
                    f"Security headers present: {list(present_headers.keys())}",
                    {'headers': present_headers}
                )
                return True
            else:
                self.log_result(
                    "Security Headers",
                    False,
                    "No security headers detected",
                    {'checked_headers': list(security_headers.keys())}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Security Headers",
                False,
                f"Security headers test failed: {str(e)}"
            )
            return False
    
    def test_environment_detection(self) -> bool:
        """测试环境检测"""
        try:
            # 尝试访问开发环境特有的端点
            response = self.session.get(f"{self.backend_url}/api/debug/logs/backend")
            
            if response.status_code == 404:
                self.log_result(
                    "Environment Detection",
                    True,
                    "Debug endpoints disabled (production mode detected)"
                )
                return True
            elif response.status_code == 200:
                self.log_result(
                    "Environment Detection",
                    False,
                    "Debug endpoints accessible (not production mode)"
                )
                return False
            else:
                self.log_result(
                    "Environment Detection",
                    True,
                    f"Debug endpoints return {response.status_code} (likely production)"
                )
                return True
                
        except Exception as e:
            self.log_result(
                "Environment Detection",
                False,
                f"Environment test failed: {str(e)}"
            )
            return False
    
    async def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("🧪 Starting MailAssistant Deployment Tests")
        print("=" * 50)
        print(f"Backend URL: {self.backend_url}")
        if self.frontend_url:
            print(f"Frontend URL: {self.frontend_url}")
        print()
        
        # 运行同步测试
        sync_tests = [
            self.test_backend_health,
            self.test_cors_headers,
            self.test_auth_endpoints,
            self.test_security_headers,
            self.test_environment_detection,
        ]
        
        if self.frontend_url:
            sync_tests.append(self.test_frontend_accessibility)
        
        for test in sync_tests:
            test()
            time.sleep(0.5)  # 避免请求过快
        
        # 运行异步测试
        await self.test_websocket_connection()
        
        # 生成报告
        print("\n" + "=" * 50)
        print("🎯 Test Results Summary")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.errors:
            print("\n🚨 Failed Tests:")
            for error in self.errors:
                print(f"   - {error['test']}: {error['message']}")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': self.results,
            'errors': self.errors
        }

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python test_deployment.py <backend_url> [frontend_url]")
        print("Example: python test_deployment.py https://your-app.railway.app https://your-app.vercel.app")
        sys.exit(1)
    
    backend_url = sys.argv[1]
    frontend_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    tester = DeploymentTester(backend_url, frontend_url)
    
    # 运行测试
    try:
        results = asyncio.run(tester.run_all_tests())
        
        # 保存结果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deployment_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📝 Detailed results saved to: {filename}")
        
        # 退出码
        if results['failed'] == 0:
            print("\n🎉 All tests passed! Deployment looks good.")
            sys.exit(0)
        else:
            print(f"\n⚠️  {results['failed']} test(s) failed. Please check the issues above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()