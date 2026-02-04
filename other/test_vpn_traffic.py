import requests
import re
import json
import pandas as pd
import time
import base64
import yaml
from typing import Dict, List, Optional
from loguru import logger

# 配置日志
logger.add("vpn_traffic_test.log", rotation="1 day", retention="7 days", encoding="utf-8")

class ClashTrafficTester:
    """Clash X Pro 流量测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    def test_config_traffic(self, url: str) -> Dict:
        """测试Clash配置文件的剩余流量"""
        if not url:
            return {
                'success': False,
                'message': '没有提供配置文件链接',
                'traffic_info': {},
                'config_type': 'unknown'
            }
        
        try:
            # 先尝试从订阅服务器获取流量信息
            server_traffic = self._get_server_traffic_info(url)
            
            # 下载配置文件
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'配置文件下载失败，状态码: {response.status_code}',
                    'traffic_info': server_traffic if server_traffic else {},
                    'config_type': 'unknown'
                }
            
            # 检查配置文件类型
            config_content = response.text
            config_type = self._detect_config_type(config_content)
            
            if config_type == 'clash':
                # Clash 配置文件
                result = self._parse_clash_config(config_content)
            elif config_type == 'surge':
                # Surge 配置文件
                result = self._parse_surge_config(config_content)
            elif config_type == 'base64':
                # Base64 编码的配置文件
                result = self._parse_base64_config(config_content)
            elif config_type == 'v2ray':
                # V2Ray 配置文件
                result = self._parse_v2ray_config(config_content)
            else:
                # 未知类型，尝试直接解析
                result = self._parse_generic_config(config_content)
            
            # 合并服务器流量信息和配置文件流量信息
            if server_traffic:
                result['traffic_info'].update({k: v for k, v in server_traffic.items() if not result['traffic_info'].get(k)})
            
            return {
                **result,
                'success': True,
                'message': f'成功解析{config_type}类型配置文件',
                'config_type': config_type
            }
            
        except Exception as e:
            logger.error(f"测试配置文件流量时发生错误: {e}")
            return {
                'success': False,
                'message': str(e),
                'traffic_info': {},
                'config_type': 'unknown'
            }
    
    def _detect_config_type(self, content: str) -> str:
        """检测配置文件类型"""
        if not content:
            return 'unknown'
        
        content_lower = content.lower()
        
        # 检查是否为Base64编码
        if re.match(r'^[A-Za-z0-9+/]+={0,2}$', content.strip()):
            return 'base64'
        
        # 检查是否为Clash配置
        if 'proxies:' in content_lower or 'proxy-providers:' in content_lower:
            return 'clash'
        
        # 检查是否为Surge配置
        if 'proxies =' in content_lower or '[proxy]' in content_lower:
            return 'surge'
        
        # 检查是否为V2Ray配置
        if 'v2ray' in content_lower or 'vmess' in content_lower or 'trojan' in content_lower:
            return 'v2ray'
        
        # 检查是否为JSON格式
        try:
            json.loads(content)
            return 'json'
        except:
            pass
        
        # 检查是否为YAML格式
        try:
            yaml.safe_load(content)
            return 'yaml'
        except:
            pass
        
        return 'unknown'
    
    def _parse_clash_config(self, content: str) -> Dict:
        """解析Clash配置文件"""
        try:
            # 尝试解析YAML格式
            config = yaml.safe_load(content)
            
            traffic_info = {
                'total_traffic': None,
                'used_traffic': None,
                'remaining_traffic': None,
                'expire_time': None,
                'proxy_count': 0
            }
            
            # Clash X Pro 特殊处理
            if config:
                # 1. 检查proxy-providers（Clash X Pro支持的方式）
                if 'proxy-providers' in config:
                    proxy_providers = config['proxy-providers']
                    traffic_info['proxy_count'] = len(proxy_providers)
                    
                    # 检查每个provider的url是否包含流量信息
                    for name, provider in proxy_providers.items():
                        if 'url' in provider:
                            provider_url = provider['url']
                            # 从url中提取流量信息
                            url_traffic = self._extract_traffic_from_url(provider_url)
                            if url_traffic:
                                traffic_info.update(url_traffic)
                            
                            # 尝试从provider的url获取服务器流量信息
                            server_traffic = self._get_server_traffic_info(provider_url)
                            if server_traffic:
                                traffic_info.update(server_traffic)
            
            # 2. 检查proxies
            if 'proxies' in config:
                traffic_info['proxy_count'] = max(traffic_info['proxy_count'], len(config['proxies']))
            
            # 3. 检查Clash X Pro特有的信息
            # 检查mixed-port或port配置
            if config and ('mixed-port' in config or 'port' in config):
                traffic_info['clash_x_pro_supported'] = True
            
            # 4. 尝试从注释中提取流量信息
            # 搜索所有注释
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # 从注释行提取流量信息
                    comment_traffic = self._extract_traffic_from_comment(line)
                    if comment_traffic:
                        traffic_info.update(comment_traffic)
                        break
            
            # 5. 尝试从整个内容中提取流量信息
            content_traffic = self._extract_traffic_from_content(content)
            if content_traffic:
                traffic_info.update({k: v for k, v in content_traffic.items() if not traffic_info.get(k)})
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析Clash配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_surge_config(self, content: str) -> Dict:
        """解析Surge配置文件"""
        try:
            traffic_info = {
                'total_traffic': None,
                'used_traffic': None,
                'remaining_traffic': None,
                'expire_time': None,
                'proxy_count': 0
            }
            
            # 计数proxy数量
            proxies = re.findall(r'^[a-zA-Z0-9_-]+\s*=.*$', content, re.MULTILINE)
            traffic_info['proxy_count'] = len(proxies)
            
            # 从注释中提取流量信息
            comments = re.findall(r'#.*流量.*', content)
            if comments:
                for comment in comments:
                    comment_traffic = self._extract_traffic_from_comment(comment)
                    if comment_traffic:
                        traffic_info.update(comment_traffic)
                        break
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析Surge配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_base64_config(self, content: str) -> Dict:
        """解析Base64编码的配置文件"""
        try:
            # 解码Base64
            decoded_content = base64.b64decode(content).decode('utf-8', errors='ignore')
            
            # 重新检测类型
            config_type = self._detect_config_type(decoded_content)
            
            if config_type == 'clash':
                return self._parse_clash_config(decoded_content)
            elif config_type == 'surge':
                return self._parse_surge_config(decoded_content)
            elif config_type == 'v2ray':
                return self._parse_v2ray_config(decoded_content)
            else:
                return self._parse_generic_config(decoded_content)
                
        except Exception as e:
            logger.error(f"解析Base64配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_v2ray_config(self, content: str) -> Dict:
        """解析V2Ray配置文件"""
        try:
            # 尝试解析JSON
            try:
                config = json.loads(content)
                traffic_info = {
                    'total_traffic': None,
                    'used_traffic': None,
                    'remaining_traffic': None,
                    'expire_time': None,
                    'proxy_count': 1
                }
            except:
                # 不是JSON格式，可能是V2RayN格式
                traffic_info = {
                    'total_traffic': None,
                    'used_traffic': None,
                    'remaining_traffic': None,
                    'expire_time': None,
                    'proxy_count': 1
                }
            
            # 尝试从内容中提取流量信息
            traffic_info.update(self._extract_traffic_from_content(content))
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析V2Ray配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_generic_config(self, content: str) -> Dict:
        """解析通用配置文件"""
        traffic_info = {
            'total_traffic': None,
            'used_traffic': None,
            'remaining_traffic': None,
            'expire_time': None,
            'proxy_count': 0
        }
        
        # 尝试提取流量信息
        traffic_info.update(self._extract_traffic_from_content(content))
        
        return {'traffic_info': traffic_info}
    
    def _extract_traffic_from_content(self, content: str) -> Dict:
        """从配置文件内容中提取流量信息"""
        traffic_info = {}
        
        # 提取流量信息的正则表达式
        patterns = {
            'total_traffic': [
                r'总流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'total[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'used_traffic': [
                r'已用流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'used[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'remaining_traffic': [
                r'剩余流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'remaining[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'剩余[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'expire_time': [
                r'到期时间[:：]\s*([^\s]+)',
                r'expire[:：]\s*([^\s]+)',
                r'有效期[:：]\s*([^\s]+)'
            ]
        }
        
        for key, key_patterns in patterns.items():
            for pattern in key_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    traffic_info[key] = match.group(1).strip()
                    break
        
        return traffic_info
    
    def _extract_traffic_from_url(self, url: str) -> Dict:
        """从URL中提取流量信息"""
        traffic_info = {}
        
        # 检查URL中是否包含流量参数
        patterns = {
            'total_traffic': r'total=([\d.]+[TGMBK]?i?B?)',
            'used_traffic': r'used=([\d.]+[TGMBK]?i?B?)',
            'remaining_traffic': r'remaining=([\d.]+[TGMBK]?i?B?)',
            'expire_time': r'expire=([^&]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                traffic_info[key] = match.group(1)
        
        return traffic_info
    
    def _extract_traffic_from_comment(self, comment: str) -> Dict:
        """从注释中提取流量信息"""
        return self._extract_traffic_from_content(comment)
    
    def _get_server_traffic_info(self, url: str) -> Dict:
        """从订阅服务器获取流量信息"""
        traffic_info = {}
        
        try:
            from urllib.parse import urlparse, parse_qs
            
            # 解析URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
            
            # 检查常见的订阅服务器提供商
            if 'shadowrocket.live' in domain:
                # shadowrocket.live 服务器
                traffic_info = self._get_shadowrocket_traffic(url)
            elif 'vip16888.com' in domain:
                # vip16888.com 服务器
                traffic_info = self._get_vip16888_traffic(url)
            elif 'clash1688.com' in domain:
                # clash1688.com 服务器
                traffic_info = self._get_clash1688_traffic(url)
            elif 'malls1688.top' in domain:
                # malls1688.top 服务器
                traffic_info = self._get_malls1688_traffic(url)
            else:
                # 尝试通用方法
                traffic_info = self._get_generic_server_traffic(url)
            
        except Exception as e:
            logger.debug(f"从服务器获取流量信息失败: {e}")
        
        return traffic_info
    
    def _get_shadowrocket_traffic(self, url: str) -> Dict:
        """获取 shadowrocket.live 服务器的流量信息"""
        # shadowrocket.live 通常在订阅链接中包含流量信息
        return self._extract_traffic_from_url(url)
    
    def _get_vip16888_traffic(self, url: str) -> Dict:
        """获取 vip16888.com 服务器的流量信息"""
        traffic_info = {}
        
        try:
            # 尝试从URL路径中提取用户ID
            match = re.search(r'cla/([a-f0-9-]+)', url, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                # vip16888.com 的流量查询API
                api_url = f"https://www.vip16888.com/api/user/traffic?uuid={user_id}"
                response = self.session.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        traffic_info = {
                            'total_traffic': data.get('totalTraffic'),
                            'used_traffic': data.get('usedTraffic'),
                            'remaining_traffic': data.get('remainingTraffic'),
                            'expire_time': data.get('expireTime')
                        }
        except Exception as e:
            logger.debug(f"获取 vip16888.com 流量信息失败: {e}")
        
        return traffic_info
    
    def _get_clash1688_traffic(self, url: str) -> Dict:
        """获取 clash1688.com 服务器的流量信息"""
        # clash1688.com 通常在配置文件中包含流量信息
        return {}
    
    def _get_malls1688_traffic(self, url: str) -> Dict:
        """获取 malls1688.top 服务器的流量信息"""
        # malls1688.top 通常在URL中包含流量信息
        return self._extract_traffic_from_url(url)
    
    def _get_generic_server_traffic(self, url: str) -> Dict:
        """获取通用服务器的流量信息"""
        traffic_info = {}
        
        try:
            # 尝试解析常见的流量参数格式
            params = re.findall(r'([^=&]+)=([^=&]+)', url)
            param_dict = dict(params)
            
            # 检查常见的流量参数
            traffic_mapping = {
                'total': 'total_traffic',
                'used': 'used_traffic',
                'remaining': 'remaining_traffic',
                'expire': 'expire_time',
                'traffic': 'total_traffic',
                'data': 'total_traffic'
            }
            
            for param, key in traffic_mapping.items():
                if param in param_dict:
                    traffic_info[key] = param_dict[param]
            
        except Exception as e:
            logger.debug(f"获取通用服务器流量信息失败: {e}")
        
        return traffic_info
    
    def batch_test_traffic(self, config_urls: List[str]) -> List[Dict]:
        """批量测试配置文件流量"""
        results = []
        
        for i, url in enumerate(config_urls):
            logger.info(f"正在测试第 {i+1}/{len(config_urls)} 个配置文件: {url}")
            result = self.test_config_traffic(url)
            
            # 检查是否为Clash X Pro格式
            is_clash_x_pro = result['traffic_info'].get('clash_x_pro_supported', False)
            
            # 生成结果
            result_dict = {
                '序号': i+1,
                '配置文件链接': url,
                '测试结果': '成功' if result['success'] else '失败',
                '配置类型': result['config_type'],
                '支持Clash X Pro': '是' if is_clash_x_pro else '否',
                '总流量': result['traffic_info'].get('total_traffic', '配置文件中未包含'),
                '已用流量': result['traffic_info'].get('used_traffic', '配置文件中未包含'),
                '剩余流量': result['traffic_info'].get('remaining_traffic', '配置文件中未包含'),
                '到期时间': result['traffic_info'].get('expire_time', '配置文件中未包含'),
                '节点数量': result['traffic_info'].get('proxy_count', 0),
                '测试信息': result['message']
            }
            
            # 检查是否为Clash格式
            if result['config_type'] == 'clash':
                result_dict['测试说明'] = 'Clash配置文件本身不包含流量信息，流量数据通常存储在服务器端，需要通过认证API获取'
            
            results.append(result_dict)
            
            # 等待一段时间避免被封禁
            time.sleep(1)
        
        return results

def main():
    """主函数"""
    # 测试用的VPN配置文件链接
    test_configs = [
        "http://shadowrocket.live/N/E/26858fd4-2930-4b5e-a86c-614a560d477c",
        "http://shadowrocket.live/N/E/e4a532c7-a2e2-47db-bbc9-058bdef04acd",
        "http://shadowrocket.live/N/E/F7E3E61B-FF3B-4D4B-9509-5FAC8F853AE8",
        "http://www.malls1688.top/N/E/7fe48b63-f263-4343-817f-5848dfde4fbd",
        "http://www.clash1688.com/N/E/4e090eba-25ad-4ab9-be3a-0140455b1404",
        "https://www.vip16888.com/cla/4a8b8bab-dcf3-42c9-b7df-0bad9f86062a"
    ]
    
    # 创建测试器
    tester = ClashTrafficTester()
    
    # 批量测试配置文件流量
    logger.info(f"开始批量测试 {len(test_configs)} 个配置文件的流量信息...")
    results = tester.batch_test_traffic(test_configs)
    
    # 统计结果
    success_count = sum(1 for r in results if r['测试结果'] == '成功')
    total_count = len(results)
    
    logger.info(f"\n测试完成！")
    logger.info(f"总测试配置文件数: {total_count}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {total_count - success_count}")
    logger.info(f"成功率: {success_count/total_count*100:.2f}%")
    
    # 将结果保存到CSV文件
    df = pd.DataFrame(results)
    output_file = 'vpn_config_traffic_test_results.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 打印详细结果
    print("\n" + "="*80)
    print("VPN配置文件流量测试结果汇总")
    print("="*80)
    
    for result in results:
        status = "✅" if result['测试结果'] == '成功' else "❌"
        print(f"{status} 序号: {result['序号']} | 类型: {result['配置类型']}")
        print(f"   Clash X Pro支持: {result['支持Clash X Pro']}")
        print(f"   总流量: {result['总流量']}")
        print(f"   已用流量: {result['已用流量']}")
        print(f"   剩余流量: {result['剩余流量']}")
        print(f"   到期时间: {result['到期时间']}")
        print(f"   节点数量: {result['节点数量']}")
        if '测试说明' in result:
            print(f"   测试说明: {result['测试说明']}")
        print(f"   配置链接: {result['配置文件链接'][:50]}...")
        print("-"*80)
    
    print("\n" + "="*80)
    print("测试说明:")
    print("1. 本测试使用Clash X Pro风格解析配置文件流量信息")
    print("2. 支持Clash、Surge、V2Ray等多种配置格式")
    print("3. 流量信息来源于配置文件内容或URL参数")
    print("4. Clash配置文件本身通常不包含流量信息，流量数据存储在服务器端")
    print("5. 要获取准确的流量信息，需要使用Clash X Pro客户端或服务器提供的API")
    print("="*80)

if __name__ == "__main__":
    main()
