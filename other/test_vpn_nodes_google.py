import requests
import yaml
import time
from loguru import logger
from typing import List, Dict, Tuple

# 配置日志
logger.add("vpn_nodes_google_test.log", rotation="1 day", retention="7 days", encoding="utf-8")

class VPNNodeTester:
    """VPN节点测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def download_config(self, config_url: str) -> str:
        """下载配置文件"""
        try:
            response = requests.get(config_url, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                logger.info(f"成功下载配置文件: {config_url}")
                return response.text
            else:
                logger.error(f"配置文件下载失败，状态码: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"下载配置文件时发生错误: {e}")
            return ""
    
    def parse_clash_config(self, config_content: str) -> List[Dict]:
        """解析Clash配置文件，提取代理节点"""
        proxies = []
        
        try:
            config = yaml.safe_load(config_content)
            
            if 'proxies' in config:
                for proxy in config['proxies']:
                    proxies.append(proxy)
            
            # 检查proxy-providers
            if 'proxy-providers' in config:
                for name, provider in config['proxy-providers'].items():
                    if 'url' in provider:
                        # 下载provider配置
                        provider_content = self.download_config(provider['url'])
                        if provider_content:
                            provider_config = yaml.safe_load(provider_content)
                            if 'proxies' in provider_config:
                                proxies.extend(provider_config['proxies'])
            
            logger.info(f"成功解析 {len(proxies)} 个代理节点")
            return proxies
            
        except Exception as e:
            logger.error(f"解析Clash配置文件失败: {e}")
            return []
    
    def test_proxy_node(self, proxy: Dict) -> Tuple[bool, str, float]:
        """测试单个代理节点是否可以访问google.com"""
        proxy_type = proxy.get('type', '')
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        username = proxy.get('username', '')
        password = proxy.get('password', '')
        name = proxy.get('name', '')
        
        if not server or not port:
            return False, '缺少服务器或端口信息', 0.0
        
        # 检查节点名称中的特殊信息
        node_name = proxy.get('name', '')
        if '到期' in node_name or '流量用完' in node_name:
            return False, '节点已到期或流量已用完（从节点名称判断）', 0.0
        
        start_time = time.time()
        
        try:
            # 设置代理连接
            if proxy_type == 'ss':
                # Shadowsocks代理
                result, message = self._test_shadowsocks_proxy(proxy)
            elif proxy_type == 'vmess':
                # V2Ray代理
                result, message = self._test_vmess_proxy(proxy)
            elif proxy_type == 'trojan':
                # Trojan代理
                result, message = self._test_trojan_proxy(proxy)
            elif proxy_type == 'http' or proxy_type == 'https':
                # HTTP/HTTPS代理
                result, message = self._test_http_proxy(proxy)
            elif proxy_type == 'vless':
                # VLESS代理（Clash X Pro支持）
                return False, 'VLESS代理需要使用Clash X Pro或V2Ray客户端测试', 0.0
            else:
                return False, f'不支持的代理类型: {proxy_type}', 0.0
            
            response_time = time.time() - start_time
            return result, message, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"测试节点 {name} 时发生错误: {e}")
            return False, str(e), response_time
    
    def _test_shadowsocks_proxy(self, proxy: Dict) -> Tuple[bool, str]:
        """测试Shadowsocks代理"""
        # 这里需要shadowsocks库，暂时返回不支持
        return False, 'Shadowsocks代理测试需要安装shadowsocks库', 0.0
    
    def _test_vmess_proxy(self, proxy: Dict) -> Tuple[bool, str]:
        """测试V2Ray代理"""
        # 这里需要v2ray库，暂时返回不支持
        return False, 'V2Ray代理测试需要安装v2ray库', 0.0
    
    def _test_trojan_proxy(self, proxy: Dict) -> Tuple[bool, str]:
        """测试Trojan代理"""
        # 这里需要trojan库，暂时返回不支持
        return False, 'Trojan代理测试需要安装trojan库', 0.0
    
    def _test_http_proxy(self, proxy: Dict) -> Tuple[bool, str]:
        """测试HTTP/HTTPS代理"""
        proxy_type = proxy.get('type', 'http')
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        username = proxy.get('username', '')
        password = proxy.get('password', '')
        
        try:
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{server}:{port}"
            else:
                proxy_url = f"{proxy_type}://{server}:{port}"
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试访问google.com
            response = self.session.get('http://www.google.com', proxies=proxies, timeout=10)
            
            if response.status_code == 200:
                return True, f'HTTP代理测试成功，状态码: {response.status_code}'
            else:
                return False, f'HTTP代理测试失败，状态码: {response.status_code}'
                
        except Exception as e:
            return False, f'HTTP代理测试失败: {str(e)}'
    
    def test_all_nodes(self, config_url: str) -> List[Dict]:
        """测试配置文件中的所有节点"""
        results = []
        
        # 下载配置文件
        config_content = self.download_config(config_url)
        if not config_content:
            logger.error("配置文件内容为空，无法测试节点")
            return results
        
        # 解析配置文件
        proxies = self.parse_clash_config(config_content)
        if not proxies:
            logger.error("没有找到代理节点，无法测试")
            return results
        
        # 测试每个节点
        for i, proxy in enumerate(proxies):
            proxy_name = proxy.get('name', f'节点{i+1}')
            proxy_type = proxy.get('type', 'unknown')
            
            logger.info(f"正在测试第 {i+1}/{len(proxies)} 个节点: {proxy_name} ({proxy_type})")
            
            success, message, response_time = self.test_proxy_node(proxy)
            
            result = {
                '序号': i+1,
                '节点名称': proxy_name,
                '代理类型': proxy_type,
                '服务器': proxy.get('server', ''),
                '端口': proxy.get('port', 0),
                '测试结果': '成功' if success else '失败',
                '响应时间': f'{response_time:.2f}秒' if response_time > 0 else '0秒',
                '测试信息': message
            }
            
            results.append(result)
            
            # 等待一段时间避免被封禁
            time.sleep(0.5)
        
        return results

def main():
    """主函数"""
    # 配置文件链接（来自Terminal#529-529）
    config_url = "https://www.vip16888.com/cla/b2b1d892-14d4-48e7-a99e-1e19b130c0bd"
    
    # 创建测试器
    tester = VPNNodeTester()
    
    # 测试所有节点
    logger.info(f"开始测试配置文件中的所有节点: {config_url}")
    results = tester.test_all_nodes(config_url)
    
    # 统计结果
    total_count = len(results)
    success_count = sum(1 for r in results if r['测试结果'] == '成功')
    
    logger.info(f"\n测试完成！")
    logger.info(f"总测试节点数: {total_count}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {total_count - success_count}")
    logger.info(f"成功率: {success_count/total_count*100:.2f}%")
    
    # 打印详细结果
    print("\n" + "="*80)
    print("VPN节点Google访问测试结果汇总")
    print("="*80)
    
    for result in results:
        status = "✅" if result['测试结果'] == '成功' else "❌"
        print(f"{status} 序号: {result['序号']} | 名称: {result['节点名称']}")
        print(f"   类型: {result['代理类型']} | 服务器: {result['服务器']}:{result['端口']}")
        print(f"   响应时间: {result['响应时间']}")
        print(f"   测试结果: {result['测试结果']} | 信息: {result['测试信息']}")
        print("-"*80)
    
    print("\n" + "="*80)
    print("测试说明:")
    print("1. 本测试检查VPN节点是否可以访问google.com")
    print("2. 支持HTTP/HTTPS代理直接测试")
    print("3. Shadowsocks、V2Ray等代理需要额外安装相应库")
    print("4. 测试结果包含节点信息、响应时间和详细状态")
    print("="*80)

if __name__ == "__main__":
    main()
